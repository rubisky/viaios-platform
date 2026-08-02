"""
Policy Engine — Independent RBAC + ABAC policy evaluation.

Manages: policy rules, policy evaluation, policy simulation,
conflict detection, audit trail. Separates policy logic from enforcement.
"""
import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY  = "deny"

@dataclass
class PolicyRule:
    id: str = field(default_factory=lambda: f"pol-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    effect: PolicyEffect = PolicyEffect.DENY
    conditions: Dict[str, Any] = field(default_factory=dict)  # attribute → expected value
    match_expression: str = ""     # Python expression or "*" for all
    applies_to: List[str] = field(default_factory=lambda: ["*"])  # services/agents
    priority: int = 0              # higher = evaluated first
    enabled: bool = True

@dataclass
class PolicyDecision:
    allowed: bool
    matched_rules: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    audit_id: str = ""

@dataclass
class PolicyContext:
    subject: str = ""       # user/agent
    action: str = ""        # what they're trying to do
    resource: str = ""      # target resource
    attributes: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Independent policy evaluation engine."""

    def __init__(self):
        self._rules: List[PolicyRule] = []
        self._lock = threading.Lock()
        self._audit: List[Dict] = []
        self._register_defaults()

    def add_rule(self, rule: PolicyRule):
        with self._lock:
            self._rules.append(rule)
            self._rules.sort(key=lambda r: -r.priority)

    def remove_rule(self, rule_id: str):
        with self._lock:
            self._rules = [r for r in self._rules if r.id != rule_id]

    def evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        """Evaluate all policies against a context. DENY takes precedence."""
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        matched = []
        reasons = []
        final_effect = PolicyEffect.ALLOW

        with self._lock:
            for rule in self._rules:
                if not rule.enabled:
                    continue
                if not self._applies_to(rule, ctx.subject):
                    continue
                if not self._matches(rule, ctx):
                    continue

                matched.append(rule.id)
                reasons.append(f"{rule.id}: {rule.name}")

                if rule.effect == PolicyEffect.DENY:
                    final_effect = PolicyEffect.DENY
                    break  # DENY wins immediately

        allowed = final_effect == PolicyEffect.ALLOW
        decision = PolicyDecision(allowed=allowed, matched_rules=matched,
                                 reasons=reasons, audit_id=audit_id)

        self._audit.append({
            "audit_id": audit_id, "subject": ctx.subject,
            "action": ctx.action, "resource": ctx.resource,
            "allowed": allowed, "rules": matched,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return decision

    def simulate(self, ctx: PolicyContext) -> List[Dict]:
        """Simulate: show which rules WOULD match without enforcing."""
        with self._lock:
            results = []
            for rule in self._rules:
                if not rule.enabled: continue
                applies = self._applies_to(rule, ctx.subject)
                matches = self._matches(rule, ctx) if applies else False
                results.append({
                    "rule_id": rule.id, "name": rule.name,
                    "applies": applies, "matches": matches,
                    "effect": rule.effect.value if matches else "N/A",
                })
            return results

    def list_rules(self) -> List[Dict]:
        with self._lock:
            return [
                {"id": r.id, "name": r.name, "effect": r.effect.value,
                 "enabled": r.enabled, "priority": r.priority,
                 "applies_to": r.applies_to}
                for r in self._rules
            ]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules if r.enabled),
            "audit_entries": len(self._audit),
            "by_effect": {
                "allow": sum(1 for r in self._rules if r.effect == PolicyEffect.ALLOW),
                "deny": sum(1 for r in self._rules if r.effect == PolicyEffect.DENY),
            },
            "recent_decisions": [
                {"subject": a["subject"], "action": a["action"], "allowed": a["allowed"]}
                for a in self._audit[-20:]
            ],
        }

    # ── Internal ────────────────────────────────────────────────

    def _matches(self, rule: PolicyRule, ctx: PolicyContext) -> bool:
        if rule.match_expression and rule.match_expression != "*":
            try:
                env = {"subject": ctx.subject, "action": ctx.action,
                      "resource": ctx.resource, "attr": ctx.attributes}
                return bool(eval(rule.match_expression, {"__builtins__": {}}, env))
            except Exception:
                return False
        # Attribute-based matching
        for attr, expected in rule.conditions.items():
            actual = ctx.attributes.get(attr)
            if callable(expected):
                if not expected(actual): return False
            elif actual != expected:
                return False
        return True

    def _applies_to(self, rule: PolicyRule, subject: str) -> bool:
        if "*" in rule.applies_to:
            return True
        return any(pattern in subject or subject in pattern
                  for pattern in rule.applies_to)

    def _register_defaults(self):
        """Register baseline security policies."""
        defaults = [
            PolicyRule(name="admin_full_access", effect=PolicyEffect.ALLOW,
                       applies_to=["ADMIN"], match_expression="'*' == '*'", priority=100,
                       description="Administrators have full access"),
            PolicyRule(name="viewer_read_only", effect=PolicyEffect.DENY,
                       applies_to=["VIEWER"],
                       match_expression="'write' in action or 'delete' in action or 'deploy' in action",
                       priority=90,
                       description="Viewers cannot write, delete, or deploy"),
            PolicyRule(name="no_cross_tenant", effect=PolicyEffect.DENY,
                       applies_to=["*"],
                       match_expression="attr.get('tenant_id') and attr.get('tenant_id') != attr.get('request_tenant')",
                       priority=95,
                       description="Cross-tenant access is prohibited"),
            PolicyRule(name="rate_limit_high_freq", effect=PolicyEffect.DENY,
                       applies_to=["search-agent"],
                       match_expression="attr.get('rate_1m', 0) > 100",
                       priority=80,
                       description="Rate limit: 100 req/min for search"),
        ]
        for rule in defaults:
            self.add_rule(rule)


_policy_engine: Optional[PolicyEngine] = None

def get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine

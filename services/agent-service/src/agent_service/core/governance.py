"""
Agent Governance — P1-4
Safety and policy enforcement for agent behavior.

The Governance module is the "guardrails" layer that ensures:
1. Rate limiting per agent/user/tenant
2. Content policy enforcement
3. Permission checks for sensitive operations
4. Audit logging for compliance
5. Cost control (token budgets, model tier enforcement)
"""
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── Domain Types ───────────────────────────────────────────────────

class PolicyAction(Enum):
    ALLOW      = "allow"
    DENY       = "deny"
    FLAG       = "flag"         # Allow but flag for review
    QUARANTINE = "quarantine"   # Allow but isolate output
    THROTTLE   = "throttle"     # Slow down

class Severity(Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"

@dataclass
class PolicyRule:
    """A single governance policy rule."""
    rule_id: str
    name: str
    description: str
    condition: str              # Python expression
    action: PolicyAction
    severity: Severity = Severity.WARNING
    applies_to: List[str] = field(default_factory=lambda: ["*"])  # agent types
    exempt_roles: List[str] = field(default_factory=list)

@dataclass
class PolicyDecision:
    """Result of evaluating governance policies."""
    allowed: bool
    action: PolicyAction
    triggered_rules: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    quarantine_id: Optional[str] = None
    audit_entry: Optional[Dict] = None

@dataclass
class RateLimitState:
    """Rate limit tracking for an entity."""
    window_start: float = 0.0
    count: int = 0
    tokens_used: int = 0

@dataclass
class GovernanceContext:
    """Context for governance policy evaluation."""
    agent_id: str
    agent_type: str
    user_id: str
    tenant_id: str
    role: str                      # ADMIN, OPERATOR, VIEWER
    action: str                    # search, analyze, report, deploy, etc.
    resource: Optional[str] = None # Target resource
    params: Dict[str, Any] = field(default_factory=dict)
    estimated_tokens: int = 0


# ── Governance Engine ──────────────────────────────────────────────

class GovernanceEngine:
    """
    Policy enforcement and guardrails for the Agent OS.

    Usage:
        gov = GovernanceEngine()
        ctx = GovernanceContext(agent_id="search-agent", ...)
        decision = gov.evaluate(ctx)
        if not decision.allowed:
            raise PolicyViolationError(decision.reasons)
    """

    # Default policies
    DEFAULT_POLICIES = [
        PolicyRule(
            rule_id="POL-001", name="rate_limit_per_minute",
            description="Rate limit: max 60 requests/min per agent",
            condition="rate_1m > 60",
            action=PolicyAction.THROTTLE, severity=Severity.WARNING,
        ),
        PolicyRule(
            rule_id="POL-002", name="token_budget",
            description="Token budget: max 100K tokens per session",
            condition="tokens_used > 100000",
            action=PolicyAction.DENY, severity=Severity.ERROR,
        ),
        PolicyRule(
            rule_id="POL-003", name="no_admin_without_role",
            description="Only ADMIN role can perform system operations",
            condition="action.startswith('admin_') and role != 'ADMIN'",
            action=PolicyAction.DENY, severity=Severity.CRITICAL,
        ),
        PolicyRule(
            rule_id="POL-004", name="content_safety_filter",
            description="Block known harmful prompt patterns",
            condition="'ignore_previous' in prompt or 'jailbreak' in prompt",
            action=PolicyAction.DENY, severity=Severity.CRITICAL,
        ),
        PolicyRule(
            rule_id="POL-005", name="sensitive_data_mask",
            description="Flag outputs containing potential PII",
            condition="contains_pii(output)",
            action=PolicyAction.QUARANTINE, severity=Severity.WARNING,
        ),
        PolicyRule(
            rule_id="POL-006", name="cost_control_tier1",
            description="VIEWER role cannot use expensive models",
            condition="role == 'VIEWER' and model_tier == 'premium'",
            action=PolicyAction.DENY, severity=Severity.ERROR,
        ),
        PolicyRule(
            rule_id="POL-007", name="deployment_approval",
            description="Model deployment requires explicit approval",
            condition="action in ('deploy_model', 'hot_swap') and not approved",
            action=PolicyAction.DENY, severity=Severity.CRITICAL,
        ),
        PolicyRule(
            rule_id="POL-008", name="cross_tenant_isolation",
            description="Tenants cannot access other tenants' resources",
            condition="resource_tenant and resource_tenant != tenant_id",
            action=PolicyAction.DENY, severity=Severity.CRITICAL,
        ),
    ]

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.policies: List[PolicyRule] = list(self.DEFAULT_POLICIES)
        self._rate_limits: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._token_usage: Dict[str, int] = defaultdict(int)
        self._audit_log: List[Dict] = []
        self._lock = threading.Lock()
        self._approval_queue: Dict[str, bool] = {}

    # ── Policy Evaluation ───────────────────────────────────────

    def evaluate(self, ctx: GovernanceContext,
                 output: Optional[Any] = None) -> PolicyDecision:
        """Evaluate all governance policies against a context."""
        triggered = []
        reasons = []
        final_action = PolicyAction.ALLOW

        # Build evaluation environment
        env = self._build_env(ctx, output)

        for policy in self.policies:
            # Check if policy applies to this agent type
            if "*" not in policy.applies_to and ctx.agent_type not in policy.applies_to:
                continue
            # Check exemption
            if ctx.role in policy.exempt_roles:
                continue

            try:
                if eval(policy.condition, {"__builtins__": {}}, env):
                    triggered.append(policy.rule_id)
                    reasons.append(f"{policy.rule_id}: {policy.description}")
                    # Escalate to most severe action
                    if self._action_severity(policy.action) > self._action_severity(final_action):
                        final_action = policy.action

                    if policy.action == PolicyAction.DENY:
                        break  # Hard stop on deny
            except Exception as e:
                logger.debug("Policy %s eval error: %s", policy.rule_id, e)

        decision = PolicyDecision(
            allowed=final_action != PolicyAction.DENY,
            action=final_action,
            triggered_rules=triggered,
            reasons=reasons,
        )

        # For quarantine, generate a tracking ID
        if final_action == PolicyAction.QUARANTINE:
            decision.quarantine_id = f"quarantine-{int(time.time())}"

        # Audit log
        decision.audit_entry = self._audit(ctx, decision)

        if triggered:
            logger.info("Governance: %s rules triggered for %s/%s [%s]",
                       len(triggered), ctx.agent_type, ctx.action, final_action.value)

        return decision

    def evaluate_pre(self, ctx: GovernanceContext) -> PolicyDecision:
        """Pre-execution check (before agent runs)."""
        return self.evaluate(ctx)

    def evaluate_post(self, ctx: GovernanceContext,
                      output: Any) -> PolicyDecision:
        """Post-execution check (after agent produces output)."""
        decision = self.evaluate(ctx, output)

        # Enforce quarantine
        if decision.action == PolicyAction.QUARANTINE:
            logger.warning("Output quarantined: %s", decision.quarantine_id)

        return decision

    # ── Rate Limiting ───────────────────────────────────────────

    def check_rate_limit(self, key: str, max_per_minute: int = 60) -> Tuple[bool, int]:
        """Check if rate limit is exceeded. Returns (allowed, remaining)."""
        with self._lock:
            now = time.time()
            state = self._rate_limits[key]

            # Reset window if needed
            if now - state.window_start > 60:
                state.window_start = now
                state.count = 0

            state.count += 1
            remaining = max(0, max_per_minute - state.count)

            if state.count > max_per_minute:
                return False, 0

            return True, remaining

    def track_tokens(self, key: str, tokens: int):
        """Track token usage for budget enforcement."""
        with self._lock:
            self._token_usage[key] += tokens

    def get_token_usage(self, key: str) -> int:
        return self._token_usage.get(key, 0)

    # ── Approval Workflow ───────────────────────────────────────

    def request_approval(self, action: str, requester: str,
                         details: Dict) -> str:
        """Request human approval for a sensitive action."""
        approval_id = f"approval-{int(time.time())}"
        self._approval_queue[approval_id] = False
        logger.info("Approval requested: %s by %s for %s", approval_id, requester, action)
        return approval_id

    def approve(self, approval_id: str):
        """Grant approval for a pending action."""
        self._approval_queue[approval_id] = True
        logger.info("Approval granted: %s", approval_id)

    def is_approved(self, approval_id: str) -> bool:
        return self._approval_queue.get(approval_id, False)

    # ── Audit ───────────────────────────────────────────────────

    def _audit(self, ctx: GovernanceContext,
               decision: PolicyDecision) -> Dict:
        """Create an audit log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": ctx.agent_id,
            "agent_type": ctx.agent_type,
            "user_id": ctx.user_id,
            "tenant_id": ctx.tenant_id,
            "role": ctx.role,
            "action": ctx.action,
            "resource": ctx.resource,
            "decision": decision.action.value,
            "allowed": decision.allowed,
            "triggered_rules": decision.triggered_rules,
        }
        self._audit_log.append(entry)
        return entry

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]

    def get_audit_for_agent(self, agent_id: str) -> List[Dict]:
        """Get audit entries for a specific agent."""
        return [e for e in self._audit_log if e["agent_id"] == agent_id]

    # ── Policy Management ───────────────────────────────────────

    def add_policy(self, rule: PolicyRule):
        """Add a custom governance policy."""
        self.policies.append(rule)
        logger.info("Policy added: %s", rule.rule_id)

    def remove_policy(self, rule_id: str):
        """Remove a governance policy."""
        self.policies = [p for p in self.policies if p.rule_id != rule_id]
        logger.info("Policy removed: %s", rule_id)

    def list_policies(self) -> List[Dict]:
        """List all active policies."""
        return [
            {"rule_id": p.rule_id, "name": p.name, "action": p.action.value,
             "severity": p.severity.value, "description": p.description}
            for p in self.policies
        ]

    def stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            "total_policies": len(self.policies),
            "active_rate_limits": len(self._rate_limits),
            "total_token_usage": sum(self._token_usage.values()),
            "audit_entries": len(self._audit_log),
            "pending_approvals": sum(1 for v in self._approval_queue.values() if not v),
            "denied_actions": sum(1 for e in self._audit_log if not e["allowed"]),
        }

    # ── Internal ────────────────────────────────────────────────

    def _build_env(self, ctx: GovernanceContext,
                   output: Any = None) -> Dict[str, Any]:
        """Build evaluation environment for policy conditions."""
        key = f"{ctx.tenant_id}:{ctx.agent_type}"
        rate_state = self._rate_limits[key]

        return {
            "agent_type": ctx.agent_type,
            "role": ctx.role,
            "action": ctx.action,
            "tenant_id": ctx.tenant_id,
            "user_id": ctx.user_id,
            "prompt": str(ctx.params.get("prompt", "")).lower(),
            "model_tier": ctx.params.get("model", "standard"),
            "approved": ctx.params.get("approved", False),
            "resource_tenant": ctx.params.get("tenant_id"),
            "rate_1m": rate_state.count,
            "tokens_used": self._token_usage.get(key, 0),
            "output": str(output or ""),
            "contains_pii": lambda s: self._check_pii(str(s)),
        }

    def _check_pii(self, text: str) -> bool:
        """Check for potential PII patterns."""
        import re
        patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b', r'\b\d{16}\b',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ]
        return any(re.search(p, text) for p in patterns)

    def _action_severity(self, action: PolicyAction) -> int:
        """Map action to severity level for escalation."""
        return {PolicyAction.ALLOW: 0, PolicyAction.FLAG: 1,
                PolicyAction.THROTTLE: 2, PolicyAction.QUARANTINE: 3,
                PolicyAction.DENY: 4}.get(action, 0)


# ── Error Types ────────────────────────────────────────────────────

class PolicyViolationError(Exception):
    """Raised when a governance policy is violated."""
    def __init__(self, reasons: List[str], decision: Optional[PolicyDecision] = None):
        super().__init__("; ".join(reasons))
        self.reasons = reasons
        self.decision = decision


# ── Convenience ────────────────────────────────────────────────────

_governance: Optional[GovernanceEngine] = None


def get_governance() -> GovernanceEngine:
    global _governance
    if _governance is None:
        _governance = GovernanceEngine()
    return _governance

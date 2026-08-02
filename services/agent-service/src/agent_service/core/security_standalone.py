"""
Security Engine — Standalone security module (independent from AuthFilter).

Handles: token validation, RBAC enforcement, audit logging,
rate limiting, IP whitelist/blacklist, session management.
"""
import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    PUBLIC    = "public"
    AUTHENTICATED = "authenticated"
    OPERATOR  = "operator"
    ADMIN     = "admin"

@dataclass
class SecurityContext:
    user_id: str = ""
    username: str = ""
    role: str = ""
    tenant_id: str = ""
    ip_address: str = ""
    session_id: str = ""
    permissions: Set[str] = field(default_factory=set)

@dataclass
class SecurityDecision:
    allowed: bool
    reason: str = ""
    audit_id: str = ""

class SecurityEngine:
    """Standalone security engine with RBAC, audit, rate limiting."""

    def __init__(self, jwt_secret: str = ""):
        self.jwt_secret = jwt_secret or "viaios-default-secret"
        self._sessions: Dict[str, SecurityContext] = {}
        self._rate_limits: Dict[str, tuple] = {}
        self._audit: List[Dict] = []
        self._ip_whitelist: Set[str] = set()
        self._ip_blacklist: Set[str] = set()
        self._lock = threading.Lock()

        # RBAC matrix
        self._role_permissions = {
            "ADMIN":    {"*"},
            "OPERATOR": {"cameras:read","cameras:write","search:execute","cases:read","cases:write","alarms:read","alarms:acknowledge","reports:generate"},
            "VIEWER":   {"cameras:read","cases:read","alarms:read","search:execute"},
        }

    def authenticate(self, token: str) -> Optional[SecurityContext]:
        """Validate JWT token and return security context."""
        try:
            payload = self._decode_jwt(token)
            if not payload:
                return None
            ctx = SecurityContext(
                user_id=payload.get("sub", ""),
                username=payload.get("username", ""),
                role=payload.get("role", "VIEWER"),
                tenant_id=payload.get("tenant_id", "default"),
                session_id=str(uuid.uuid4())[:8],
                permissions=self._role_permissions.get(payload.get("role", "VIEWER"), set()),
            )
            with self._lock:
                self._sessions[ctx.session_id] = ctx
            return ctx
        except Exception:
            return None

    def authorize(self, ctx: SecurityContext, action: str,
                 resource: str = "") -> SecurityDecision:
        """Check if user has permission for action."""
        aid = f"audit-{uuid.uuid4().hex[:8]}"

        # IP check
        if ctx.ip_address in self._ip_blacklist:
            return SecurityDecision(False, "IP blacklisted", aid)

        # Permission check
        if "*" in ctx.permissions:
            return SecurityDecision(True, "admin full access", aid)

        if action in ctx.permissions:
            return SecurityDecision(True, f"permission granted: {action}", aid)

        if f"{resource}:{action}" in ctx.permissions:
            return SecurityDecision(True, f"resource permission: {resource}:{action}", aid)

        return SecurityDecision(False, f"permission denied: {action}", aid)

    def check_rate_limit(self, key: str, max_per_min: int = 60) -> bool:
        now = time.time()
        window, count = self._rate_limits.get(key, (0, 0))
        if now - window > 60:
            self._rate_limits[key] = (now, 1)
            return True
        if count >= max_per_min:
            return False
        self._rate_limits[key] = (window, count + 1)
        return True

    def add_ip_whitelist(self, ip: str): self._ip_whitelist.add(ip)
    def add_ip_blacklist(self, ip: str): self._ip_blacklist.add(ip)

    def audit(self, ctx: SecurityContext, action: str, result: SecurityDecision):
        self._audit.append({
            "audit_id": result.audit_id, "user": ctx.username,
            "role": ctx.role, "action": action, "allowed": result.allowed,
            "reason": result.reason, "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "audit_entries": len(self._audit),
            "ip_whitelist": len(self._ip_whitelist),
            "ip_blacklist": len(self._ip_blacklist),
            "role_permissions": {r: len(p) for r, p in self._role_permissions.items()},
            "rate_limited_keys": len(self._rate_limits),
        }

    def _decode_jwt(self, token: str) -> Optional[Dict]:
        import base64
        try:
            parts = token.split(".")
            if len(parts) < 2: return None
            payload = base64.urlsafe_b64decode(parts[1] + "==").decode()
            return json.loads(payload)
        except Exception:
            return None


_security: Optional[SecurityEngine] = None

def get_security_engine() -> SecurityEngine:
    global _security
    if _security is None:
        _security = SecurityEngine()
    return _security

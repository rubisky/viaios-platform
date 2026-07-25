"""AI Kernel Security Engine — RBAC, Audit, Policy Enforcement."""
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Permission(Enum):
    # Camera
    CAMERA_VIEW = "camera:view"
    CAMERA_MANAGE = "camera:manage"
    CAMERA_STREAM = "camera:stream"
    # Search
    SEARCH_EXECUTE = "search:execute"
    SEARCH_EXPORT = "search:export"
    # Cases
    CASE_VIEW = "case:view"
    CASE_CREATE = "case:create"
    CASE_MANAGE = "case:manage"
    # Alarms
    ALARM_VIEW = "alarm:view"
    ALARM_ACKNOWLEDGE = "alarm:acknowledge"
    ALARM_RESOLVE = "alarm:resolve"
    # Reports
    REPORT_VIEW = "report:view"
    REPORT_GENERATE = "report:generate"
    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_ROLES = "admin:roles"
    ADMIN_SYSTEM = "admin:system"


class AuditEventType(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    API_ACCESS = "api_access"
    CASE_CREATED = "case_created"
    ALARM_TRIGGERED = "alarm_triggered"
    SEARCH_EXECUTED = "search_executed"
    CONFIG_CHANGED = "config_changed"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class AuditRecord:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: str = ""
    user: str = "anonymous"
    action: str = ""
    resource: str = ""
    result: str = "success"  # success, denied, error
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: str(v) if isinstance(v, Enum) else v for k, v in self.__dict__.items()}


class SecurityManager:
    """Manages authentication, authorization, and audit logging."""

    def __init__(self):
        self._roles: Dict[str, List[str]] = {
            "ADMIN": [p.value for p in Permission],
            "OPERATOR": [
                Permission.CAMERA_VIEW.value, Permission.CAMERA_STREAM.value,
                Permission.SEARCH_EXECUTE.value, Permission.CASE_VIEW.value,
                Permission.ALARM_VIEW.value, Permission.ALARM_ACKNOWLEDGE.value,
                Permission.REPORT_VIEW.value,
            ],
            "VIEWER": [
                Permission.CAMERA_VIEW.value, Permission.CASE_VIEW.value,
                Permission.ALARM_VIEW.value, Permission.REPORT_VIEW.value,
            ],
        }
        self._audit_log: List[AuditRecord] = []
        self._user_roles: Dict[str, str] = {"admin": "ADMIN"}  # user_id -> role

    def has_permission(self, user: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        role = self._user_roles.get(user, "VIEWER")
        allowed = self._roles.get(role, [])
        return permission in allowed or "*" in allowed

    def check_access(self, user: str, resource: str, action: str) -> Dict[str, Any]:
        """Check access and return result with audit."""
        permission = f"{resource}:{action}"
        allowed = self.has_permission(user, permission)
        result = "success" if allowed else "denied"

        audit = AuditRecord(
            event_type=AuditEventType.API_ACCESS.value if allowed else AuditEventType.PERMISSION_DENIED.value,
            user=user, action=action, resource=resource, result=result,
        )
        self._audit_log.append(audit)
        if not allowed:
            logger.warning("ACCESS DENIED: %s -> %s:%s", user, resource, action)

        return {"allowed": allowed, "user": user, "resource": resource, "action": action, "audit_id": audit.event_id}

    def assign_role(self, user: str, role: str):
        if role in self._roles:
            self._user_roles[user] = role
            logger.info("Role assigned: %s -> %s", user, role)

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        return [a.to_dict() for a in self._audit_log[-limit:]]

    def get_roles(self) -> Dict[str, List[str]]:
        return dict(self._roles)

    def get_user_role(self, user: str) -> str:
        return self._user_roles.get(user, "VIEWER")


class PolicyEngine:
    """Evaluates and enforces operational policies."""

    def __init__(self):
        self._policies: Dict[str, Dict] = {
            "max_streams_per_user": {"value": 10, "type": "limit", "description": "Maximum concurrent streams per user"},
            "max_search_per_minute": {"value": 100, "type": "rate_limit", "description": "Search API rate limit"},
            "alarm_auto_resolve_hours": {"value": 72, "type": "ttl", "description": "Auto-resolve alarms after hours"},
            "snapshot_retention_days": {"value": 90, "type": "retention", "description": "Snapshot retention period"},
            "max_case_evidence_count": {"value": 100, "type": "limit", "description": "Max evidence items per case"},
            "session_timeout_minutes": {"value": 60, "type": "timeout", "description": "User session timeout"},
        }
        self._evaluation_log: List[Dict] = []

    def evaluate(self, policy_name: str, current_value: Any) -> Dict[str, Any]:
        """Evaluate a policy against a current value."""
        policy = self._policies.get(policy_name)
        if not policy:
            return {"policy": policy_name, "result": "not_found"}

        ptype = policy["type"]
        limit = policy["value"]
        result = {"policy": policy_name, "type": ptype, "limit": limit, "current": current_value}

        if ptype in ("limit", "rate_limit"):
            result["within_limit"] = current_value <= limit
            result["action"] = "allow" if current_value <= limit else "deny"
        elif ptype == "ttl":
            result["expired"] = current_value > limit
            result["action"] = "auto_resolve" if current_value > limit else "keep"
        elif ptype == "retention":
            result["exceeded"] = current_value > limit
            result["action"] = "delete_old" if current_value > limit else "keep"
        elif ptype == "timeout":
            result["expired"] = current_value > limit
            result["action"] = "force_logout" if current_value > limit else "keep"

        self._evaluation_log.append(result)
        return result

    def get_policy(self, name: str) -> Optional[Dict]:
        return self._policies.get(name)

    def list_policies(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self._policies.items()]

    def update_policy(self, name: str, value: Any):
        if name in self._policies:
            self._policies[name]["value"] = value
            return True
        return False


# Global instances
security_manager = SecurityManager()
policy_engine = PolicyEngine()

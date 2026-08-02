"""
Surveillance Engine — Real-time monitoring and alarm escalation.

Manages: surveillance rules, real-time alarm correlation,
escalation policies, false positive filtering, notification dispatch.
"""
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AlarmSeverity(Enum):
    INFO     = "INFO"
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

class AlarmStatus(Enum):
    TRIGGERED    = "TRIGGERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED    = "ESCALATED"
    RESOLVED     = "RESOLVED"
    DISMISSED    = "DISMISSED"

@dataclass
class SurveillanceRule:
    id: str = field(default_factory=lambda: f"rule-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    condition: str = ""          # Python expression
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    cooldown_seconds: int = 60   # minimum time between triggers
    auto_resolve_seconds: int = 0  # 0 = manual resolve only
    notify_channels: List[str] = field(default_factory=lambda: ["webhook"])
    enabled: bool = True
    camera_ids: List[str] = field(default_factory=list)

@dataclass
class Alarm:
    id: str = field(default_factory=lambda: f"alarm-{uuid.uuid4().hex[:8]}")
    rule_id: str = ""
    rule_name: str = ""
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    status: AlarmStatus = AlarmStatus.TRIGGERED
    message: str = ""
    camera_id: str = ""
    snapshot_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    escalation_level: int = 0

@dataclass
class EscalationPolicy:
    id: str = field(default_factory=lambda: f"esc-{uuid.uuid4().hex[:8]}")
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    escalate_after_seconds: int = 300
    max_escalations: int = 3
    notify_roles: List[str] = field(default_factory=list)


class SurveillanceEngine:
    """Real-time surveillance and alarm management."""

    def __init__(self):
        self._rules: Dict[str, SurveillanceRule] = {}
        self._alarms: Dict[str, Alarm] = {}
        self._escalations: Dict[AlarmSeverity, EscalationPolicy] = {}
        self._last_trigger: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._register_defaults()

    def add_rule(self, rule: SurveillanceRule):
        with self._lock:
            self._rules[rule.id] = rule

    def evaluate(self, event: Dict[str, Any]) -> Optional[Alarm]:
        """Evaluate all rules against an incoming event."""
        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Check cooldown
            last = self._last_trigger.get(rule.id)
            if last and (datetime.now(timezone.utc) - last).seconds < rule.cooldown_seconds:
                continue

            # Check camera filter
            cam_id = event.get("camera_id", "")
            if rule.camera_ids and cam_id not in rule.camera_ids:
                continue

            # Evaluate condition
            if self._check_condition(rule.condition, event):
                alarm = self._create_alarm(rule, event)
                self._last_trigger[rule.id] = datetime.now(timezone.utc)
                return alarm
        return None

    def acknowledge(self, alarm_id: str, user: str = "") -> Alarm:
        alarm = self._alarms.get(alarm_id)
        if not alarm: raise KeyError(f"Alarm not found: {alarm_id}")
        alarm.status = AlarmStatus.ACKNOWLEDGED
        alarm.acknowledged_at = datetime.now(timezone.utc)
        logger.info("Alarm acknowledged: %s by %s", alarm_id, user)
        return alarm

    def resolve(self, alarm_id: str, note: str = "") -> Alarm:
        alarm = self._alarms.get(alarm_id)
        if not alarm: raise KeyError(f"Alarm not found: {alarm_id}")
        alarm.status = AlarmStatus.RESOLVED
        alarm.resolved_at = datetime.now(timezone.utc)
        alarm.metadata["resolution_note"] = note
        return alarm

    def dismiss(self, alarm_id: str, reason: str = "") -> Alarm:
        alarm = self._alarms.get(alarm_id)
        if not alarm: raise KeyError(f"Alarm not found: {alarm_id}")
        alarm.status = AlarmStatus.DISMISSED
        alarm.metadata["dismiss_reason"] = reason
        return alarm

    def check_escalations(self) -> List[Alarm]:
        """Check and escalate unacknowledged alarms."""
        escalated = []
        now = datetime.now(timezone.utc)
        for alarm in self._alarms.values():
            if alarm.status != AlarmStatus.TRIGGERED:
                continue
            policy = self._escalations.get(alarm.severity)
            if not policy:
                continue
            elapsed = (now - alarm.triggered_at).total_seconds()
            should_escalate_at = policy.escalate_after_seconds * (alarm.escalation_level + 1)
            if elapsed > should_escalate_at and alarm.escalation_level < policy.max_escalations:
                alarm.escalation_level += 1
                alarm.escalated_at = now
                alarm.status = AlarmStatus.ESCALATED
                # Bump severity
                sev_order = list(AlarmSeverity)
                idx = sev_order.index(alarm.severity)
                if idx < len(sev_order) - 1:
                    alarm.severity = sev_order[idx + 1]
                escalated.append(alarm)
                logger.warning("Alarm escalated: %s → %s (level %d)",
                              alarm.id, alarm.severity.value, alarm.escalation_level)
        return escalated

    def get_active_alarms(self, severity: str = None) -> List[Alarm]:
        alarms = [a for a in self._alarms.values()
                 if a.status in (AlarmStatus.TRIGGERED, AlarmStatus.ACKNOWLEDGED, AlarmStatus.ESCALATED)]
        if severity:
            alarms = [a for a in alarms if a.severity.value == severity]
        return sorted(alarms, key=lambda a: a.triggered_at, reverse=True)

    def list_rules(self) -> List[Dict]:
        return [{"id": r.id, "name": r.name, "severity": r.severity.value,
                 "enabled": r.enabled, "cooldown_s": r.cooldown_seconds}
                for r in self._rules.values()]

    def stats(self) -> Dict[str, Any]:
        alarms = list(self._alarms.values())
        active = sum(1 for a in alarms if a.status != AlarmStatus.RESOLVED)
        return {
            "total_alarms": len(alarms),
            "active_alarms": active,
            "rules_count": len(self._rules),
            "by_severity": {s.value: sum(1 for a in alarms if a.severity == s)
                          for s in AlarmSeverity},
            "by_status": {s.value: sum(1 for a in alarms if a.status == s)
                         for s in AlarmStatus},
        }

    def _check_condition(self, condition: str, event: Dict) -> bool:
        try:
            env = {"event": event, "now": datetime.now(timezone.utc)}
            return bool(eval(condition, {"__builtins__": {}}, env))
        except Exception:
            return False

    def _create_alarm(self, rule: SurveillanceRule, event: Dict) -> Alarm:
        alarm = Alarm(
            rule_id=rule.id, rule_name=rule.name, severity=rule.severity,
            message=event.get("message", f"{rule.name} triggered"),
            camera_id=event.get("camera_id", ""),
            snapshot_url=event.get("snapshot_url", ""),
            metadata=event,
        )
        with self._lock:
            self._alarms[alarm.id] = alarm
        logger.info("Alarm triggered: %s [%s]", alarm.id, rule.name)
        return alarm

    def _register_defaults(self):
        # Default escalation policies
        self._escalations = {
            AlarmSeverity.CRITICAL: EscalationPolicy(severity=AlarmSeverity.CRITICAL, escalate_after_seconds=60, max_escalations=2),
            AlarmSeverity.HIGH:     EscalationPolicy(severity=AlarmSeverity.HIGH, escalate_after_seconds=300, max_escalations=3),
            AlarmSeverity.MEDIUM:   EscalationPolicy(severity=AlarmSeverity.MEDIUM, escalate_after_seconds=900, max_escalations=2),
        }
        # Default rules
        for rule in [
            SurveillanceRule(name="intrusion_detection", severity=AlarmSeverity.HIGH,
                condition="event.get('object_class') == 'person' and event.get('confidence', 0) > 0.85",
                description="Person detected with high confidence"),
            SurveillanceRule(name="vehicle_unauthorized", severity=AlarmSeverity.MEDIUM,
                condition="event.get('object_class') == 'vehicle' and event.get('zone') == 'restricted'",
                description="Vehicle in restricted zone", cooldown_seconds=120),
            SurveillanceRule(name="camera_offline", severity=AlarmSeverity.CRITICAL,
                condition="event.get('status') == 'OFFLINE'",
                description="Camera went offline", cooldown_seconds=30),
            SurveillanceRule(name="crowd_detected", severity=AlarmSeverity.MEDIUM,
                condition="event.get('person_count', 0) > 10",
                description="Crowd detected (>10 people)", cooldown_seconds=300),
        ]:
            self.add_rule(rule)


_surveillance: Optional[SurveillanceEngine] = None

def get_surveillance() -> SurveillanceEngine:
    global _surveillance
    if _surveillance is None:
        _surveillance = SurveillanceEngine()
    return _surveillance

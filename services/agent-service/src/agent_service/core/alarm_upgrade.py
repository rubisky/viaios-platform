"""Alarm Production Upgrade — alarm processing, auto-case creation, notification chain.
   Integration point: receives alarms via POST /api/v1/alarms/simulate or direct process_alarm() call.
   For Kafka integration, deploy viaios-kafka-bridge to consume from alarm topic."""
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .production_upgrade import db_store, health_monitor, retry, circuit_breaker

logger = logging.getLogger(__name__)


class AlarmAction(Enum):
    NOTIFY = "notify"
    CREATE_CASE = "create_case"
    START_RECORDING = "start_recording"
    ESCALATE = "escalate"
    AUTO_RESOLVE = "auto_resolve"


class AlarmRule:
    """A rule that triggers actions when alarm conditions are met."""

    def __init__(self, rule_id: str, name: str, condition: Dict, actions: List[str],
                 severity: str = "HIGH"):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.actions = actions
        self.severity = severity
        self.enabled = True
        self.trigger_count = 0
        self.last_triggered: Optional[str] = None

    def evaluate(self, alarm: Dict) -> bool:
        """Check if this alarm matches the rule condition."""
        if not self.enabled: return False
        cond = self.condition
        alarm_type = alarm.get("type", "")
        alarm_severity = alarm.get("severity", "")
        location = alarm.get("location", "")
        camera = alarm.get("camera", "")

        if cond.get("alarm_type") and alarm_type not in cond["alarm_type"]: return False
        if cond.get("severity") and alarm_severity not in cond["severity"]: return False
        if cond.get("location") and location != cond["location"]: return False
        if cond.get("camera") and camera != cond["camera"]: return False
        return True

    def trigger(self, alarm: Dict) -> Dict:
        self.trigger_count += 1
        self.last_triggered = datetime.now(timezone.utc).isoformat()
        return {"rule_id": self.rule_id, "rule_name": self.name, "actions": self.actions,
                "alarm": alarm, "trigger_count": self.trigger_count}

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "name": self.name, "severity": self.severity,
                "enabled": self.enabled, "trigger_count": self.trigger_count,
                "actions": self.actions, "condition": self.condition}


class AlarmActionExecutor:
    """Executes alarm actions: create case, notify, escalate."""

    def __init__(self):
        self._cases_created: List[Dict] = []
        self._notifications_sent: List[Dict] = []

    @retry(max_attempts=2)
    def execute(self, action: str, alarm: Dict, rule: AlarmRule) -> Dict:
        """Execute a single alarm action."""
        result = {"action": action, "status": "completed"}

        if action == "create_case":
            case = {
                "case_id": str(uuid.uuid4())[:12],
                "title": f"Auto-generated: {rule.name}",
                "description": f"Alarm: {alarm.get('message', '')} at {alarm.get('location', '')}",
                "priority": "P1" if alarm.get("severity") == "CRITICAL" else "P2",
                "source_alarm": alarm.get("id", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._cases_created.append(case)
            result["case"] = case
            health_monitor.record("auto_cases_created", 1)

        elif action == "notify":
            notif = {
                "id": str(uuid.uuid4())[:8],
                "channel": "dashboard",
                "title": f"[{alarm.get('severity', 'HIGH')}] {alarm.get('message', 'Alarm')}",
                "message": f"Rule '{rule.name}' triggered. Location: {alarm.get('location', 'unknown')}",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            self._notifications_sent.append(notif)
            result["notification"] = notif
            health_monitor.record("auto_notifications", 1)

        elif action == "escalate":
            result["escalated"] = True
            result["escalation_level"] = "P0"

        logger.info("Alarm action executed: %s for rule %s", action, rule.name)
        return result

    def get_cases(self) -> List[Dict]: return self._cases_created
    def get_notifications(self) -> List[Dict]: return self._notifications_sent


class AlarmEngine:
    """Production alarm engine with rule evaluation and action execution."""

    def __init__(self):
        self._rules: Dict[str, AlarmRule] = {}
        self._executor = AlarmActionExecutor()
        self._alarm_log: List[Dict] = []
        self._init_rules()

    def _init_rules(self):
        rules = [
            AlarmRule("rule-001", "Intrusion Critical",
                      {"alarm_type": ["intrusion", "tamper_detection"], "severity": ["CRITICAL", "HIGH"]},
                      ["create_case", "notify", "escalate"], "CRITICAL"),
            AlarmRule("rule-002", "Speed Violation",
                      {"alarm_type": ["speed_violation", "wrong_direction"], "severity": ["HIGH", "MEDIUM"]},
                      ["notify", "start_recording"], "HIGH"),
            AlarmRule("rule-003", "Camera Offline",
                      {"alarm_type": ["camera_offline"], "severity": ["HIGH", "MEDIUM", "LOW"]},
                      ["notify"], "MEDIUM"),
            AlarmRule("rule-004", "Restricted Zone",
                      {"alarm_type": ["restricted_area"], "severity": ["CRITICAL", "HIGH"]},
                      ["create_case", "notify", "escalate"], "CRITICAL"),
        ]
        for r in rules:
            self._rules[r.rule_id] = r
            db_store.set(f"alarm_rule:{r.rule_id}", r.to_dict())

    @retry(max_attempts=2)
    def process_alarm(self, alarm: Dict) -> Dict:
        """Process an alarm through the rule engine."""
        results = []
        triggered_rules = []

        for rule in self._rules.values():
            if rule.evaluate(alarm):
                try:
                    trigger_result = circuit_breaker.call(
                        f"alarm_rule_{rule.rule_id}",
                        rule.trigger, alarm
                    )
                    for action in rule.actions:
                        action_result = self._executor.execute(action, alarm, rule)
                        results.append(action_result)
                    triggered_rules.append(rule.rule_id)
                except Exception as e:
                    logger.error("Rule %s execution failed: %s", rule.rule_id, e)
                    results.append({"rule": rule.rule_id, "error": str(e)})

        alarm_record = {
            **alarm,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "triggered_rules": triggered_rules,
            "action_count": len(results),
        }
        self._alarm_log.append(alarm_record)
        db_store.set(f"alarm_log:{alarm.get('id', uuid.uuid4().hex[:8])}", alarm_record)
        health_monitor.record("alarms_processed", 1)

        return {"alarm": alarm_record, "rules_triggered": len(triggered_rules), "actions": results}

    def get_rules(self) -> List[Dict]:
        return [r.to_dict() for r in self._rules.values()]

    def get_alarm_log(self, limit: int = 50) -> List[Dict]:
        return self._alarm_log[-limit:]

    def get_cases_created(self) -> List[Dict]:
        return self._executor.get_cases()

    def get_stats(self) -> Dict:
        return {
            "rules_count": len(self._rules),
            "alarms_processed": len(self._alarm_log),
            "cases_created": len(self._executor.get_cases()),
            "notifications_sent": len(self._executor.get_notifications()),
        }

    def simulate_alarm(self) -> Dict:
        """Generate and process a simulated alarm for testing."""
        types = ["intrusion", "speed_violation", "camera_offline", "restricted_area"]
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        locations = ["Gate A", "Parking Lot", "Warehouse C", "Perimeter North"]
        alarm = {
            "id": f"alm-{uuid.uuid4().hex[:8]}",
            "type": random.choice(types),
            "severity": random.choices(severities, weights=[1, 2, 4, 3])[0],
            "location": random.choice(locations),
            "camera": f"cam-{random.randint(1, 12):03d}",
            "message": f"Alarm triggered at {random.choice(locations)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self.process_alarm(alarm)


alarm_engine = AlarmEngine()

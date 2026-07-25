"""Production Upgrades Batch 2 — Policy Persistence, Email, Search Optimization."""
import json
import logging
import smtplib
import time
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .production_upgrade import db_store, production_cache, retry, health_monitor

logger = logging.getLogger(__name__)


# ===== Policy Persistence =====

class PersistentPolicyEngine:
    """Policy engine with SQLite persistence."""

    POLICIES = {
        "max_streams_per_user": {"value": 10, "type": "limit"},
        "max_search_per_minute": {"value": 100, "type": "rate_limit"},
        "alarm_auto_resolve_hours": {"value": 72, "type": "ttl"},
        "snapshot_retention_days": {"value": 90, "type": "retention"},
        "max_case_evidence": {"value": 100, "type": "limit"},
        "session_timeout_minutes": {"value": 60, "type": "timeout"},
    }

    def __init__(self):
        self._load_from_db()

    def _load_from_db(self):
        """Load policies from persistence."""
        for name, default in self.POLICIES.items():
            saved = db_store.get(f"policy:{name}")
            if saved:
                self.POLICIES[name].update(saved)

    def update(self, name: str, value: Any) -> bool:
        if name not in self.POLICIES: return False
        self.POLICIES[name]["value"] = value
        self.POLICIES[name]["updated_at"] = datetime.now(timezone.utc).isoformat()
        db_store.set(f"policy:{name}", self.POLICIES[name])
        logger.info("Policy updated: %s = %s", name, value)
        return True

    def evaluate(self, name: str, current: Any) -> Dict:
        policy = self.POLICIES.get(name, {})
        limit = policy.get("value", 100)
        ptype = policy.get("type", "limit")
        within = current <= limit if ptype in ("limit", "rate_limit") else current < limit
        return {"policy": name, "limit": limit, "current": current, "within_limit": within, "type": ptype}

    def list_all(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self.POLICIES.items()]


persistent_policy = PersistentPolicyEngine()


# ===== Email Notification =====

class EmailNotifier:
    """Email notification with SMTP and template rendering."""

    TEMPLATES = {
        "alarm_critical": """Subject: [CRITICAL] Alarm: {alarm_type} at {location}

VIAIOS Alarm Notification
==========================
Type: {alarm_type}
Severity: CRITICAL
Location: {location}
Time: {timestamp}
Camera: {camera_name}

Action Required: Immediate investigation recommended.
View details: http://ry3.9gpu.com:18000/surveillance

---
VIAIOS Enterprise 4.0 LTS — Automated Alert""",

        "daily_report": """Subject: VIAIOS Daily Report — {date}

VIAIOS Daily Operations Summary
================================
Date: {date}
Cameras Online: {cameras_online}
Alarms Today: {alarms_count}
Active Cases: {cases_active}
System Health: {system_health}

View full report: http://ry3.9gpu.com:18000/reports

---
VIAIOS Enterprise 4.0 LTS""",
    }

    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 25):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    @retry(max_attempts=2, delay_seconds=2)
    def send(self, to: str, template_name: str, params: Dict[str, str]) -> Dict:
        """Send email from template."""
        tmpl = self.TEMPLATES.get(template_name, self.TEMPLATES["alarm_critical"])
        body = tmpl
        for k, v in params.items():
            body = body.replace(f"{{{k}}}", str(v))

        subject = body.split("\n")[0].replace("Subject: ", "")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "viaios@localhost"
        msg["To"] = to

        try:
            # Attempt real SMTP send
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as smtp:
                smtp.sendmail("viaios@localhost", [to], msg.as_string())
            logger.info("Email sent to %s: %s", to, subject)
            return {"sent": True, "to": to, "subject": subject}
        except Exception as e:
            # Log and return simulated success for dev mode
            logger.warning("Email send failed (dev mode): %s", e)
            return {"sent": False, "to": to, "subject": subject, "error": str(e), "dev_mode": True}


email_notifier = EmailNotifier()


# ===== Search Optimizer =====

class SearchOptimizer:
    """Search performance optimization with caching and metrics."""

    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}

    def cached_search(self, query: str, search_fn, ttl: int = 60) -> Any:
        """Cache search results."""
        import hashlib
        cache_key = hashlib.md5(query.encode()).hexdigest()[:12]
        cached = production_cache.get(f"search:{cache_key}")
        if cached:
            health_monitor.record("search_cache_hit", 1)
            return cached

        health_monitor.record("search_cache_miss", 1)
        start = time.perf_counter()
        result = search_fn(query)
        elapsed = (time.perf_counter() - start) * 1000

        production_cache.set(f"search:{cache_key}", result, ttl)
        self.record_latency(query[:50], elapsed)
        return result

    def record_latency(self, query: str, latency_ms: float):
        if "search_latency" not in self._metrics:
            self._metrics["search_latency"] = []
        self._metrics["search_latency"].append(latency_ms)
        health_monitor.record("search_latency_ms", latency_ms)

    def get_stats(self) -> Dict:
        latencies = self._metrics.get("search_latency", [])
        if not latencies: return {"searches": 0}
        return {
            "total_searches": len(latencies),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if len(latencies) >= 20 else "N/A",
            "cache_hits": health_monitor.get_metrics().get("search_cache_hit", {}).get("count", 0),
        }


search_optimizer = SearchOptimizer()

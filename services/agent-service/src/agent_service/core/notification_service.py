"""
Notification Service — Multi-channel alert delivery (P5-2).
Channels: webhook, email, SMS, DingTalk, WeChat Work.
"""
import json
import logging
import smtplib
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class Channel(Enum):
    WEBHOOK   = "webhook"
    EMAIL     = "email"
    SMS       = "sms"
    DINGTALK  = "dingtalk"
    WECHAT    = "wechat_work"
    CONSOLE   = "console"

class Priority(Enum):
    LOW    = "low"
    NORMAL = "normal"
    HIGH   = "high"
    URGENT = "urgent"

@dataclass
class Notification:
    id: str = field(default_factory=lambda: f"notif-{uuid.uuid4().hex[:8]}")
    title: str = ""
    message: str = ""
    priority: Priority = Priority.NORMAL
    channel: Channel = Channel.CONSOLE
    recipients: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    sent_at: Optional[datetime] = None
    error: str = ""

class NotificationService:
    """Multi-channel notification delivery."""
    def __init__(self):
        self._history: List[Notification] = []
        self._config = {
            "smtp_host": "smtp.example.com", "smtp_port": 587,
            "smtp_user": "", "smtp_pass": "",
            "dingtalk_webhook": "", "wechat_webhook": "",
            "sms_api_key": "",
        }
        self._lock = threading.Lock()
        self._stats = {ch.value: {"sent": 0, "failed": 0} for ch in Channel}

    def send(self, title: str, message: str, channel: Channel = Channel.CONSOLE,
             priority: Priority = Priority.NORMAL, recipients: List[str] = None,
             metadata: Dict = None) -> Notification:
        notif = Notification(title=title, message=message, priority=priority,
                            channel=channel, recipients=recipients or [], metadata=metadata or {})

        handlers = {Channel.CONSOLE: self._send_console, Channel.WEBHOOK: self._send_webhook,
                    Channel.EMAIL: self._send_email, Channel.DINGTALK: self._send_dingtalk,
                    Channel.WECHAT: self._send_wechat, Channel.SMS: self._send_sms}
        handler = handlers.get(channel, self._send_console)

        try:
            handler(notif)
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            self._stats[channel.value]["sent"] += 1
        except Exception as e:
            notif.status = "failed"
            notif.error = str(e)
            self._stats[channel.value]["failed"] += 1

        with self._lock:
            self._history.append(notif)
            if len(self._history) > 500:
                self._history = self._history[-250:]
        return notif

    def send_multi(self, title: str, message: str, channels: List[Channel],
                   priority: Priority = Priority.NORMAL) -> List[Notification]:
        return [self.send(title, message, ch, priority) for ch in channels]

    def get_history(self, limit: int = 50) -> List[Dict]:
        return [{"id": n.id, "title": n.title, "channel": n.channel.value,
                 "priority": n.priority.value, "status": n.status,
                 "sent_at": n.sent_at.isoformat() if n.sent_at else None}
                for n in self._history[-limit:]]

    def stats(self) -> Dict[str, Any]:
        return {"total_sent": sum(s["sent"] for s in self._stats.values()),
                "total_failed": sum(s["failed"] for s in self._stats.values()),
                "by_channel": self._stats}

    # Channel implementations
    def _send_console(self, n: Notification):
        logger.info("[%s] %s: %s", n.priority.value.upper(), n.title, n.message[:200])

    def _send_webhook(self, n: Notification):
        import urllib.request
        body = json.dumps({"title": n.title, "message": n.message, "priority": n.priority.value}).encode()
        req = urllib.request.Request(n.metadata.get("webhook_url", ""), data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)

    def _send_email(self, n: Notification):
        if not self._config["smtp_host"] or not n.recipients:
            raise ValueError("SMTP not configured or no recipients")
        msg = MIMEText(n.message)
        msg["Subject"] = f"[{n.priority.value.upper()}] {n.title}"
        msg["From"] = self._config["smtp_user"] or "noreply@viaios.com"
        msg["To"] = ", ".join(n.recipients)
        with smtplib.SMTP(self._config["smtp_host"], self._config["smtp_port"]) as s:
            s.starttls()
            if self._config["smtp_user"]:
                s.login(self._config["smtp_user"], self._config["smtp_pass"])
            s.send_message(msg)

    def _send_dingtalk(self, n: Notification):
        import urllib.request
        webhook = self._config["dingtalk_webhook"] or n.metadata.get("dingtalk_webhook", "")
        body = json.dumps({"msgtype": "text", "text": {"content": f"[{n.priority.value}] {n.title}\n{n.message}"}}).encode()
        urllib.request.urlopen(urllib.request.Request(webhook, data=body,
            headers={"Content-Type": "application/json"}, method="POST"), timeout=10)

    def _send_wechat(self, n: Notification):
        import urllib.request
        webhook = self._config["wechat_webhook"] or n.metadata.get("wechat_webhook", "")
        body = json.dumps({"msgtype": "markdown", "markdown": {"content": f"## {n.title}\n{n.message}"}}).encode()
        urllib.request.urlopen(urllib.request.Request(webhook, data=body,
            headers={"Content-Type": "application/json"}, method="POST"), timeout=10)

    def _send_sms(self, n: Notification):
        logger.info("[SMS] To: %s | %s", n.recipients, n.message[:100])


_notification: Optional[NotificationService] = None
def get_notification_service() -> NotificationService:
    global _notification
    if _notification is None:
        _notification = NotificationService()
    return _notification

"""Platform Services — GPU Scheduler, Notification Center, Log Aggregator."""
import logging
import queue
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== GPU Resource Scheduler =====

class GPUModel(Enum):
    A100 = "NVIDIA A100 80GB"
    A10 = "NVIDIA A10 24GB"
    RTX3090 = "NVIDIA RTX 3090 24GB"
    RTX4090 = "NVIDIA RTX 4090 24GB"
    V100 = "NVIDIA V100 32GB"

class TaskPriority(Enum):
    P0 = 0   # Critical
    P1 = 1   # High
    P2 = 2   # Medium
    P3 = 3   # Low

@dataclass
class GPUNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "gpu-node-01"
    model: str = "NVIDIA RTX 3090"
    total_memory_mb: int = 24576
    used_memory_mb: int = 0
    utilization_percent: float = 0
    temperature_c: float = 45
    status: str = "ready"
    active_tasks: int = 0

    def available_memory_mb(self) -> int:
        return self.total_memory_mb - self.used_memory_mb

@dataclass
class GPUAllocation:
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_id: str = ""
    task_name: str = ""
    gpu_memory_mb: int = 0
    priority: str = "P2"
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GPUScheduler:
    """GPU resource pool scheduler with priority queuing."""

    def __init__(self):
        self._nodes: List[GPUNode] = [
            GPUNode(name="gpu-node-01", model="NVIDIA RTX 3090", total_memory_mb=24576),
            GPUNode(name="gpu-node-02", model="NVIDIA RTX 3090", total_memory_mb=24576),
        ]
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._allocations: Dict[str, GPUAllocation] = {}
        self._total_allocated = 0

    def allocate(self, task_name: str, gpu_memory_mb: int,
                 priority: str = "P2") -> GPUAllocation:
        """Allocate GPU resources for a task."""
        alloc = GPUAllocation(task_name=task_name, gpu_memory_mb=gpu_memory_mb, priority=priority)
        p_val = getattr(TaskPriority, priority, TaskPriority.P2).value
        self._queue.put((p_val, time.time(), alloc))

        # Try to assign immediately
        for node in sorted(self._nodes, key=lambda n: n.active_tasks):
            if node.available_memory_mb() >= gpu_memory_mb and node.status == "ready":
                node.used_memory_mb += gpu_memory_mb
                node.active_tasks += 1
                node.utilization_percent = round(node.used_memory_mb / node.total_memory_mb * 100, 1)
                alloc.node_id = node.node_id
                alloc.status = "allocated"
                self._total_allocated += 1
                break

        self._allocations[alloc.allocation_id] = alloc
        return alloc

    def deallocate(self, allocation_id: str) -> bool:
        alloc = self._allocations.get(allocation_id)
        if not alloc: return False
        for node in self._nodes:
            if node.node_id == alloc.node_id:
                node.used_memory_mb -= alloc.gpu_memory_mb
                node.active_tasks = max(0, node.active_tasks - 1)
                node.utilization_percent = round(node.used_memory_mb / node.total_memory_mb * 100, 1)
        alloc.status = "released"
        return True

    def get_status(self) -> Dict[str, Any]:
        nodes = [{"name": n.name, "model": n.model, "memory_used": f"{n.used_memory_mb}/{n.total_memory_mb}MB",
                   "utilization": n.utilization_percent, "active_tasks": n.active_tasks, "status": n.status}
                 for n in self._nodes]
        return {"nodes": nodes, "total_allocations": self._total_allocated, "queue_size": self._queue.qsize()}


# ===== Notification Center =====

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"

@dataclass
class Notification:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    message: str = ""
    severity: str = "info"
    channel: str = "dashboard"
    recipient: str = ""
    read: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class NotificationCenter:
    """Multi-channel notification system."""

    def __init__(self):
        self._notifications: List[Notification] = []
        self._templates: Dict[str, str] = {
            "alarm_triggered": "[{severity}] Alarm: {alarm_type} at {location}",
            "alarm_resolved": "Alarm resolved: {alarm_id} by {user}",
            "case_created": "New case: {case_title} (Priority: {priority})",
            "system_alert": "System alert: {component} {status}",
        }

    def send(self, title: str, message: str, severity: str = "info",
             channel: str = "dashboard", recipient: str = "") -> Notification:
        notif = Notification(title=title, message=message, severity=severity,
                             channel=channel, recipient=recipient)
        self._notifications.append(notif)
        if channel == "email":
            logger.info("[EMAIL] To: %s | %s", recipient, message)
        elif channel == "sms":
            logger.info("[SMS] To: %s | %s", recipient, message)
        elif channel == "webhook":
            logger.info("[WEBHOOK] POST | %s", message)
        return notif

    def send_from_template(self, template_name: str, params: Dict[str, str],
                           severity: str = "info", channel: str = "dashboard") -> Notification:
        tmpl = self._templates.get(template_name, "{message}")
        msg = tmpl
        for k, v in params.items():
            msg = msg.replace(f"{{{k}}}", v)
        return self.send(title=f"{template_name.replace('_', ' ').title()}", message=msg,
                         severity=severity, channel=channel)

    def list_notifications(self, limit: int = 20, unread_only: bool = False) -> List[Dict]:
        items = self._notifications
        if unread_only: items = [n for n in items if not n.read]
        return [n.to_dict() for n in items[-limit:]]

    def mark_read(self, notification_id: str):
        for n in self._notifications:
            if n.id == notification_id: n.read = True

    def get_unread_count(self) -> int:
        return sum(1 for n in self._notifications if not n.read)


# ===== Log Aggregator =====

class LogAggregator:
    """Simple in-memory log aggregator with search."""

    def __init__(self, max_logs: int = 1000):
        self._logs: List[Dict] = []
        self._max = max_logs

    def add(self, level: str, service: str, message: str, metadata: Dict = None):
        self._logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(), "level": level,
            "service": service, "message": message, "metadata": metadata or {},
        })
        if len(self._logs) > self._max: self._logs.pop(0)

    def search(self, query: str = "", level: str = "", service: str = "",
               limit: int = 50) -> List[Dict]:
        results = self._logs
        if level: results = [l for l in results if l["level"] == level]
        if service: results = [l for l in results if l["service"] == service]
        if query: results = [l for l in results if query.lower() in l["message"].lower()]
        return results[-limit:]

    def get_stats(self) -> dict:
        levels = {"ERROR": 0, "WARN": 0, "INFO": 0}
        for log in self._logs:
            lvl = log["level"]
            if lvl in levels: levels[lvl] += 1
        return {"total_logs": len(self._logs), "by_level": levels}


# Globals
gpu_scheduler = GPUScheduler()
notification_center = NotificationCenter()
log_aggregator = LogAggregator()

# Seed demo data
for i in range(5):
    log_aggregator.add("INFO", "api-gateway", f"Request processed: /api/v1/cameras ({random.randint(10,50)}ms)")
    log_aggregator.add("WARN", "ai-kernel", f"GPU memory usage above 80% on gpu-node-0{random.randint(1,2)}")
log_aggregator.add("ERROR", "video-access", "Camera cam-003 connection timeout")
notification_center.send("System Started", "All 16 services operational", "info")
notification_center.send_from_template("alarm_triggered", {"alarm_type":"Intrusion","location":"Gate A"}, "high")

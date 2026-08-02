"""
Event Manager — Event-driven architecture for VIAIOS.

Manages: event types, subscriptions, dispatch, retry, dead-letter queue,
event sourcing, and audit trail. Integrates with Kafka bridge for pub/sub.
"""
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventStatus(Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    DEAD_LETTER = "dead_letter"

class EventPriority(Enum):
    LOW    = 0
    NORMAL = 50
    HIGH   = 80
    CRITICAL = 100

@dataclass
class Event:
    id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    type: str = ""                      # e.g. "alarm.triggered", "case.opened"
    source: str = ""                    # service name
    priority: EventPriority = EventPriority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    correlation_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error: str = ""

@dataclass
class Subscription:
    id: str = field(default_factory=lambda: f"sub-{uuid.uuid4().hex[:8]}")
    event_type: str = ""
    handler: Callable = None
    filter_expr: Optional[str] = None   # e.g. "payload.severity == 'CRITICAL'"
    priority: int = 0                   # lower = earlier
    concurrent: bool = True

@dataclass
class EventStats:
    total_published: int = 0
    total_processed: int = 0
    total_failed: int = 0
    dead_letter_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    avg_latency_ms: float = 0


class EventManager:
    """Event-driven architecture core."""

    def __init__(self, max_queue: int = 10000):
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self._dead_letter: List[Event] = []
        self._history: List[Event] = []
        self._lock = threading.Lock()
        self._stats = EventStats()
        self._processing = False
        self._kafka = None

    def publish(self, event_type: str, payload: Dict[str, Any],
                source: str = "", priority: EventPriority = EventPriority.NORMAL,
                correlation_id: str = "") -> Event:
        """Publish an event. Returns immediately; processing is async."""
        event = Event(type=event_type, source=source, priority=priority,
                     payload=payload, correlation_id=correlation_id)
        with self._lock:
            self._stats.total_published += 1
            self._stats.by_type[event_type] = self._stats.by_type.get(event_type, 0) + 1

        # Dispatch to subscribers asynchronously
        subs = self._subscriptions.get(event_type, []) + self._subscriptions.get("*", [])
        subs.sort(key=lambda s: s.priority)

        import threading as th
        th.Thread(target=self._dispatch, args=(event, subs), daemon=True).start()

        # Also publish to Kafka if available
        self._publish_kafka(event)

        logger.debug("Event published: %s [%s]", event.type, event.id)
        return event

    def subscribe(self, event_type: str, handler: Callable,
                  filter_expr: str = None, priority: int = 0) -> Subscription:
        """Subscribe to an event type. Use '*' for all events."""
        sub = Subscription(event_type=event_type, handler=handler,
                          filter_expr=filter_expr, priority=priority)
        with self._lock:
            self._subscriptions[event_type].append(sub)
        logger.info("Subscription added: %s → %s", event_type, sub.id)
        return sub

    def unsubscribe(self, subscription_id: str):
        with self._lock:
            for etype, subs in self._subscriptions.items():
                self._subscriptions[etype] = [s for s in subs if s.id != subscription_id]

    # ── Internal ────────────────────────────────────────────────

    def _dispatch(self, event: Event, subscriptions: List[Subscription]):
        """Dispatch event to matching subscribers."""
        event.status = EventStatus.PROCESSING
        start = time.time()

        for sub in subscriptions:
            if not self._matches_filter(event, sub.filter_expr):
                continue
            try:
                sub.handler(event)
            except Exception as e:
                logger.warning("Event handler failed [%s]: %s", sub.id, e)

        event.processed_at = datetime.now(timezone.utc)
        event.status = EventStatus.COMPLETED
        latency = (time.time() - start) * 1000

        with self._lock:
            self._stats.total_processed += 1
            n = self._stats.total_processed
            self._stats.avg_latency_ms = ((self._stats.avg_latency_ms * (n-1)) + latency) / n
            self._history.append(event)
            if len(self._history) > 1000:
                self._history = self._history[-500:]

    def _matches_filter(self, event: Event, filter_expr: str) -> bool:
        if not filter_expr:
            return True
        try:
            ctx = {"payload": event.payload, "source": event.source, "priority": event.priority.value}
            return bool(eval(filter_expr, {"__builtins__": {}}, ctx))
        except Exception:
            return True

    def _publish_kafka(self, event: Event):
        """Publish event to Kafka for cross-service distribution."""
        try:
            from agent_service.core.kafka_bridge import kafka_producer
            kafka_producer.send(
                topic=f"viaios.{event.type.replace('.', '_')}",
                key=event.correlation_id or event.id,
                value=json.dumps({
                    "id": event.id, "type": event.type, "source": event.source,
                    "payload": event.payload, "timestamp": event.created_at.isoformat(),
                }, default=str).encode(),
            )
        except ImportError:
            pass
        except Exception as e:
            logger.debug("Kafka publish skipped: %s", e)

    # ── Dead Letter ─────────────────────────────────────────────

    def dead_letter_queue(self) -> List[Event]:
        return self._dead_letter

    def retry_dead_letter(self, event_id: str):
        for evt in self._dead_letter:
            if evt.id == event_id:
                evt.retry_count = 0
                evt.status = EventStatus.PENDING
                self._dead_letter.remove(evt)
                self.publish(evt.type, evt.payload, evt.source, evt.priority)
                return True
        return False

    # ── Query ───────────────────────────────────────────────────

    def list_subscriptions(self) -> List[Dict]:
        return [{"id": s.id, "event_type": s.event_type, "filter": s.filter_expr}
                for subs in self._subscriptions.values() for s in subs]

    def recent_events(self, limit: int = 50) -> List[Dict]:
        return [{"id": e.id, "type": e.type, "source": e.source,
                 "status": e.status.value, "ts": e.created_at.isoformat()[:19]}
                for e in self._history[-limit:]]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_published": self._stats.total_published,
            "total_processed": self._stats.total_processed,
            "dead_letter": len(self._dead_letter),
            "subscriptions": sum(len(v) for v in self._subscriptions.values()),
            "by_type": dict(sorted(self._stats.by_type.items(), key=lambda x: -x[1])[:10]),
            "avg_latency_ms": round(self._stats.avg_latency_ms, 2),
        }


# ── Convenience ────────────────────────────────────────────────────

_event_manager: Optional[EventManager] = None

def get_event_manager() -> EventManager:
    global _event_manager
    if _event_manager is None:
        _event_manager = EventManager()
        # Register built-in event handlers
        _event_manager.subscribe("alarm.triggered",
            lambda e: logger.info("Alarm event: %s", e.payload.get("message", "")),
            filter_expr="payload.severity == 'CRITICAL'")
        _event_manager.subscribe("case.opened",
            lambda e: logger.info("Case opened: %s", e.payload.get("case_id", "")))
        _event_manager.subscribe("model.deployed",
            lambda e: logger.info("Model deployed: %s", e.payload.get("model_name", "")))
    return _event_manager

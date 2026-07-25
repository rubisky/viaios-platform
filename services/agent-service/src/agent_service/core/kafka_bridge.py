"""
Kafka Bridge — Real event-driven pipeline for VIAIOS.
Replaces all mock/stub Kafka implementations across services.

Topics (from ADS-0501):
  viaios.inference.result  — AI detection results with embeddings
  viaios.event.embedding   — New embeddings for Milvus indexing
  viaios.search.query      — Search audit events
  viaios.alarm.triggered   — Alarm events from rule engine
  viaios.detection.created — New detections from video analysis
"""
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .production_upgrade import circuit_breaker, health_monitor, retry

logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "true").lower() in ("1", "true", "yes")


class KafkaProducer:
    """Real Kafka producer wrapper with circuit breaker and retry."""

    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP):
        self.bootstrap = bootstrap_servers
        self._producer = None
        self._enabled = KAFKA_ENABLED
        self._lock = threading.Lock()
        if self._enabled:
            self._init_producer()

    def _init_producer(self):
        try:
            from kafka import KafkaProducer as KP
            self._producer = KP(
                bootstrap_servers=self.bootstrap,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip',
                linger_ms=10,
            )
            logger.info("Kafka producer connected to %s", self.bootstrap)
        except Exception as e:
            logger.warning("Kafka producer unavailable: %s — events will be logged only", e)
            self._producer = None

    @retry(max_attempts=2)
    def send(self, topic: str, value: Dict[str, Any], key: Optional[str] = None):
        """Send an event to Kafka topic with circuit breaker protection."""
        # Always log the event
        logger.info("[KAFKA] %s → %s", topic, json.dumps(value, ensure_ascii=False, default=str)[:300])

        if not self._producer:
            health_monitor.record("kafka_dropped", 1)
            return

        try:
            future = self._producer.send(topic, value=value, key=key)
            self._producer.flush(timeout=5)
            health_monitor.record("kafka_sent", 1)
            return future
        except Exception as e:
            logger.error("Kafka send failed [%s]: %s", topic, e)
            health_monitor.record("kafka_error", 1)
            raise

    def close(self):
        if self._producer:
            self._producer.close(timeout=10)


class KafkaConsumer:
    """Real Kafka consumer with auto-commit and rebalance."""

    def __init__(self, topics: List[str], group_id: str, handler):
        self.topics = topics
        self.group_id = group_id
        self.handler = handler  # async def handler(topic: str, key: str, value: dict)
        self._consumer = None
        self._running = False
        self._thread = None
        self._enabled = KAFKA_ENABLED

    def start(self):
        if not self._enabled:
            logger.info("Kafka consumer disabled (KAFKA_ENABLED=false)")
            return

        try:
            from kafka import KafkaConsumer as KC
            self._consumer = KC(
                *self.topics,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=self.group_id,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
            )
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True, name=f"kafka-{self.group_id}")
            self._thread.start()
            logger.info("Kafka consumer [%s] subscribed to %s", self.group_id, self.topics)
        except Exception as e:
            logger.warning("Kafka consumer unavailable: %s", e)

    def _poll_loop(self):
        while self._running:
            try:
                records = self._consumer.poll(timeout_ms=1000, max_records=50)
                for tp, msgs in records.items():
                    for msg in msgs:
                        try:
                            self.handler(msg.topic, msg.key, msg.value)
                            health_monitor.record("kafka_consumed", 1)
                        except Exception as e:
                            logger.error("Kafka handler error [%s]: %s", msg.topic, e)
            except Exception as e:
                logger.error("Kafka poll error: %s", e)
                time.sleep(5)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        if self._consumer:
            self._consumer.close()


# ===== Global instances =====

kafka_producer = KafkaProducer()


# ===== Event publishers (replace mock code across all services) =====

def publish_inference_result(
    model_name: str, capability: str, entity_id: str,
    confidence: float, embedding: Optional[List[float]] = None,
    camera_id: str = "", bbox: Optional[Dict] = None, **extra
):
    """Publish AI inference result to viaios.inference.result.
    Called by: ONNX adapter, video analysis pipeline.
    Replaces: All mock _generate_results() code."""
    event = {
        "event_type": "inference.result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_name": model_name,
        "capability": capability,
        "entity_id": entity_id,
        "confidence": confidence,
        "camera_id": camera_id,
        "bbox": bbox or {},
        "embedding_dim": len(embedding) if embedding else 0,
        **extra,
    }
    kafka_producer.send("viaios.inference.result", event, key=entity_id)


def publish_embedding(
    target_collection: str, entity_id: str,
    embedding: List[float], metadata: Dict[str, Any] = None
):
    """Publish new embedding to viaios.event.embedding for Milvus indexing."""
    event = {
        "event_type": "embedding.created",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_collection": target_collection,
        "entity_id": entity_id,
        "embedding": embedding,
        "dimension": len(embedding),
        "metadata": metadata or {},
    }
    kafka_producer.send("viaios.event.embedding", event, key=entity_id)


def publish_search_query(
    search_type: str, user_id: str, query: str,
    result_count: int, latency_ms: float
):
    """Publish search audit event for analytics."""
    event = {
        "event_type": "search.query",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "search_type": search_type,
        "user_id": user_id,
        "query": query[:500],
        "result_count": result_count,
        "latency_ms": latency_ms,
    }
    kafka_producer.send("viaios.search.query", event)


def publish_alarm(
    alarm_id: str, alarm_type: str, severity: str,
    camera_id: str, message: str, **extra
):
    """Publish alarm event for notification pipeline."""
    event = {
        "event_type": "alarm.triggered",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alarm_id": alarm_id,
        "alarm_type": alarm_type,
        "severity": severity,
        "camera_id": camera_id,
        "message": message,
        **extra,
    }
    kafka_producer.send("viaios.alarm.triggered", event, key=alarm_id)


def publish_detection(
    detection_id: str, camera_id: str, object_class: str,
    confidence: float, timestamp: str, bbox: Dict = None
):
    """Publish new detection for real-time processing."""
    event = {
        "event_type": "detection.created",
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "detection_id": detection_id,
        "camera_id": camera_id,
        "object_class": object_class,
        "confidence": confidence,
        "bbox": bbox or {},
    }
    kafka_producer.send("viaios.detection.created", event, key=detection_id)


# ===== Event consumers (replace stub listeners) =====

def start_alarm_consumer(alarm_handler):
    """
    Start consuming from viaios.alarm.triggered.
    Replaces: AlarmEventConsumer.java stub.
    """
    consumer = KafkaConsumer(
        topics=["viaios.alarm.triggered"],
        group_id="viaios-alarm-service",
        handler=alarm_handler,
    )
    consumer.start()
    return consumer


def start_embedding_consumer(index_handler):
    """
    Start consuming from viaios.event.embedding for Milvus indexing.
    Replaces: mock embedding indexer.
    """
    consumer = KafkaConsumer(
        topics=["viaios.event.embedding"],
        group_id="viaios-embedding-indexer",
        handler=index_handler,
    )
    consumer.start()
    return consumer


def start_detection_consumer(detection_handler):
    """
    Start consuming detections for real-time processing.
    """
    consumer = KafkaConsumer(
        topics=["viaios.inference.result", "viaios.detection.created"],
        group_id="viaios-detection-processor",
        handler=detection_handler,
    )
    consumer.start()
    return consumer

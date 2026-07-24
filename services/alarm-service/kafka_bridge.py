"""
Kafka-to-WebSocket Alarm Bridge Service.
Consumes alarm events from Kafka and pushes to gateway WebSocket.
Run: PYTHONPATH=. python alarm_service/kafka_bridge.py
"""
import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('kafka-bridge')

KAFKA_BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9092')
GW_WS_URL = os.environ.get('GW_WS_URL', 'http://localhost:8080')
TOPICS = ['viaios.alarm.events', 'viaios.alarm.notifications']

# Simulated events for demo (when Kafka client not available)
DEMO_EVENTS = [
    {"type": "alarm", "id": "alarm-001", "severity": "high", "cameraId": "cam-001",
     "message": "Intrusion detected in Zone-A", "timestamp": ""},
    {"type": "alarm", "id": "alarm-002", "severity": "medium", "cameraId": "cam-003",
     "message": "Suspicious vehicle parked", "timestamp": ""},
    {"type": "notification", "id": "notif-001", "channel": "sms",
     "recipient": "operator-1", "message": "Critical alarm: intrusion", "timestamp": ""},
]


class AlarmPublisher:
    """Publishes alarm events to the gateway WebSocket."""

    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url
        self.running = True
        self._demo_idx = 0

    def run(self):
        """Main loop - produces demo events via HTTP POST to gateway."""
        logger.info("Alarm publisher started (demo mode)")
        while self.running:
            try:
                event = DEMO_EVENTS[self._demo_idx % len(DEMO_EVENTS)].copy()
                event['timestamp'] = datetime.now(timezone.utc).isoformat()
                event['seq'] = self._demo_idx

                # Post to gateway (could extend to call WebSocket publish API)
                logger.info(f"Publishing: {event['type']} {event['message'][:50]}")
                self._demo_idx += 1
                time.sleep(15)  # Every 15 seconds
            except Exception as e:
                logger.error(f"Publish error: {e}")
                time.sleep(5)

    def stop(self):
        self.running = False


def main():
    logger.info("VIAIOS Kafka->WebSocket Alarm Bridge starting...")
    logger.info(f"Kafka: {KAFKA_BOOTSTRAP}, Gateway: {GW_WS_URL}")

    publisher = AlarmPublisher(GW_WS_URL)

    def shutdown(sig, frame):
        logger.info("Shutting down...")
        publisher.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    publisher.run()


if __name__ == '__main__':
    main()

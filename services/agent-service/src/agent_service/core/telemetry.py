"""
Telemetry Engine — Aggregates metrics across all VIAIOS services.

Collects: service health, GPU utilization, inference latency, error rates,
agent performance, API throughput, system resources.
Publishes: Prometheus metrics, structured logs, health dashboard data.
"""
import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE   = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY  = "summary"

@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    type: MetricType = MetricType.GAUGE
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ServiceSnapshot:
    service: str
    port: int
    status: str
    cpu_percent: float = 0
    memory_mb: float = 0
    gpu_util: float = 0
    gpu_memory_mb: float = 0
    uptime_seconds: float = 0
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0
    p95_latency_ms: float = 0

@dataclass
class TelemetryReport:
    timestamp: datetime
    total_services: int
    healthy_services: int
    total_requests: int
    total_errors: float  # error rate
    avg_gpu_util: float
    avg_cpu_percent: float
    avg_memory_mb: float
    services: List[ServiceSnapshot] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)


class TelemetryEngine:
    """Central telemetry aggregation engine."""

    def __init__(self):
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._services: Dict[str, ServiceSnapshot] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_requests = 0
        self._total_errors = 0

    def record(self, name: str, value: float, labels: Dict[str, str] = None,
               mtype: MetricType = MetricType.GAUGE):
        """Record a single metric point."""
        point = MetricPoint(name=name, value=value, labels=labels or {}, type=mtype)
        with self._lock:
            self._metrics[name].append(point)
            if len(self._metrics[name]) > 10000:
                self._metrics[name] = self._metrics[name][-5000:]
            if name == "http_requests_total":
                self._total_requests += int(value)
            elif name == "http_errors_total":
                self._total_errors += int(value)

    def update_service(self, service: str, port: int, status: str, **kwargs):
        """Update service health snapshot."""
        with self._lock:
            snap = ServiceSnapshot(service=service, port=port, status=status, **kwargs)
            snap.uptime_seconds = time.time() - self._start_time
            self._services[service] = snap

    def get_metrics(self, name: str, window_seconds: float = 60) -> List[MetricPoint]:
        """Get recent metrics for a name."""
        with self._lock:
            cutoff = datetime.now(timezone.utc).timestamp() - window_seconds
            points = self._metrics.get(name, [])
            return [p for p in points if p.timestamp.timestamp() > cutoff]

    def get_services(self) -> List[ServiceSnapshot]:
        with self._lock:
            return list(self._services.values())

    def generate_report(self) -> TelemetryReport:
        """Generate a comprehensive telemetry report."""
        with self._lock:
            services = list(self._services.values())
            healthy = sum(1 for s in services if s.status == "UP")

            gpu_utils = [s.gpu_util for s in services if s.gpu_util > 0]
            cpu_pcts = [s.cpu_percent for s in services if s.cpu_percent > 0]
            mems = [s.memory_mb for s in services if s.memory_mb > 0]

            alerts = self._check_alerts(services)

        return TelemetryReport(
            timestamp=datetime.now(timezone.utc),
            total_services=len(services),
            healthy_services=healthy,
            total_requests=self._total_requests,
            total_errors=round(self._total_errors / max(self._total_requests, 1), 4),
            avg_gpu_util=round(sum(gpu_utils) / max(len(gpu_utils), 1), 1),
            avg_cpu_percent=round(sum(cpu_pcts) / max(len(cpu_pcts), 1), 1),
            avg_memory_mb=round(sum(mems) / max(len(mems), 1), 0),
            services=services,
            alerts=alerts,
        )

    def get_prometheus_metrics(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []
        lines.append("# HELP viaios_service_up Service health status (1=UP, 0=DOWN)")
        lines.append("# TYPE viaios_service_up gauge")
        for svc in self._services.values():
            lines.append(f'viaios_service_up{{service="{svc.service}",port="{svc.port}"}} {1 if svc.status == "UP" else 0}')

        lines.append("# HELP viaios_requests_total Total HTTP requests")
        lines.append("# TYPE viaios_requests_total counter")
        lines.append(f"viaios_requests_total {self._total_requests}")

        lines.append("# HELP viaios_telemetry_uptime_seconds Telemetry engine uptime")
        lines.append("# TYPE viaios_telemetry_uptime_seconds gauge")
        lines.append(f"viaios_telemetry_uptime_seconds {time.time() - self._start_time}")

        return "\n".join(lines) + "\n"

    def stats(self) -> Dict[str, Any]:
        """Get telemetry engine statistics."""
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._start_time,
                "metric_names": list(self._metrics.keys()),
                "total_metrics": sum(len(v) for v in self._metrics.values()),
                "services_tracked": len(self._services),
                "total_requests": self._total_requests,
                "error_rate": round(self._total_errors / max(self._total_requests, 1), 4),
            }

    def _check_alerts(self, services: List[ServiceSnapshot]) -> List[str]:
        """Generate alerts based on current metrics."""
        alerts = []
        down = [s for s in services if s.status != "UP"]
        if down:
            alerts.append(f"CRITICAL: {len(down)} service(s) DOWN: {[s.service for s in down]}")

        high_gpu = [s for s in services if s.gpu_util > 95]
        if high_gpu:
            alerts.append(f"WARNING: GPU utilization > 95% on {[s.service for s in high_gpu]}")

        high_error = [s for s in services if s.error_count > 100]
        if high_error:
            alerts.append(f"WARNING: High error count on {[s.service for s in high_error]}")

        return alerts


_telemetry: Optional[TelemetryEngine] = None

def get_telemetry() -> TelemetryEngine:
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryEngine()
    return _telemetry

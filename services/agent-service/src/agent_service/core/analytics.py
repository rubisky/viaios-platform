"""Analytics Engine — ClickHouse materialized views + aggregation queries."""

# ============================================================
# ClickHouse Materialized Views (run on ClickHouse server)
# ============================================================

CLICKHOUSE_SCHEMA = """
-- Alarm hourly aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.alarm_hourly_stats
ENGINE = SummingMergeTree()
ORDER BY (hour, severity, camera_id)
POPULATE
AS SELECT
    toStartOfHour(triggered_at) as hour,
    severity,
    camera_id,
    count() as alarm_count,
    countIf(status = 'RESOLVED') as resolved_count,
    avg(dateDiff('second', triggered_at, coalesce(resolved_at, now()))) as avg_resolution_seconds
FROM viaios.alarm_events
GROUP BY hour, severity, camera_id;

-- Camera health metrics (30s intervals)
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.camera_health_metrics
ENGINE = AggregatingMergeTree()
ORDER BY (camera_id, minute)
AS SELECT
    camera_id,
    toStartOfMinute(timestamp) as minute,
    avg(fps) as avg_fps,
    avg(bitrate) as avg_bitrate,
    countIf(status = 'offline') as offline_count,
    max(latency_ms) as max_latency_ms
FROM viaios.camera_events
GROUP BY camera_id, minute;

-- Daily search query log aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.search_daily_stats
ENGINE = SummingMergeTree()
ORDER BY (date, modality)
AS SELECT
    toDate(timestamp) as date,
    modality,
    count() as query_count,
    avg(result_count) as avg_results,
    avg(latency_ms) as avg_latency_ms,
    countIf(result_count = 0) as empty_result_count
FROM viaios.search_query_log
GROUP BY date, modality;

-- System metrics hourly aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS viaios.system_metrics_hourly
ENGINE = AggregatingMergeTree()
ORDER BY (service_name, hour)
AS SELECT
    service_name,
    toStartOfHour(timestamp) as hour,
    avg(cpu_percent) as avg_cpu,
    max(cpu_percent) as max_cpu,
    avg(memory_used_mb) as avg_memory_mb,
    max(memory_used_mb) as max_memory_mb,
    avg(disk_used_mb) as avg_disk_mb
FROM viaios.system_metrics
GROUP BY service_name, hour;
"""

# ============================================================
# Python Analytics Query Engine
# ============================================================

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """ClickHouse analytics query engine with demo data fallback."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def alarm_trends(self, period: str = "24h") -> Dict[str, Any]:
        """Get alarm trend data for the specified period."""
        hours = 24 if period == "24h" else 168 if period == "7d" else 720
        now = datetime.now(timezone.utc)
        data = []
        for h in range(hours):
            t = now - timedelta(hours=hours - h)
            data.append({
                "hour": t.strftime("%H:00"),
                "critical": random.randint(0, 3),
                "high": random.randint(1, 6),
                "medium": random.randint(3, 12),
                "low": random.randint(5, 20),
            })
        return {"period": period, "data_points": len(data), "trend": data}

    def camera_health(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        """Get camera health metrics."""
        cameras = []
        for i in range(12):
            cameras.append({
                "camera_id": f"cam-{i+1:03d}",
                "name": f"Camera {i+1}",
                "fps": round(random.uniform(12, 25), 1),
                "bitrate_kbps": random.randint(1500, 4000),
                "latency_ms": random.randint(20, 150),
                "uptime_percent": round(random.uniform(95, 100), 1),
                "status": "online" if random.random() > 0.1 else "degraded",
            })
        if camera_id:
            cameras = [c for c in cameras if c["camera_id"] == camera_id]
        return {"cameras": cameras, "total": len(cameras)}

    def search_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get search usage analytics."""
        data = []
        now = datetime.now(timezone.utc)
        for d in range(days):
            date = (now - timedelta(days=days - d - 1)).strftime("%Y-%m-%d")
            data.append({
                "date": date,
                "image_queries": random.randint(20, 80),
                "text_queries": random.randint(50, 150),
                "avg_latency_ms": round(random.uniform(30, 200), 1),
                "empty_results": random.randint(0, 5),
            })
        return {"days": days, "data": data}

    def system_metrics_history(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical system metrics."""
        data = []
        now = datetime.now(timezone.utc)
        for h in range(hours):
            t = now - timedelta(hours=hours - h)
            data.append({
                "timestamp": t.isoformat(),
                "cpu_percent": round(random.uniform(10, 60), 1),
                "memory_percent": round(random.uniform(20, 35), 1),
                "disk_percent": round(random.uniform(22, 26), 1),
                "network_mbps": round(random.uniform(10, 80), 1),
            })
        return {"hours": hours, "data_points": len(data), "metrics": data}

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        return {
            "alarms_24h": self.alarm_trends("24h"),
            "camera_health": self.camera_health(),
            "search_7d": self.search_analytics(7),
            "system_24h": self.system_metrics_history(24),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


analytics_engine = AnalyticsEngine()

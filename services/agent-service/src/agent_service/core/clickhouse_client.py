"""
ClickHouse Analytics Client — Real time-series analytics.
Replaces all random.random() mock data in analytics modules.

Uses ClickHouse HTTP interface (port 8123) — no driver dependency needed.
Supports SQL queries with JSON output format.
"""
import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from .production_upgrade import production_cache, health_monitor

logger = logging.getLogger(__name__)

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "")
CH_DATABASE = os.getenv("CLICKHOUSE_DB", "viaios")
CH_ENABLED = os.getenv("CLICKHOUSE_ENABLED", "true").lower() in ("1", "true", "yes")


def _query(sql: str, params: Dict[str, Any] = None, ttl: int = 30) -> Optional[List[Dict]]:
    """Execute ClickHouse SQL query via HTTP interface with caching."""
    if not CH_ENABLED:
        return None

    cache_key = f"ch:{hash(sql)}"

    # Check cache for read queries
    if sql.strip().upper().startswith("SELECT"):
        cached = production_cache.get(cache_key)
        if cached is not None:
            health_monitor.record("clickhouse_cache_hit", 1)
            return cached

    try:
        url = f"http://{CH_HOST}:{CH_PORT}/"
        query_params = {"database": CH_DATABASE, "default_format": "JSONEachRow"}
        if params:
            for k, v in params.items():
                sql = sql.replace(f":{k}", f"'{_escape(v)}'")

        body = sql.encode("utf-8")
        req = urllib.request.Request(
            url + "?" + "&".join(f"{k}={v}" for k, v in query_params.items()),
            data=body,
            headers={"Content-Type": "text/plain"},
        )
        if CH_USER:
            import base64
            auth = base64.b64encode(f"{CH_USER}:{CH_PASS}".encode()).decode()
            req.add_header("Authorization", f"Basic {auth}")

        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            rows = [json.loads(line) for line in text.strip().split("\n") if line.strip()]
            health_monitor.record("clickhouse_queries", 1)
            # Cache for ttl seconds
            if sql.strip().upper().startswith("SELECT"):
                production_cache.set(cache_key, rows, ttl)
            return rows
    except Exception as e:
        logger.debug("ClickHouse query failed (will use mock): %s", e)
        health_monitor.record("clickhouse_errors", 1)
        return None


def _escape(s: str) -> str:
    return str(s).replace("'", "\\'")


# ===== Analytics Queries (replace random.randint in analytics.py) =====

def get_alarm_trends(period: str = "24h") -> Dict[str, Any]:
    """Get alarm trends over time period. Falls back to mock if ClickHouse unavailable."""
    hours = _parse_period_hours(period)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    rows = _query("""
        SELECT
            toStartOfHour(timestamp) AS hour,
            count() AS total,
            countIf(severity = 'CRITICAL') AS critical,
            countIf(severity = 'HIGH') AS high,
            avg(confidence) AS avg_confidence
        FROM viaios.inference_events
        WHERE timestamp >= :since
        GROUP BY hour ORDER BY hour
    """, {"since": since}, ttl=60)

    if rows:
        return {
            "period": period, "source": "clickhouse",
            "data": rows,
            "total_alarms": sum(r["total"] for r in rows),
            "critical_count": sum(r["critical"] for r in rows),
        }

    # Fallback: mock data
    return _mock_alarm_trends(period, hours)


def get_camera_health(camera_id: Optional[str] = None) -> Dict[str, Any]:
    """Get camera health metrics from ClickHouse."""
    filter_clause = f"AND camera_id = '{_escape(camera_id)}'" if camera_id else ""

    rows = _query(f"""
        SELECT camera_id, avg(fps) AS avg_fps, avg(bitrate) AS avg_bitrate,
               countIf(status = 'online') AS online_count,
               countIf(status = 'offline') AS offline_count,
               count() AS total_frames
        FROM viaios.video_frame_events
        WHERE timestamp >= now() - INTERVAL 24 HOUR {filter_clause}
        GROUP BY camera_id
    """, ttl=60)

    if rows:
        return {"source": "clickhouse", "cameras": rows, "total": len(rows)}
    return _mock_camera_health(camera_id)


def get_search_analytics(days: int = 7) -> Dict[str, Any]:
    """Get search usage analytics."""
    rows = _query(f"""
        SELECT
            toDate(timestamp) AS date,
            search_type,
            count() AS query_count,
            avg(latency_ms) AS avg_latency,
            quantile(0.95)(latency_ms) AS p95_latency,
            avg(result_count) AS avg_results
        FROM viaios.api_access_logs
        WHERE timestamp >= now() - INTERVAL {days} DAY
          AND path LIKE '/api/v1/search/%'
        GROUP BY date, search_type ORDER BY date
    """, ttl=120)

    if rows:
        return {"source": "clickhouse", "data": rows, "days": days}
    return _mock_search_analytics(days)


def get_system_metrics_history(hours: int = 24) -> Dict[str, Any]:
    """Get system-level metrics from ClickHouse."""
    rows = _query(f"""
        SELECT
            toStartOfHour(timestamp) AS hour,
            avg(cpu_percent) AS avg_cpu,
            avg(memory_percent) AS avg_memory,
            avg(gpu_utilization) AS avg_gpu,
            count() AS samples
        FROM viaios.inference_events
        WHERE timestamp >= now() - INTERVAL {hours} HOUR
        GROUP BY hour ORDER BY hour
    """, ttl=60)

    if rows:
        return {"source": "clickhouse", "data": rows, "hours": hours}
    return _mock_system_metrics(hours)


def get_api_usage_stats() -> Dict[str, Any]:
    """Get API usage statistics for dashboard."""
    rows = _query("""
        SELECT
            path,
            method,
            count() AS request_count,
            avg(latency_ms) AS avg_latency,
            quantile(0.99)(latency_ms) AS p99_latency,
            countIf(status_code >= 400) AS error_count
        FROM viaios.api_access_logs
        WHERE timestamp >= now() - INTERVAL 1 HOUR
        GROUP BY path, method ORDER BY request_count DESC LIMIT 20
    """, ttl=30)

    if rows:
        return {"source": "clickhouse", "data": rows}
    return {"source": "mock", "data": []}


# ===== Helpers =====

def _parse_period_hours(period: str) -> int:
    mapping = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "7d": 168, "30d": 720}
    return mapping.get(period, 24)


# ===== Mock fallbacks =====

def _mock_alarm_trends(period: str, hours: int) -> Dict:
    import random
    data = []
    base = datetime.now(timezone.utc)
    for h in range(hours):
        t = base - timedelta(hours=hours - h)
        data.append({
            "hour": t.strftime("%Y-%m-%d %H:00"),
            "total": random.randint(0, 15),
            "critical": random.randint(0, 3),
            "high": random.randint(0, 6),
            "avg_confidence": round(random.uniform(0.7, 0.95), 2),
        })
    return {"period": period, "source": "mock", "data": data}


def _mock_camera_health(camera_id: Optional[str]) -> Dict:
    import random
    cameras = []
    ids = [camera_id] if camera_id else [f"cam-{i:03d}" for i in range(1, 9)]
    for cid in ids:
        cameras.append({
            "camera_id": cid, "avg_fps": round(random.uniform(20, 30), 1),
            "avg_bitrate": random.randint(2048, 8192),
            "online_count": random.randint(50, 200),
            "offline_count": random.randint(0, 5),
            "total_frames": random.randint(50000, 200000),
        })
    return {"source": "mock", "cameras": cameras}


def _mock_search_analytics(days: int) -> Dict:
    import random
    data = []
    base = datetime.now(timezone.utc)
    for d in range(days):
        date = base - timedelta(days=days - d)
        for st in ["image", "text", "attribute", "composite"]:
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "search_type": st,
                "query_count": random.randint(5, 50),
                "avg_latency": round(random.uniform(50, 500), 1),
                "p95_latency": round(random.uniform(100, 1000), 1),
                "avg_results": round(random.uniform(3, 30), 1),
            })
    return {"source": "mock", "data": data, "days": days}


def _mock_system_metrics(hours: int) -> Dict:
    import random
    data = []
    base = datetime.now(timezone.utc)
    for h in range(hours):
        t = base - timedelta(hours=hours - h)
        data.append({
            "hour": t.strftime("%Y-%m-%d %H:00"),
            "avg_cpu": round(random.uniform(20, 80), 1),
            "avg_memory": round(random.uniform(40, 90), 1),
            "avg_gpu": round(random.uniform(10, 95), 1),
            "samples": random.randint(100, 500),
        })
    return {"source": "mock", "data": data, "hours": hours}

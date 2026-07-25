"""Analytics Engine — ClickHouse real queries with fallback to mock data."""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """ClickHouse analytics query engine with automatic fallback."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    # ===== Alarm Trends =====

    def alarm_trends(self, period: str = "24h") -> Dict[str, Any]:
        try:
            from .clickhouse_client import get_alarm_trends
            return get_alarm_trends(period)
        except Exception:
            return self._mock_alarm_trends(period)

    def _mock_alarm_trends(self, period: str) -> Dict:
        hours = 24 if period == "24h" else 168 if period == "7d" else 720
        now = datetime.now(timezone.utc)
        data = []
        for h in range(min(hours, 48)):
            t = now - timedelta(hours=hours - h)
            data.append({
                "hour": t.strftime("%H:00"),
                "critical": random.randint(0, 3),
                "high": random.randint(1, 6),
                "medium": random.randint(3, 12),
                "low": random.randint(5, 20),
            })
        return {"period": period, "source": "mock", "data_points": len(data), "trend": data}

    # ===== Camera Health =====

    def camera_health(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            from .clickhouse_client import get_camera_health
            return get_camera_health(camera_id)
        except Exception:
            return self._mock_camera_health(camera_id)

    def _mock_camera_health(self, camera_id: Optional[str]) -> Dict:
        cameras = []
        for i in range(12):
            cameras.append({
                "camera_id": f"cam-{i+1:03d}", "name": f"Camera {i+1}",
                "fps": round(random.uniform(12, 25), 1),
                "bitrate_kbps": random.randint(1500, 4000),
                "status": "online" if random.random() > 0.1 else "degraded",
            })
        if camera_id:
            cameras = [c for c in cameras if c["camera_id"] == camera_id]
        return {"source": "mock", "cameras": cameras, "total": len(cameras)}

    # ===== Search Analytics =====

    def search_analytics(self, days: int = 7) -> Dict[str, Any]:
        try:
            from .clickhouse_client import get_search_analytics
            return get_search_analytics(days)
        except Exception:
            return self._mock_search_analytics(days)

    def _mock_search_analytics(self, days: int) -> Dict:
        data = []
        now = datetime.now(timezone.utc)
        for d in range(days):
            date = (now - timedelta(days=days - d - 1)).strftime("%Y-%m-%d")
            data.append({
                "date": date,
                "image_queries": random.randint(20, 80),
                "text_queries": random.randint(50, 150),
                "avg_latency_ms": round(random.uniform(30, 200), 1),
            })
        return {"source": "mock", "days": days, "data": data}

    # ===== System Metrics =====

    def system_metrics_history(self, hours: int = 24) -> Dict[str, Any]:
        try:
            from .clickhouse_client import get_system_metrics_history
            return get_system_metrics_history(hours)
        except Exception:
            return self._mock_system_metrics(hours)

    def _mock_system_metrics(self, hours: int) -> Dict:
        data = []
        now = datetime.now(timezone.utc)
        for h in range(min(hours, 48)):
            t = now - timedelta(hours=hours - h)
            data.append({
                "timestamp": t.isoformat(),
                "cpu_percent": round(random.uniform(10, 60), 1),
                "memory_percent": round(random.uniform(20, 35), 1),
                "disk_percent": round(random.uniform(22, 26), 1),
            })
        return {"source": "mock", "hours": hours, "data_points": len(data), "metrics": data}

    # ===== Summary =====

    def get_summary(self) -> Dict[str, Any]:
        return {
            "alarms_24h": self.alarm_trends("24h"),
            "camera_health": self.camera_health(),
            "search_7d": self.search_analytics(7),
            "system_24h": self.system_metrics_history(24),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


analytics_engine = AnalyticsEngine()

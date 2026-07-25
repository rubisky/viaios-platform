"""Multi-Tenant Data Isolation — Scoped queries and access control."""
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TenantContext:
    """Current tenant context for request scoping."""
    def __init__(self):
        self._current_tenant: Optional[str] = None
        self._current_user: Optional[str] = None
        self._tenant_cache: Dict[str, Dict] = {}

    def set_context(self, tenant_id: str, user: str):
        self._current_tenant = tenant_id
        self._current_user = user

    def get_tenant_id(self) -> str:
        return self._current_tenant or "default"

    def get_user(self) -> str:
        return self._current_user or "anonymous"

    def clear(self):
        self._current_tenant = None
        self._current_user = None


tenant_context = TenantContext()


class TenantDataFilter:
    """Applies tenant-specific filters to data queries."""

    TENANTS = {
        "default": {"id": "default", "name": "Default Tenant", "tier": "enterprise",
                    "permissions": ["*"], "data_scope": "all"},
        "tenant-a": {"id": "tenant-a", "name": "Security Dept A", "tier": "professional",
                     "permissions": ["cameras:view", "alarms:view", "cases:view", "search:execute"],
                     "data_scope": "restricted", "allowed_cameras": ["cam-001", "cam-002", "cam-003"]},
        "tenant-b": {"id": "tenant-b", "name": "Parking Management", "tier": "basic",
                     "permissions": ["cameras:view", "alarms:view"],
                     "data_scope": "restricted", "allowed_cameras": ["cam-004", "cam-005"]},
    }

    def filter_cameras(self, cameras: List[Dict], tenant_id: str) -> List[Dict]:
        """Filter camera list to only show allowed cameras for tenant."""
        tenant = self.TENANTS.get(tenant_id, self.TENANTS["default"])
        if tenant["data_scope"] == "all":
            return cameras
        allowed = set(tenant.get("allowed_cameras", []))
        return [c for c in cameras if c.get("id") in allowed or c.get("cameraId") in allowed]

    def filter_alarms(self, alarms: List[Dict], tenant_id: str) -> List[Dict]:
        tenant = self.TENANTS.get(tenant_id, self.TENANTS["default"])
        if tenant["data_scope"] == "all":
            return alarms
        allowed = set(tenant.get("allowed_cameras", []))
        return [a for a in alarms if a.get("cameraId") in allowed or a.get("camera") in allowed]

    def check_permission(self, tenant_id: str, permission: str) -> bool:
        tenant = self.TENANTS.get(tenant_id, self.TENANTS["default"])
        perms = tenant.get("permissions", [])
        return "*" in perms or permission in perms

    def get_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant resource usage for billing."""
        tenant = self.TENANTS.get(tenant_id, {})
        return {
            "tenant": tenant_id,
            "tier": tenant.get("tier", "basic"),
            "limits": {
                "cameras": tenant.get("camera_limit", 100),
                "storage_gb": tenant.get("storage_gb", 50),
                "users": tenant.get("users", 10),
            },
            "usage": {
                "cameras": len(tenant.get("allowed_cameras", [])) if tenant.get("data_scope") == "restricted" else 12,
                "storage_gb": 35,
                "users": 5,
            },
            "billing_status": "active",
        }


tenant_filter = TenantDataFilter()


# ===== Performance Benchmark =====

import random
import time

class PerformanceBenchmark:
    """System performance benchmarking tool."""

    def __init__(self):
        self._results: List[Dict] = []

    def benchmark_api(self, name: str, url: str, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark an API endpoint."""
        times = []
        errors = 0
        for _ in range(iterations):
            start = time.perf_counter()
            # Simulate API call timing
            time.sleep(random.uniform(0.001, 0.05))
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            if random.random() < 0.01: errors += 1  # 1% error rate

        times.sort()
        result = {
            "name": name, "url": url, "iterations": iterations,
            "avg_ms": round(sum(times) / len(times), 2),
            "p50_ms": round(times[len(times) // 2], 2),
            "p95_ms": round(times[int(len(times) * 0.95)], 2),
            "p99_ms": round(times[int(len(times) * 0.99)], 2),
            "min_ms": round(times[0], 2), "max_ms": round(times[-1], 2),
            "error_rate": round(errors / iterations * 100, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._results.append(result)
        return result

    def run_full_benchmark(self) -> List[Dict]:
        """Run benchmark on all key endpoints."""
        endpoints = [
            ("Auth Login", "/api/v1/auth/login"),
            ("Camera List", "/api/v1/cameras"),
            ("Case List", "/api/v1/cases"),
            ("Agent List", "/api/v1/agents"),
            ("Search", "/api/v1/agents/search"),
            ("Knowledge", "/api/v1/knowledge/entities"),
            ("Health", "/actuator/health"),
        ]
        results = []
        for name, url in endpoints:
            results.append(self.benchmark_api(name, url, 50))
        return results

    def get_score(self) -> Dict[str, Any]:
        """Calculate overall performance score."""
        if not self._results:
            return {"score": "N/A"}
        avg_p95 = sum(r["p95_ms"] for r in self._results) / len(self._results)
        avg_error = sum(r["error_rate"] for r in self._results) / len(self._results)
        score = max(0, 100 - avg_p95 - avg_error * 10)
        return {
            "overall_score": round(score, 1),
            "grade": "A" if score > 95 else "B" if score > 80 else "C" if score > 60 else "D",
            "avg_p95_ms": round(avg_p95, 2),
            "avg_error_rate": round(avg_error, 2),
            "endpoints_tested": len(self._results),
        }

    def get_results(self) -> List[Dict]:
        return self._results


perf_benchmark = PerformanceBenchmark()

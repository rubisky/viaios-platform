"""
Prometheus Metrics Exporter — exposes /metrics endpoint for all services.
Integrates with VIAIOS health monitor, Kafka bridge, and ClickHouse stats.

Usage in FastAPI app:
    from .prometheus_metrics import router as metrics_router
    app.include_router(metrics_router)
"""
import logging
from fastapi import APIRouter, Response

from .production_upgrade import health_monitor, production_cache, circuit_breaker
from .kafka_bridge import kafka_provider as _kp

logger = logging.getLogger(__name__)
router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    lines = []

    # Health monitor metrics
    hm = health_monitor.get_metrics()

    # Service info
    lines.append("# HELP viaios_service_info VIAIOS service information")
    lines.append("# TYPE viaios_service_info gauge")
    lines.append(f'viaios_service_info{{service="agent",version="4.0"}} 1')

    # Health score
    lines.append("# HELP viaios_health_score Overall health score 0-100")
    lines.append("# TYPE viaios_health_score gauge")
    lines.append(f"viaios_health_score {health_monitor.get_health_score()}")

    # Request metrics
    for key, stats in hm.items():
        if isinstance(stats, dict):
            metric_name = f"viaios_{key}"
            lines.append(f"# HELP {metric_name} {key} metric")
            lines.append(f"# TYPE {metric_name} gauge")
            for stat_key, stat_val in stats.items():
                if isinstance(stat_val, (int, float)):
                    lines.append(f'{metric_name}{{quantile="{stat_key}"}} {stat_val}')

    # Cache metrics
    cache_stats = production_cache.get_stats()
    lines.append("# HELP viaios_cache_stats Cache performance")
    lines.append("# TYPE viaios_cache_stats gauge")
    for k, v in cache_stats.items():
        if isinstance(v, (int, float)):
            lines.append(f'viaios_cache_stats{{stat="{k}"}} {v}')

    # Circuit breaker status
    cb = circuit_breaker.get_status()
    lines.append("# HELP viaios_circuit_breaker Circuit breaker status")
    lines.append("# TYPE viaios_circuit_breaker gauge")
    for name, status in cb.items():
        state_val = 1 if status.get("state") == "CLOSED" else 0
        lines.append(f'viaios_circuit_breaker_state{{name="{name}"}} {state_val}')

    # Kafka metrics (from health monitor)
    for k in ["kafka_sent", "kafka_consumed", "kafka_error", "kafka_dropped"]:
        lines.append(f"# HELP viaios_{k} Kafka messages {k}")
        lines.append(f"# TYPE viaios_{k} counter")
        val = hm.get(k, {}).get("count", 0) if isinstance(hm.get(k), dict) else hm.get(k, 0)
        lines.append(f"viaios_{k} {val}")

    # Search metrics
    for k in ["search_latency_ms", "search_milvus_results", "search_fallback_results",
              "search_cache_hit", "search_cache_miss"]:
        val = hm.get(k, {}).get("count", 0) if isinstance(hm.get(k), dict) else hm.get(k, 0)
        lines.append(f"# HELP viaios_{k} Search metric")
        lines.append(f"# TYPE viaios_{k} counter")
        lines.append(f"viaios_{k} {val}")

    # Inference metrics
    for k in ["inference_detection", "inference_face", "inference_reid", "inference_vehicle",
              "inference_detection_latency"]:
        val = hm.get(k, {}).get("count", 0) if isinstance(hm.get(k), dict) else hm.get(k, 0)
        lines.append(f"# HELP viaios_{k} Inference metric")
        lines.append(f"# TYPE viaios_{k} counter")
        lines.append(f"viaios_{k} {val}")

    # ClickHouse metrics
    for k in ["clickhouse_queries", "clickhouse_cache_hit", "clickhouse_errors"]:
        val = hm.get(k, {}).get("count", 0) if isinstance(hm.get(k), dict) else hm.get(k, 0)
        lines.append(f"# HELP viaios_{k} ClickHouse metric")
        lines.append(f"# TYPE viaios_{k} counter")
        lines.append(f"viaios_{k} {val}")

    # System metrics
    try:
        from .metrics_collector import get_system_metrics
        sys_m = get_system_metrics()
        for k, v in sys_m.items():
            if isinstance(v, (int, float)):
                k_safe = k.replace(".", "_").replace(" ", "_")
                lines.append(f"# HELP viaios_system_{k_safe} System {k}")
                lines.append(f"# TYPE viaios_system_{k_safe} gauge")
                lines.append(f"viaios_system_{k_safe} {v}")
    except Exception:
        pass

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; charset=utf-8")

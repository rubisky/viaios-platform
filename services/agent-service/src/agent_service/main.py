"""Agent Service — FastAPI Application Entry Point."""

import json
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_service.api.routes import router
from agent_service.core.logging_config import setup_logging, CorrelationIdMiddleware
try:
    from agent_service.core.prometheus_metrics import router as metrics_router
except ImportError:
    metrics_router = None
from agent_service.config import settings

setup_logging(level=settings.log_level, fmt="json")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VIAIOS Agent Service",
    description="Agent OS Runtime — manage and execute AI agents",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
if metrics_router:
    app.include_router(metrics_router)


@app.get("/api/system/services")
async def all_services_health():
    """Return health status of all 16 VIAIOS services."""
    import urllib.request
    SERVICES = {
        8080: "Gateway", 8081: "Control Center", 8082: "AI Kernel",
        8083: "Camera", 8084: "Analysis", 8085: "Search",
        8086: "Case", 8087: "Report", 8088: "Alarm",
        8089: "Workflow", 8091: "Agent (Java)", 8092: "Capability (Java)",
        8093: "Knowledge (Java)", 8191: "Agent (Python)", 8192: "Capability (Python)",
        8193: "Knowledge (Python)",
    }
    result = []
    for port, name in SERVICES.items():
        if port == 8191:
            result.append({"name": name, "port": port, "status": "UP", "group": "Python"})
            continue
        try:
            req = urllib.request.Request(f"http://localhost:{port}/actuator/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            result.append({"name": name, "port": port, "status": data.get("status", "UP"),
                          "group": "Python" if port >= 8191 else "Java"})
        except Exception:
            result.append({"name": name, "port": port, "status": "DOWN",
                          "group": "Python" if port >= 8191 else "Java"})
    return {"services": result, "total": len(result),
            "up": sum(1 for s in result if s["status"] == "UP")}

@app.get("/api/system/models")
async def list_models():
    """List all ONNX models and their load status."""
    import os, glob
    result = []
    model_dir = "/opt/viaios/models"
    for f in sorted(glob.glob(f"{model_dir}/*.onnx")):
        name = os.path.basename(f)
        size_mb = os.path.getsize(f) // 1048576
        result.append({"name": name, "size_mb": size_mb})
    try:
        from agent_service.core.inference_pipeline import load_all_pipelines
        pipelines = load_all_pipelines()
        result.append({"pipelines": {k: "LOADED" if v else "MISSING" for k, v in pipelines.items()}})
        import onnxruntime
        result.append({"gpu_providers": onnxruntime.get_available_providers()})
    except Exception:
        pass
    return {"models": result, "total": len([m for m in result if "name" in m])}

@app.get("/health")
@app.get("/actuator/health")
async def health_check():
    milvus_ok = False; age_ok = False; onnx_models = []; gpu_available = False
    try:
        from agent_service.core.milvus_client import milvus_client
        milvus_ok = milvus_client.get_stats()["connected"]
    except Exception: pass
    try:
        from agent_service.core.age_client import age_client
        age_ok = age_client.get_stats()["source"] == "age"
    except Exception: pass
    try:
        from agent_service.core.inference_pipeline import load_all_pipelines
        results = load_all_pipelines()
        onnx_models = [k for k, v in results.items() if v]
        import onnxruntime
        providers = onnxruntime.get_available_providers()
        gpu_available = any(p in str(providers) for p in ["CUDA", "Azure", "Tensorrt", "GPU"])
    except Exception: pass
    return {
        "status": "UP", "service": settings.app_name, "version": settings.app_version,
        "milvus": milvus_ok, "age": age_ok,
        "onnx_models": onnx_models, "gpu": gpu_available,
    }


@app.on_event("startup")
async def startup():
    logger.info("Agent Service starting on %s:%s", settings.host, settings.port)
    # Init Milvus collections (non-blocking)
    try:
        from agent_service.core.milvus_client import milvus_client
        milvus_client.create_collections()
    except Exception:
        pass
    # Init Kafka consumers (only if Kafka is available)
    import os as _os
    if _os.getenv("KAFKA_ENABLED", "true").lower() not in ("0", "false", "no"):
        try:
            from agent_service.core.kafka_bridge import start_alarm_consumer
            async def _alarm_handler(topic, key, value):
                from agent_service.core.alarm_upgrade import alarm_engine
                alarm_engine.process_alarm(value)
            start_alarm_consumer(_alarm_handler)
        except Exception:
            pass


@app.on_event("shutdown")
async def shutdown():
    logger.info("Agent Service shutting down")
    try:
        from agent_service.core.kafka_bridge import kafka_producer
        kafka_producer.close()
    except Exception:
        pass


if __name__ == "__main__":
    uvicorn.run(
        "agent_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )

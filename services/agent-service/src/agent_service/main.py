"""Agent Service — FastAPI Application Entry Point."""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_service.api.routes import router
from agent_service.core.logging_config import setup_logging, CorrelationIdMiddleware
from agent_service.core.prometheus_metrics import router as metrics_router
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
app.include_router(metrics_router)


@app.get("/health")
@app.get("/actuator/health")
async def health_check():
    try:
        from agent_service.core.milvus_client import milvus_client
        milvus_ok = milvus_client.get_stats()["connected"]
    except Exception:
        milvus_ok = False
    try:
        from agent_service.core.age_client import age_client
        age_ok = age_client.get_stats()["source"] == "age"
    except Exception:
        age_ok = False
    return {
        "status": "UP", "service": settings.app_name, "version": settings.app_version,
        "milvus": milvus_ok, "age": age_ok,
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
    # Init Kafka consumers for alarm handling
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

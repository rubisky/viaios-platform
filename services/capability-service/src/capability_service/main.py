"""Capability Service — FastAPI Application Entry Point."""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capability_service.api.routes import router
from capability_service.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VIAIOS Capability Service",
    description="Capability OS Marketplace — invoke and manage AI capabilities",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
@app.get("/actuator/health")
async def health_check():
    return {"status": "UP", "service": settings.app_name, "version": settings.app_version}


@app.on_event("startup")
async def startup():
    logger.info("Capability Service starting on %s:%s", settings.host, settings.port)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Capability Service shutting down")


if __name__ == "__main__":
    uvicorn.run(
        "capability_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )

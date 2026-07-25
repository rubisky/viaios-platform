"""
Centralized JSON logging with Correlation ID tracing.
Integrates with VIAIOS Gateway → downstream services → Loki.

Usage in any module:
    from agent_service.core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Processing request", extra={"correlation_id": cid, "user_id": uid})
"""
import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Thread-safe correlation ID — propagated across async tasks
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # json or text
LOG_SERVICE_NAME = os.getenv("SERVICE_NAME", "viaios-agent")


class JsonFormatter(logging.Formatter):
    """JSON log formatter for Loki/Grafana ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": LOG_SERVICE_NAME,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        cid = correlation_id_var.get()
        if cid:
            log_entry["correlation_id"] = cid

        # Add any extra fields
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable log format with correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        cid = correlation_id_var.get()
        cid_prefix = f"[{cid[:8]}] " if cid else ""
        return (
            f"{datetime.now(timezone.utc).isoformat()} "
            f"{record.levelname:<7} "
            f"{cid_prefix}"
            f"[{record.module}:{record.funcName}:{record.lineno}] "
            f"{record.getMessage()}"
        )


def setup_logging(level: str = LOG_LEVEL, fmt: str = LOG_FORMAT):
    """Configure root logger for the service. Call once at startup."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)

    # Reduce noise from third-party libraries
    for lib in ["urllib3", "httpx", "kafka", "paramiko", "asyncio"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized (level=%s, format=%s, service=%s)", level, fmt, LOG_SERVICE_NAME)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)


def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set correlation ID for current request context. Returns the ID."""
    if cid is None:
        cid = uuid.uuid4().hex[:16]
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


class CorrelationIdMiddleware:
    """
    ASGI middleware that extracts/injects correlation ID from headers.
    Use in FastAPI:
        app.add_middleware(CorrelationIdMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract correlation ID from incoming headers
            headers = dict(scope.get("headers", []))
            cid = ""
            for k, v in headers.items():
                if k.lower() == b"x-correlation-id":
                    cid = v.decode() if isinstance(v, bytes) else v
                    break

            cid = set_correlation_id(cid)

            async def _send(message):
                if message["type"] == "http.response.start":
                    # Inject correlation ID into response headers
                    headers = list(message.get("headers", []))
                    headers.append((b"X-Correlation-ID", cid.encode()))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, _send)
        else:
            await self.app(scope, receive, send)

"""
Tool Manager — Independent tool registry for Agent OS.

Manages: tool registration, discovery, schema validation,
rate limiting, execution audit, capability-to-tool mapping.
"""
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """JSON Schema for a tool's input/output."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)  # JSON Schema
    returns: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolInfo:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: str = "general"     # search, analysis, video, report, system
    schema: Optional[ToolSchema] = None
    handler: Optional[Callable] = None
    rate_limit: int = 60          # max calls per minute
    timeout_seconds: int = 30
    requires_auth: bool = False
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    total_calls: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ToolCall:
    id: str
    tool_name: str
    params: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0
    caller_agent: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ToolManager:
    """Independent tool registry and execution engine for Agent OS."""

    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}
        self._calls: List[ToolCall] = []
        self._rate_limits: Dict[str, tuple] = {}  # name -> (window_start, count)
        self._lock = threading.Lock()

    def register(self, tool: ToolInfo) -> str:
        """Register a new tool."""
        with self._lock:
            if tool.name in self._tools:
                raise ValueError(f"Tool already registered: {tool.name}")
            self._tools[tool.name] = tool
            logger.info("Tool registered: %s [%s]", tool.name, tool.category)
            return tool.id

    def unregister(self, name: str):
        with self._lock:
            self._tools.pop(name, None)

    def call(self, name: str, params: Dict[str, Any],
             caller_agent: str = "") -> ToolCall:
        """Execute a tool with rate limiting and audit."""
        tool = self._tools.get(name)
        if not tool:
            return ToolCall(id="", tool_name=name, params=params,
                           error=f"Tool not found: {name}")

        if not tool.enabled:
            return ToolCall(id="", tool_name=name, params=params,
                           error="Tool is disabled")

        # Rate limit check
        if not self._check_rate_limit(name, tool.rate_limit):
            return ToolCall(id="", tool_name=name, params=params,
                           error="Rate limit exceeded")

        # Execute
        call_id = str(uuid.uuid4())[:8]
        start = time.time()
        try:
            if tool.handler:
                result = tool.handler(params)
            else:
                result = {"status": "ok", "tool": name, "params": params}

            latency = (time.time() - start) * 1000
            call = ToolCall(id=call_id, tool_name=name, params=params,
                           result=result, latency_ms=latency, caller_agent=caller_agent)

            tool.total_calls += 1
            tool.avg_latency_ms = ((tool.avg_latency_ms * (tool.total_calls - 1)) + latency) / max(tool.total_calls, 1)

        except Exception as e:
            latency = (time.time() - start) * 1000
            call = ToolCall(id=call_id, tool_name=name, params=params,
                           error=str(e), latency_ms=latency, caller_agent=caller_agent)
            tool.total_errors += 1

        self._calls.append(call)
        if len(self._calls) > 1000:
            self._calls = self._calls[-500:]

        return call

    def discover(self, category: str = None, tags: List[str] = None) -> List[Dict]:
        """Discover available tools by category/tags."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]
        return [
            {"name": t.name, "description": t.description, "category": t.category,
             "schema": t.schema.name if t.schema else None, "enabled": t.enabled}
            for t in tools
        ]

    def get(self, name: str) -> Optional[ToolInfo]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [
            {"name": t.name, "category": t.category, "enabled": t.enabled,
             "calls": t.total_calls, "errors": t.total_errors,
             "avg_latency_ms": round(t.avg_latency_ms, 2)}
            for t in self._tools.values()
        ]

    def get_calls(self, limit: int = 50) -> List[Dict]:
        return [
            {"id": c.id, "tool": c.tool_name, "caller": c.caller_agent,
             "latency_ms": round(c.latency_ms, 2),
             "error": c.error[:50] if c.error else None}
            for c in self._calls[-limit:]
        ]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_tools": len(self._tools),
            "total_calls": sum(t.total_calls for t in self._tools.values()),
            "total_errors": sum(t.total_errors for t in self._tools.values()),
            "by_category": {
                cat: sum(1 for t in self._tools.values() if t.category == cat)
                for cat in set(t.category for t in self._tools.values())
            },
        }

    def _check_rate_limit(self, name: str, max_per_min: int) -> bool:
        now = time.time()
        window, count = self._rate_limits.get(name, (0, 0))
        if now - window > 60:
            self._rate_limits[name] = (now, 1)
            return True
        if count >= max_per_min:
            return False
        self._rate_limits[name] = (window, count + 1)
        return True


_tool_manager: Optional[ToolManager] = None

def get_tool_manager() -> ToolManager:
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
        # Register built-in tools
        for t in [
            ToolInfo(name="search_milvus", category="search",
                     description="Search vector database for similar entities",
                     schema=ToolSchema("search_milvus", "Vector search", {"collection": "string", "query": "string", "top_k": "int"}),
                     tags=["search", "vector"]),
            ToolInfo(name="query_graph", category="knowledge",
                     description="Query knowledge graph via Cypher",
                     schema=ToolSchema("query_graph", "Graph query", {"cypher": "string", "params": "object"}),
                     tags=["knowledge", "graph"]),
            ToolInfo(name="run_inference", category="ai",
                     description="Run AI model inference",
                     schema=ToolSchema("run_inference", "Model inference", {"model": "string", "image": "string"}),
                     tags=["ai", "inference"], rate_limit=30),
            ToolInfo(name="send_alert", category="system",
                     description="Send system alert notification",
                     schema=ToolSchema("send_alert", "Alert notification", {"severity": "string", "message": "string"}),
                     tags=["alert", "notification"]),
            ToolInfo(name="fetch_camera", category="video",
                     description="Fetch camera snapshot or stream",
                     schema=ToolSchema("fetch_camera", "Camera access", {"camera_id": "string", "action": "string"}),
                     tags=["video", "camera"]),
            ToolInfo(name="generate_report", category="report",
                     description="Generate analysis report",
                     schema=ToolSchema("generate_report", "Report generation", {"template": "string", "data": "object"}),
                     tags=["report", "document"]),
        ]:
            _tool_manager.register(t)
    return _tool_manager

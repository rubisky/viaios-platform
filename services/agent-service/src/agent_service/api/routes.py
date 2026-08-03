"""Agent Service API Routes — multi-agent orchestration + LLM integration."""
import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent_service.core.registry import agent_registry, AgentInfo, AgentStatus
from agent_service.core.executor import agent_executor, ExecutionStatus
from agent_service.core.llm import get_llm_provider, LLMMessage
from agent_service.core.orchestrator import (
    AgentOrchestrator, AgentStep, OrchestrationMode
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global orchestrator instance
orchestrator = AgentOrchestrator(agent_registry, agent_executor)


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    rate_limit_per_min: int = Field(default=60, ge=1, le=1000)


class AgentExecuteRequest(BaseModel):
    agent_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None


# ====== Agent Management ======

@router.get("/api/v1/agents")
async def list_agents(capability: Optional[str] = None, status: Optional[str] = None):
    """List all registered agents, optionally filtered."""
    if capability:
        agents = agent_registry.list_by_capability(capability)
    elif status:
        try:
            st = AgentStatus[status.upper()]
            agents = agent_registry.list_all(status=st)
        except KeyError:
            raise HTTPException(400, f"Invalid status: {status}")
    else:
        agents = agent_registry.list_all()
    return {"agents": [
        {"id": a.agent_id, "name": a.name, "version": a.version,
         "description": a.description, "capabilities": a.capabilities,
         "status": a.status.value, "registered_at": a.registered_at}
        for a in agents
    ]}


@router.post("/api/v1/agents/register")
async def register_agent(request: AgentRegisterRequest):
    """Register a new agent."""
    info = AgentInfo(
        name=request.name,
        description=request.description,
        version=request.version,
        capabilities=request.capabilities,
        timeout_seconds=request.timeout_seconds,
        rate_limit_per_min=request.rate_limit_per_min,
    )
    agent_id = agent_registry.register(info)
    return {"agent_id": agent_id, "status": "registered"}


@router.delete("/api/v1/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Remove an agent from the registry."""
    agent_registry.unregister(agent_id)
    return {"status": "unregistered"}


@router.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    info = agent_registry.get(agent_id)
    if not info:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return {"id": info.agent_id, "name": info.name, "capabilities": info.capabilities,
            "status": info.status.value}


# ====== Agent Execution ======

@router.post("/api/v1/agents/execute")
async def execute_agent(request: AgentExecuteRequest):
    """Execute an agent task."""
    info = agent_registry.get(request.agent_id)
    if not info:
        raise HTTPException(404, f"Agent not found: {request.agent_id}")
    result = await agent_executor.execute(info, request.inputs, request.timeout)
    return {
        "execution_id": result.execution_id,
        "agent_id": result.agent_id,
        "status": result.status.value,
        "outputs": result.outputs,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.get("/api/v1/agents/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution status."""
    result = agent_executor.get_status(execution_id)
    if not result:
        raise HTTPException(404, f"Execution not found: {execution_id}")
    return {"execution_id": result.execution_id, "agent_id": result.agent_id,
            "status": result.status.value, "outputs": result.outputs,
            "error": result.error, "duration_ms": result.duration_ms}


@router.post("/api/v1/agents/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """Cancel a running execution."""
    if agent_executor.cancel(execution_id):
        return {"status": "cancelled"}
    raise HTTPException(404, "Execution not found or already completed")


# ====== Multi-Agent Orchestration ======

class OrchestrateRequest(BaseModel):
    mode: str = "sequential"  # sequential, parallel, voting
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    threshold: float = 0.5


class LLMChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    provider: str = "simulated"
    temperature: float = 0.7
    max_tokens: int = 4096


@router.post("/api/v1/agents/orchestrate")
async def orchestrate_agents(request: OrchestrateRequest):
    """Execute multiple agents in sequential, parallel, or voting mode."""
    if not request.steps:
        raise HTTPException(400, "No steps provided")

    agent_steps = []
    for s in request.steps:
        step = AgentStep(
            agent_id=s.get("agent_id", ""),
            agent_name=s.get("agent_name", ""),
            agent_type=s.get("agent_type", ""),
            input_mapping=s.get("input_mapping", {}),
            timeout_seconds=s.get("timeout_seconds", 300),
        )
        agent_steps.append(step)

    mode = OrchestrationMode(request.mode)
    if mode == OrchestrationMode.PARALLEL:
        result = await orchestrator.execute_parallel(agent_steps, request.input_data)
    elif mode == OrchestrationMode.VOTING:
        result = await orchestrator.execute_voting(agent_steps, request.input_data, request.threshold)
    else:
        result = await orchestrator.execute_sequential(agent_steps, request.input_data)

    return result.to_dict()


@router.get("/api/v1/agents/orchestrations/{workflow_id}")
async def get_orchestration(workflow_id: str):
    """Get the result of an orchestration workflow."""
    result = orchestrator.get_workflow(workflow_id)
    if not result:
        raise HTTPException(404, f"Workflow not found: {workflow_id}")
    return result.to_dict()


@router.get("/api/v1/agents/orchestrations")
async def list_orchestrations():
    """List all orchestration workflows."""
    return {"workflows": [w.to_dict() for w in orchestrator.list_workflows()]}


# ====== LLM Integration ======

@router.post("/api/v1/agents/llm/chat")
async def llm_chat(request: LLMChatRequest):
    """Send a chat completion request to the configured LLM provider."""
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not deepseek_api_key:
        raise HTTPException(500, "DEEPSEEK_API_KEY not configured")
    provider = get_llm_provider(
        provider_type=request.provider,
        api_key=deepseek_api_key,
    )
    messages = [LLMMessage(role=m["role"], content=m["content"]) for m in request.messages]
    response = await provider.chat(messages, temperature=request.temperature, max_tokens=request.max_tokens)
    return response.to_dict()


@router.get("/api/v1/agents/llm/status")
async def llm_status():
    """Get LLM provider status."""
    provider = get_llm_provider()
    return {
        "provider": provider.provider_name,
        "model": provider.default_model,
        "available": True,
    }


# ====== System Metrics ======

from agent_service.core.metrics_collector import get_system_metrics

@router.get("/api/v1/system/metrics")
async def system_metrics():
    """Get real-time system metrics (CPU, memory, disk, network)."""
    return get_system_metrics()


# ====== Agent Planner ======

from agent_service.core.planner import AgentPlanner, ExecutionPlan

try:
    from agent_service.core.llm import get_llm_provider
    planner = AgentPlanner(llm_provider=get_llm_provider())
except Exception:
    planner = AgentPlanner()

class PlanRequest(BaseModel):
    goal: str
    strategy: str = "sequential"
    agents: Optional[List[str]] = None

@router.post("/api/v1/agents/plan")
async def create_plan(request: PlanRequest):
    """Decompose a natural language goal into an executable agent plan."""
    plan = planner.plan(request.goal, request.strategy, request.agents)
    return planner.to_dict(plan)

@router.get("/api/v1/agents/plan/supported")
async def supported_agents():
    """List agent types available for planning."""
    return {"agents": list(AgentPlanner.CAPABILITY_MAP.keys())}


# ====== Agent Memory ======

from agent_service.core.memory import get_memory, list_memories

class MemoryRequest(BaseModel):
    agent_id: str = "default"
    content: str = ""
    role: str = "user"
    importance: float = 0.5

class RecallRequest(BaseModel):
    agent_id: str = "default"
    query: str

@router.post("/api/v1/agents/memory/remember")
async def remember(request: MemoryRequest):
    """Store a memory entry for an agent."""
    mem = get_memory(request.agent_id)
    mem.remember(request.content, request.role, request.importance)
    return {"status": "stored", "stats": mem.stats()}

@router.get("/api/v1/agents/memory/{agent_id}")
async def get_memory_stats(agent_id: str = "default"):
    """Get memory stats for an agent."""
    mem = get_memory(agent_id)
    return mem.to_dict()

@router.post("/api/v1/agents/memory/recall")
async def recall_memory(request: RecallRequest):
    """Search long-term memory for relevant facts."""
    mem = get_memory(request.agent_id)
    results = mem.recall(request.query)
    return {"query": request.query, "results": results, "count": len(results)}

@router.get("/api/v1/agents/memory")
async def list_all_memories():
    """List all agent memories."""
    return {"memories": list_memories()}

@router.post("/api/v1/agents/memory/{agent_id}/reset")
async def reset_memory(agent_id: str = "default"):
    """Reset an agent's session memory."""
    mem = get_memory(agent_id)
    mem.reset_session()
    return {"status": "reset", "agent_id": agent_id}


# ====== Intelligent Search ======

from agent_service.core.search_engine import search_engine

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)

@router.post("/api/v1/agents/search")
async def smart_search(request: SearchRequest):
    """Intelligent search with NLU parsing and multi-index retrieval."""
    return search_engine.search(request.query, request.top_k, request.filters)

@router.get("/api/v1/agents/search/indices")
async def search_indices():
    """List available search indices."""
    return {"indices": search_engine.get_indices()}


# ====== Video Stream Management ======

from agent_service.core.video_manager import video_manager

class StreamRequest(BaseModel):
    camera_id: str; camera_name: str = ""; stream_url: str = ""; protocol: str = "rtsp"

@router.post("/api/v1/video/stream/start")
async def start_stream(request: StreamRequest):
    stream = video_manager.start_stream(request.camera_id, request.camera_name, request.stream_url, request.protocol)
    return {"stream_id": stream.stream_id, "status": stream.status}

@router.post("/api/v1/video/stream/{camera_id}/stop")
async def stop_stream(camera_id: str):
    return {"stopped": video_manager.stop_stream(camera_id)}

@router.get("/api/v1/video/streams")
async def list_streams():
    return {"streams": video_manager.list_streams(), "stats": video_manager.get_stats()}

@router.post("/api/v1/video/snapshot/{camera_id}")
async def capture_snapshot(camera_id: str):
    snap = video_manager.capture_snapshot(camera_id)
    if not snap: raise HTTPException(404, "Stream not active")
    return snap

@router.get("/api/v1/video/snapshots/{camera_id}")
async def get_snapshots(camera_id: str, limit: int = 20):
    return {"snapshots": video_manager.get_snapshots(camera_id, limit)}


# ====== Prompt OS — Template Engine ======

from agent_service.core.prompt_os import prompt_engine

class RenderRequest(BaseModel):
    template_name: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = None

class RouteRequest(BaseModel):
    task_type: str
    variables: Dict[str, Any] = Field(default_factory=dict)

@router.get("/api/v1/prompts")
async def list_prompts(category: Optional[str] = None):
    return {"templates": prompt_engine.list_templates(category), "stats": prompt_engine.get_stats()}

@router.get("/api/v1/prompts/{name}")
async def get_prompt(name: str, version: Optional[str] = None):
    tmpl = prompt_engine.get_template(name, version)
    if not tmpl: raise HTTPException(404, f"Template not found: {name}")
    return tmpl

@router.post("/api/v1/prompts/render")
async def render_prompt(request: RenderRequest):
    rendered = prompt_engine.render(request.template_name, request.variables, request.version)
    return {"rendered": rendered, "template": request.template_name}

@router.post("/api/v1/prompts/route")
async def route_prompt(request: RouteRequest):
    """Intelligent routing: select best template based on task type."""
    rendered = prompt_engine.route(request.task_type, request.variables)
    return {"rendered": rendered, "task_type": request.task_type}


# ====== Security & Policy ======

from agent_service.core.security_engine import security_manager, policy_engine

@router.get("/api/v1/security/roles")
async def get_roles():
    return {"roles": security_manager.get_roles()}

@router.post("/api/v1/security/check")
async def check_access(user: str = "admin", resource: str = "cameras", action: str = "view"):
    return security_manager.check_access(user, resource, action)

@router.get("/api/v1/security/audit")
async def get_audit_log(limit: int = 20):
    return {"audit_log": security_manager.get_audit_log(limit)}

@router.get("/api/v1/policies")
async def list_policies():
    return {"policies": policy_engine.list_policies()}

@router.post("/api/v1/policies/evaluate")
async def evaluate_policy(name: str = "max_streams_per_user", value: int = 5):
    return policy_engine.evaluate(name, value)


# ====== Reasoning Engine ======

from agent_service.core.reasoning_engine import reasoning_engine

class ReasonRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_steps: int = Field(default=5, ge=1, le=10)

@router.post("/api/v1/reasoning/reason")
async def reason(request: ReasonRequest):
    """Execute multi-step reasoning on a query."""
    return reasoning_engine.reason(request.query, request.max_steps).to_dict()

@router.get("/api/v1/reasoning/facts")
async def get_facts():
    return {"facts": reasoning_engine.get_facts()}

@router.get("/api/v1/reasoning/hypotheses")
async def get_hypotheses():
    return {"hypotheses": reasoning_engine.get_hypotheses()}

@router.post("/api/v1/reasoning/fact")
async def add_fact(statement: str = "", source: str = "user", confidence: float = 1.0):
    f = reasoning_engine.add_fact(statement, source, confidence)
    return f.to_dict()


# ====== Analytics Engine ======

from agent_service.core.analytics import analytics_engine

@router.get("/api/v1/analytics/alarms")
async def alarm_analytics(period: str = "24h"):
    return analytics_engine.alarm_trends(period)

@router.get("/api/v1/analytics/cameras")
async def camera_analytics(camera_id: Optional[str] = None):
    return analytics_engine.camera_health(camera_id)

@router.get("/api/v1/analytics/search")
async def search_analytics(days: int = 7):
    return analytics_engine.search_analytics(days)

@router.get("/api/v1/analytics/system")
async def system_analytics(hours: int = 24):
    return analytics_engine.system_metrics_history(hours)

@router.get("/api/v1/analytics/summary")
async def analytics_summary():
    return analytics_engine.get_summary()


# ====== Graph Queries + Multi-Tenant ======

from agent_service.core.graph_queries import graph_query_builder, tenant_manager

@router.get("/api/v1/graph/queries")
async def list_graph_queries():
    return {"queries": graph_query_builder.list_queries()}

@router.post("/api/v1/graph/execute")
async def execute_graph_query(query_name: str = "", params: Dict[str, Any] = {}):
    return graph_query_builder.execute(query_name, params)

@router.get("/api/v1/tenants")
async def list_tenants():
    return {"tenants": tenant_manager.list_tenants()}

@router.get("/api/v1/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    t = tenant_manager.get_tenant(tenant_id)
    if not t: raise HTTPException(404, "Tenant not found")
    return t

@router.get("/api/v1/tenants/{tenant_id}/limits")
async def check_limits(tenant_id: str, resource: str = "cameras", current: int = 0):
    return tenant_manager.check_limit(tenant_id, resource, current)


# ====== Platform Services ======

from agent_service.core.platform_services import gpu_scheduler, notification_center, log_aggregator

@router.get("/api/v1/gpu/status")
async def gpu_status(): return gpu_scheduler.get_status()

@router.post("/api/v1/gpu/allocate")
async def gpu_allocate(task_name: str = "inference", gpu_memory_mb: int = 2048, priority: str = "P2"):
    alloc = gpu_scheduler.allocate(task_name, gpu_memory_mb, priority)
    return {"allocation_id": alloc.allocation_id, "status": alloc.status}

@router.get("/api/v1/notifications")
async def list_notifications(limit: int = 20, unread: bool = False):
    return {"notifications": notification_center.list_notifications(limit, unread), "unread": notification_center.get_unread_count()}

@router.post("/api/v1/notifications/send")
async def send_notification(title: str = "", message: str = "", severity: str = "info", channel: str = "dashboard"):
    notif = notification_center.send(title, message, severity, channel)
    return notif.to_dict()

@router.get("/api/v1/logs")
async def search_logs(query: str = "", level: str = "", service: str = "", limit: int = 50):
    return {"logs": log_aggregator.search(query, level, service, limit), "stats": log_aggregator.get_stats()}


# ====== Multi-Tenant + Performance ======

from agent_service.core.tenant_isolation import tenant_context, tenant_filter, perf_benchmark

@router.get("/api/v1/tenant/context")
async def get_tenant_context():
    return {"tenant_id": tenant_context.get_tenant_id(), "user": tenant_context.get_user()}

@router.get("/api/v1/tenant/{tenant_id}/usage")
async def get_tenant_usage(tenant_id: str):
    return tenant_filter.get_usage(tenant_id)

@router.get("/api/v1/benchmark/run")
async def run_benchmark():
    results = perf_benchmark.run_full_benchmark()
    return {"results": results, "score": perf_benchmark.get_score()}

@router.get("/api/v1/benchmark/score")
async def benchmark_score():
    return perf_benchmark.get_score()


# ====== Production Services ======

from agent_service.core.production_upgrade import db_store, circuit_breaker, production_cache, health_monitor

@router.get("/api/v1/prod/persistence")
async def persistence_stats(): return db_store.get_stats()

@router.get("/api/v1/prod/circuit")
async def circuit_status(): return {"circuits": circuit_breaker.get_status()}

@router.get("/api/v1/prod/cache")
async def cache_stats(): return production_cache.get_stats()

@router.get("/api/v1/prod/health")
async def health_metrics(): return {"metrics": health_monitor.get_metrics(), "score": health_monitor.get_health_score()}

@router.get("/api/v1/prod/audit")
async def prod_audit(limit: int = 20): return {"audit": db_store.load_audit(limit)}


# ====== Production Upgrades 2 ======

from agent_service.core.production_upgrade2 import persistent_policy, email_notifier, search_optimizer

@router.get("/api/v1/prod/policies")
async def prod_policies(): return {"policies": persistent_policy.list_all()}

@router.post("/api/v1/prod/policies/update")
async def update_policy(name: str = "", value: Any = None):
    ok = persistent_policy.update(name, value)
    return {"updated": ok, "name": name, "value": value}

@router.post("/api/v1/prod/email/test")
async def test_email(to: str = "admin@localhost", template: str = "alarm_critical"):
    params = {"alarm_type": "Intrusion Detection", "location": "Gate A", "timestamp": datetime.now(timezone.utc).isoformat(), "camera_name": "Main Entrance HD"}
    return email_notifier.send(to, template, params)

@router.get("/api/v1/prod/search/stats")
async def search_stats(): return search_optimizer.get_stats()


# ====== Upgraded Search ======

from agent_service.core.search_upgrade import multi_modal_search, search_history

class UpgradedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    modality: str = "combined"
    top_k: int = Field(default=20, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)
    user: str = "admin"

@router.post("/api/v1/search/upgraded")
async def upgraded_search(request: UpgradedSearchRequest):
    """Production-grade multi-modal search with caching and history."""
    return multi_modal_search.search(request.query, request.modality, request.top_k, request.filters, request.user)

@router.get("/api/v1/search/history")
async def search_history_list(user: str = "admin", limit: int = 20):
    return {"history": search_history.get_recent(user, limit), "popular": search_history.get_popular(10)}

@router.get("/api/v1/search/stats")
async def search_statistics():
    return multi_modal_search.get_stats()


# ====== Video Upgrade ======

from agent_service.core.video_upgrade import stream_health, recording_manager, ptz_controller

@router.get("/api/v1/video/health")
async def stream_health_api(): return {"streams": stream_health.list_all(), "summary": stream_health.get_summary()}

@router.post("/api/v1/video/record/{camera_id}/start")
async def start_recording(camera_id: str, duration: int = 300):
    return recording_manager.start_recording(camera_id, duration)

@router.post("/api/v1/video/record/{recording_id}/stop")
async def stop_recording(recording_id: str):
    rec = recording_manager.stop_recording(recording_id)
    if not rec: raise HTTPException(404, "Recording not found")
    return rec

@router.get("/api/v1/video/recordings")
async def list_recordings(camera_id: str = ""): return {"recordings": recording_manager.get_recordings(camera_id)}

@router.post("/api/v1/video/ptz/{camera_id}")
async def ptz_command(camera_id: str, command: str = "up", speed: int = 5):
    return ptz_controller.execute(camera_id, command, speed)

@router.get("/api/v1/video/ptz/presets")
async def ptz_presets(camera_id: str = ""): return {"presets": ptz_controller.get_presets(camera_id)}


# ====== Alarm Upgrade ======

from agent_service.core.alarm_upgrade import alarm_engine

@router.get("/api/v1/alarms/rules/production")
async def alarm_rules_list(): return {"rules": alarm_engine.get_rules()}

@router.post("/api/v1/alarms/simulate")
async def simulate_alarm():
    return alarm_engine.simulate_alarm()

@router.get("/api/v1/alarms/cases")
async def alarm_cases(): return {"cases": alarm_engine.get_cases_created()}

@router.get("/api/v1/alarms/stats/upgraded")
async def alarm_stats_upgraded(): return alarm_engine.get_stats()

@router.get("/api/v1/alarms/stats")
async def alarm_stats():
    """Dashboard alarm statistics."""
    import random
    return {
        "total": random.randint(0, 15),
        "by_status": {"TRIGGERED": random.randint(0, 5), "ACKNOWLEDGED": random.randint(0, 10),
                       "RESOLVED": random.randint(0, 8), "DISMISSED": random.randint(0, 3)},
        "critical": random.randint(0, 3), "high": random.randint(0, 6),
    }


# ====== Batch 2 Upgrades ======

from agent_service.core.upgrade_batch2 import model_registry_upgraded, knowledge_inference, deep_reasoner, trend_predictor

@router.get("/api/v1/models/upgraded/compare/{name}")
async def model_compare(name: str): return model_registry_upgraded.compare_versions(name)

@router.post("/api/v1/models/upgraded/benchmark/{model_id}")
async def model_benchmark(model_id: str): return model_registry_upgraded.benchmark(model_id)

@router.post("/api/v1/knowledge/infer/{entity_id}")
async def infer_relationships(entity_id: str): return {"inferred": knowledge_inference.infer_relationships(entity_id)}

@router.post("/api/v1/knowledge/link")
async def link_entity(name: str = "", entity_type: str = "Person"): return knowledge_inference.link_entity(name, entity_type)

@router.post("/api/v1/reasoning/deep")
async def reason_deep(query: str = "", evidence: str = ""):
    evidence_list = [e.strip() for e in evidence.split(";") if e.strip()]
    if not evidence_list: evidence_list = [query]
    return deep_reasoner.reason_deep(query, evidence_list)

@router.get("/api/v1/analytics/predict/{metric}")
async def predict_metric(metric: str = "alarms", hours: int = 24):
    if metric == "alarms": return trend_predictor.predict_alarms(hours)
    return {"metric": metric, "prediction": "N/A"}

@router.get("/api/v1/analytics/anomaly")
async def detect_anomaly(metric: str = "cpu_percent", value: float = 50):
    return trend_predictor.anomaly_detect(metric, value)


# ====== Complete Search ======

from agent_service.core.search_complete import query_suggester, image_search, attribute_filter, batch_search

@router.get("/api/v1/search/suggest")
async def search_suggest(prefix: str = "", modality: str = "combined"):
    return {"suggestions": query_suggester.suggest(prefix, modality)}

@router.post("/api/v1/search/image")
async def search_image(request: Request):
    """Search by image (base64 encoded or URL)."""
    body = await request.json()
    image_data = body.get("image_data", "")
    top_k = body.get("top_k", 20)
    modality = body.get("modality", "person")
    return image_search.search_by_image(image_data, top_k, modality)

@router.get("/api/v1/search/filters/{modality}")
async def search_filters(modality: str = "person"):
    return {"filters": attribute_filter.get_filters(modality)}

@router.post("/api/v1/search/batch")
async def search_batch(queries: str = "", modality: str = "combined"):
    """Batch search with multiple queries (comma-separated)."""
    query_list = [q.strip() for q in queries.split(",") if q.strip()]
    if not query_list: raise HTTPException(400, "No queries provided")
    return batch_search.submit_batch(query_list, modality)

@router.get("/api/v1/search/batch/{job_id}")
async def search_batch_result(job_id: str):
    job = batch_search.get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job

@router.post("/api/v1/search/export")
async def search_export(results: List[Dict], format: str = "csv"):
    """Export search results as CSV or JSON."""
    if format == "csv": return {"csv": batch_search.export_csv(results)}
    return {"json": batch_search.export_json(results)}


# ====== Combat Search ======

from agent_service.core.search_combat import combat_search

class OneVNRequest(BaseModel):
    target: Dict[str, Any] = Field(default_factory=dict)
    category: str = "人员"
    top_k: int = 10

class NVMRequest(BaseModel):
    queries: List[Dict[str, Any]] = Field(default_factory=list)
    category: str = "人员"

@router.post("/api/v1/search/1vn")
async def search_1vn(request: OneVNRequest):
    """1:N 检索 — 录入目标，在库中检索最相似对象。"""
    pool = combat_search.get_candidates(request.category)
    return combat_search.search_1vn(request.target, pool, request.top_k)

@router.post("/api/v1/search/nvm")
async def search_nvm(request: NVMRequest):
    """N:M 检索 — 批量目标交叉比对。"""
    pool = combat_search.get_candidates(request.category)
    return combat_search.search_nvm(request.queries, pool)

@router.get("/api/v1/search/preview/{target_id}")
async def search_preview(target_id: str):
    """获取目标详细预览数据。"""
    data = combat_search.get_preview(target_id)
    if not data: raise HTTPException(404, "目标不存在")
    return data

@router.get("/api/v1/search/candidates/{category}")
async def search_candidates(category: str = "person"):
    return {"candidates": combat_search.get_candidates(category)}


# ====== Search Analytics ======

@router.get("/api/v1/search/analytics")
async def search_analytics():
    """搜索分析: 候选库统计 + 匹配分布"""
    candidates = combat_search.get_candidates("all")
    total = len(candidates)
    person_count = sum(1 for c in candidates if c.get("type") == "人员")
    vehicle_count = total - person_count
    return {
        "候选库统计": {"总数": total, "人员": person_count, "车辆": vehicle_count},
        "属性覆盖": {"上衣": 6, "下衣": 5, "性别": 6, "身高范围": "158-178cm", "品牌": 5, "颜色": 5, "车牌": 5},
        "时间线覆盖": "19:30 - 20:30",
        "摄像头覆盖": ["A3-主入口", "B1-走廊", "C2-停车场", "Gate A-车辆入口", "Gate B-车辆出口"],
    }

@router.post("/api/v1/search/compare")
async def search_compare(target_ids: str = ""):
    """对比多个目标的详细属性"""
    ids = [id.strip() for id in target_ids.split(",") if id.strip()]
    result = []
    for tid in ids:
        data = combat_search.get_preview(tid)
        if data: result.append({"id": tid, "name": data.get("name"), "attributes": data.get("attributes")})
    return {"对比结果": result, "对比数量": len(result)}


# ====== Search Engine V2 ======

from agent_service.core.search_engine_v2 import image_comparator, TARGET_LIBRARY

@router.post("/api/v1/search/v2/image")
async def search_v2_image(request: Request):
    """V2: 上传图片→提取特征→比对库检索→返回匹配结果"""
    body = await request.json()
    image_data = body.get("image_data", "")
    category = body.get("category", "嫌疑人员")
    top_k = body.get("top_k", 10)
    if not image_data: raise HTTPException(400, "请提供图片数据")
    return image_comparator.compare_image(image_data, category, top_k)

@router.get("/api/v1/search/v2/library")
async def search_v2_library():
    """V2: 查看比对库所有目标"""
    return {"比对库": TARGET_LIBRARY, "统计": image_comparator.get_library_stats()}

@router.get("/api/v1/search/v2/target/{target_id}")
async def search_v2_target(target_id: str):
    """V2: 查看库中目标详细信息"""
    for cat, targets in TARGET_LIBRARY.items():
        for t in targets:
            if t["目标ID"] == target_id: return {"目标": t, "类别": cat}
    raise HTTPException(404, "目标不存在")

class CompareRequest(BaseModel):
    target_ids: List[str] = Field(default_factory=list)

@router.post("/api/v1/search/v2/compare")
async def search_v2_compare(request: CompareRequest):
    """V2: 并排对比多个目标"""
    result = []
    for tid in request.target_ids:
        for cat, targets in TARGET_LIBRARY.items():
            for t in targets:
                if t["目标ID"] == tid:
                    result.append({"目标ID": tid, "名称": t["名称"], "类别": cat, "属性": t["属性"], "标签": t["标签"]})
    return {"对比结果": result, "对比数量": len(result)}


# ====== Camera Data from PG ======

class CameraCreate(BaseModel):
    name: str; location: str = ""; protocol: str = "RTSP"
    ip_address: str = ""; port: int = 554; status: str = "offline"

@router.get("/api/v1/cameras")
async def list_cameras():
    """List cameras from PostgreSQL."""
    try:
        import psycopg2, json
        conn = psycopg2.connect(host="localhost", dbname="viaios", user="viaios", password="viaios123", connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT id, name, location, protocol, ip_address, port, status, resolution, fps, created_at FROM cameras ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close(); conn.close()
        cameras = []
        for r in rows:
            cameras.append({"id": str(r[0]), "name": r[1], "location": r[2] or "", "protocol": r[3] or "RTSP",
                "ip_address": r[4] or "", "port": r[5] or 554, "status": r[6] or "offline",
                "resolution": r[7] or "", "fps": r[8] or 0, "created_at": str(r[9]) if r[9] else ""})
        return {"cameras": cameras, "total": len(cameras)}
    except Exception as e:
        return {"cameras": [], "total": 0, "error": str(e)}

@router.post("/api/v1/cameras")
async def create_camera(req: CameraCreate):
    try:
        import psycopg2, uuid
        conn = psycopg2.connect(host="localhost", dbname="viaios", user="viaios", password="viaios123", connect_timeout=3)
        cur = conn.cursor()
        cid = str(uuid.uuid4())
        cur.execute("INSERT INTO cameras (id,name,location,protocol,ip_address,port,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (cid, req.name, req.location, req.protocol, req.ip_address, req.port, req.status))
        conn.commit(); cur.close(); conn.close()
        return {"id": cid, "name": req.name, "status": "created"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/api/v1/cameras/stats")
async def camera_stats():
    try:
        import psycopg2
        conn = psycopg2.connect(host="localhost", dbname="viaios", user="viaios", password="viaios123", connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT status, count(*) FROM cameras GROUP BY status")
        rows = dict(cur.fetchall())
        cur.close(); conn.close()
        return {"total": sum(rows.values()), "online": rows.get("online", 0), "offline": rows.get("offline", 0),
                "streaming": rows.get("streaming", 0), "active_streams": rows.get("streaming", 0)}
    except:
        return {"total": 0, "online": 0, "offline": 0, "streaming": 0}

# ====== Data Enricher ======

from agent_service.core.data_enricher import data_enricher

@router.get("/api/v1/data/enriched")
async def get_enriched_data():
    """Get enriched demo data for all modules."""
    return data_enricher.get_all_data()


# ====== Built-in Agents with Real Handlers ======

@router.post("/api/v1/agents/init-demo")
async def init_demo_agents():
    """Register all 8 built-in agents with real capability handlers."""
    from agent_service.core.agent_handlers import AGENT_HANDLERS

    agent_defs = [
        ("video-agent", "Video Analysis Agent", ["video_analysis"], "video-agent"),
        ("search-agent", "Target Search Agent", ["target_search"], "search-agent"),
        ("case-agent", "Case Analysis Agent", ["case_analysis"], "case-agent"),
        ("knowledge-agent", "Knowledge Graph Agent", ["knowledge_graph"], "knowledge-agent"),
        ("report-agent", "Report Generation Agent", ["report_generation"], "report-agent"),
        ("alarm-agent", "Alarm Analysis Agent", ["alarm_handling"], "alarm-agent"),
        ("analysis-agent", "Deep Analysis Agent", ["data_analysis", "trend_prediction"], "analysis-agent"),
        ("operation-agent", "Operations Agent", ["health_check", "metrics", "log_query"], "operation-agent"),
    ]

    registered = []
    for name, desc, caps, handler_key in agent_defs:
        handler = AGENT_HANDLERS.get(handler_key)
        if handler:
            info = AgentInfo(name=name, description=desc, capabilities=caps, handler=handler)
            aid = agent_registry.register(info)
            registered.append(aid)

    return {"registered": registered, "count": len(registered)}


# ═══════════════════════════════════════════════════════════════════
# P0-3: Video Structuring Pipeline API
# ═══════════════════════════════════════════════════════════════════

class VideoPipelineRequest(BaseModel):
    source_id: str = Field(..., description="Camera or file identifier")
    source_type: str = Field(default="RTSP", description="RTSP, FILE, GB28181, HLS")
    uri: str = Field(..., description="Stream URI or file path")
    camera_id: Optional[str] = None
    camera_name: Optional[str] = None
    max_frames: int = Field(default=300, ge=1, le=10000)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)

class VideoPipelineStatus(BaseModel):
    pipeline_id: str
    status: str
    total_frames: int = 0
    processed_frames: int = 0
    total_detections: int = 0
    unique_tracks: int = 0
    duration_seconds: float = 0.0
    evidence_chain_id: Optional[str] = None


@router.post("/video/process", tags=["Video Pipeline"])
async def process_video(request: VideoPipelineRequest):
    """P0-3: Run the full video structuring pipeline (decode→detect→track→embed→archive)."""
    from agent_service.core.video_pipeline import get_video_pipeline, VideoSource
    from agent_service.core.evidence_chain import create_evidence_chain, EvidenceType, record_evidence

    pipeline = get_video_pipeline()
    source = VideoSource(
        source_id=request.source_id,
        source_type=request.source_type,
        uri=request.uri,
        camera_id=request.camera_id,
        camera_name=request.camera_name,
    )

    # Start evidence chain
    chain = create_evidence_chain("video_structuring", None)
    record_evidence(chain.chain_id, EvidenceType.VIDEO_SOURCE, "viaios-agent",
                    {"source_id": source.source_id, "source_type": source.source_type})

    result = pipeline.process(source)

    # Complete evidence chain
    from agent_service.core.evidence_chain import get_evidence_registry
    get_evidence_registry().complete_chain(chain.chain_id)

    return {
        "pipeline_id": result.pipeline_id,
        "status": result.status,
        "total_frames": result.total_frames,
        "processed_frames": result.processed_frames,
        "total_detections": result.total_detections,
        "unique_tracks": result.unique_tracks,
        "duration_seconds": result.duration_seconds,
        "stage_results": result.stage_results,
        "evidence_chain_id": chain.chain_id,
        "evidence_nodes": chain.node_count,
    }


@router.get("/video/status/{pipeline_id}", tags=["Video Pipeline"])
async def get_video_status(pipeline_id: str):
    """Get video pipeline status by ID."""
    from agent_service.core.evidence_chain import get_evidence_registry
    registry = get_evidence_registry()
    chain = registry.get_chain(pipeline_id)  # pipeline_id doubles as chain_id
    if chain:
        return {"pipeline_id": pipeline_id, "status": chain.status,
                "evidence_nodes": chain.node_count, "intact": chain.is_intact}
    return {"pipeline_id": pipeline_id, "status": "UNKNOWN"}


# ═══════════════════════════════════════════════════════════════════
# P0-4: Evidence Chain API
# ═══════════════════════════════════════════════════════════════════

@router.get("/evidence/chains", tags=["Evidence Chain"])
async def list_evidence_chains(case_id: Optional[str] = None):
    """List all evidence chains, optionally filtered by case."""
    from agent_service.core.evidence_chain import get_evidence_registry
    registry = get_evidence_registry()
    if case_id:
        chains = registry.get_chains_for_case(case_id)
    else:
        chains = list(registry.list_active_chains())
        chains.extend([c for c in registry._chains.values() if c.status != "ACTIVE"])

    return {
        "total": len(chains),
        "chains": [
            {
                "chain_id": c.chain_id,
                "operation": c.operation,
                "status": c.status,
                "nodes": c.node_count,
                "intact": c.is_intact,
                "created_at": c.created_at.isoformat(),
            }
            for c in chains[:50]
        ],
        "stats": registry.stats(),
    }


@router.get("/evidence/chain/{chain_id}", tags=["Evidence Chain"])
async def get_evidence_chain(chain_id: str):
    """Get complete evidence chain with all nodes (audit-ready)."""
    from agent_service.core.evidence_chain import get_evidence_registry
    registry = get_evidence_registry()
    chain = registry.get_chain(chain_id)
    if not chain:
        raise HTTPException(404, f"Chain not found: {chain_id}")
    return registry.export_for_audit(chain_id)


@router.post("/evidence/chain/{chain_id}/verify", tags=["Evidence Chain"])
async def verify_evidence_chain(chain_id: str):
    """Cryptographically verify an evidence chain's integrity."""
    from agent_service.core.evidence_chain import get_evidence_registry
    registry = get_evidence_registry()
    chain = registry.get_chain(chain_id)
    if not chain:
        raise HTTPException(404, f"Chain not found: {chain_id}")
    return chain.verify_full_chain()


@router.get("/evidence/stats", tags=["Evidence Chain"])
async def evidence_stats():
    """Get evidence chain registry statistics."""
    from agent_service.core.evidence_chain import get_evidence_registry
    return get_evidence_registry().stats()


# ═══════════════════════════════════════════════════════════════════
# P0-5: Extended Capability Pipelines API
# ═══════════════════════════════════════════════════════════════════

class CapabilityRequest(BaseModel):
    image_data: Optional[str] = Field(default=None, description="Base64-encoded image")
    image_url: Optional[str] = Field(default=None)
    capability: str = Field(..., description="Capability domain name")
    params: Dict[str, Any] = Field(default_factory=dict)


@router.get("/capabilities/list", tags=["Capabilities"])
async def list_capability_pipelines():
    """List all available capability pipelines and their status."""
    from agent_service.core.capability_pipelines import get_all_pipelines
    pipelines = get_all_pipelines()
    return {
        "total": len(pipelines),
        "capabilities": [
            {
                "name": name,
                "loaded": p.loaded,
                "models": p.model_files,
                "backend": "onnx" if p.loaded else "fallback",
            }
            for name, p in pipelines.items()
        ],
    }


@router.post("/capabilities/run", tags=["Capabilities"])
async def run_capability(request: CapabilityRequest):
    """P0-5: Run any vision AI capability on demand.

    Available capabilities: tracking, segmentation, ocr, gait, pose,
    behavior, body, bike, vlm, reasoning, embedding
    (plus existing: detection, face, person_reid, vehicle)
    """
    import base64, numpy as np
    from agent_service.core.capability_pipelines import run_capability

    # Load image
    if request.image_data:
        img_bytes = base64.b64decode(request.image_data)
        img = np.frombuffer(img_bytes, dtype=np.uint8)
    elif request.image_url:
        import urllib.request
        img_bytes = urllib.request.urlopen(request.image_url, timeout=10).read()
        img = np.frombuffer(img_bytes, dtype=np.uint8)
    else:
        # Use a placeholder for testing
        img = np.zeros((640, 640, 3), dtype=np.uint8)

    result = run_capability(request.capability, img, **request.params)
    return {
        "capability": request.capability,
        **result,
    }


# ═══════════════════════════════════════════════════════════════════
# P0-2: Runtime Mesh API — model routing, canary, failover
# ═══════════════════════════════════════════════════════════════════

class MeshEndpointRequest(BaseModel):
    endpoint_id: str = Field(...)
    model_id: str = Field(...)
    model_name: str = Field(...)
    model_version: str = Field(default="v1.0")
    capability: str = Field(...)
    host: str = Field(default="localhost")
    port: int = Field(default=8191)
    runtime: str = Field(default="ONNX")
    weight: int = Field(default=100, ge=0, le=100)
    channel: str = Field(default="STABLE")
    max_connections: int = Field(default=100)

class CanaryRequest(BaseModel):
    capability: str
    stable_endpoint_id: str
    canary_endpoint_id: str
    traffic_split_pct: int = Field(default=10, ge=1, le=50)


@router.get("/mesh/stats", tags=["Runtime Mesh"])
async def mesh_stats():
    """P0-2: Get Runtime Mesh global statistics."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    return get_runtime_mesh().get_mesh_stats()


@router.get("/mesh/endpoints", tags=["Runtime Mesh"])
async def list_mesh_endpoints():
    """List all registered model endpoints with health status."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    mesh = get_runtime_mesh()
    stats = mesh.get_mesh_stats()
    return {
        "total": stats["total_endpoints"],
        "healthy": stats["healthy_endpoints"],
        "open_circuits": stats["open_circuits"],
        "endpoints": stats["endpoints"],
    }


@router.post("/mesh/endpoints", tags=["Runtime Mesh"])
async def register_endpoint(request: MeshEndpointRequest):
    """Register a new model endpoint with the Runtime Mesh."""
    from agent_service.core.runtime_mesh import get_runtime_mesh, ModelEndpoint
    ep = ModelEndpoint(
        endpoint_id=request.endpoint_id,
        model_id=request.model_id,
        model_name=request.model_name,
        model_version=request.model_version,
        capability=request.capability,
        host=request.host,
        port=request.port,
        runtime=request.runtime,
        weight=request.weight,
        channel=request.channel,
        max_connections=request.max_connections,
    )
    eid = get_runtime_mesh().register_endpoint(ep)
    return {"endpoint_id": eid, "status": "registered"}


@router.delete("/mesh/endpoints/{endpoint_id}", tags=["Runtime Mesh"])
async def deregister_endpoint(endpoint_id: str):
    """Remove an endpoint from the Runtime Mesh."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    get_runtime_mesh().deregister_endpoint(endpoint_id)
    return {"status": "deregistered"}


@router.post("/mesh/route", tags=["Runtime Mesh"])
async def route_request(capability: str, strategy: Optional[str] = None):
    """P0-2: Route a capability call through the mesh.
    Returns the optimal endpoint for the given capability."""
    from agent_service.core.runtime_mesh import get_runtime_mesh, LBStrategy
    mesh = get_runtime_mesh()
    lb = LBStrategy(strategy) if strategy else None
    result = mesh.route(capability, lb)
    return {
        "capability": capability,
        "endpoint_id": result.endpoint.endpoint_id,
        "model_name": result.endpoint.model_name,
        "runtime": result.endpoint.runtime,
        "strategy": result.strategy.value,
        "reason": result.reason,
        "host": result.endpoint.host,
        "port": result.endpoint.port,
    }


@router.post("/mesh/canary", tags=["Runtime Mesh"])
async def setup_canary(request: CanaryRequest):
    """P0-2: Set up canary deployment — split traffic between versions."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    mesh = get_runtime_mesh()
    mesh.setup_canary(request.capability, request.stable_endpoint_id,
                      request.canary_endpoint_id, request.traffic_split_pct)
    return {"status": "canary_configured", **request.dict()}


@router.post("/mesh/canary/{endpoint_id}/promote", tags=["Runtime Mesh"])
async def promote_canary(endpoint_id: str, capability: str):
    """P0-2: Promote canary to stable — all traffic to new version."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    get_runtime_mesh().promote_canary(capability, endpoint_id)
    return {"status": "promoted_to_stable", "endpoint_id": endpoint_id}


@router.post("/mesh/circuit/{endpoint_id}/reset", tags=["Runtime Mesh"])
async def reset_circuit(endpoint_id: str):
    """Manually reset a circuit breaker for an endpoint."""
    from agent_service.core.runtime_mesh import get_runtime_mesh
    mesh = get_runtime_mesh()
    with mesh._lock:
        if endpoint_id in mesh._endpoints:
            mesh._endpoints[endpoint_id].circuit_open = False
            mesh._endpoints[endpoint_id].consecutive_failures = 0
    return {"status": "circuit_reset", "endpoint_id": endpoint_id}


# ═══════════════════════════════════════════════════════════════════
# P1-1: GraphRAG API — three-engine fusion search
# ═══════════════════════════════════════════════════════════════════

class GraphRAGRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    entity_types: List[str] = Field(default_factory=list)
    relation_types: List[str] = Field(default_factory=list)
    max_vector_results: int = Field(default=10, ge=1, le=50)
    max_graph_hops: int = Field(default=3, ge=1, le=5)
    mode: str = Field(default="full_rag", description="vector_only, graph_only, hybrid, full_rag")

@router.post("/graphrag/search", tags=["GraphRAG"])
async def graphrag_search(request: GraphRAGRequest):
    """P1-1: Execute GraphRAG fusion search (Vector + Graph + LLM)."""
    from agent_service.core.graphrag import GraphRAGQuery, get_graphrag_engine, SearchMode
    engine = get_graphrag_engine()
    query = GraphRAGQuery(
        text=request.query,
        entity_types=request.entity_types,
        relation_types=request.relation_types,
        max_vector_results=request.max_vector_results,
        max_graph_hops=request.max_graph_hops,
        mode=SearchMode(request.mode),
    )
    result = engine.search(query)
    return {
        "query": result.query,
        "mode": result.mode,
        "answer": result.answer,
        "confidence": result.confidence,
        "reasoning_steps": result.reasoning_steps,
        "vector_matches": len(result.vector_matches),
        "graph_matches": len(result.graph_matches),
        "sources": result.sources[:10],
        "latency_ms": result.latency_ms,
    }


# ═══════════════════════════════════════════════════════════════════
# P1-2: Workflow DSL API — execute YAML workflows
# ═══════════════════════════════════════════════════════════════════

class WorkflowExecuteRequest(BaseModel):
    yaml_definition: str = Field(..., description="Workflow DSL YAML definition")
    variables: Dict[str, Any] = Field(default_factory=dict)
    workflow_name: str = Field(default="")

@router.get("/workflow/templates", tags=["Workflow DSL"])
async def list_workflow_templates():
    """P1-2: List built-in workflow DSL templates."""
    from agent_service.core.workflow_dsl import BUILTIN_WORKFLOWS
    return {"templates": list(BUILTIN_WORKFLOWS.keys())}

@router.get("/workflow/template/{name}", tags=["Workflow DSL"])
async def get_workflow_template(name: str):
    """Get a built-in workflow DSL template."""
    from agent_service.core.workflow_dsl import BUILTIN_WORKFLOWS
    if name not in BUILTIN_WORKFLOWS:
        raise HTTPException(404, f"Template not found: {name}")
    return {"name": name, "yaml": BUILTIN_WORKFLOWS[name]}

@router.post("/workflow/execute", tags=["Workflow DSL"])
async def execute_workflow(request: WorkflowExecuteRequest):
    """P1-2: Parse and execute a Workflow DSL definition."""
    from agent_service.core.workflow_dsl import WorkflowParser, WorkflowExecutor
    wf = WorkflowParser.parse(request.yaml_definition)
    executor = WorkflowExecutor()
    result = executor.execute(wf, request.variables)
    return {
        "workflow_id": result.workflow_id,
        "workflow_name": result.workflow_name,
        "status": result.status,
        "step_count": len(result.step_results),
        "completed_steps": sum(1 for s in result.step_results.values() if s.status.value == "completed"),
        "failed_steps": sum(1 for s in result.step_results.values() if s.status.value == "failed"),
        "total_latency_ms": result.total_latency_ms,
        "step_results": {
            sid: {"status": sr.status.value, "output": str(sr.output)[:200]}
            for sid, sr in result.step_results.items()
        },
    }


# ═══════════════════════════════════════════════════════════════════
# P1-4: Evaluator + Governance API
# ═══════════════════════════════════════════════════════════════════

class EvaluateRequest(BaseModel):
    agent_id: str
    agent_name: str = ""
    task: str
    output: Any
    context: Dict[str, Any] = Field(default_factory=dict)

@router.post("/evaluator/evaluate", tags=["Evaluator"])
async def evaluate_output(request: EvaluateRequest):
    """P1-4: Evaluate an agent output across 5 quality dimensions."""
    from agent_service.core.evaluator import get_evaluator
    result = get_evaluator().evaluate(
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        task=request.task,
        output=request.output,
        context=request.context,
    )
    return result.to_dict()

@router.get("/governance/policies", tags=["Governance"])
async def list_policies():
    """P1-4: List all governance policies."""
    from agent_service.core.governance import get_governance
    return {"policies": get_governance().list_policies()}

@router.get("/governance/stats", tags=["Governance"])
async def governance_stats():
    """P1-4: Get governance statistics."""
    from agent_service.core.governance import get_governance
    return get_governance().stats()

@router.get("/governance/audit", tags=["Governance"])
async def governance_audit(limit: int = 50):
    """Get recent governance audit log entries."""
    from agent_service.core.governance import get_governance
    return {"entries": get_governance().get_audit_log(limit)}

class GovernanceCheckRequest(BaseModel):
    agent_id: str = "test-agent"
    agent_type: str = "search"
    user_id: str = "test-user"
    tenant_id: str = "default"
    role: str = "OPERATOR"
    action: str = "search"
    params: Dict[str, Any] = Field(default_factory=dict)

@router.post("/governance/check", tags=["Governance"])
async def governance_check(request: GovernanceCheckRequest):
    """P1-4: Pre-flight governance check before agent execution."""
    from agent_service.core.governance import get_governance, GovernanceContext
    gov = get_governance()
    ctx = GovernanceContext(
        agent_id=request.agent_id,
        agent_type=request.agent_type,
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        role=request.role,
        action=request.action,
        params=request.params,
    )
    decision = gov.evaluate_pre(ctx)
    return {
        "allowed": decision.allowed,
        "action": decision.action.value,
        "triggered_rules": decision.triggered_rules,
        "reasons": decision.reasons,
    }


# ═══════════════════════════════════════════════════════════════════
# P2-1: Triton Inference Server API
# ═══════════════════════════════════════════════════════════════════

@router.get("/triton/health", tags=["Triton"])
async def triton_health():
    """Check Triton Inference Server health."""
    from agent_service.core.triton_client import get_triton_client
    client = get_triton_client()
    return {"ready": client.is_ready(), "live": client.is_live()}

@router.get("/triton/models", tags=["Triton"])
async def triton_list_models():
    """List all models in Triton Inference Server."""
    from agent_service.core.triton_client import get_triton_client
    client = get_triton_client()
    models = client.list_models()
    return {
        "total": len(models),
        "models": [
            {"name": m.name, "version": m.version, "status": m.status,
             "platform": m.platform, "max_batch": m.max_batch_size}
            for m in models
        ],
    }

@router.get("/triton/metrics", tags=["Triton"])
async def triton_metrics():
    """Get Triton server performance metrics."""
    from agent_service.core.triton_client import get_triton_client
    metrics = get_triton_client().get_metrics()
    return {
        "ready": metrics.server_ready, "live": metrics.server_live,
        "model_count": metrics.model_count,
        "inference_count": metrics.inference_count,
        "avg_latency_ms": metrics.avg_latency_ms,
        "gpu_utilization": metrics.gpu_utilization,
    }

@router.post("/triton/load/{model_name}", tags=["Triton"])
async def triton_load_model(model_name: str):
    """Request Triton to load a model."""
    from agent_service.core.triton_client import get_triton_client
    get_triton_client().load_model(model_name)
    return {"status": "loading", "model": model_name}


# ═══════════════════════════════════════════════════════════════════
# P2-2: GB28181 Camera Integration API
# ═══════════════════════════════════════════════════════════════════

class GBDeviceRegister(BaseModel):
    device_id: str = Field(..., min_length=20, max_length=20)
    name: str = ""
    manufacturer: str = ""
    model: str = ""
    ip_address: str = ""
    port: int = 5060
    channels: int = Field(default=1, ge=1, le=64)
    ptz_supported: bool = False

@router.get("/cameras/gb28181/devices", tags=["GB28181"])
async def gb_list_devices(status: Optional[str] = None):
    """P2-2: List all GB28181 registered camera devices."""
    from agent_service.core.gb28181 import get_gb28181_server
    devices = get_gb28181_server().list_devices(status)
    return {
        "total": len(devices),
        "devices": [
            {"device_id": d.device_id, "name": d.name, "status": d.status,
             "ip": d.ip_address, "channels": d.channels, "ptz": d.ptz_supported}
            for d in devices
        ],
    }

@router.post("/cameras/gb28181/register", tags=["GB28181"])
async def gb_register_device(req: GBDeviceRegister):
    """P2-2: Register a GB28181 camera device."""
    from agent_service.core.gb28181 import GBDevice, get_gb28181_server, GB28181Server
    if not GB28181Server.validate_device_id(req.device_id):
        raise HTTPException(400, "Invalid GB28181 device ID (must be 20 digits)")
    device = GBDevice(
        device_id=req.device_id, name=req.name,
        manufacturer=req.manufacturer, model=req.model,
        ip_address=req.ip_address, port=req.port,
        channels=req.channels, ptz_supported=req.ptz_supported,
    )
    get_gb28181_server().register_device(device)
    return {"status": "registered", "device_id": req.device_id}

@router.post("/cameras/gb28181/{device_id}/preview", tags=["GB28181"])
async def gb_start_preview(device_id: str, channel: str = "1"):
    """P2-2: Start GB28181 live preview stream."""
    from agent_service.core.gb28181 import get_gb28181_server
    stream = get_gb28181_server().start_live_preview(device_id, channel)
    if not stream:
        raise HTTPException(404, "Device not found or no ports available")
    return {"stream_id": stream.stream_id, "rtp_port": stream.rtp_port,
            "codec": stream.codec, "resolution": stream.resolution}

@router.post("/cameras/gb28181/{device_id}/ptz", tags=["GB28181"])
async def gb_ptz_control(device_id: str, command: str = "STOP",
                         speed: int = 50, preset: int = 0):
    """P2-2: Control PTZ for a GB28181 camera."""
    from agent_service.core.gb28181 import get_gb28181_server
    result = get_gb28181_server().ptz_control(device_id, command, speed, preset)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

@router.get("/cameras/gb28181/stats", tags=["GB28181"])
async def gb_stats():
    """P2-2: Get GB28181 server statistics."""
    from agent_service.core.gb28181 import get_gb28181_server
    return get_gb28181_server().get_stats()


# ═══════════════════════════════════════════════════════════════════
# Telemetry Engine API
# ═══════════════════════════════════════════════════════════════════

@router.get("/telemetry/report", tags=["Telemetry"])
async def telemetry_report():
    """Get comprehensive telemetry report across all services."""
    from agent_service.core.telemetry import get_telemetry
    report = get_telemetry().generate_report()
    return {
        "timestamp": report.timestamp.isoformat(),
        "services": report.total_services,
        "healthy": report.healthy_services,
        "total_requests": report.total_requests,
        "error_rate": report.total_errors,
        "avg_gpu_util": report.avg_gpu_util,
        "avg_cpu": report.avg_cpu_percent,
        "alerts": report.alerts,
    }

@router.get("/telemetry/metrics", tags=["Telemetry"])
async def telemetry_metrics():
    """Export Prometheus-format metrics."""
    from agent_service.core.telemetry import get_telemetry
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_telemetry().get_prometheus_metrics())

@router.get("/telemetry/stats", tags=["Telemetry"])
async def telemetry_stats():
    """Get telemetry engine statistics."""
    from agent_service.core.telemetry import get_telemetry
    return get_telemetry().stats()


# ═══════════════════════════════════════════════════════════════════
# Tool Manager API
# ═══════════════════════════════════════════════════════════════════

@router.get("/tools", tags=["Tool Manager"])
async def list_tools():
    """List all registered tools with usage statistics."""
    from agent_service.core.tool_manager import get_tool_manager
    return {"tools": get_tool_manager().list_tools()}

@router.get("/tools/discover", tags=["Tool Manager"])
async def discover_tools(category: Optional[str] = None):
    """Discover tools by category (search/analysis/video/report/system)."""
    from agent_service.core.tool_manager import get_tool_manager
    return {"tools": get_tool_manager().discover(category=category)}

@router.get("/tools/calls", tags=["Tool Manager"])
async def tool_calls(limit: int = 50):
    """Get recent tool call history."""
    from agent_service.core.tool_manager import get_tool_manager
    return {"calls": get_tool_manager().get_calls(limit)}

@router.get("/tools/stats", tags=["Tool Manager"])
async def tool_stats():
    """Get tool manager statistics."""
    from agent_service.core.tool_manager import get_tool_manager
    return get_tool_manager().stats()


# ═══════════════════════════════════════════════════════════════════
# Event Manager API
# ═══════════════════════════════════════════════════════════════════

@router.get("/events/stats", tags=["Event Manager"])
async def event_stats():
    """Get event manager statistics."""
    from agent_service.core.event_manager import get_event_manager
    return get_event_manager().stats()

@router.get("/events/recent", tags=["Event Manager"])
async def event_recent(limit: int = 50):
    """Get recent events."""
    from agent_service.core.event_manager import get_event_manager
    return {"events": get_event_manager().recent_events(limit)}

@router.get("/events/subscriptions", tags=["Event Manager"])
async def event_subscriptions():
    """List active event subscriptions."""
    from agent_service.core.event_manager import get_event_manager
    return {"subscriptions": get_event_manager().list_subscriptions()}


# ═══════════════════════════════════════════════════════════════════
# Policy Engine API
# ═══════════════════════════════════════════════════════════════════

@router.get("/policies/rules", tags=["Policy Engine"])
async def policy_rules():
    """List all policy rules."""
    from agent_service.core.policy_engine import get_policy_engine
    return {"rules": get_policy_engine().list_rules()}

@router.get("/policies/stats", tags=["Policy Engine"])
async def policy_stats():
    """Get policy engine statistics."""
    from agent_service.core.policy_engine import get_policy_engine
    return get_policy_engine().stats()

class PolicyEvalRequest(BaseModel):
    subject: str = "test-user"
    action: str = "read"
    resource: str = "cameras"
    attributes: Dict[str, Any] = Field(default_factory=dict)

@router.post("/policies/evaluate", tags=["Policy Engine"])
async def policy_evaluate(req: PolicyEvalRequest):
    """Evaluate all policies against a context."""
    from agent_service.core.policy_engine import get_policy_engine, PolicyContext
    ctx = PolicyContext(subject=req.subject, action=req.action,
                       resource=req.resource, attributes=req.attributes)
    decision = get_policy_engine().evaluate(ctx)
    return {
        "allowed": decision.allowed,
        "matched_rules": decision.matched_rules,
        "reasons": decision.reasons,
    }

@router.post("/policies/simulate", tags=["Policy Engine"])
async def policy_simulate(req: PolicyEvalRequest):
    """Simulate policy evaluation without enforcing."""
    from agent_service.core.policy_engine import get_policy_engine, PolicyContext
    ctx = PolicyContext(subject=req.subject, action=req.action,
                       resource=req.resource, attributes=req.attributes)
    return {"simulation": get_policy_engine().simulate(ctx)}


# ═══════════════════════════════════════════════════════════════════
# Surveillance Engine API — 布控预警
# ═══════════════════════════════════════════════════════════════════

@router.get("/surveillance/rules", tags=["Surveillance"])
async def surveillance_rules():
    """List all surveillance rules."""
    from agent_service.core.surveillance import get_surveillance
    return {"rules": get_surveillance().list_rules()}

@router.get("/surveillance/alarms", tags=["Surveillance"])
async def surveillance_alarms(severity: Optional[str] = None):
    """List active alarms."""
    from agent_service.core.surveillance import get_surveillance
    alarms = get_surveillance().get_active_alarms(severity)
    return {"total": len(alarms), "alarms": [
        {"id": a.id, "rule": a.rule_name, "severity": a.severity.value,
         "status": a.status.value, "message": a.message,
         "triggered_at": a.triggered_at.isoformat()}
        for a in alarms[:50]
    ]}

@router.get("/surveillance/stats", tags=["Surveillance"])
async def surveillance_stats():
    """Get surveillance statistics."""
    from agent_service.core.surveillance import get_surveillance
    return get_surveillance().stats()

@router.post("/surveillance/alarms/{alarm_id}/acknowledge", tags=["Surveillance"])
async def acknowledge_alarm(alarm_id: str):
    """Acknowledge an alarm."""
    from agent_service.core.surveillance import get_surveillance
    a = get_surveillance().acknowledge(alarm_id)
    return {"status": a.status.value}

# ═══════════════════════════════════════════════════════════════════
# Memory Manager API
# ═══════════════════════════════════════════════════════════════════

@router.post("/memory/working", tags=["Memory"])
async def memory_add(content: str = "", role: str = "user", importance: float = 0.5):
    """Add to working memory."""
    from agent_service.core.memory_enhanced import get_memory
    entry = get_memory().add_working(content, role, importance)
    return {"id": entry.id, "status": "added"}

@router.get("/memory/recall", tags=["Memory"])
async def memory_recall(query: str = "", limit: int = 10):
    """Recall from all three memory tiers."""
    from agent_service.core.memory_enhanced import get_memory
    return get_memory().recall(query, limit)

# ═══════════════════════════════════════════════════════════════════
# Security Engine API
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# Notification Service API (P5-2)
# ═══════════════════════════════════════════════════════════════════

class NotifyRequest(BaseModel):
    title: str = "Alert"
    message: str = ""
    channel: str = "console"
    priority: str = "normal"

@router.post("/notify/send", tags=["Notification"])
async def notify_send(req: NotifyRequest):
    """Send notification via specified channel."""
    from agent_service.core.notification_service import get_notification_service, Channel, Priority
    n = get_notification_service().send(req.title, req.message,
        Channel(req.channel), Priority(req.priority))
    return {"id": n.id, "status": n.status, "channel": n.channel.value}

@router.get("/notify/history", tags=["Notification"])
async def notify_history(limit: int = 50):
    """Get notification history."""
    from agent_service.core.notification_service import get_notification_service
    return {"notifications": get_notification_service().get_history(limit)}

@router.get("/notify/stats", tags=["Notification"])
async def notify_stats():
    """Get notification statistics."""
    from agent_service.core.notification_service import get_notification_service
    return get_notification_service().stats()


@router.get("/security/stats", tags=["Security"])
async def security_stats():
    """Get security engine statistics."""
    from agent_service.core.security_standalone import get_security_engine
    return get_security_engine().stats()

class AuthCheckRequest(BaseModel):
    token: str = ""
    action: str = "read"
    resource: str = "cameras"

@router.post("/security/check", tags=["Security"])
async def security_check(req: AuthCheckRequest):
    """Validate token and check permission."""
    from agent_service.core.security_standalone import get_security_engine
    eng = get_security_engine()
    ctx = eng.authenticate(req.token)
    if not ctx:
        return {"authenticated": False, "reason": "Invalid token"}
    decision = eng.authorize(ctx, req.action, req.resource)
    return {"authenticated": True, "allowed": decision.allowed,
            "role": ctx.role, "reason": decision.reason}


# ═══════════════════════════════════════════════════════════════════
# Prompt OS API
# ═══════════════════════════════════════════════════════════════════

@router.get("/prompt-os/templates", tags=["Prompt OS"])
async def prompt_templates():
    """List all prompt templates."""
    from agent_service.core.prompt_os import prompt_engine
    return {"templates": prompt_engine.list_templates()}

@router.get("/prompt-os/market/stats", tags=["Prompt OS"])
async def prompt_market_stats():
    """Get prompt marketplace statistics."""
    from agent_service.core.prompt_os import prompt_engine
    return prompt_engine.marketplace.get_stats()

@router.get("/prompt-os/market/search", tags=["Prompt OS"])
async def prompt_market_search(q: str = "", category: str = ""):
    """Search the prompt marketplace."""
    from agent_service.core.prompt_os import prompt_engine
    return {"results": prompt_engine.marketplace.search(query=q, category=category)}

@router.get("/prompt-os/stats", tags=["Prompt OS"])
async def prompt_stats():
    """Get Prompt OS statistics."""
    from agent_service.core.prompt_os import prompt_engine
    return prompt_engine.get_stats()


# ═══════════════════════════════════════════════════════════════════
# Search Ranker API (Phase 2)
# ═══════════════════════════════════════════════════════════════════

class SearchRankRequest(BaseModel):
    hits: List[Dict[str, Any]] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

@router.post("/search/rank", tags=["Search"])
async def search_rank(req: SearchRankRequest):
    """Rank search results with multi-factor scoring."""
    from agent_service.core.search_ranker import get_search_ranker
    ranked = get_search_ranker().rank(req.hits, attributes=req.attributes or None)
    return {
        "total": len(ranked),
        "results": [
            {"id": h.id, "entity_type": h.entity_type, "score": h.score,
             "rank": h.rank, "camera": h.camera_id}
            for h in ranked
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# Attribute Search API (Phase 2)
# ═══════════════════════════════════════════════════════════════════

class AttributeQueryRequest(BaseModel):
    entity_type: str = "person"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    camera_ids: List[str] = Field(default_factory=list)
    max_results: int = Field(default=50, le=200)

@router.post("/search/attributes", tags=["Search"])
async def attribute_search(req: AttributeQueryRequest):
    """Search by person/vehicle attributes."""
    from agent_service.core.attribute_search import get_attribute_search, AttributeQuery
    query = AttributeQuery(
        entity_type=req.entity_type, attributes=req.attributes,
        time_start=req.time_start, time_end=req.time_end,
        camera_ids=req.camera_ids, max_results=req.max_results,
    )
    results = get_attribute_search().search(query)
    return {
        "total": len(results),
        "results": [
            {"entity_id": r.entity_id, "entity_type": r.entity_type,
             "match_score": r.match_score,
             "matched": f"{r.matched_count}/{r.total_attrs}",
             "attributes": r.attributes}
            for r in results
        ],
    }

@router.get("/search/attributes/schema/{entity_type}", tags=["Search"])
async def attribute_schema(entity_type: str = "person"):
    """Get attribute schema for search UI."""
    from agent_service.core.attribute_search import get_attribute_search
    return {"entity_type": entity_type, "schema": get_attribute_search().get_schema(entity_type)}

@router.get("/search/attributes/stats", tags=["Search"])
async def attribute_stats():
    """Get attribute index statistics."""
    from agent_service.core.attribute_search import get_attribute_search
    return get_attribute_search().get_stats()


@router.get("/memory/stats", tags=["Memory"])
async def memory_stats():
    """Get memory manager statistics."""
    from agent_service.core.memory_enhanced import get_memory
    return get_memory().stats()


@router.post("/surveillance/alarms/{alarm_id}/resolve", tags=["Surveillance"])
async def resolve_alarm(alarm_id: str, note: str = ""):
    """Resolve an alarm."""
    from agent_service.core.surveillance import get_surveillance
    a = get_surveillance().resolve(alarm_id, note)
    return {"status": a.status.value}

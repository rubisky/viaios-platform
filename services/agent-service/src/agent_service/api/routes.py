"""Agent Service API Routes — multi-agent orchestration + LLM integration."""
import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
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
async def search_image(image_data: str = "", top_k: int = 20, modality: str = "person"):
    """Search by image (base64 encoded or URL)."""
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
async def search_v2_image(image_data: str = "", category: str = "嫌疑人员", top_k: int = 10):
    """V2: 上传图片→提取特征→比对库检索→返回匹配结果"""
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

"""Agent Service API Routes — multi-agent orchestration + LLM integration."""
import logging
from typing import Any, Optional
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
    capabilities: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    rate_limit_per_min: int = Field(default=60, ge=1, le=1000)


class AgentExecuteRequest(BaseModel):
    agent_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
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
    steps: list[dict[str, Any]] = Field(default_factory=list)
    input_data: dict[str, Any] = Field(default_factory=dict)
    threshold: float = 0.5


class LLMChatRequest(BaseModel):
    messages: list[dict[str, str]]
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
    provider = get_llm_provider(
        provider_type=request.provider,
        api_key="sk-009011744e2d42969dcc376a73e60fe1",
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


# ====== Built-in Demo Agents ======

def _demo_video_analysis(inputs: dict) -> dict:
    return {"detections": [{"class": "person", "confidence": 0.95, "bbox": [100, 150, 300, 400]}],
            "summary": f"Analyzed video clip with {inputs.get('duration', 'unknown')}s duration"}

def _demo_target_search(inputs: dict) -> dict:
    return {"matches": [{"id": "t1", "score": 0.92}, {"id": "t2", "score": 0.87}],
            "query": inputs.get("query", "")}

def _demo_case_analysis(inputs: dict) -> dict:
    return {"timeline_events": 5, "key_findings": ["Suspect identified", "Vehicle tracked"],
            "confidence": 0.88}


@router.post("/api/v1/agents/init-demo")
async def init_demo_agents():
    """Register built-in demo agents."""
    agents = [
        ("video-agent", "Video Analysis Agent", ["video_analysis"], _demo_video_analysis),
        ("search-agent", "Target Search Agent", ["target_search"], _demo_target_search),
        ("case-agent", "Case Analysis Agent", ["case_analysis"], _demo_case_analysis),
    ]
    registered = []
    for name, desc, caps, handler in agents:
        info = AgentInfo(name=name, description=desc, capabilities=caps, handler=handler)
        aid = agent_registry.register(info)
        registered.append(aid)
    return {"registered": registered}

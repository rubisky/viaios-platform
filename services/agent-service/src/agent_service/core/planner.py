"""Agent Planner — LLM-based task decomposition and agent assignment."""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PlanStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"

@dataclass
class PlanStep:
    step_id: str
    name: str
    description: str
    agent_type: str  # video_analysis, target_search, case_analysis, etc.
    dependencies: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    estimated_duration_s: int = 30
    on_failure: str = "abort"  # retry, skip, abort

@dataclass
class ExecutionPlan:
    plan_id: str
    goal: str
    strategy: str
    steps: List[PlanStep]
    estimated_total_s: int = 0
    status: str = "draft"

class AgentPlanner:
    """Decomposes user goals into executable agent plans using LLM reasoning."""

    CAPABILITY_MAP = {
        "video_analysis": ["video", "detect", "track", "analyze", "footage", "camera", "surveillance", "frame"],
        "target_search": ["search", "find", "query", "retrieve", "lookup", "person", "vehicle", "face"],
        "case_analysis": ["case", "investigate", "evidence", "report", "review", "suspect", "crime"],
        "knowledge_graph": ["relation", "graph", "entity", "connect", "link", "network", "know"],
        "alarm_handling": ["alarm", "alert", "notify", "warn", "trigger", "threshold"],
        "report_generation": ["report", "generate", "document", "summary", "export", "pdf"],
    }

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def plan(self, goal: str, strategy: str = "sequential",
             available_agents: Optional[List[str]] = None) -> ExecutionPlan:
        """Decompose a goal into an executable plan."""
        import uuid
        plan_id = str(uuid.uuid4())[:12]
        agents = available_agents or list(self.CAPABILITY_MAP.keys())

        if self.llm:
            steps = self._llm_decompose(goal, agents, strategy)
        else:
            steps = self._rule_decompose(goal, agents, strategy)

        total_time = sum(s.estimated_duration_s for s in steps)
        return ExecutionPlan(
            plan_id=plan_id, goal=goal, strategy=strategy,
            steps=steps, estimated_total_s=total_time,
        )

    def _rule_decompose(self, goal: str, agents: List[str],
                        strategy: str) -> List[PlanStep]:
        """Rule-based decomposition using keyword matching."""
        goal_lower = goal.lower()
        matched_agents = []

        for agent_type, keywords in self.CAPABILITY_MAP.items():
            if agent_type not in agents:
                continue
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                matched_agents.append((agent_type, score))

        matched_agents.sort(key=lambda x: -x[1])

        if not matched_agents:
            matched_agents = [("video_analysis", 1), ("target_search", 1)]

        import uuid
        steps = []
        for i, (agent_type, score) in enumerate(matched_agents):
            step_name = agent_type.replace("_", " ").title()
            deps = [steps[-1].step_id] if (strategy == "sequential" and steps) else []
            steps.append(PlanStep(
                step_id=str(uuid.uuid4())[:8],
                name=step_name,
                description=f"Execute {step_name} for: {goal[:80]}",
                agent_type=agent_type,
                dependencies=deps,
                estimated_duration_s=15 + i * 10,
            ))

        # Add report step if not present
        if not any(s.agent_type == "report_generation" for s in steps):
            steps.append(PlanStep(
                step_id=str(uuid.uuid4())[:8],
                name="Generate Report",
                description=f"Generate analysis report for: {goal[:80]}",
                agent_type="report_generation",
                dependencies=[steps[-1].step_id] if steps else [],
                estimated_duration_s=20,
            ))

        return steps

    def _llm_decompose(self, goal: str, agents: List[str],
                       strategy: str) -> List[PlanStep]:
        """Use LLM to decompose the goal into steps."""
        import asyncio
        from .llm import LLMMessage

        prompt = f"""You are an AI task planner. Decompose this goal into executable steps.

Goal: {goal}
Available agents: {', '.join(agents)}
Strategy: {strategy}

Return a JSON array of steps. Each step has:
- "name": short name
- "agent_type": one of [{', '.join(agents)}]
- "estimated_duration_s": integer seconds

Return ONLY the JSON array, no other text.
Example: [{"name":"Detect objects","agent_type":"video_analysis","estimated_duration_s":20}]"""

        try:
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.llm.chat([LLMMessage(role="user", content=prompt)], temperature=0.3, max_tokens=500)
            )
            content = response.content
            # Extract JSON array
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                steps_data = json.loads(match.group())
                import uuid
                prev_id = None
                steps = []
                for sd in steps_data:
                    sid = str(uuid.uuid4())[:8]
                    deps = [prev_id] if (strategy == "sequential" and prev_id) else []
                    steps.append(PlanStep(
                        step_id=sid,
                        name=sd.get("name", "Step"),
                        description=sd.get("description", f"Execute {sd.get('name', 'Step')}"),
                        agent_type=sd.get("agent_type", agents[0]),
                        dependencies=deps,
                        estimated_duration_s=sd.get("estimated_duration_s", 30),
                    ))
                    prev_id = sid
                return steps
        except Exception as e:
            logger.warning(f"LLM planning failed, falling back to rule-based: {e}")

        return self._rule_decompose(goal, agents, strategy)

    def to_dict(self, plan: ExecutionPlan) -> dict:
        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "strategy": plan.strategy,
            "estimated_total_s": plan.estimated_total_s,
            "status": plan.status,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "agent_type": s.agent_type,
                    "dependencies": s.dependencies,
                    "estimated_duration_s": s.estimated_duration_s,
                }
                for s in plan.steps
            ],
        }

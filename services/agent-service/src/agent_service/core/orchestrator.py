"""Multi-Agent Orchestration — chain, parallel, and conditional agent execution."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    VOTING = "voting"


@dataclass
class AgentStep:
    agent_id: str
    agent_name: str = ""
    agent_type: str = ""
    input_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None
    timeout_seconds: int = 300


@dataclass
class OrchestrationResult:
    """Result of a multi-agent orchestration."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mode: str = "sequential"
    status: str = "pending"  # pending, running, completed, failed, timeout
    steps: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Any = None
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""
    total_latency_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "mode": self.mode,
            "status": self.status,
            "steps": self.steps,
            "final_output": self.final_output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_latency_ms": self.total_latency_ms,
        }


class AgentOrchestrator:
    """Orchestrates multiple agents in various execution modes.

    Supports:
    - Sequential: A -> B -> C (each agent receives previous output)
    - Parallel: A, B, C run concurrently, results merged
    - Conditional: A -> (if condition then B else C)
    - Voting: A, B, C run in parallel, output is majority consensus
    """

    def __init__(self, agent_registry, task_executor):
        self.registry = agent_registry
        self.executor = task_executor
        self._workflows: dict[str, OrchestrationResult] = {}

    async def execute_sequential(
        self,
        steps: List[AgentStep],
        initial_input: Dict[str, Any],
    ) -> OrchestrationResult:
        """Execute agents sequentially, passing output from one to the next."""
        import time
        start = time.perf_counter()

        result = OrchestrationResult(
            mode="sequential",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        current_input = initial_input

        try:
            for i, step in enumerate(steps):
                agent = self.registry.get(step.agent_id)
                if not agent:
                    raise ValueError(f"Agent not found: {step.agent_id}")

                step_input = self._map_input(current_input, step.input_mapping)
                task_result = await self.executor.execute(
                    step.agent_id, step_input, timeout=step.timeout_seconds
                )

                # Call executor with AgentInfo object (new API)
                task_result = await self.executor.execute(
                    agent, step_input, timeout=step.timeout_seconds
                )

                status_str = task_result.status.value if hasattr(task_result.status, 'value') else str(task_result.status)

                step_output = {
                    "step": i + 1,
                    "agent_id": step.agent_id,
                    "agent_name": agent.name,
                    "capabilities": agent.capabilities,
                    "status": status_str,
                    "output": task_result.outputs,
                    "error": task_result.error,
                    "duration_ms": task_result.duration_ms,
                }
                result.steps.append(step_output)

                if status_str not in ("COMPLETED",):
                    result.status = status_str.lower()
                    result.error = task_result.error
                    break

                # Pass output as input to next step
                current_input = {"previous_output": task_result.outputs, **initial_input}
            else:
                result.status = "completed"
                result.final_output = result.steps[-1]["output"] if result.steps else None

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        self._workflows[result.workflow_id] = result
        return result

    async def execute_parallel(
        self,
        steps: List[AgentStep],
        initial_input: Dict[str, Any],
    ) -> OrchestrationResult:
        """Execute agents in parallel, merge results."""
        import time
        start = time.perf_counter()

        result = OrchestrationResult(
            mode="parallel",
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        async def run_step(i: int, step: AgentStep):
            agent = self.registry.get(step.agent_id)
            if not agent:
                return {"step": i + 1, "agent_id": step.agent_id, "status": "FAILED",
                        "error": f"Agent not found: {step.agent_id}"}
            step_input = self._map_input(initial_input, step.input_mapping)
            task_result = await self.executor.execute(
                agent, step_input, timeout=step.timeout_seconds
            )
            status_str = task_result.status.value if hasattr(task_result.status, 'value') else str(task_result.status)
            return {
                "step": i + 1,
                "agent_id": step.agent_id,
                "agent_name": agent.name,
                "capabilities": agent.capabilities,
                "status": status_str,
                "output": task_result.outputs,
                "error": task_result.error,
                "duration_ms": task_result.duration_ms,
            }

        try:
            tasks = [run_step(i, step) for i, step in enumerate(steps)]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)

            for sr in step_results:
                if isinstance(sr, Exception):
                    result.steps.append({"status": "failed", "error": str(sr)})
                else:
                    result.steps.append(sr)

            # Merge successful outputs
            outputs = [s["output"] for s in result.steps if s["status"] == "COMPLETED"]
            failures = [s for s in result.steps if s["status"] != "COMPLETED"]

            if failures:
                result.status = "partial"
                result.error = f"{len(failures)}/{len(steps)} steps failed"
            else:
                result.status = "completed"

            result.final_output = {"parallel_results": outputs, "successful": len(outputs),
                                   "total": len(steps)}

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        self._workflows[result.workflow_id] = result
        return result

    async def execute_voting(
        self,
        steps: List[AgentStep],
        initial_input: Dict[str, Any],
        threshold: float = 0.5,
    ) -> OrchestrationResult:
        """Run agents in parallel and vote on the result.

        Each agent returns a confidence score. Results above the threshold
        are counted. Majority (>50% of agents) determines the final output.
        """
        result = await self.execute_parallel(steps, initial_input)

        if result.status not in ("completed", "partial", "COMPLETED", "PARTIAL"):
            return result

        # Extract confidence scores and determine consensus
        confidences = []
        for step in result.steps:
            output = step.get("output", {})
            if isinstance(output, dict):
                conf = output.get("confidence", 0.5)
            else:
                conf = 0.5
            confidences.append(conf)

        above_threshold = sum(1 for c in confidences if c >= threshold)
        result.final_output = {
            "vote_result": "accepted" if above_threshold > len(steps) / 2 else "rejected",
            "votes_for": above_threshold,
            "votes_against": len(steps) - above_threshold,
            "total_voters": len(steps),
            "threshold": threshold,
            "confidences": confidences,
            "individual_results": [s.get("output") for s in result.steps],
        }

        result.mode = "voting"
        self._workflows[result.workflow_id] = result
        return result

    def _map_input(self, source: dict, mapping: Dict[str, str]) -> dict:
        """Map input fields according to the mapping configuration."""
        if not mapping:
            return source
        result = {}
        for target_key, source_key in mapping.items():
            if source_key in source:
                result[target_key] = source[source_key]
        # Include unmapped fields
        for key, value in source.items():
            if key not in mapping.values():
                result.setdefault(key, value)
        return result

    def get_workflow(self, workflow_id: str) -> Optional[OrchestrationResult]:
        """Get a workflow result by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[OrchestrationResult]:
        """List all workflow results."""
        return list(self._workflows.values())

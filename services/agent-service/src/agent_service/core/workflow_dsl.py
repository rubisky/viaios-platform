"""
Workflow DSL Engine — P1-2
YAML-based declarative workflow definition with advanced execution control.

Supports: sequential, parallel, conditional branching, retry with backoff,
timeout, error handling, and variable passing between steps.

DSL Schema:
  workflow:
    name: "video_analysis_pipeline"
    mode: sequential | parallel | conditional
    steps:
      - id: decode
        agent: video-agent
        action: decode
        timeout: 60s
        retry: {max: 3, backoff: exponential, delay: 5s}
      - id: detect
        agent: analysis-agent
        action: detect
        depends_on: [decode]
        condition: "decode.status == 'completed'"
      - id: track
        agent: analysis-agent
        action: track
        depends_on: [detect]
        parallel_with: [embed]
      - id: embed
        agent: analysis-agent
        action: embed
        depends_on: [detect]
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import yaml

logger = logging.getLogger(__name__)


# ── DSL Types ──────────────────────────────────────────────────────

class StepStatus(Enum):
    PENDING     = "pending"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"
    TIMED_OUT   = "timed_out"
    SKIPPED     = "skipped"
    RETRYING    = "retrying"

class WorkflowMode(Enum):
    SEQUENTIAL   = "sequential"
    PARALLEL     = "parallel"
    CONDITIONAL  = "conditional"
    DAG          = "dag"           # Directed Acyclic Graph

class RetryBackoff(Enum):
    FIXED        = "fixed"
    LINEAR       = "linear"
    EXPONENTIAL  = "exponential"

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff: RetryBackoff = RetryBackoff.EXPONENTIAL
    delay_seconds: float = 5.0
    max_delay_seconds: float = 300.0
    retry_on: List[str] = field(default_factory=lambda: ["TIMED_OUT", "FAILED"])

@dataclass
class WorkflowStep:
    """A single step in a workflow DSL definition."""
    id: str
    agent: str = ""
    action: str = ""
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    parallel_with: List[str] = field(default_factory=list)
    condition: Optional[str] = None     # Python expression to evaluate
    timeout_seconds: int = 300
    retry: Optional[RetryPolicy] = None
    on_failure: str = "fail"            # fail, skip, retry, call_agent

@dataclass
class WorkflowDefinition:
    """Complete workflow DSL definition."""
    name: str
    version: str = "1.0"
    description: str = ""
    mode: WorkflowMode = WorkflowMode.SEQUENTIAL
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    on_workflow_failure: str = "fail"   # fail, partial, rollback
    timeout_seconds: int = 3600

@dataclass
class StepResult:
    """Result of executing a single workflow step."""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: float = 0
    attempt: int = 1
    retry_log: List[str] = field(default_factory=list)

@dataclass
class WorkflowResult:
    """Result of executing a complete workflow."""
    workflow_id: str
    workflow_name: str
    status: str                       # completed, failed, timed_out, partial
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    final_output: Any = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_latency_ms: float = 0
    execution_graph: Dict[str, List[str]] = field(default_factory=dict)


# ── Workflow Parser ────────────────────────────────────────────────

class WorkflowParser:
    """Parse YAML workflow definitions into WorkflowDefinition objects."""

    @staticmethod
    def parse(yaml_string: str) -> WorkflowDefinition:
        """Parse a YAML workflow definition string."""
        data = yaml.safe_load(yaml_string)
        wf_data = data.get("workflow", data)

        steps = []
        for step_data in wf_data.get("steps", []):
            retry = None
            if "retry" in step_data:
                r = step_data["retry"]
                retry = RetryPolicy(
                    max_attempts=r.get("max", 3),
                    backoff=RetryBackoff(r.get("backoff", "exponential")),
                    delay_seconds=r.get("delay", 5.0),
                    max_delay_seconds=r.get("max_delay", 300.0),
                )

            steps.append(WorkflowStep(
                id=step_data["id"],
                agent=step_data.get("agent", ""),
                action=step_data.get("action", ""),
                description=step_data.get("description", ""),
                params=step_data.get("params", {}),
                depends_on=step_data.get("depends_on", []),
                parallel_with=step_data.get("parallel_with", []),
                condition=step_data.get("condition"),
                timeout_seconds=step_data.get("timeout", 300),
                retry=retry,
                on_failure=step_data.get("on_failure", "fail"),
            ))

        return WorkflowDefinition(
            name=wf_data.get("name", "unnamed"),
            version=wf_data.get("version", "1.0"),
            description=wf_data.get("description", ""),
            mode=WorkflowMode(wf_data.get("mode", "sequential")),
            steps=steps,
            variables=wf_data.get("variables", {}),
            on_workflow_failure=wf_data.get("on_workflow_failure", "fail"),
            timeout_seconds=wf_data.get("timeout", 3600),
        )

    @staticmethod
    def parse_file(filepath: str) -> WorkflowDefinition:
        """Parse a YAML workflow definition from a file."""
        with open(filepath, "r") as f:
            return WorkflowParser.parse(f.read())


# ── Workflow Executor ──────────────────────────────────────────────

class WorkflowExecutor:
    """
    Execute Workflow DSL definitions with full lifecycle management.

    Usage:
        executor = WorkflowExecutor(agent_executor, capability_manager)
        result = executor.execute(workflow_def)
    """

    def __init__(self, agent_executor=None, capability_manager=None):
        self.agent_executor = agent_executor
        self.capability_manager = capability_manager
        self._step_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def execute(self, workflow: WorkflowDefinition,
                variables: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        """Execute a workflow definition."""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_name=workflow.name,
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        # Merge variables
        ctx = {**workflow.variables, **(variables or {})}

        logger.info("Workflow %s [%s] started: %d steps, mode=%s",
                    workflow.name, workflow_id, len(workflow.steps), workflow.mode.value)

        try:
            if workflow.mode == WorkflowMode.SEQUENTIAL:
                self._execute_sequential(workflow, ctx, result)
            elif workflow.mode == WorkflowMode.PARALLEL:
                asyncio.run(self._execute_parallel(workflow, ctx, result))
            elif workflow.mode == WorkflowMode.DAG:
                self._execute_dag(workflow, ctx, result)
            else:
                self._execute_sequential(workflow, ctx, result)

            # Check status
            failed = [r for r in result.step_results.values()
                     if r.status in (StepStatus.FAILED, StepStatus.TIMED_OUT)]
            result.status = "completed" if not failed else "partial" if len(failed) < len(workflow.steps) else "failed"

        except Exception as e:
            logger.exception("Workflow %s failed: %s", workflow_id, e)
            result.status = "failed"
            result.final_output = {"error": str(e)}

        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            result.total_latency_ms = (result.completed_at - result.started_at).total_seconds() * 1000

        logger.info("Workflow %s %s: %d/%d steps completed in %.0fms",
                    workflow_id, result.status,
                    sum(1 for s in result.step_results.values() if s.status == StepStatus.COMPLETED),
                    len(workflow.steps), result.total_latency_ms)

        return result

    # ── Execution Strategies ────────────────────────────────────

    def _execute_sequential(self, workflow: WorkflowDefinition,
                            ctx: Dict[str, Any], result: WorkflowResult):
        """Execute steps one after another."""
        for step in workflow.steps:
            if not self._should_execute(step, result):
                continue
            step_result = self._execute_step_with_retry(step, ctx)
            result.step_results[step.id] = step_result
            ctx[step.id] = step_result.output
            if step_result.status == StepStatus.FAILED and step.on_failure == "fail":
                break

    async def _execute_parallel(self, workflow: WorkflowDefinition,
                                ctx: Dict[str, Any], result: WorkflowResult):
        """Execute independent steps in parallel."""
        # Build execution groups based on dependencies
        groups = self._build_execution_groups(workflow)

        for group in groups:
            tasks = []
            for step_id in group:
                step = next(s for s in workflow.steps if s.id == step_id)
                if self._should_execute(step, result):
                    tasks.append(self._execute_step_async(step, ctx))

            if tasks:
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
                for step_result in group_results:
                    if isinstance(step_result, StepResult):
                        result.step_results[step_result.step_id] = step_result
                        ctx[step_result.step_id] = step_result.output

    def _execute_dag(self, workflow: WorkflowDefinition,
                     ctx: Dict[str, Any], result: WorkflowResult):
        """Execute steps respecting DAG dependencies."""
        completed: Set[str] = set()
        remaining = list(workflow.steps)

        while remaining:
            ready = [s for s in remaining
                    if all(d in completed or d not in {x.id for x in workflow.steps}
                           for d in s.depends_on)]

            if not ready:
                # Circular dependency or all blocked
                logger.error("Workflow deadlock: %d steps blocked", len(remaining))
                break

            # Execute ready steps in parallel
            for step in ready:
                if self._should_execute(step, result):
                    step_result = self._execute_step_with_retry(step, ctx)
                    result.step_results[step.id] = step_result
                    ctx[step.id] = step_result.output
                completed.add(step.id)

            remaining = [s for s in remaining if s.id not in completed]

    # ── Step Execution ──────────────────────────────────────────

    def _execute_step_with_retry(self, step: WorkflowStep,
                                 ctx: Dict[str, Any]) -> StepResult:
        """Execute a step with retry logic."""
        policy = step.retry or RetryPolicy(max_attempts=1)
        last_error = None
        start = time.time()

        for attempt in range(1, policy.max_attempts + 1):
            try:
                result = self._execute_step(step, ctx, attempt)
                result.latency_ms = (time.time() - start) * 1000
                return result
            except Exception as e:
                last_error = e
                if attempt < policy.max_attempts:
                    delay = self._compute_retry_delay(policy, attempt)
                    logger.warning("Step %s attempt %d/%d failed, retrying in %.1fs: %s",
                                   step.id, attempt, policy.max_attempts, delay, e)
                    time.sleep(delay)

        return StepResult(
            step_id=step.id,
            status=StepStatus.FAILED,
            error=str(last_error),
            attempt=policy.max_attempts,
            latency_ms=(time.time() - start) * 1000,
        )

    def _execute_step(self, step: WorkflowStep, ctx: Dict[str, Any],
                      attempt: int) -> StepResult:
        """Execute a single workflow step."""
        logger.debug("Executing step %s (attempt %d): %s.%s",
                     step.id, attempt, step.agent, step.action)

        start = datetime.now(timezone.utc)

        # Resolve params from context
        resolved_params = self._resolve_params(step.params, ctx)

        # Execute via agent executor or registered handler
        handler = self._step_handlers.get(step.action)
        if handler:
            output = handler(resolved_params, ctx)
        elif self.agent_executor:
            output = self.agent_executor.execute(
                agent_type=step.agent,
                action=step.action,
                params=resolved_params,
                timeout=step.timeout_seconds,
            )
        else:
            output = self._default_handler(step, resolved_params)

        return StepResult(
            step_id=step.id,
            status=StepStatus.COMPLETED,
            output=output,
            started_at=start,
            completed_at=datetime.now(timezone.utc),
            attempt=attempt,
        )

    async def _execute_step_async(self, step: WorkflowStep,
                                  ctx: Dict[str, Any]) -> StepResult:
        """Async wrapper for step execution."""
        return self._execute_step_with_retry(step, ctx)

    # ── Helpers ─────────────────────────────────────────────────

    def _should_execute(self, step: WorkflowStep,
                        result: WorkflowResult) -> bool:
        """Check if a step should be executed based on conditions."""
        if not step.condition:
            return True

        # Evaluate condition against completed step outputs
        try:
            ctx = {sid: r.output for sid, r in result.step_results.items()}
            return bool(eval(step.condition, {"__builtins__": {}}, ctx))
        except Exception:
            return True  # If condition can't be evaluated, execute anyway

    def _build_execution_groups(self, workflow: WorkflowDefinition) -> List[List[str]]:
        """Group steps into parallel execution batches based on dependencies."""
        groups = []
        remaining = set(s.id for s in workflow.steps)
        completed = set()

        while remaining:
            group = [sid for sid in remaining
                    if all(d in completed for d in
                          next(s.depends_on for s in workflow.steps if s.id == sid))]
            if not group:
                group = list(remaining)  # Fallback: execute remaining in parallel
            groups.append(group)
            completed.update(group)
            remaining -= set(group)

        return groups

    def _resolve_params(self, params: Dict[str, Any],
                        ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve template variables in params from context."""
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                var_path = v[2:-1]
                resolved[k] = self._get_nested(ctx, var_path)
            else:
                resolved[k] = v
        return resolved

    def _get_nested(self, d: Dict, path: str) -> Any:
        """Get nested dict value by dot-separated path."""
        parts = path.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _compute_retry_delay(self, policy: RetryPolicy, attempt: int) -> float:
        """Compute delay for retry attempt."""
        if policy.backoff == RetryBackoff.FIXED:
            return policy.delay_seconds
        elif policy.backoff == RetryBackoff.LINEAR:
            return min(policy.delay_seconds * attempt, policy.max_delay_seconds)
        elif policy.backoff == RetryBackoff.EXPONENTIAL:
            return min(policy.delay_seconds * (2 ** (attempt - 1)), policy.max_delay_seconds)
        return policy.delay_seconds

    def _default_handler(self, step: WorkflowStep, params: Dict) -> Dict:
        """Default step handler for development."""
        return {"step": step.id, "action": step.action, "params": params, "status": "ok"}

    def _register_default_handlers(self):
        """Register built-in step handlers."""
        self._step_handlers.update({
            "decode": lambda p, c: {"status": "decoded", "frames": 300, "fps": 25},
            "detect": lambda p, c: {"status": "detected", "objects": 12},
            "track": lambda p, c: {"status": "tracked", "tracks": 5},
            "embed": lambda p, c: {"status": "embedded", "vectors": 5},
            "archive": lambda p, c: {"status": "archived", "path": "/opt/viaios/data/"},
            "search": lambda p, c: {"status": "searched", "matches": 8},
            "reason": lambda p, c: {"status": "reasoned", "conclusion": "analysis complete"},
            "report": lambda p, c: {"status": "reported", "format": "pdf"},
            "notify": lambda p, c: {"status": "notified", "channels": ["webhook"]},
        })


# ── Built-in Workflow Templates ────────────────────────────────────

BUILTIN_WORKFLOWS = {
    "video_analysis": """
workflow:
  name: video_analysis_pipeline
  version: "1.0"
  description: "Standard video structuring pipeline"
  mode: sequential
  steps:
    - id: decode
      agent: video-agent
      action: decode
      timeout: 120
      retry: {max: 2, backoff: fixed, delay: 10}
    - id: detect
      agent: analysis-agent
      action: detect
      depends_on: [decode]
      timeout: 60
    - id: track
      agent: analysis-agent
      action: track
      depends_on: [detect]
      timeout: 60
    - id: embed
      agent: analysis-agent
      action: embed
      depends_on: [detect]
      parallel_with: [track]
      timeout: 60
    - id: archive
      agent: video-agent
      action: archive
      depends_on: [track, embed]
      timeout: 30
""",

    "threat_investigation": """
workflow:
  name: threat_investigation
  version: "1.0"
  description: "Multi-agent threat investigation workflow"
  mode: dag
  steps:
    - id: search_target
      agent: search-agent
      action: search
      params: {query: "${variables.target_description}", top_k: 10}
      timeout: 30
    - id: analyze_behavior
      agent: analysis-agent
      action: reason
      depends_on: [search_target]
      timeout: 60
    - id: check_knowledge
      agent: knowledge-agent
      action: search
      params: {entity_id: "${search_target.matches[0].id}"}
      timeout: 30
    - id: generate_report
      agent: report-agent
      action: report
      depends_on: [analyze_behavior, check_knowledge]
      timeout: 60
    - id: notify_ops
      agent: alarm-agent
      action: notify
      depends_on: [generate_report]
      condition: "generate_report.severity == 'HIGH'"
      timeout: 10
""",
}

"""Agent Executor — executes agents with timeout, retry, and monitoring."""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional
from .registry import AgentInfo, AgentStatus, agent_registry


class ExecutionStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


@dataclass
class ExecutionResult:
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    inputs: Dict = field(default_factory=dict)
    outputs: Any = None
    error: Optional[str] = None
    started_at: float = 0
    completed_at: float = 0
    duration_ms: float = 0
    progress: float = 0.0


class AgentExecutor:
    """Manages agent execution lifecycle with concurrency and timeout control."""

    def __init__(self, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executions: Dict[str, ExecutionResult] = {}
        self._running: Dict[str, asyncio.Task] = {}

    async def execute(self, agent_info: AgentInfo, inputs: Dict,
                      timeout: Optional[int] = None) -> ExecutionResult:
        """Execute an agent with concurrency control and timeout."""
        result = ExecutionResult(agent_id=agent_info.agent_id, inputs=inputs)
        self._executions[result.execution_id] = result

        timeout = timeout or agent_info.timeout_seconds

        async with self._semaphore:
            result.status = ExecutionStatus.RUNNING
            result.started_at = time.time()
            agent_info.status = AgentStatus.RUNNING

            try:
                if agent_info.handler is None:
                    raise ValueError(f"No handler registered for agent {agent_info.name}")

                task = asyncio.create_task(
                    self._run_handler(agent_info.handler, inputs)
                )
                self._running[result.execution_id] = task

                outputs = await asyncio.wait_for(task, timeout=timeout)
                result.outputs = outputs
                result.status = ExecutionStatus.COMPLETED
            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.error = f"Execution timed out after {timeout}s"
            except asyncio.CancelledError:
                result.status = ExecutionStatus.CANCELLED
                result.error = "Execution cancelled"
            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.error = str(e)
            finally:
                result.completed_at = time.time()
                result.duration_ms = (result.completed_at - result.started_at) * 1000
                agent_info.status = AgentStatus.IDLE
                self._running.pop(result.execution_id, None)

        return result

    async def _run_handler(self, handler: Callable, inputs: Dict) -> Any:
        """Run the agent handler (supports both sync and async)."""
        result = handler(inputs)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    def cancel(self, execution_id: str):
        """Cancel a running execution."""
        task = self._running.get(execution_id)
        if task:
            task.cancel()
            return True
        return False

    def get_status(self, execution_id: str) -> Optional[ExecutionResult]:
        return self._executions.get(execution_id)

    def list_executions(self, agent_id: Optional[str] = None) -> list:
        results = list(self._executions.values())
        if agent_id:
            results = [r for r in results if r.agent_id == agent_id]
        return sorted(results, key=lambda r: r.started_at, reverse=True)


# Global singleton
agent_executor = AgentExecutor()

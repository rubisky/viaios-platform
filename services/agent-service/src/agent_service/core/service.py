"""Agent OS Runtime — Agent Registry and Task Executor."""

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class Agent:
    """Registered agent descriptor."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        agent_type: str,
        config: dict[str, Any] | None = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.config = config or {}
        self.created_at = datetime.now(timezone.utc)
        self.status = "idle"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
        }


class TaskResult:
    """Result of an agent task execution."""

    def __init__(
        self,
        task_id: str,
        agent_id: str,
        status: str,
        output: Any = None,
        error: str | None = None,
    ):
        self.task_id = task_id
        self.agent_id = agent_id
        self.status = status
        self.output = output
        self.error = error
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AgentRegistry:
    """In-memory registry of AI agents."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(
        self,
        name: str,
        description: str,
        agent_type: str,
        config: dict[str, Any] | None = None,
    ) -> Agent:
        agent_id = hashlib.sha256(
            f"{name}:{agent_type}:{uuid.uuid4()}".encode()
        ).hexdigest()[:16]
        agent = Agent(
            agent_id=agent_id,
            name=name,
            description=description,
            agent_type=agent_type,
            config=config,
        )
        self._agents[agent_id] = agent
        logger.info("Registered agent: %s (%s)", name, agent_id)
        return agent

    def list(self, agent_type: str | None = None) -> list[Agent]:
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        return agents

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def remove(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False


class TaskExecutor:
    """Executes agent tasks asynchronously."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._tasks: dict[str, TaskResult] = {}
        self._running: dict[str, asyncio.Task] = {}

    async def execute(
        self, agent_id: str, input_params: dict[str, Any], timeout: int = 300
    ) -> TaskResult:
        agent = self.registry.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        task_id = hashlib.sha256(
            f"{agent_id}:{uuid.uuid4()}".encode()
        ).hexdigest()[:16]

        result = TaskResult(
            task_id=task_id,
            agent_id=agent_id,
            status="running",
        )
        self._tasks[task_id] = result

        agent.status = "running"

        try:
            output = await asyncio.wait_for(
                self._run_agent(agent, input_params),
                timeout=timeout,
            )
            result.status = "completed"
            result.output = output
            result.completed_at = datetime.now(timezone.utc)
        except asyncio.TimeoutError:
            result.status = "timeout"
            result.error = f"Task timed out after {timeout}s"
            result.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
        finally:
            agent.status = "idle"

        logger.info("Task %s finished with status: %s", task_id, result.status)
        return result

    async def _run_agent(self, agent: Agent, input_params: dict[str, Any]) -> dict[str, Any]:
        """Simulate agent execution."""
        await asyncio.sleep(2)  # Simulate AI processing
        return {
            "agent_name": agent.name,
            "agent_type": agent.agent_type,
            "input": input_params,
            "result": f"Processed by {agent.name}",
            "confidence": 0.95,
        }

    def get_task(self, task_id: str) -> TaskResult | None:
        return self._tasks.get(task_id)

    def list_tasks(self, agent_id: str | None = None) -> list[TaskResult]:
        tasks = list(self._tasks.values())
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        return tasks


# Global instances
agent_registry = AgentRegistry()
task_executor = TaskExecutor(agent_registry)

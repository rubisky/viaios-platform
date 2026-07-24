"""Agent Registry — manages agent registration, discovery, and lifecycle."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from enum import Enum
import uuid
import time


class AgentStatus(Enum):
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


@dataclass
class AgentInfo:
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.REGISTERED
    handler: Optional[Callable] = None
    resource_requirements: Dict = field(default_factory=dict)
    rate_limit_per_min: int = 60
    timeout_seconds: int = 300
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)


class AgentRegistry:
    """Central registry for all agents in the system."""

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._by_capability: Dict[str, List[str]] = {}

    def register(self, info: AgentInfo) -> str:
        """Register a new agent or update existing."""
        self._agents[info.agent_id] = info
        for cap in info.capabilities:
            if cap not in self._by_capability:
                self._by_capability[cap] = []
            if info.agent_id not in self._by_capability[cap]:
                self._by_capability[cap].append(info.agent_id)
        return info.agent_id

    def unregister(self, agent_id: str):
        info = self._agents.pop(agent_id, None)
        if info:
            for cap in info.capabilities:
                self._by_capability.get(cap, []).remove(agent_id)

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        return self._agents.get(agent_id)

    def list_by_capability(self, capability: str) -> List[AgentInfo]:
        ids = self._by_capability.get(capability, [])
        return [self._agents[aid] for aid in ids if aid in self._agents]

    def list_all(self, status: Optional[AgentStatus] = None) -> List[AgentInfo]:
        agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        return agents

    def heartbeat(self, agent_id: str):
        info = self._agents.get(agent_id)
        if info:
            info.last_heartbeat = time.time()
            if info.status == AgentStatus.OFFLINE:
                info.status = AgentStatus.IDLE

    def mark_stale(self, threshold_seconds: float = 60) -> List[str]:
        """Mark agents as offline if no heartbeat within threshold."""
        now = time.time()
        stale = []
        for agent_id, info in self._agents.items():
            if now - info.last_heartbeat > threshold_seconds:
                info.status = AgentStatus.OFFLINE
                stale.append(agent_id)
        return stale


# Global singleton
agent_registry = AgentRegistry()

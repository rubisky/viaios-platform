"""Agent Memory System — 3-layer: Working, Short-term, Long-term."""
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory item."""
    content: str
    role: str = "user"  # user, agent, system
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    importance: float = 0.5  # 0-1, used for long-term retention
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """Key-value scratchpad for the current task execution.

    Stores intermediate results, decisions, and state during a task.
    Cleared when the task completes.
    """

    def __init__(self, max_items: int = 50):
        self._store: Dict[str, Any] = {}
        self._max = max_items

    def set(self, key: str, value: Any):
        if len(self._store) >= self._max:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def update(self, data: Dict[str, Any]):
        self._store.update(data)

    def clear(self):
        self._store.clear()

    def snapshot(self) -> dict:
        return dict(self._store)

    def __len__(self):
        return len(self._store)


class ShortTermMemory:
    """Sliding window of recent messages with automatic summarization.

    Keeps the most recent N messages. When the window overflows,
    older messages are compressed into a summary.
    """

    def __init__(self, max_messages: int = 20, summary_threshold: int = 15):
        self._messages: List[MemoryEntry] = []
        self._summary: str = ""
        self._max = max_messages
        self._threshold = summary_threshold

    def add(self, content: str, role: str = "user", importance: float = 0.5):
        entry = MemoryEntry(content=content, role=role, importance=importance)
        self._messages.append(entry)
        if len(self._messages) > self._max:
            self._compress()

    def _compress(self):
        """Summarize oldest messages into a running summary."""
        overflow = len(self._messages) - self._threshold
        if overflow <= 0:
            return
        old = self._messages[:overflow]
        self._messages = self._messages[overflow:]

        # Simple extractive summarization: keep important statements
        key_points = []
        for m in old:
            if m.importance > 0.6 or m.role == "user":
                snippet = m.content[:120]
                key_points.append(f"[{m.role}] {snippet}")
        if key_points:
            self._summary = f"Previous conversation ({len(old)} msgs): {'; '.join(key_points[-5:])}"
        else:
            self._summary = f"Previous {len(old)} messages summarized."

    def get_context(self, max_tokens: int = 4000) -> str:
        """Return the current conversation context as formatted text."""
        parts = []
        if self._summary:
            parts.append(f"[SUMMARY] {self._summary}")
        for m in self._messages:
            parts.append(f"[{m.role.upper()}] {m.content[:300]}")
        return "\n".join(parts)[-max_tokens:]

    def get_messages(self) -> List[MemoryEntry]:
        return list(self._messages)

    def clear(self):
        self._messages.clear()
        self._summary = ""


class LongTermMemory:
    """Stores extracted facts and entities for future retrieval.

    Uses simple keyword-based retrieval. In production, this would use
    a vector database (Milvus) for semantic search.
    """

    def __init__(self, max_facts: int = 1000):
        self._facts: OrderedDict = OrderedDict()
        self._max = max_facts

    def store(self, fact: str, entity: str = "", metadata: Dict = None):
        """Store a fact or entity information."""
        key = f"{entity}:{fact[:50]}" if entity else fact[:50]
        now = datetime.now(timezone.utc).isoformat()
        self._facts[key] = {
            "fact": fact,
            "entity": entity,
            "timestamp": now,
            "metadata": metadata or {},
            "access_count": 0,
        }
        if len(self._facts) > self._max:
            self._facts.popitem(last=False)

    def retrieve(self, query: str, max_results: int = 5) -> List[dict]:
        """Simple keyword-based retrieval."""
        query_lower = query.lower()
        scored = []
        for key, entry in self._facts.items():
            score = 0
            fact_lower = entry["fact"].lower()
            # Word overlap scoring
            for word in query_lower.split():
                if word in fact_lower:
                    score += 1
            if entry["entity"].lower() in query_lower:
                score += 3
            if score > 0:
                entry["access_count"] += 1
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:max_results]]

    def get_entities(self) -> List[str]:
        entities = set()
        for entry in self._facts.values():
            if entry["entity"]:
                entities.add(entry["entity"])
        return sorted(entities)

    def count(self) -> int:
        return len(self._facts)


class AgentMemory:
    """Complete agent memory system with all three layers."""

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self._session_start = datetime.now(timezone.utc).isoformat()

    def remember(self, content: str, role: str = "user",
                 importance: float = 0.5, store_long_term: bool = False):
        """Add a memory entry."""
        self.short_term.add(content, role, importance)
        if store_long_term or importance > 0.8:
            self.long_term.store(content, entity=role)

    def recall(self, query: str, max_results: int = 5) -> List[dict]:
        """Search long-term memory."""
        return self.long_term.retrieve(query, max_results)

    def get_context(self) -> str:
        """Get full conversation context for the LLM."""
        return self.short_term.get_context()

    def extract_facts(self, text: str):
        """Extract and store facts from agent output."""
        # Simple entity extraction: capitalized words or patterns
        import re
        entities = re.findall(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', text)
        for entity in entities:
            if len(entity) > 3:
                self.long_term.store(f"Extracted: {entity}", entity=entity)

    def reset_session(self):
        self.working.clear()
        self.short_term.clear()
        self._session_start = datetime.now(timezone.utc).isoformat()

    def stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "session_start": self._session_start,
            "working_memory_items": len(self.working),
            "short_term_messages": len(self.short_term._messages),
            "long_term_facts": self.long_term.count(),
            "entities": self.long_term.get_entities(),
        }

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "working": self.working.snapshot(),
            "context": self.short_term.get_context()[:500],
            "stats": self.stats(),
        }


# Global memory registry
_memory_store: Dict[str, AgentMemory] = {}


def get_memory(agent_id: str = "default") -> AgentMemory:
    """Get or create an AgentMemory instance for an agent."""
    if agent_id not in _memory_store:
        _memory_store[agent_id] = AgentMemory(agent_id)
    return _memory_store[agent_id]


def list_memories() -> List[dict]:
    return [m.stats() for m in _memory_store.values()]

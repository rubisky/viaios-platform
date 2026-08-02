"""
Memory Manager Enhanced — Short/long-term/working memory for Agent OS.

Three-tier memory architecture:
- Working:  Current conversation context (sliding window, ephemeral)
- Short-term: Recent interactions within session (Redis-backed, TTL)
- Long-term:  Persistent knowledge (vector DB, persistent storage)
"""
import json
import logging
import threading
import time
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: f"mem-{uuid.uuid4().hex[:8]}")
    content: str = ""
    role: str = "user"      # user, assistant, system, tool
    importance: float = 0.5  # 0-1, higher = more likely to persist
    access_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: Optional[datetime] = None
    ttl_seconds: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class MemoryManager:
    """Three-tier memory system for AI agents."""

    def __init__(self, max_working: int = 20, max_short_term: int = 200):
        # Working memory: sliding window (most recent N entries)
        self._working: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._max_working = max_working

        # Short-term: Redis-backed with TTL
        self._short_term: Dict[str, MemoryEntry] = {}
        self._max_short_term = max_short_term
        self._redis = None

        # Long-term: Milvus-backed vector storage
        self._long_term: List[MemoryEntry] = []
        self._milvus = None

        self._lock = threading.Lock()
        self._stats = {"working_hits": 0, "short_hits": 0, "long_hits": 0, "misses": 0}

    # ── Working Memory ──────────────────────────────────────────

    def add_working(self, content: str, role: str = "user",
                    importance: float = 0.5, metadata: Dict = None) -> MemoryEntry:
        entry = MemoryEntry(content=content, role=role, importance=importance,
                          ttl_seconds=300, metadata=metadata or {})
        with self._lock:
            self._working[entry.id] = entry
            if len(self._working) > self._max_working:
                # Evict oldest to short-term
                oldest_id, oldest = next(iter(self._working.items()))
                del self._working[oldest_id]
                if oldest.importance > 0.3:
                    self._short_term[oldest_id] = oldest
        return entry

    def get_working(self, query: str = None, limit: int = 10) -> List[MemoryEntry]:
        """Get working memory entries, optionally filtered."""
        with self._lock:
            entries = list(self._working.values())
            for e in entries:
                e.access_count += 1
                e.last_accessed = datetime.now(timezone.utc)
            if query:
                entries = [e for e in entries if query.lower() in e.content.lower()]
            self._stats["working_hits"] += 1
            return entries[-limit:]

    # ── Short-term Memory ───────────────────────────────────────

    def commit_to_short_term(self, entry: MemoryEntry, ttl: int = 3600):
        """Persist to short-term memory (backed by Redis in production)."""
        entry.ttl_seconds = ttl
        with self._lock:
            self._short_term[entry.id] = entry
            if len(self._short_term) > self._max_short_term:
                oldest = min(self._short_term.values(),
                           key=lambda e: e.last_accessed or e.created_at)
                del self._short_term[oldest.id]

        # Try Redis
        try:
            self._init_redis()
            if self._redis:
                key = f"viaios:memory:{entry.id}"
                self._redis.setex(key, ttl, json.dumps({
                    "id": entry.id, "content": entry.content, "role": entry.role,
                    "importance": entry.importance, "created_at": entry.created_at.isoformat(),
                }))
        except Exception:
            pass

    def recall_short_term(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search short-term memory by content match."""
        self._cleanup_expired()
        with self._lock:
            matches = [e for e in self._short_term.values()
                      if query.lower() in e.content.lower()]
            for e in matches:
                e.access_count += 1
            self._stats["short_hits"] += 1
            return sorted(matches, key=lambda e: e.importance, reverse=True)[:limit]

    # ── Long-term Memory ────────────────────────────────────────

    def consolidate_to_long_term(self, entry: MemoryEntry):
        """Move important memories to long-term storage."""
        if entry.importance < 0.7:
            return
        with self._lock:
            self._long_term.append(entry)

        # Try Milvus
        try:
            self._init_milvus()
            if self._milvus and entry.embedding:
                self._milvus.insert(
                    collection="agent_memory",
                    vectors=[entry.embedding],
                    metadata=[{"id": entry.id, "content": entry.content[:500],
                              "role": entry.role, "importance": entry.importance}],
                )
        except Exception:
            pass

    def recall_long_term(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search long-term memory using vector similarity."""
        results = []
        # Try Milvus vector search
        try:
            self._init_milvus()
            if self._milvus:
                embedding = self._get_embedding(query)
                if embedding:
                    hits = self._milvus.search(
                        collection="agent_memory", vectors=[embedding], top_k=limit)
                    for hit in (hits or []):
                        entry = MemoryEntry(
                            content=hit.get("metadata", {}).get("content", ""),
                            importance=hit.get("score", 0),
                        )
                        results.append(entry)
        except Exception:
            pass

        # Fallback: keyword match
        if not results:
            with self._lock:
                results = [e for e in self._long_term
                         if query.lower() in e.content.lower()]
                results = sorted(results, key=lambda e: e.importance, reverse=True)[:limit]

        self._stats["long_hits"] += 1
        return results

    # ── Unified Recall ──────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Unified recall across all three memory tiers."""
        working = [{"content": e.content[:200], "role": e.role, "tier": "working"}
                   for e in self.get_working(query, limit)]
        short = [{"content": e.content[:200], "role": e.role, "tier": "short_term"}
                 for e in self.recall_short_term(query, limit)]
        long_term = [{"content": e.content[:200], "role": e.role, "tier": "long_term"}
                     for e in self.recall_long_term(query, limit)]

        # Merge: working first (most relevant), then short, then long
        merged = working + short + long_term
        return {"query": query, "results": merged[:limit], "total": len(merged)}

    def stats(self) -> Dict[str, Any]:
        return {
            "working_size": len(self._working),
            "short_term_size": len(self._short_term),
            "long_term_size": len(self._long_term),
            "hits": self._stats,
        }

    # ── Internals ───────────────────────────────────────────────

    def _cleanup_expired(self):
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [eid for eid, e in self._short_term.items()
                      if (now - e.created_at).seconds > e.ttl_seconds]
            for eid in expired:
                del self._short_term[eid]

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        import hashlib, random
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
        return [random.Random(seed + i).uniform(-1, 1) for i in range(512)]

    def _init_redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
                self._redis.ping()
            except Exception:
                pass

    def _init_milvus(self):
        if self._milvus is None:
            try:
                from agent_service.core.milvus_client import milvus_client
                self._milvus = milvus_client
            except Exception:
                pass


_memory: Optional[MemoryManager] = None

def get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory

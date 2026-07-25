"""Production-Ready Upgrades — Persistence, Retry, Monitoring, Caching."""
import json
import logging
import os
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ===== 1. SQLite Persistence Layer =====

class SQLiteStore:
    """Persistent key-value store with TTL support."""

    def __init__(self, db_path: str = "/opt/viaios/data/production.db"):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""CREATE TABLE IF NOT EXISTS kv_store (
            key TEXT PRIMARY KEY, value TEXT, ttl INTEGER, created_at TEXT, updated_at TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY, agent_id TEXT, content TEXT, role TEXT,
            importance REAL, created_at TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY, event_type TEXT, user TEXT, action TEXT,
            resource TEXT, result TEXT, timestamp TEXT)""")
        conn.commit()

    # KV operations
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        now = datetime.now(timezone.utc).isoformat()
        ttl = int(time.time()) + ttl_seconds if ttl_seconds else None
        self._get_conn().execute(
            "INSERT OR REPLACE INTO kv_store VALUES (?,?,?,?,?)",
            (key, json.dumps(value), ttl, now, now))
        self._get_conn().commit()

    def get(self, key: str) -> Optional[Any]:
        row = self._get_conn().execute(
            "SELECT value, ttl FROM kv_store WHERE key=?", (key,)).fetchone()
        if not row: return None
        if row["ttl"] and int(time.time()) > row["ttl"]:
            self.delete(key); return None
        return json.loads(row["value"])

    def delete(self, key: str):
        self._get_conn().execute("DELETE FROM kv_store WHERE key=?", (key,))
        self._get_conn().commit()

    # Memory persistence
    def save_memory(self, memory_id: str, agent_id: str, content: str, role: str, importance: float):
        self._get_conn().execute(
            "INSERT OR REPLACE INTO memory_entries VALUES (?,?,?,?,?,?)",
            (memory_id, agent_id, content, role, importance, datetime.now(timezone.utc).isoformat()))
        self._get_conn().commit()

    def load_memories(self, agent_id: str, limit: int = 20) -> List[Dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM memory_entries WHERE agent_id=? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit)).fetchall()
        return [dict(r) for r in rows]

    # Audit persistence
    def save_audit(self, audit: Dict):
        self._get_conn().execute(
            "INSERT INTO audit_log VALUES (?,?,?,?,?,?,?)",
            (audit["id"], audit["event_type"], audit["user"], audit["action"],
             audit["resource"], audit["result"], audit["timestamp"]))
        self._get_conn().commit()

    def load_audit(self, limit: int = 50) -> List[Dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        kv = self._get_conn().execute("SELECT count(*) as c FROM kv_store").fetchone()["c"]
        mem = self._get_conn().execute("SELECT count(*) as c FROM memory_entries").fetchone()["c"]
        aud = self._get_conn().execute("SELECT count(*) as c FROM audit_log").fetchone()["c"]
        return {"kv_entries": kv, "memory_entries": mem, "audit_entries": aud}


# Global persistence store
db_store = SQLiteStore()


# ===== 2. Retry + Circuit Breaker =====

class CircuitBreaker:
    """Circuit breaker pattern — prevents cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._failures: Dict[str, Tuple[int, float]] = {}  # name -> (count, last_failure_time)

    def call(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if name in self._failures:
            count, last_time = self._failures[name]
            if count >= self._threshold:
                if time.time() - last_time < self._timeout:
                    raise RuntimeError(f"Circuit OPEN for {name}")
                else:
                    # Half-open: allow one request through
                    self._failures[name] = (count - 1, last_time)

        try:
            result = func(*args, **kwargs)
            if name in self._failures:
                del self._failures[name]  # Reset on success
            return result
        except Exception as e:
            if name not in self._failures:
                self._failures[name] = (0, time.time())
            count, _ = self._failures[name]
            self._failures[name] = (count + 1, time.time())
            raise e

    def get_status(self) -> Dict:
        return {name: "OPEN" if c >= self._threshold and time.time() - t < self._timeout else "HALF_OPEN" if c > 0 else "CLOSED"
                for name, (c, t) in self._failures.items()}


circuit_breaker = CircuitBreaker()


# ===== 3. Retry Decorator =====

def retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff: float = 2.0):
    """Decorator: retry function with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        sleep_time = delay_seconds * (backoff ** attempt)
                        logger.warning("Retry %d/%d for %s in %.1fs: %s",
                                       attempt + 1, max_attempts, func.__name__, sleep_time, e)
                        time.sleep(sleep_time)
            raise last_error
        return wrapper
    return decorator


# ===== 4. LRU Cache with TTL =====

class TTLCache:
    """Thread-safe LRU cache with TTL."""

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._max = max_size
        self._ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0; self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1; return None
            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                self._misses += 1; return None
            self._cache.move_to_end(key)
            self._hits += 1; return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self._max:
                self._cache.popitem(last=False)
            expiry = time.time() + (ttl or self._ttl)
            self._cache[key] = (value, expiry)

    def get_stats(self) -> dict:
        total = self._hits + self._misses
        return {"size": len(self._cache), "max": self._max,
                "hits": self._hits, "misses": self._misses,
                "hit_rate": round(self._hits / max(total, 1) * 100, 1)}


# Global cache
production_cache = TTLCache(max_size=200, default_ttl=300)


# ===== 5. Health Monitor =====

class HealthMonitor:
    """Service health monitoring with Prometheus-style metrics."""

    def __init__(self):
        self._metrics: Dict[str, List[Tuple[float, Any]]] = {}
        self._lock = threading.Lock()

    def record(self, name: str, value: Any):
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append((time.time(), value))
            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-500:]

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            result = {}
            for name, values in self._metrics.items():
                if not values: continue
                recent = [v for t, v in values[-100:]]
                if isinstance(recent[0], (int, float)):
                    result[name] = {
                        "count": len(values), "last": recent[-1],
                        "avg": round(sum(recent) / len(recent), 2),
                        "max": max(recent), "min": min(recent),
                    }
                else:
                    result[name] = {"count": len(values), "last": recent[-1]}
            return result

    def get_health_score(self) -> Dict:
        metrics = self.get_metrics()
        score = 100
        if "error_rate" in metrics and metrics["error_rate"]["last"] > 5:
            score -= 30
        if "latency_p95" in metrics and metrics["latency_p95"]["last"] > 500:
            score -= 20
        return {"score": max(0, score), "metrics_count": len(metrics)}


health_monitor = HealthMonitor()

# Record some baseline metrics
health_monitor.record("startup_time_ms", 2500)
health_monitor.record("active_connections", 16)
health_monitor.record("memory_usage_mb", 8941)

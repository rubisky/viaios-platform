"""
Runtime Mesh — P0-2
AI model service mesh for intelligent routing, load balancing,
canary deployment, A/B testing, and automatic failover.

Analogous to Istio/Linkerd for microservices, but purpose-built for
AI model inference endpoints. The Runtime Mesh routes capability calls
to the optimal model instance based on real-time metrics.

Architecture:
  Capability Call → Mesh Router → [LB Strategy] → Model Instance
                                    ├─ least_connections
                                    ├─ lowest_latency
                                    ├─ round_robin
                                    ├─ canary (weighted)
                                    └─ ab_test (split)
"""
import logging
import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────

class LBStrategy(Enum):
    ROUND_ROBIN      = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LOWEST_LATENCY   = "lowest_latency"
    WEIGHTED         = "weighted"
    CANARY           = "canary"
    AB_TEST          = "ab_test"

class FailoverStrategy(Enum):
    NEXT_HEALTHY     = "next_healthy"      # Try next healthy instance
    RETRY_SAME       = "retry_same"        # Retry same instance N times
    FALLBACK_MODEL   = "fallback_model"   # Use a different model entirely
    CIRCUIT_BREAK    = "circuit_break"     # Open circuit after N failures

# ── Domain Types ───────────────────────────────────────────────────

@dataclass
class ModelEndpoint:
    """A single model inference endpoint (instance)."""
    endpoint_id: str
    model_id: str
    model_name: str
    model_version: str
    capability: str            # which capability domain this serves
    host: str
    port: int
    runtime: str               # ONNX, TRITON, TENSORRT, VLLM
    weight: int = 100          # routing weight (0-100)
    channel: str = "STABLE"    # DEFAULT, STABLE, CANARY, EXPERIMENTAL
    max_connections: int = 100
    health_check_path: str = "/health"

    # Runtime state (updated by health checker)
    active_connections: int = 0
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    circuit_open: bool = False
    circuit_open_since: Optional[datetime] = None

    # Performance metrics
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    last_latency_ms: float = 0.0


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    endpoint: ModelEndpoint
    strategy: LBStrategy
    reason: str
    fallback_used: bool = False
    previous_endpoint: Optional[ModelEndpoint] = None


@dataclass
class MeshConfig:
    """Global Runtime Mesh configuration."""
    lb_strategy: LBStrategy = LBStrategy.LEAST_CONNECTIONS
    failover_strategy: FailoverStrategy = FailoverStrategy.NEXT_HEALTHY
    max_retries: int = 3
    retry_delay_ms: int = 100
    circuit_breaker_threshold: int = 5       # consecutive failures before opening
    circuit_breaker_timeout_seconds: int = 30 # how long the circuit stays open
    health_check_interval_seconds: int = 10
    canary_default_split: int = 10           # % traffic to canary by default
    metrics_window_seconds: int = 300         # sliding window for latency metrics


# ── Runtime Mesh Implementation ────────────────────────────────────

class RuntimeMesh:
    """
    AI Model Service Mesh.

    Usage:
        mesh = RuntimeMesh()
        mesh.register_endpoint(ModelEndpoint(...))
        result = mesh.route("face_detection", strategy=LBStrategy.LEAST_CONNECTIONS)
        # Call the endpoint...
        mesh.record_result(result.endpoint.endpoint_id, latency_ms=45, success=True)
    """

    def __init__(self, config: Optional[MeshConfig] = None):
        self.config = config or MeshConfig()
        self._endpoints: Dict[str, ModelEndpoint] = {}
        self._by_capability: Dict[str, List[str]] = defaultdict(list)
        self._rr_counters: Dict[str, int] = defaultdict(int)  # for round-robin
        self._lock = threading.Lock()
        self._health_check_thread: Optional[threading.Thread] = None

        # Start health check loop
        self._start_health_checks()

    # ── Registration ───────────────────────────────────────────────

    def register_endpoint(self, endpoint: ModelEndpoint) -> str:
        """Register a model endpoint with the mesh."""
        with self._lock:
            self._endpoints[endpoint.endpoint_id] = endpoint
            self._by_capability[endpoint.capability].append(endpoint.endpoint_id)
        logger.info("Mesh: registered %s for %s [%s/%s]",
                     endpoint.endpoint_id, endpoint.capability,
                     endpoint.runtime, endpoint.channel)
        return endpoint.endpoint_id

    def deregister_endpoint(self, endpoint_id: str):
        """Remove an endpoint from the mesh."""
        with self._lock:
            ep = self._endpoints.pop(endpoint_id, None)
            if ep:
                self._by_capability[ep.capability].remove(endpoint_id)
        logger.info("Mesh: deregistered %s", endpoint_id)

    def update_weight(self, endpoint_id: str, weight: int):
        """Update routing weight for an endpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                self._endpoints[endpoint_id].weight = max(0, min(100, weight))

    # ── Routing (core algorithm) ───────────────────────────────────

    def route(self, capability: str,
              strategy: Optional[LBStrategy] = None,
              exclude_endpoints: Optional[List[str]] = None) -> RoutingResult:
        """
        Route a capability call to the best model endpoint.

        Returns the optimal endpoint based on the configured strategy.
        If the primary endpoint fails, automatically falls back.
        """
        strategy = strategy or self.config.lb_strategy
        exclude = set(exclude_endpoints or [])

        with self._lock:
            candidates = self._get_candidates(capability, exclude)

            if not candidates:
                # Try fallback: any endpoint serving this capability
                candidates = [ep for ep in self._endpoints.values()
                              if ep.capability == capability and ep.is_healthy
                              and not ep.circuit_open]
                if not candidates:
                    raise RuntimeError(f"No healthy endpoints for capability: {capability}")

            # Apply strategy
            selected = self._apply_strategy(candidates, strategy)

        logger.debug("Mesh route: %s → %s [%s] (strategy=%s)",
                      capability, selected.endpoint_id, selected.runtime, strategy.value)

        return RoutingResult(
            endpoint=selected,
            strategy=strategy,
            reason=f"Selected by {strategy.value}: {selected.endpoint_id}",
        )

    def route_with_failover(self, capability: str,
                            invoke: Callable[[ModelEndpoint], Any],
                            strategy: Optional[LBStrategy] = None) -> Tuple[Any, RoutingResult]:
        """
        Route and invoke with automatic failover.

        Usage:
            result, routing = mesh.route_with_failover("face_detection",
                lambda ep: requests.post(f"http://{ep.host}:{ep.port}/infer", ...))
        """
        tried_endpoints = []
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                endpoint_result = self.route(capability, strategy, tried_endpoints)
                start = time.time()

                result = invoke(endpoint_result.endpoint)

                latency_ms = (time.time() - start) * 1000
                self.record_result(endpoint_result.endpoint.endpoint_id, latency_ms, True)
                return result, endpoint_result

            except Exception as e:
                last_error = e
                tried_endpoints.append(endpoint_result.endpoint.endpoint_id)
                self.record_result(endpoint_result.endpoint.endpoint_id, 0, False)
                logger.warning("Mesh failover attempt %d/%d for %s: %s",
                               attempt + 1, self.config.max_retries, capability, e)

                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay_ms / 1000)

        raise RuntimeError(f"All {len(tried_endpoints)} endpoints failed for {capability}. "
                          f"Last error: {last_error}")

    # ── Metrics ────────────────────────────────────────────────────

    def record_result(self, endpoint_id: str, latency_ms: float, success: bool):
        """Record an inference result for metrics tracking."""
        with self._lock:
            ep = self._endpoints.get(endpoint_id)
            if not ep:
                return

            ep.total_requests += 1
            ep.last_latency_ms = latency_ms

            if success:
                # Exponential moving average for latency
                alpha = 0.1
                ep.avg_latency_ms = (alpha * latency_ms +
                                     (1 - alpha) * ep.avg_latency_ms)
                ep.p95_latency_ms = max(ep.p95_latency_ms, latency_ms)
                ep.consecutive_failures = 0

                # Auto-recover circuit
                if ep.circuit_open:
                    ep.circuit_open = False
                    ep.circuit_open_since = None
                    logger.info("Mesh: circuit closed for %s (recovered)", endpoint_id)
            else:
                ep.total_errors += 1
                ep.consecutive_failures += 1

                # Circuit breaker
                if (ep.consecutive_failures >= self.config.circuit_breaker_threshold
                        and not ep.circuit_open):
                    ep.circuit_open = True
                    ep.circuit_open_since = datetime.now(timezone.utc)
                    logger.warning("Mesh: CIRCUIT OPEN for %s (%d consecutive failures)",
                                   endpoint_id, ep.consecutive_failures)

    def get_endpoint_metrics(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metrics for an endpoint."""
        ep = self._endpoints.get(endpoint_id)
        if not ep:
            return None
        return {
            "endpoint_id": ep.endpoint_id,
            "model_name": ep.model_name,
            "model_version": ep.model_version,
            "capability": ep.capability,
            "is_healthy": ep.is_healthy,
            "circuit_open": ep.circuit_open,
            "active_connections": ep.active_connections,
            "total_requests": ep.total_requests,
            "error_rate": ep.total_errors / max(ep.total_requests, 1),
            "avg_latency_ms": round(ep.avg_latency_ms, 2),
            "p95_latency_ms": round(ep.p95_latency_ms, 2),
            "last_latency_ms": round(ep.last_latency_ms, 2),
            "consecutive_failures": ep.consecutive_failures,
        }

    def get_mesh_stats(self) -> Dict[str, Any]:
        """Get global mesh statistics."""
        with self._lock:
            endpoints_stats = [self.get_endpoint_metrics(eid) for eid in self._endpoints]
            healthy = sum(1 for e in self._endpoints.values() if e.is_healthy)
            open_circuits = sum(1 for e in self._endpoints.values() if e.circuit_open)
            total_req = sum(e.total_requests for e in self._endpoints.values())

            return {
                "total_endpoints": len(self._endpoints),
                "healthy_endpoints": healthy,
                "open_circuits": open_circuits,
                "total_requests": total_req,
                "by_capability": {
                    cap: len(eps) for cap, eps in self._by_capability.items()
                },
                "config": {
                    "lb_strategy": self.config.lb_strategy.value,
                    "failover_strategy": self.config.failover_strategy.value,
                    "max_retries": self.config.max_retries,
                    "circuit_breaker_threshold": self.config.circuit_breaker_threshold,
                },
                "endpoints": endpoints_stats,
            }

    # ── Canary Deployment ──────────────────────────────────────────

    def setup_canary(self, capability: str, stable_endpoint_id: str,
                     canary_endpoint_id: str, traffic_split_pct: int = 10):
        """Set up canary deployment: route X% traffic to new version."""
        self.update_weight(stable_endpoint_id, 100 - traffic_split_pct)
        self.update_weight(canary_endpoint_id, traffic_split_pct)

        # Update channel labels
        with self._lock:
            if stable_endpoint_id in self._endpoints:
                self._endpoints[stable_endpoint_id].channel = "STABLE"
            if canary_endpoint_id in self._endpoints:
                self._endpoints[canary_endpoint_id].channel = "CANARY"

        logger.info("Mesh canary: %s %d%% STABLE / %d%% CANARY",
                     capability, 100 - traffic_split_pct, traffic_split_pct)

    def promote_canary(self, capability: str, canary_endpoint_id: str):
        """Promote canary to stable — 100% traffic to new version."""
        stable_eps = [eid for eid in self._by_capability.get(capability, [])
                      if eid != canary_endpoint_id]
        for eid in stable_eps:
            self.update_weight(eid, 0)  # retire old
        self.update_weight(canary_endpoint_id, 100)
        with self._lock:
            if canary_endpoint_id in self._endpoints:
                self._endpoints[canary_endpoint_id].channel = "STABLE"
        logger.info("Mesh: promoted canary %s → STABLE for %s", canary_endpoint_id, capability)

    # ── Internal ───────────────────────────────────────────────────

    def _get_candidates(self, capability: str, exclude: set) -> List[ModelEndpoint]:
        """Get healthy, non-excluded candidates for a capability."""
        endpoint_ids = self._by_capability.get(capability, [])
        candidates = []
        for eid in endpoint_ids:
            if eid in exclude:
                continue
            ep = self._endpoints.get(eid)
            if not ep:
                continue
            if not ep.is_healthy:
                continue
            if ep.circuit_open:
                # Check if circuit breaker timeout has elapsed
                if ep.circuit_open_since:
                    elapsed = (datetime.now(timezone.utc) - ep.circuit_open_since).total_seconds()
                    if elapsed > self.config.circuit_breaker_timeout_seconds:
                        ep.circuit_open = False  # half-open
                        ep.consecutive_failures = 0
                        logger.info("Mesh: circuit half-open for %s", eid)
                    else:
                        continue
            candidates.append(ep)
        return candidates

    def _apply_strategy(self, candidates: List[ModelEndpoint],
                        strategy: LBStrategy) -> ModelEndpoint:
        """Apply the load balancing strategy to select one endpoint."""
        if not candidates:
            raise RuntimeError("No candidates available")

        if strategy == LBStrategy.ROUND_ROBIN:
            cap = candidates[0].capability
            idx = self._rr_counters[cap] % len(candidates)
            self._rr_counters[cap] += 1
            return candidates[idx]

        elif strategy == LBStrategy.LEAST_CONNECTIONS:
            return min(candidates, key=lambda e: e.active_connections)

        elif strategy == LBStrategy.LOWEST_LATENCY:
            return min(candidates, key=lambda e: e.avg_latency_ms if e.avg_latency_ms > 0 else float('inf'))

        elif strategy == LBStrategy.WEIGHTED:
            total_weight = sum(e.weight for e in candidates)
            if total_weight == 0:
                return random.choice(candidates)
            r = random.uniform(0, total_weight)
            cumulative = 0
            for ep in candidates:
                cumulative += ep.weight
                if r <= cumulative:
                    return ep
            return candidates[-1]

        elif strategy in (LBStrategy.CANARY, LBStrategy.AB_TEST):
            # Weighted selection based on channel weights
            return self._apply_strategy(candidates, LBStrategy.WEIGHTED)

        return candidates[0]

    def _start_health_checks(self):
        """Start background health check thread."""
        def _health_loop():
            while True:
                time.sleep(self.config.health_check_interval_seconds)
                self._run_health_checks()

        self._health_check_thread = threading.Thread(target=_health_loop, daemon=True)
        self._health_check_thread.start()

    def _run_health_checks(self):
        """Check health of all registered endpoints."""
        for endpoint_id, ep in list(self._endpoints.items()):
            try:
                # In production: HTTP GET to health endpoint
                # For now, assume healthy if recently active
                ep.last_health_check = datetime.now(timezone.utc)
                ep.is_healthy = True
            except Exception:
                ep.is_healthy = False
                logger.warning("Mesh: health check failed for %s", endpoint_id)


# ── Singleton ──────────────────────────────────────────────────────

_mesh_instance: Optional[RuntimeMesh] = None


def get_runtime_mesh(config: Optional[MeshConfig] = None) -> RuntimeMesh:
    """Get or create the global Runtime Mesh."""
    global _mesh_instance
    if _mesh_instance is None:
        _mesh_instance = RuntimeMesh(config)
        _initialize_default_endpoints(_mesh_instance)
    return _mesh_instance


def _initialize_default_endpoints(mesh: RuntimeMesh):
    """Register default model endpoints from the existing inference pipeline."""
    default_endpoints = [
        ModelEndpoint(
            endpoint_id="det-yolov8n-onnx",
            model_id="yolov8n", model_name="YOLOv8n", model_version="v8.2",
            capability="detection", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=80,
        ),
        ModelEndpoint(
            endpoint_id="det-yolov8s-onnx",
            model_id="yolov8s", model_name="YOLOv8s", model_version="v8.2",
            capability="detection", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=20,
        ),
        ModelEndpoint(
            endpoint_id="face-arcface-onnx",
            model_id="arcface_r100", model_name="ArcFace R100", model_version="v2.1",
            capability="face_recognition", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
        ModelEndpoint(
            endpoint_id="reid-resnet50-onnx",
            model_id="resnet50_reid", model_name="ResNet50 ReID", model_version="v1.0",
            capability="person_reid", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
        ModelEndpoint(
            endpoint_id="vehicle-reid-onnx",
            model_id="vehicle_reid", model_name="Vehicle ReID", model_version="v1.0",
            capability="vehicle_recog", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
        ModelEndpoint(
            endpoint_id="pose-yolov8n-onnx",
            model_id="yolov8n-pose", model_name="YOLOv8n-Pose", model_version="v8.2",
            capability="pose_estimation", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
        ModelEndpoint(
            endpoint_id="embed-mobilenet-onnx",
            model_id="mobilenet_v3", model_name="MobileNetV3", model_version="v1.0",
            capability="embedding", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
        ModelEndpoint(
            endpoint_id="vlm-clip-onnx",
            model_id="clip-vit-b-32", model_name="CLIP ViT-B/32", model_version="v1.0",
            capability="vlm", host="localhost", port=8191,
            runtime="ONNX", channel="STABLE", weight=100,
        ),
    ]

    for ep in default_endpoints:
        mesh.register_endpoint(ep)

    logger.info("Runtime Mesh initialized with %d default endpoints", len(default_endpoints))

"""Runtime OS — Multi-Backend Inference Adapter (Triton, vLLM, ONNX, PyTorch)."""
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RuntimeBackend(Enum):
    TENSORRT = "tensorrt"
    TRITON = "triton"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    VLLM = "vllm"
    ASCEND = "ascend"


class DeviceType(Enum):
    CPU = "cpu"
    CUDA = "cuda"
    NPU = "npu"


@dataclass
class InferRequest:
    model_name: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    batch_size: int = 1
    timeout_ms: int = 5000
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class InferResult:
    request_id: str = ""
    model_name: str = ""
    backend: str = ""
    outputs: Any = None
    latency_ms: float = 0
    gpu_memory_mb: int = 0
    success: bool = True
    error: Optional[str] = None


class BaseRuntime(ABC):
    """Abstract base for all inference runtimes."""

    def __init__(self, name: str, device: str = "cpu"):
        self.name = name
        self.device = device
        self._loaded: Dict[str, Any] = {}
        self._infer_count: int = 0
        self._total_latency: float = 0

    @abstractmethod
    def load_model(self, model_path: str, model_name: str) -> bool:
        ...

    @abstractmethod
    def infer(self, request: InferRequest) -> InferResult:
        ...

    @abstractmethod
    def unload_model(self, model_name: str) -> bool:
        ...

    def list_models(self) -> List[str]:
        return list(self._loaded.keys())

    def get_stats(self) -> dict:
        return {"backend": self.name, "loaded_models": len(self._loaded),
                "infer_count": self._infer_count,
                "avg_latency_ms": round(self._total_latency / max(self._infer_count, 1), 2)}


class TritonRuntime(BaseRuntime):
    """NVIDIA Triton Inference Server adapter."""

    def __init__(self, endpoint: str = "localhost:8000", device: str = "cuda"):
        super().__init__("triton", device)
        self.endpoint = endpoint
        logger.info("Triton Runtime initialized at %s", endpoint)

    def load_model(self, model_path: str, model_name: str) -> bool:
        self._loaded[model_name] = {"path": model_path, "loaded_at": time.time()}
        logger.info("Triton: model %s registered", model_name)
        return True

    def infer(self, request: InferRequest) -> InferResult:
        start = time.perf_counter()
        # Simulated Triton inference
        time.sleep(0.01)
        result = InferResult(
            request_id=request.request_id, model_name=request.model_name,
            backend="triton", outputs={"predictions": [[0.95, 0.03, 0.02]]},
            gpu_memory_mb=1024, success=True,
        )
        result.latency_ms = (time.perf_counter() - start) * 1000
        self._infer_count += 1; self._total_latency += result.latency_ms
        return result

    def unload_model(self, model_name: str) -> bool:
        return self._loaded.pop(model_name, None) is not None


class VLLMRuntime(BaseRuntime):
    """vLLM adapter for large language model inference."""

    def __init__(self, endpoint: str = "localhost:13700", device: str = "cuda"):
        super().__init__("vllm", device)
        self.endpoint = endpoint
        self._max_tokens: int = 4096
        logger.info("vLLM Runtime initialized at %s", endpoint)

    def load_model(self, model_path: str, model_name: str) -> bool:
        self._loaded[model_name] = {"path": model_path, "loaded_at": time.time()}
        logger.info("vLLM: model %s loaded", model_name)
        return True

    def infer(self, request: InferRequest) -> InferResult:
        start = time.perf_counter()
        time.sleep(0.05)  # Simulated vLLM inference
        result = InferResult(
            request_id=request.request_id, model_name=request.model_name,
            backend="vllm", outputs={
                "text": f"[vLLM Response] Processed prompt with {request.batch_size} batch",
                "tokens": 150, "finish_reason": "stop",
            },
            gpu_memory_mb=8192, success=True,
        )
        result.latency_ms = (time.perf_counter() - start) * 1000
        self._infer_count += 1; self._total_latency += result.latency_ms
        return result

    def unload_model(self, model_name: str) -> bool:
        return self._loaded.pop(model_name, None) is not None


class RuntimeMesh:
    """Routes inference requests to the best available runtime."""

    def __init__(self):
        self._runtimes: Dict[str, BaseRuntime] = {}
        self._model_routing: Dict[str, str] = {}  # model_name -> runtime_name

    def register_runtime(self, runtime: BaseRuntime):
        self._runtimes[runtime.name] = runtime
        logger.info("Runtime registered: %s (%s)", runtime.name, runtime.device)

    def load_model(self, model_name: str, model_path: str, preferred_runtime: str = "triton") -> bool:
        runtime = self._runtimes.get(preferred_runtime)
        if runtime:
            ok = runtime.load_model(model_path, model_name)
            if ok: self._model_routing[model_name] = preferred_runtime
            return ok
        return False

    def infer(self, request: InferRequest, preferred_runtime: Optional[str] = None) -> InferResult:
        runtime_name = preferred_runtime or self._model_routing.get(request.model_name, "triton")
        runtime = self._runtimes.get(runtime_name)
        if not runtime:
            return InferResult(request_id=request.request_id, success=False, error=f"No runtime: {runtime_name}")
        return runtime.infer(request)

    def switch_runtime(self, model_name: str, new_runtime: str):
        """Hot-swap model to a different runtime."""
        old = self._model_routing.get(model_name)
        self._model_routing[model_name] = new_runtime
        logger.info("Runtime switched: %s %s -> %s", model_name, old, new_runtime)

    def list_runtimes(self) -> List[Dict]:
        return [{"name": r.name, "device": r.device, "models": r.list_models(), "stats": r.get_stats()}
                for r in self._runtimes.values()]

    def get_stats(self) -> dict:
        return {"total_runtimes": len(self._runtimes), "routed_models": len(self._model_routing)}


# Global runtime mesh
runtime_mesh = RuntimeMesh()
runtime_mesh.register_runtime(TritonRuntime())
runtime_mesh.register_runtime(VLLMRuntime())
# ONNX is already registered via the capability service's ONNX adapter

"""Runtime OS Adapter Framework — abstraction over inference runtimes."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid


@dataclass
class InferRequest:
    model_name: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    batch_size: int = 1
    timeout_ms: int = 5000


@dataclass
class InferResult:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_name: str = ""
    outputs: Any = None
    latency_ms: float = 0
    gpu_memory_used_mb: int = 0
    success: bool = True
    error: Optional[str] = None


class BaseRuntimeAdapter(ABC):
    """Abstract base for all runtime adapters (TensorRT, ONNX, Triton, PyTorch, vLLM, Ascend)."""

    def __init__(self, name: str = "base", device: str = "CPU"):
        self.name = name
        self.device = device
        self._loaded_models: Dict[str, Any] = {}
        self._model_info: Dict[str, Dict] = {}

    @abstractmethod
    def load_model(self, model_path: str, model_name: str, **kwargs) -> bool:
        """Load a model into the runtime. Returns True if successful."""
        ...

    @abstractmethod
    def infer(self, request: InferRequest) -> InferResult:
        """Run inference on a loaded model."""
        ...

    @abstractmethod
    def unload_model(self, model_name: str) -> bool:
        """Unload a model and free resources."""
        ...

    def list_models(self) -> List[str]:
        return list(self._loaded_models.keys())

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        return self._model_info.get(model_name)

    def is_loaded(self, model_name: str) -> bool:
        return model_name in self._loaded_models


class ONNXRuntimeAdapter(BaseRuntimeAdapter):
    """ONNX Runtime adapter — supports CPU, CUDA, OpenVINO, TensorRT EP."""

    def __init__(self, device: str = "CPU"):
        super().__init__(name="onnxruntime", device=device)
        self._session = None
        try:
            import onnxruntime as ort
            self._ort = ort
            self._available = True
            providers = ort.get_available_providers()
            self._providers = providers
        except ImportError:
            self._ort = None
            self._available = False
            self._providers = []

    @property
    def available(self) -> bool:
        return self._available

    def load_model(self, model_path: str, model_name: str, **kwargs) -> bool:
        if not self._available:
            return False
        try:
            sess_options = self._ort.SessionOptions()
            sess_options.graph_optimization_level = self._ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            provider = ['CUDAExecutionProvider'] if self.device == 'CUDA' else ['CPUExecutionProvider']
            # Filter to available providers
            provider = [p for p in provider if p in self._providers]
            if not provider:
                provider = ['CPUExecutionProvider']

            session = self._ort.InferenceSession(model_path, sess_options, providers=provider)
            self._loaded_models[model_name] = session
            self._model_info[model_name] = {
                'path': model_path, 'device': self.device,
                'input_names': [i.name for i in session.get_inputs()],
                'output_names': [o.name for o in session.get_outputs()],
            }
            return True
        except Exception as e:
            print(f"ONNX load failed: {e}")
            return False

    def infer(self, request: InferRequest) -> InferResult:
        result = InferResult(model_name=request.model_name)
        start = time.time()
        try:
            session = self._loaded_models.get(request.model_name)
            if not session:
                result.success = False
                result.error = f"Model not loaded: {request.model_name}"
                return result

            ort_inputs = {}
            for input_meta in session.get_inputs():
                name = input_meta.name
                if name in request.inputs:
                    ort_inputs[name] = request.inputs[name]
                else:
                    import numpy as np
                    shape = [dim if isinstance(dim, int) else 1 for dim in input_meta.shape]
                    ort_inputs[name] = np.random.randn(*shape).astype(np.float32)

            outputs = session.run(None, ort_inputs)
            result.outputs = {out.name: val.tolist() if hasattr(val, 'tolist') else val
                              for out, val in zip(session.get_outputs(), outputs)}
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
        result.latency_ms = (time.time() - start) * 1000
        return result

    def unload_model(self, model_name: str) -> bool:
        if model_name in self._loaded_models:
            del self._loaded_models[model_name]
            self._model_info.pop(model_name, None)
            return True
        return False


# Global runtime registry
class RuntimeRegistry:
    """Manages all runtime adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseRuntimeAdapter] = {}

    def register(self, adapter: BaseRuntimeAdapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[BaseRuntimeAdapter]:
        return self._adapters.get(name)

    def list_adapters(self) -> List[Dict]:
        return [{'name': a.name, 'device': a.device, 'models': a.list_models(),
                  'available': getattr(a, 'available', True)}
                for a in self._adapters.values()]

    def route(self, model_name: str) -> Optional[BaseRuntimeAdapter]:
        """Find which adapter has the model loaded."""
        for adapter in self._adapters.values():
            if adapter.is_loaded(model_name):
                return adapter
        return None


runtime_registry = RuntimeRegistry()
onnx_adapter = ONNXRuntimeAdapter(device="CPU")
if onnx_adapter.available:
    runtime_registry.register(onnx_adapter)

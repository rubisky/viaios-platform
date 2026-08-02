"""
Extended Runtimes — vLLM + PyTorch integration (P5-3).
Provides additional inference runtimes beyond ONNX/Triton.
"""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── vLLM Runtime ──────────────────────────────────────────────────

class VLLMRuntime:
    """vLLM-based LLM inference runtime for high-throughput text generation."""
    def __init__(self, model: str = "", tensor_parallel: int = 1):
        self.model = model or os.getenv("VLLM_MODEL", "deepseek-chat")
        self.tensor_parallel = tensor_parallel
        self._client = None

    def load(self) -> bool:
        try:
            # vLLM Python API
            from vllm import LLM, SamplingParams
            self._client = LLM(model=self.model, tensor_parallel_size=self.tensor_parallel)
            logger.info("vLLM loaded: %s (TP=%d)", self.model, self.tensor_parallel)
            return True
        except ImportError:
            logger.info("vLLM not installed — available via: pip install vllm")
            return False
        except Exception as e:
            logger.warning("vLLM load failed: %s", e)
            return False

    def generate(self, prompt: str, max_tokens: int = 256,
                 temperature: float = 0.7) -> Dict[str, Any]:
        if not self._client:
            return {"text": f"[vLLM not loaded] {prompt[:50]}...", "tokens": 0}
        from vllm import SamplingParams
        params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
        outputs = self._client.generate([prompt], params)
        return {"text": outputs[0].outputs[0].text, "tokens": len(outputs[0].outputs[0].token_ids)}


# ── PyTorch Runtime ───────────────────────────────────────────────

class PyTorchRuntime:
    """Native PyTorch inference runtime for custom models."""
    def __init__(self, model_path: str = ""):
        self.model_path = model_path
        self._model = None
        self._device = "cuda" if self._has_cuda() else "cpu"

    def load(self, model_class: str = "") -> bool:
        try:
            import torch
            if not self.model_path:
                logger.info("PyTorch Runtime ready (CPU: %s)", self._device)
                return True
            self._model = torch.jit.load(self.model_path, map_location=self._device)
            self._model.eval()
            logger.info("PyTorch model loaded: %s on %s", self.model_path, self._device)
            return True
        except ImportError:
            logger.info("PyTorch not installed")
            return False
        except Exception as e:
            logger.warning("PyTorch load failed: %s", e)
            return False

    def infer(self, inputs: Any) -> Any:
        import torch
        if not self._model:
            return {"output": "model not loaded"}
        with torch.no_grad():
            if isinstance(inputs, dict):
                inputs = {k: torch.tensor(v).to(self._device) for k, v in inputs.items()}
            output = self._model(**inputs) if isinstance(inputs, dict) else self._model(inputs)
            return output

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False


# ── Convenience ────────────────────────────────────────────────────

_vllm: Optional[VLLMRuntime] = None
_torch: Optional[PyTorchRuntime] = None

def get_vllm() -> VLLMRuntime:
    global _vllm
    if _vllm is None: _vllm = VLLMRuntime()
    return _vllm

def get_torch_runtime() -> PyTorchRuntime:
    global _torch
    if _torch is None: _torch = PyTorchRuntime()
    return _torch

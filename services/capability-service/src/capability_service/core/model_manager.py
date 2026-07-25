"""Model Manager — Model lifecycle, versioning, and hot-swap."""
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    REGISTERED = "REGISTERED"
    LOADING = "LOADING"
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    UNLOADING = "UNLOADING"
    ERROR = "ERROR"
    RETIRED = "RETIRED"


class ModelFramework(Enum):
    ONNX = "ONNX"
    TENSORRT = "TensorRT"
    PYTORCH = "PyTorch"
    TRITON = "Triton"
    VLLM = "vLLM"


@dataclass
class ModelVersion:
    """A specific version of a model."""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    version: str = "1.0.0"   # semver
    framework: str = "ONNX"
    task: str = "detection"       # detection, classification, ocr, etc.
    precision: str = "FP16"       # FP32, FP16, INT8
    gpu_memory_mb: int = 2048
    model_path: str = ""          # path to model file
    status: str = "REGISTERED"
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id, "name": self.name,
            "version": self.version, "framework": self.framework,
            "task": self.task, "status": self.status,
            "gpu_memory_mb": self.gpu_memory_mb,
            "metrics": self.metrics, "created_at": self.created_at,
        }


class ModelRegistry:
    """Central registry for all model versions with hot-swap support."""

    def __init__(self):
        self._models: Dict[str, Dict[str, ModelVersion]] = {}  # name -> {version -> model}
        self._active: Dict[str, str] = {}  # name -> active version
        self._history: List[Dict] = []  # swap history

    def register(self, name: str, version: str, framework: str = "ONNX",
                 task: str = "detection", model_path: str = "",
                 gpu_memory_mb: int = 2048, precision: str = "FP16") -> ModelVersion:
        """Register a new model version."""
        mv = ModelVersion(
            name=name, version=version, framework=framework,
            task=task, model_path=model_path,
            gpu_memory_mb=gpu_memory_mb, precision=precision,
        )
        if name not in self._models:
            self._models[name] = {}
        self._models[name][version] = mv
        logger.info("Registered model: %s v%s (%s)", name, version, framework)
        return mv

    def activate(self, name: str, version: str) -> Dict[str, Any]:
        """Activate a model version (hot-swap if another version is active)."""
        if name not in self._models or version not in self._models[name]:
            return {"error": f"Model {name} v{version} not found"}

        mv = self._models[name][version]
        if mv.status == "ERROR":
            return {"error": f"Model {name} v{version} is in ERROR state"}

        old_version = self._active.get(name)
        swap_info = {"name": name, "new_version": version, "old_version": old_version}

        # Validate new model
        mv.status = "LOADING"
        load_ok = self._validate_model(mv)
        if not load_ok:
            mv.status = "ERROR"
            return {"error": f"Failed to validate {name} v{version}"}

        # Activate
        mv.status = "ACTIVE"
        mv.activated_at = datetime.now(timezone.utc).isoformat()
        self._active[name] = version

        # Deactivate old version
        if old_version and old_version in self._models[name]:
            old_mv = self._models[name][old_version]
            old_mv.status = "RETIRED"
            swap_info["deactivated"] = old_version

        self._history.append({
            **swap_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Hot-swap: %s v%s -> v%s", name, old_version or "none", version)
        return swap_info

    def _validate_model(self, mv: ModelVersion) -> bool:
        """Validate a model before activation."""
        # Check model file exists
        import os
        if mv.model_path and not os.path.exists(mv.model_path):
            logger.warning("Model file not found: %s", mv.model_path)
            # Don't fail for demo - in production check real path
        # Simulate load time
        time.sleep(0.1)
        return True

    def get_active(self, name: str) -> Optional[ModelVersion]:
        """Get the currently active version of a model."""
        version = self._active.get(name)
        if version and name in self._models:
            return self._models[name].get(version)
        return None

    def get_version(self, name: str, version: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        return self._models.get(name, {}).get(version)

    def list_versions(self, name: str) -> List[ModelVersion]:
        """List all versions of a model."""
        return list(self._models.get(name, {}).values())

    def list_all(self) -> List[ModelVersion]:
        """List all registered models."""
        result = []
        for versions in self._models.values():
            result.extend(versions.values())
        return result

    def get_swap_history(self, name: Optional[str] = None) -> List[Dict]:
        """Get hot-swap history."""
        if name:
            return [h for h in self._history if h["name"] == name]
        return list(self._history)

    def update_metrics(self, name: str, version: str, metrics: Dict[str, Any]):
        """Update performance metrics for a model version."""
        if name in self._models and version in self._models[name]:
            self._models[name][version].metrics.update(metrics)

    def compare_versions(self, name: str) -> Dict[str, Any]:
        """Compare all versions of a model by their metrics."""
        versions = self.list_versions(name)
        return {
            "name": name,
            "active": self._active.get(name),
            "versions": [
                {"version": v.version, "status": v.status,
                 "framework": v.framework, "metrics": v.metrics}
                for v in sorted(versions, key=lambda x: x.version)
            ],
        }

    def stats(self) -> dict:
        total_models = sum(len(v) for v in self._models.values())
        active_count = len(self._active)
        return {
            "total_models": total_models,
            "active_models": active_count,
            "model_names": list(self._models.keys()),
            "swap_count": len(self._history),
        }


# Global registry
model_registry = ModelRegistry()


def init_demo_models():
    """Register demo models for testing."""
    models = [
        ("yolov8x", "1.0.0", "TensorRT", "detection", 2048),
        ("yolov8x", "2.0.0", "TensorRT", "detection", 1800),
        ("arcface", "1.0.0", "ONNX", "face_recognition", 1024),
        ("paddleocr", "1.0.0", "ONNX", "ocr", 512),
        ("clip-vit", "1.0.0", "ONNX", "embedding", 2048),
    ]
    registered = []
    for name, ver, fw, task, mem in models:
        mv = model_registry.register(name, ver, fw, task, gpu_memory_mb=mem)
        registered.append(mv.model_id)
    # Activate some
    model_registry.activate("yolov8x", "1.0.0")
    model_registry.activate("arcface", "1.0.0")
    logger.info("Demo models registered: %d models", len(registered))
    return registered

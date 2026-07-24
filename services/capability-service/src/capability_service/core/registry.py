"""Capability Registry — manages AI capabilities and model mesh routing."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import time
import uuid


class CapabilityType(Enum):
    DETECTION = "detection"
    TRACKING = "tracking"
    SEGMENTATION = "segmentation"
    FACE_RECOGNITION = "face_recognition"
    PERSON_REID = "person_reid"
    VEHICLE_RECOGNITION = "vehicle_recognition"
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    OCR = "ocr"
    IMAGE_ENHANCEMENT = "image_enhancement"
    VLM = "vlm"
    POSE_ESTIMATION = "pose_estimation"
    EMBEDDING = "embedding"


@dataclass
class ModelInfo:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    version: str = "1.0.0"
    framework: str = "ONNX"  # TENSORRT, ONNX, PYTORCH, TRITON, VLLM
    task: str = ""
    precision: str = "FP16"
    gpu_memory_mb: int = 2048
    avg_latency_ms: int = 50
    status: str = "REGISTERED"


@dataclass
class Capability:
    cap_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    cap_type: CapabilityType = CapabilityType.DETECTION
    description: str = ""
    default_model: Optional[str] = None
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    handler: Optional[Callable] = None
    version: str = "1.0.0"


class CapabilityRegistry:
    """Central registry for all AI capabilities with model mesh routing."""

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._models: Dict[str, ModelInfo] = {}

    def register(self, cap: Capability) -> str:
        self._capabilities[cap.cap_id] = cap
        for mid, model in cap.models.items():
            self._models[mid] = model
        return cap.cap_id

    def get(self, cap_id: str) -> Optional[Capability]:
        return self._capabilities.get(cap_id)

    def get_by_type(self, cap_type: CapabilityType) -> List[Capability]:
        return [c for c in self._capabilities.values() if c.cap_type == cap_type]

    def list_all(self) -> List[Capability]:
        return list(self._capabilities.values())

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def route_model(self, cap_type: CapabilityType) -> Optional[ModelInfo]:
        """Model Mesh: route to best available model for capability type."""
        caps = self.get_by_type(cap_type)
        for cap in caps:
            for model in cap.models.values():
                if model.status == "ACTIVE":
                    return model
        return None


# Global singleton
capability_registry = CapabilityRegistry()

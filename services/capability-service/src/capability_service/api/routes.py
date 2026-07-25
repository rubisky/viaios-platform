"""Capability Service API Routes — 15 AI capabilities with Model Mesh."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from capability_service.core.registry import (
    capability_registry, Capability, ModelInfo, CapabilityType
)
from capability_service.core.runtime_adapter import (
    runtime_registry, onnx_adapter, InferRequest as RtInferRequest
)
from capability_service.core.benchmark import (
    benchmark_engine, BenchmarkConfig, BenchmarkResult
)

logger = logging.getLogger(__name__)
router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    cap_type: str
    description: str = ""
    version: str = "1.0.0"


class ModelRegisterRequest(BaseModel):
    cap_id: str
    name: str
    version: str = "1.0.0"
    framework: str = "ONNX"
    task: str = ""
    precision: str = "FP16"
    gpu_memory_mb: int = 2048


class InferRequest(BaseModel):
    cap_type: Optional[str] = None
    cap_id: Optional[str] = None
    model_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)


@router.get("/api/v1/capabilities")
async def list_capabilities(cap_type: Optional[str] = None):
    if cap_type:
        try:
            ct = CapabilityType(cap_type)
            caps = capability_registry.get_by_type(ct)
        except ValueError:
            raise HTTPException(400, f"Invalid type: {cap_type}")
    else:
        caps = capability_registry.list_all()
    return {"capabilities": [
        {"id": c.cap_id, "name": c.name, "type": c.cap_type.value,
         "description": c.description, "models": len(c.models)} for c in caps
    ]}


@router.post("/api/v1/capabilities/register")
async def register_capability(request: RegisterRequest):
    try:
        ct = CapabilityType(request.cap_type)
    except ValueError:
        raise HTTPException(400, f"Unknown type: {request.cap_type}")
    cap = Capability(name=request.name, cap_type=ct, description=request.description)
    return {"cap_id": capability_registry.register(cap)}


@router.post("/api/v1/capabilities/models")
async def register_model(request: ModelRegisterRequest):
    cap = capability_registry.get(request.cap_id)
    if not cap:
        raise HTTPException(404, f"Capability not found: {request.cap_id}")
    model = ModelInfo(name=request.name, version=request.version,
                      framework=request.framework, task=request.task,
                      precision=request.precision, gpu_memory_mb=request.gpu_memory_mb)
    cap.models[model.model_id] = model
    capability_registry.register(cap)
    return {"model_id": model.model_id}


@router.post("/api/v1/capabilities/infer")
async def infer(request: InferRequest):
    model = None
    if request.model_id:
        model = capability_registry.get_model(request.model_id)
    elif request.cap_type:
        try:
            ct = CapabilityType(request.cap_type)
            model = capability_registry.route_model(ct)
        except ValueError:
            raise HTTPException(400, f"Invalid type: {request.cap_type}")
    if not model:
        raise HTTPException(404, "No suitable model found")

    # Try real ONNX inference first
    result = None
    if onnx_adapter.available and onnx_adapter.is_loaded("test_model"):
        infer_req = InferRequest(model_name="test_model", inputs=request.inputs)
        result = onnx_adapter.infer(infer_req)

    if result and result.success:
        outputs = {
            "model_id": model.model_id, "model_name": model.name,
            "framework": model.framework, "engine": "ONNX Runtime CPU",
            "latency_ms": result.latency_ms,
            "results": [{"real_inference": True, "output": str(result.outputs)}],
        }
    else:
        outputs = {
            "model_id": model.model_id, "model_name": model.name,
            "framework": model.framework, "latency_ms": model.avg_latency_ms,
            "engine": "Simulated",
            "results": _simulate(model.task, request.inputs),
        }
    return {"status": "completed", "data": outputs}


def _simulate(task: str, inputs: dict) -> list:
    if "detect" in task:
        return [{"class": "person", "confidence": 0.95, "bbox": [100, 150, 300, 400]}]
    if "face" in task:
        return [{"identity": "person_001", "confidence": 0.93}]
    if "ocr" in task:
        return [{"text": "VIAIOS", "confidence": 0.99}]
    return [{"result": "ok", "confidence": 0.90}]


@router.post("/api/v1/capabilities/init-onnx")
async def init_onnx():
    """Load the ONNX model into the runtime for real inference."""
    if onnx_adapter.available:
        ok = onnx_adapter.load_model("/opt/models/test_model.onnx", "test_model")
        return {"onnx_available": True, "model_loaded": ok,
                "models": onnx_adapter.list_models(),
                "providers": onnx_adapter._providers}
    return {"onnx_available": False, "error": "ONNX Runtime not installed"}

@router.get("/api/v1/capabilities/runtimes")
async def list_runtimes():
    """List all runtime adapters and their loaded models."""
    return {"adapters": runtime_registry.list_adapters()}

@router.post("/api/v1/capabilities/init-demo")
async def init_demo():
    demos = [
        ("object-detection", CapabilityType.DETECTION, "detection"),
        ("face-recognition", CapabilityType.FACE_RECOGNITION, "face_recognition"),
        ("vehicle-recognition", CapabilityType.VEHICLE_RECOGNITION, "vehicle_recognition"),
        ("ocr-engine", CapabilityType.OCR, "ocr"),
    ]
    ids = []
    for name, ct, task in demos:
        cap = Capability(name=name, cap_type=ct)
        model = ModelInfo(name=f"{name}-v1", framework="ONNX", task=task, status="ACTIVE")
        cap.models[model.model_id] = model
        cap.default_model = model.model_id
        ids.append(capability_registry.register(cap))
    return {"registered": ids}


# ===== Benchmark Endpoints =====

class BenchmarkRequest(BaseModel):
    model_id: str
    warmup_iterations: int = 5
    benchmark_iterations: int = 50
    batch_size: int = 1


class CompareRequest(BaseModel):
    model_ids: List[str]


@router.post("/api/v1/capabilities/benchmark")
async def run_benchmark(request: BenchmarkRequest):
    """Run a performance benchmark on a registered model."""
    model = capability_registry.get_model(request.model_id)
    if not model:
        raise HTTPException(404, f"Model not found: {request.model_id}")

    # Find the capability this model belongs to
    model_name = model.name
    cap_name = ""
    for cap in capability_registry.list_all():
        if request.model_id in cap.models:
            cap_name = cap.name
            model_name = f"{cap.name}/{model.name}"
            break

    config = BenchmarkConfig(
        model_id=request.model_id,
        warmup_iterations=request.warmup_iterations,
        benchmark_iterations=request.benchmark_iterations,
        batch_sizes=[request.batch_size],
    )

    # Create inference function based on model type
    def inference_fn():
        if onnx_adapter.available and onnx_adapter.is_loaded("test_model"):
            req = RtInferRequest(model_name="test_model", inputs={"test": "data"})
            onnx_adapter.infer(req)
        else:
            # Simulated inference
            import random, math
            _ = sum(math.sqrt(random.random()) for _ in range(10000))

    result = benchmark_engine.run_benchmark(
        model_id=request.model_id,
        model_name=model_name,
        framework=model.framework,
        task=model.task,
        inference_fn=inference_fn,
        config=config,
    )

    return {"status": "completed", "benchmark": result.to_dict()}


@router.get("/api/v1/capabilities/benchmark/{model_id}")
async def get_benchmark_results(model_id: str):
    """Get all benchmark results for a specific model."""
    results = benchmark_engine.get_results(model_id)
    if not results:
        raise HTTPException(404, f"No benchmark results for model: {model_id}")
    return {
        "model_id": model_id,
        "total_runs": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.post("/api/v1/capabilities/benchmark/compare")
async def compare_models(request: CompareRequest):
    """Compare benchmark results across multiple models."""
    comparison = benchmark_engine.compare_models(request.model_ids)
    if not comparison["models"]:
        raise HTTPException(404, "No benchmark results found for any of the specified models")
    return comparison


@router.get("/api/v1/capabilities/benchmarks")
async def list_all_benchmarks():
    """List all benchmark results for all models."""
    return {"benchmarks": benchmark_engine.list_all_results()}


@router.post("/api/v1/capabilities/quick-benchmark")
async def quick_benchmark(request: BenchmarkRequest):
    """Run a quick 20-iteration benchmark for rapid evaluation."""
    model = capability_registry.get_model(request.model_id)
    if not model:
        raise HTTPException(404, f"Model not found: {request.model_id}")

    model_name = model.name
    for cap in capability_registry.list_all():
        if request.model_id in cap.models:
            model_name = f"{cap.name}/{model.name}"
            break

    def inference_fn():
        import random, math
        _ = sum(math.sqrt(random.random()) for _ in range(5000))

    result = benchmark_engine.quick_benchmark(
        model_id=request.model_id,
        model_name=model_name,
        framework=model.framework,
        task=model.task,
        inference_fn=inference_fn,
    )

    return {"status": "completed", "benchmark": result.to_dict()}


# ===== Model Manager (Hot-Swap) =====
from capability_service.core.model_manager import model_registry, init_demo_models

class ModelRegReq(BaseModel):
    name: str; version: str = "1.0.0"; framework: str = "ONNX"; task: str = "detection"; gpu_memory_mb: int = 2048

class HotSwapReq(BaseModel):
    name: str; version: str

@router.post("/api/v1/models/register")
async def register_new_model(request: ModelRegReq):
    mv = model_registry.register(request.name, request.version, request.framework, request.task, gpu_memory_mb=request.gpu_memory_mb)
    return {"model_id": mv.model_id, "status": mv.status}

@router.post("/api/v1/models/hot-swap")
async def hot_swap_model(request: HotSwapReq):
    return model_registry.activate(request.name, request.version)

@router.get("/api/v1/models")
async def list_all_models():
    return {"models": [m.to_dict() for m in model_registry.list_all()]}

@router.get("/api/v1/models/{name}")
async def get_model(name: str):
    return model_registry.compare_versions(name)

@router.post("/api/v1/models/init-demo")
async def init_models_demo():
    return {"registered": init_demo_models(), "stats": model_registry.stats()}

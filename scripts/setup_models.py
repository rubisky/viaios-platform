#!/usr/bin/env python3
"""VIAIOS 一键模型部署 — 下载/导出全部ONNX模型 + 验证 + 重启"""

import os, sys, subprocess, time

MODEL_DIR = os.getenv("VIAIOS_MODEL_DIR", "/opt/viaios/models")
os.makedirs(MODEL_DIR, exist_ok=True)

def check(model):
    """Check if model exists, return (name, size_mb)."""
    p = os.path.join(MODEL_DIR, f"{model}.onnx")
    if os.path.exists(p):
        return (True, os.path.getsize(p) / 1048576)
    return (False, 0)

def export_yolo(name):
    """Export YOLO model from ultralytics."""
    dest = os.path.join(MODEL_DIR, f"{name}.onnx")
    if os.path.exists(dest):
        mb = os.path.getsize(dest) / 1048576
        print(f"  [SKIP] {name}.onnx ({mb:.1f} MB)")
        return True
    print(f"  [EXPORT] {name} -> ONNX ...")
    try:
        from ultralytics import YOLO
        m = YOLO(f"{name}.pt")
        m.export(format="onnx", imgsz=640, opset=12, simplify=True)
        # move to model dir
        src = f"{name}.onnx"
        if os.path.exists(src):
            os.rename(src, dest)
            mb = os.path.getsize(dest) / 1048576
            print(f"  [OK] {name}.onnx ({mb:.1f} MB)")
            return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
    return False

def export_torch(model_name, factory, input_shape=(1,3,224,224)):
    """Export torchvision model to ONNX."""
    dest = os.path.join(MODEL_DIR, f"{model_name}.onnx")
    if os.path.exists(dest):
        mb = os.path.getsize(dest) / 1048576
        print(f"  [SKIP] {model_name}.onnx ({mb:.1f} MB)")
        return True
    print(f"  [EXPORT] {model_name} -> ONNX ...")
    try:
        import torch
        m = factory(weights="DEFAULT")
        m.eval()
        torch.onnx.export(m, torch.randn(*input_shape), dest,
                         opset_version=12, input_names=["input"], output_names=["output"])
        mb = os.path.getsize(dest) / 1048576
        print(f"  [OK] {model_name}.onnx ({mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [FAIL] {model_name}: {e}")
    return False

def restart_services():
    """Restart Python agent service."""
    print("\n  Restarting services...")
    for unit in ["viaios-py-agent", "viaios-py-capability", "viaios-py-knowledge"]:
        r = subprocess.run(["systemctl", "restart", unit], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  [OK] {unit} restarted")
        else:
            print(f"  [WARN] {unit}: {r.stderr.strip()}")
    time.sleep(5)

def verify():
    """Verify all models load correctly."""
    sys.path.insert(0, "/opt/viaios/services/agent-service/src")
    from agent_service.core.inference_pipeline import load_all_pipelines, get_pipeline
    import numpy as np

    print("\n  Verifying models ...")
    results = load_all_pipelines()
    all_ok = True
    for name, ok in results.items():
        status = "LOADED" if ok else "MISSING"
        if not ok: all_ok = False
        print(f"  [{status:<7}] {name}")

    # Quick inference test
    if results.get("detection"):
        pipe = get_pipeline("detection")
        img = (np.random.rand(640, 640, 3) * 255).astype(np.uint8)
        r = pipe.run(img)
        print(f"  [TEST] YOLO inference: {r.get('count')} detections, {r.get('latency_ms', 0):.0f}ms, source={r.get('source')}")

    if results.get("person_reid"):
        pipe = get_pipeline("person_reid")
        img = (np.random.rand(720, 1280, 3) * 255).astype(np.uint8)
        r = pipe.run(img)
        print(f"  [TEST] Person ReID: {r.get('count')} persons, {r.get('latency_ms', 0):.0f}ms, source={r.get('source')}")

    return all_ok

def main():
    print("=" * 55)
    print("  VIAIOS 一键模型部署")
    print("=" * 55)
    print(f"  Model dir: {MODEL_DIR}\n")

    ok = 0
    total = 0

    # --- YOLO detection ---
    print("[1/4] YOLO 检测模型")
    for m in ["yolov8n"]:  # yolov8s optional
        if export_yolo(m): ok += 1
        total += 1

    # --- Torchvision backbones ---
    print("\n[2/4] ResNet50 行人ReID主干")
    import torchvision
    if export_torch("resnet50_reid", torchvision.models.resnet50): ok += 1
    total += 1

    print("\n[3/4] MobileNetV3 车辆ReID主干")
    if export_torch("vehicle_reid", torchvision.models.mobilenet_v3_small): ok += 1
    total += 1

    # --- Restart ---
    print(f"\n{'-'*40}")
    print(f"  Models: {ok}/{total} ready")
    restart_services()

    # --- Verify ---
    all_ok = verify()

    # --- Summary ---
    print(f"\n{'='*55}")
    print(f"  Models: {ok}/{total} exported")
    print(f"  Files:")
    for f in sorted(os.listdir(MODEL_DIR)):
        if f.endswith('.onnx'):
            mb = os.path.getsize(os.path.join(MODEL_DIR, f)) / 1048576
            print(f"    {f:<30} {mb:.1f} MB")
    print(f"  Status: {'ALL OK' if all_ok else 'Some models missing (non-critical)'}")
    print(f"  Test: curl http://localhost:8191/actuator/health")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()

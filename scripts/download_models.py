"""
Export ONNX models for VIAIOS AI inference pipelines.
Uses ultralytics/torch to download + export to ONNX (no external URLs).
Run: python3 scripts/download_models.py --all
     python3 scripts/download_models.py --detection  (YOLO only, ~30 MB)
"""
import argparse
import os
import sys

MODEL_DIR = os.getenv("VIAIOS_MODEL_DIR", "/opt/viaios/models")

MODELS = {
    "yolov8n":       {"size_mb": 12,  "pipeline": "detection",   "desc": "YOLOv8 nano — general object detection"},
    "yolov8s":       {"size_mb": 43,  "pipeline": "detection",   "desc": "YOLOv8 small — more accurate detection"},
    "yolov8n-pose":  {"size_mb": 13,  "pipeline": "pose",        "desc": "YOLOv8 nano pose — human pose estimation"},
}


def export_yolo(model_name: str, dest_dir: str) -> bool:
    """Download and export YOLO model to ONNX using ultralytics."""
    dest = os.path.join(dest_dir, f"{model_name}.onnx")
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  [SKIP] {model_name}.onnx exists ({size_mb:.1f} MB)")
        return True

    try:
        from ultralytics import YOLO
        print(f"  [EXPORT] {model_name} → ONNX ...")
        model = YOLO(f"{model_name}.pt")  # Auto-downloads from ultralytics
        model.export(format="onnx", imgsz=640, opset=12, simplify=True)
        src = f"{model_name}.onnx"
        if os.path.exists(src):
            os.rename(src, dest)
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"  [OK] {model_name}.onnx ({size_mb:.1f} MB)")
            return True
        print(f"  [FAIL] export did not produce {src}")
        return False
    except ImportError:
        print(f"  [FAIL] ultralytics not installed. Run: pip install ultralytics")
        return False
    except Exception as e:
        print(f"  [FAIL] {model_name}: {e}")
        return False


def export_torchvision(model_name: str, dest_dir: str) -> bool:
    """Export torchvision classification model to ONNX."""
    dest = os.path.join(dest_dir, f"{model_name}.onnx")
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  [SKIP] {model_name}.onnx exists ({size_mb:.1f} MB)")
        return True

    try:
        import torch
        import torchvision

        model_map = {
            "resnet50": torchvision.models.resnet50,
            "mobilenet_v3_small": torchvision.models.mobilenet_v3_small,
        }
        factory = model_map.get(model_name)
        if not factory:
            print(f"  [FAIL] unknown model: {model_name}")
            return False

        model = factory(weights="DEFAULT")
        model.eval()
        dummy = torch.randn(1, 3, 224, 224)
        torch.onnx.export(model, dummy, dest, opset_version=12,
                         input_names=["input"], output_names=["output"],
                         dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}})
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  [OK] {model_name}.onnx ({size_mb:.1f} MB)")
        return True
    except ImportError:
        print(f"  [FAIL] torch/torchvision not installed. Run: pip install torch torchvision")
        return False
    except Exception as e:
        print(f"  [FAIL] {model_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Export VIAIOS ONNX models")
    parser.add_argument("--all", action="store_true", help="Export all available models")
    parser.add_argument("--detection", action="store_true", help="Export YOLO detection models only")
    parser.add_argument("--pose", action="store_true", help="Export YOLO pose model")
    parser.add_argument("--reid", action="store_true", help="Export torchvision ReID backbone")
    parser.add_argument("--dir", type=str, default=MODEL_DIR, help="Destination directory")
    parser.add_argument("--list", action="store_true", help="List available models")

    args = parser.parse_args()
    dest = args.dir
    os.makedirs(dest, exist_ok=True)
    print(f"Model directory: {dest}\n")

    if args.list:
        print(f"{'Model':<18} {'Size':<8} {'Pipeline':<14} Description")
        print("-" * 72)
        for name, info in MODELS.items():
            print(f"{name:<18} {info['size_mb']} MB{'':<3} {info['pipeline']:<14} {info['desc']}")
        print(f"\nManual install required for:")
        print(f"  arcface, vehicle_reid — need insightface/torchreid packages")
        print(f"  ppocr — need paddleocr package")
        print(f"  clip — need open_clip or transformers")
        print(f"  deepsort — need deep-sort-realtime package")
        return

    success = 0
    total = 0

    # YOLO detection models
    if args.all or args.detection:
        print("=== Detection Models (ultralytics) ===")
        for name in ["yolov8n", "yolov8s"]:
            if export_yolo(name, dest):
                success += 1
            total += 1

    # YOLO pose
    if args.all or args.pose:
        print("\n=== Pose Model (ultralytics) ===")
        if export_yolo("yolov8n-pose", dest):
            success += 1
        total += 1

    # Torchvision ReID backbone
    if args.all or args.reid:
        print("\n=== ReID Backbone (torchvision) ===")
        if export_torchvision("mobilenet_v3_small", dest):
            success += 1
        total += 1

    if not any([args.all, args.detection, args.pose, args.reid]):
        print("Usage examples:")
        print("  python3 download_models.py --detection   # YOLO only, ~30MB, fast")
        print("  python3 download_models.py --all          # All auto-exportable models")
        print("  python3 download_models.py --list         # List all models")
        return

    print(f"\nDone: {success}/{total} models exported to {dest}")
    if success > 0:
        print(f"Models ready for inference!")
        print(f"Test: curl http://localhost:8191/metrics  # check inference counters")


if __name__ == "__main__":
    main()

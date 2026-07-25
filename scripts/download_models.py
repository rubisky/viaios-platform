"""
Download ONNX models for VIAIOS AI inference pipelines.
Run: python scripts/download_models.py --all
     python scripts/download_models.py --model yolov8n
"""
import argparse
import os
import sys
import urllib.request

MODEL_DIR = os.getenv("VIAIOS_MODEL_DIR", "/opt/viaios/models")

MODELS = {
    "yolov8n": {
        "url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.onnx",
        "file": "yolov8n.onnx", "size_mb": 12, "pipeline": "detection",
    },
    "yolov8n-pose": {
        "url": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.onnx",
        "file": "yolov8n-pose.onnx", "size_mb": 13, "pipeline": "pose",
    },
    "resnet50_reid": {
        "url": "https://github.com/JDAI-CV/fast-reid/releases/download/v1.0.0/resnet50_market1501.onnx",
        "file": "resnet50_reid.onnx", "size_mb": 95, "pipeline": "person_reid",
    },
    "arcface": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/arcface_r100.onnx",
        "file": "arcface_r100.onnx", "size_mb": 167, "pipeline": "face",
    },
    "vehicle_reid": {
        "url": "https://github.com/JDAI-CV/fast-reid/releases/download/v1.0.0/resnet50_veri.onnx",
        "file": "vehicle_reid.onnx", "size_mb": 95, "pipeline": "vehicle",
    },
    "clip-vit": {
        "url": "https://github.com/onnx/models/raw/main/vision/classification/vit/model/vit-b-32.onnx",
        "file": "clip-vit-b-32.onnx", "size_mb": 350, "pipeline": "embedding",
    },
    "ppocr_det": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.onnx",
        "file": "ppocr_det.onnx", "size_mb": 5, "pipeline": "ocr",
    },
    "ppocr_rec": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.onnx",
        "file": "ppocr_rec.onnx", "size_mb": 12, "pipeline": "ocr",
    },
    "deepsort": {
        "url": "https://github.com/SharperM/ONNX-DeepSORT/raw/main/deepsort.onnx",
        "file": "deepsort.onnx", "size_mb": 52, "pipeline": "tracking",
    },
}


def download_model(name: str, dest_dir: str = MODEL_DIR) -> bool:
    info = MODELS.get(name)
    if not info:
        print(f"Unknown model: {name}")
        return False

    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, info["file"])

    if os.path.exists(dest):
        size = os.path.getsize(dest) / (1024 * 1024)
        print(f"[SKIP] {info['file']} exists ({size:.1f} MB)")
        return True

    print(f"[DOWNLOAD] {info['file']} ({info['size_mb']} MB) for {info['pipeline']}")
    print(f"           {info['url'][:100]}...")

    try:
        def report_progress(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(100, int(block_num * block_size * 100 / total_size))
                if block_num % 10 == 0:
                    print(f"\r  {pct}%", end="", flush=True)

        urllib.request.urlretrieve(info["url"], dest, reporthook=report_progress)
        print(f"\r  [OK] {info['file']} downloaded ({os.path.getsize(dest)/(1024*1024):.1f} MB)")
        return True
    except Exception as e:
        print(f"\n  [FAIL] {info['file']}: {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False


def main():
    parser = argparse.ArgumentParser(description="Download VIAIOS ONNX models")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--model", type=str, help="Download specific model")
    parser.add_argument("--dir", type=str, default=MODEL_DIR, help="Destination directory")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--pipeline", type=str, help="Download all models for a pipeline (detection/face/person_reid/vehicle/ocr/tracking/embedding)")

    args = parser.parse_args()

    if args.list:
        print(f"{'Model':<20} {'Pipeline':<15} {'Size':<10} {'File'}")
        print("-" * 70)
        for name, info in MODELS.items():
            print(f"{name:<20} {info['pipeline']:<15} {info['size_mb']} MB{'':<5} {info['file']}")
        return

    dest = args.dir
    os.makedirs(dest, exist_ok=True)
    print(f"Model directory: {dest}\n")

    to_download = []
    if args.model:
        to_download = [args.model]
    elif args.pipeline:
        to_download = [name for name, info in MODELS.items() if info["pipeline"] == args.pipeline]
    elif args.all:
        to_download = list(MODELS.keys())
    else:
        print("Usage: python download_models.py --all | --model <name> | --pipeline <name> | --list")
        print("Try --list to see available models.")
        return

    success = 0
    for name in to_download:
        if download_model(name, dest):
            success += 1
        print()

    print(f"\nDone: {success}/{len(to_download)} models downloaded to {dest}")


if __name__ == "__main__":
    main()

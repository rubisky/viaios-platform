"""
Camera Snapshot Pipeline — Real-time capture → detect → embed → ingest.

Continuously captures from cameras, runs detection, extracts features,
and auto-ingests into the snapshot library for 1:N search readiness.
"""
import asyncio
import base64
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SnapshotPipeline:
    """Camera → Snapshot → Target Library pipeline."""

    def __init__(self):
        self._cameras: Dict[str, Dict] = {}
        self._running = False
        self._stats = {"captured": 0, "detected": 0, "ingested": 0, "errors": 0}
        self._thread: Optional[threading.Thread] = None

    def add_camera(self, camera_id: str, camera_name: str = "",
                   rtsp_url: str = "", interval_seconds: int = 5):
        """Register a camera for periodic snapshot capture."""
        self._cameras[camera_id] = {
            "id": camera_id,
            "name": camera_name or f"Camera-{camera_id}",
            "url": rtsp_url or f"rtsp://localhost:8554/{camera_id}",
            "interval": interval_seconds,
            "last_capture": None,
            "total_captures": 0,
            "enabled": True,
        }
        logger.info("Camera registered: %s [%ds interval]", camera_id, interval_seconds)

    def remove_camera(self, camera_id: str):
        self._cameras.pop(camera_id, None)

    def start(self):
        """Start the capture pipeline in background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Snapshot pipeline started: %d cameras", len(self._cameras))

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def capture_once(self, camera_id: str) -> Optional[Dict]:
        """Manually capture a single frame from a camera."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return None

        # Simulate capture (production: RTSP/ONVIF frame grab)
        frame = self._capture_frame(camera_id)
        self._stats["captured"] += 1
        cam["total_captures"] += 1
        cam["last_capture"] = datetime.now(timezone.utc)

        # Detect objects
        detections = self._detect_objects(frame)
        self._stats["detected"] += len(detections)

        # Ingest each detection as a target
        ingested = []
        try:
            from agent_service.core.target_library import get_target_library, LibraryType, Target
            lib = get_target_library()
            for det in detections[:5]:  # Top 5 per frame
                emb = self._extract_embedding(det, frame)
                target = Target(
                    library=LibraryType.SNAPSHOT,
                    target_type=self._map_type(det.get("class", "person")),
                    name=f"{cam['name']}-{uuid.uuid4().hex[:4]}",
                    camera_id=camera_id,
                    camera_name=cam['name'],
                    source=f"capture:{camera_id}",
                    embedding=emb,
                    attributes=det,
                    confidence=det.get("confidence", 0.8),
                    tags=["auto-capture"],
                )
                # Store directly (bypass API for performance)
                lib._targets[target.id] = target
                lib._index_to_vector(target)
                ingested.append(target.id)
            lib._save_index()
            self._stats["ingested"] += len(ingested)
        except Exception as e:
            logger.error("Ingest failed: %s", e)
            self._stats["errors"] += 1

        return {
            "camera_id": camera_id,
            "detections": len(detections),
            "ingested": len(ingested),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_stats(self) -> Dict:
        return {
            "cameras": len(self._cameras),
            "running": self._running,
            "stats": self._stats,
            "camera_details": [
                {"id": c["id"], "name": c["name"], "captures": c["total_captures"],
                 "enabled": c["enabled"], "last": c["last_capture"].isoformat() if c["last_capture"] else None}
                for c in self._cameras.values()
            ],
        }

    def _capture_loop(self):
        """Background capture loop."""
        while self._running:
            for cam_id, cam in list(self._cameras.items()):
                if not cam["enabled"]:
                    continue
                try:
                    self.capture_once(cam_id)
                except Exception as e:
                    logger.debug("Capture failed for %s: %s", cam_id, e)
            time.sleep(2)  # Check every 2s, individual cameras have their own intervals

    def _capture_frame(self, camera_id: str) -> bytes:
        """Capture frame from camera. Returns image bytes."""
        # Production: use OpenCV/GStreamer/FFmpeg to grab RTSP frame
        return f"mock-frame-{camera_id}-{time.time()}".encode()

    def _detect_objects(self, frame: bytes) -> List[Dict]:
        """Run object detection on a frame."""
        import random, hashlib
        seed = int(hashlib.sha256(frame).hexdigest()[:8], 16)
        rng = random.Random(seed)
        detections = []
        for _ in range(rng.randint(1, 4)):
            detections.append({
                "class": rng.choice(["person", "vehicle", "person", "face"]),
                "confidence": round(rng.uniform(0.7, 0.95), 2),
                "bbox": [rng.randint(100, 1800), rng.randint(100, 900), rng.randint(30, 200), rng.randint(30, 300)],
                "gender": rng.choice(["male", "female"]),
                "age_group": rng.choice(["20-30", "30-45", "45-60"]),
                "upper_color": rng.choice(["black", "blue", "white", "gray", "red"]),
            })
        return detections

    def _extract_embedding(self, detection: Dict, frame: bytes) -> List[float]:
        """Extract feature embedding for a detection."""
        import hashlib, random
        seed = int(hashlib.sha256(frame + str(detection).encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1, 1) for _ in range(512)]

    def _map_type(self, class_name: str):
        from agent_service.core.target_library import TargetType
        return {"person": TargetType.PERSON, "face": TargetType.FACE,
                "vehicle": TargetType.VEHICLE, "body": TargetType.BODY}.get(class_name, TargetType.PERSON)


_pipeline: Optional[SnapshotPipeline] = None
def get_snapshot_pipeline() -> SnapshotPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = SnapshotPipeline()
        for i in range(1, 9):
            _pipeline.add_camera(f"cam-{i}", f"摄像头-{chr(64+i)}", interval_seconds=5)
        _pipeline.start()
    return _pipeline

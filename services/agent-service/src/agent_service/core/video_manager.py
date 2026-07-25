"""Video Stream Manager — Snapshot capture, stream status, recording control."""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamInfo:
    stream_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    camera_id: str = ""
    camera_name: str = ""
    protocol: str = "rtsp"  # rtsp, gb28181, hls
    stream_url: str = ""
    status: str = "inactive"  # inactive, active, error
    resolution: str = "1920x1080"
    fps: int = 15
    bitrate_kbps: int = 2048
    started_at: Optional[str] = None
    snapshots: List[Dict] = field(default_factory=list)


class VideoManager:
    """Manages video streams, snapshots, and recording for cameras."""

    def __init__(self, max_snapshots_per_camera: int = 50):
        self._streams: Dict[str, StreamInfo] = {}
        self._max_snapshots = max_snapshots_per_camera

    def start_stream(self, camera_id: str, camera_name: str = "",
                     stream_url: str = "", protocol: str = "rtsp") -> StreamInfo:
        """Start or resume a video stream."""
        if camera_id in self._streams:
            stream = self._streams[camera_id]
            if stream.status == "inactive":
                stream.status = "active"
                stream.started_at = datetime.now(timezone.utc).isoformat()
                logger.info("Stream resumed: %s", camera_id)
            return stream

        stream = StreamInfo(
            camera_id=camera_id, camera_name=camera_name,
            protocol=protocol, stream_url=stream_url,
            status="active", started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._streams[camera_id] = stream
        logger.info("Stream started: %s (%s)", camera_id, protocol)
        return stream

    def stop_stream(self, camera_id: str):
        """Stop a video stream."""
        if camera_id in self._streams:
            self._streams[camera_id].status = "inactive"
            return True
        return False

    def get_stream(self, camera_id: str) -> Optional[StreamInfo]:
        return self._streams.get(camera_id)

    def capture_snapshot(self, camera_id: str, resolution: str = "1920x1080") -> Optional[Dict]:
        """Capture a snapshot from a camera stream."""
        stream = self._streams.get(camera_id)
        if not stream or stream.status != "active":
            # Generate demo snapshot for inactive streams
            snapshot = {
                "snapshot_id": str(uuid.uuid4())[:8],
                "camera_id": camera_id,
                "camera_name": stream.camera_name if stream else camera_id,
                "resolution": resolution,
                "format": "JPEG",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "image_url": f"/snapshots/{camera_id}_{uuid.uuid4().hex[:6]}.jpg",
                "file_size_kb": 120,
                "ai_detections": [],
            }
        else:
            snapshot = {
                "snapshot_id": str(uuid.uuid4())[:8],
                "camera_id": camera_id,
                "camera_name": stream.camera_name,
                "resolution": resolution or stream.resolution,
                "format": "JPEG",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "image_url": f"/snapshots/{camera_id}_{uuid.uuid4().hex[:6]}.jpg",
                "file_size_kb": 150,
                "ai_detections": self._get_demo_detections(),
            }
            stream.snapshots.append(snapshot)
            if len(stream.snapshots) > self._max_snapshots:
                stream.snapshots.pop(0)
        return snapshot

    def get_snapshots(self, camera_id: str, limit: int = 20) -> List[Dict]:
        """Get recent snapshots for a camera."""
        stream = self._streams.get(camera_id)
        if stream:
            return stream.snapshots[-limit:]
        return []

    def list_streams(self) -> List[Dict]:
        """List all managed streams."""
        return [
            {
                "camera_id": s.camera_id, "camera_name": s.camera_name,
                "protocol": s.protocol, "status": s.status,
                "resolution": s.resolution, "fps": s.fps,
                "started_at": s.started_at,
                "snapshot_count": len(s.snapshots),
            }
            for s in self._streams.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self._streams.values() if s.status == "active")
        return {
            "total_streams": len(self._streams),
            "active_streams": active,
            "total_snapshots": sum(len(s.snapshots) for s in self._streams.values()),
        }

    def _get_demo_detections(self) -> List[Dict]:
        import random
        objects = ["person", "vehicle", "bicycle", "dog"]
        return [{"class": random.choice(objects), "confidence": round(random.uniform(0.7, 0.99), 2),
                 "bbox": [random.randint(50, 200), random.randint(50, 200),
                          random.randint(100, 300), random.randint(100, 300)]}
                for _ in range(random.randint(1, 3))]


video_manager = VideoManager()

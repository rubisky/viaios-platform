"""Video Access Production Upgrade — Recording, Stream Health, PTZ."""
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .production_upgrade import db_store, health_monitor, retry

logger = logging.getLogger(__name__)


class PTZCommand(Enum):
    UP = "up"; DOWN = "down"; LEFT = "left"; RIGHT = "right"
    ZOOM_IN = "zoom_in"; ZOOM_OUT = "zoom_out"
    FOCUS_NEAR = "focus_near"; FOCUS_FAR = "focus_far"
    GOTO_PRESET = "goto_preset"; SET_PRESET = "set_preset"


class RecordingState(Enum):
    STOPPED = "stopped"; RECORDING = "recording"; PAUSED = "paused"


class StreamHealth:
    """Monitor stream health metrics."""

    def __init__(self):
        self._streams: Dict[str, Dict] = {}

    def update(self, camera_id: str, fps: float, bitrate_kbps: int, latency_ms: int,
               packet_loss_percent: float):
        self._streams[camera_id] = {
            "camera_id": camera_id,
            "fps": fps, "bitrate_kbps": bitrate_kbps,
            "latency_ms": latency_ms, "packet_loss_percent": packet_loss_percent,
            "status": "healthy" if packet_loss_percent < 2 and fps > 10 else "degraded",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        health_monitor.record(f"stream_fps_{camera_id}", fps)
        health_monitor.record("stream_packet_loss", packet_loss_percent)

    def get(self, camera_id: str) -> Optional[Dict]:
        return self._streams.get(camera_id)

    def list_all(self) -> List[Dict]:
        return list(self._streams.values())

    def get_summary(self) -> Dict:
        streams = list(self._streams.values())
        if not streams: return {"total": 0}
        healthy = sum(1 for s in streams if s["status"] == "healthy")
        degraded = len(streams) - healthy
        avg_fps = sum(s["fps"] for s in streams) / len(streams)
        avg_latency = sum(s["latency_ms"] for s in streams) / len(streams)
        return {
            "total": len(streams), "healthy": healthy, "degraded": degraded,
            "avg_fps": round(avg_fps, 1), "avg_latency_ms": round(avg_latency, 1),
        }


stream_health = StreamHealth()


class RecordingManager:
    """Manage video recording sessions with persistence."""

    def __init__(self):
        self._recordings: Dict[str, Dict] = {}

    @retry(max_attempts=2)
    def start_recording(self, camera_id: str, duration_seconds: int = 300,
                        format: str = "mp4") -> Dict:
        """Start recording from a camera stream."""
        recording_id = str(uuid.uuid4())[:8]
        recording = {
            "recording_id": recording_id,
            "camera_id": camera_id,
            "format": format,
            "duration_limit_s": duration_seconds,
            "state": "recording",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "file_path": f"/recordings/{camera_id}/{recording_id}.{format}",
            "size_bytes": 0,
        }
        self._recordings[recording_id] = recording
        db_store.set(f"recording:{recording_id}", recording)
        logger.info("Recording started: %s -> %s", camera_id, recording_id)
        return recording

    def stop_recording(self, recording_id: str) -> Optional[Dict]:
        rec = self._recordings.get(recording_id)
        if rec:
            rec["state"] = "stopped"
            rec["stopped_at"] = datetime.now(timezone.utc).isoformat()
            rec["size_bytes"] = 50 * 1024 * 1024  # Simulated 50MB
            db_store.set(f"recording:{recording_id}", rec)
        return rec

    def get_recordings(self, camera_id: str = "") -> List[Dict]:
        recs = list(self._recordings.values())
        if camera_id:
            recs = [r for r in recs if r["camera_id"] == camera_id]
        return recs

    def get_stats(self) -> Dict:
        active = sum(1 for r in self._recordings.values() if r["state"] == "recording")
        return {"total_recordings": len(self._recordings), "active": active}


recording_manager = RecordingManager()


class PTZController:
    """PTZ camera control with command queuing."""

    def __init__(self):
        self._presets: Dict[str, Dict] = {}
        self._command_history: List[Dict] = []

    def execute(self, camera_id: str, command: str, speed: int = 5,
                preset_id: Optional[str] = None) -> Dict:
        """Execute a PTZ command."""
        cmd = {
            "id": str(uuid.uuid4())[:8],
            "camera_id": camera_id,
            "command": command,
            "speed": min(max(speed, 1), 10),
            "preset": preset_id,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
        self._command_history.append(cmd)
        health_monitor.record("ptz_commands", 1)
        return cmd

    def save_preset(self, camera_id: str, name: str, pan: float, tilt: float, zoom: float):
        preset_id = str(uuid.uuid4())[:8]
        self._presets[preset_id] = {"id": preset_id, "camera_id": camera_id,
                                     "name": name, "pan": pan, "tilt": tilt, "zoom": zoom}
        return self._presets[preset_id]

    def get_presets(self, camera_id: str = "") -> List[Dict]:
        presets = list(self._presets.values())
        if camera_id: presets = [p for p in presets if p["camera_id"] == camera_id]
        return presets

    def get_history(self, limit: int = 20) -> List[Dict]:
        return self._command_history[-limit:]


ptz_controller = PTZController()


# Initialize demo data
for i in range(1, 5):
    stream_health.update(f"cam-{i:03d}", fps=15 + i, bitrate_kbps=2048 + i * 100,
                         latency_ms=30 + i * 5, packet_loss_percent=i * 0.1)
    recording_manager.start_recording(f"cam-{i:03d}", 300)
    ptz_controller.save_preset(f"cam-{i:03d}", f"Gate {i}", pan=0, tilt=i * 15, zoom=1.0)

"""RTSP/GB28181 Protocol Adapter Framework."""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StreamProtocol(Enum):
    RTSP = "rtsp"
    GB28181 = "gb28181"
    ONVIF = "onvif"
    RTMP = "rtmp"
    HLS = "hls"


class DeviceState(Enum):
    OFFLINE = "offline"
    REGISTERING = "registering"
    ONLINE = "online"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass
class CameraDevice:
    device_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    protocol: str = "rtsp"
    ip_address: str = ""
    port: int = 554
    username: str = "admin"
    password: str = ""
    stream_url: str = ""
    resolution: str = "1920x1080"
    fps: int = 15
    state: str = "offline"
    registered_at: Optional[str] = None
    last_seen: Optional[str] = None
    channels: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: str(v) if isinstance(v, Enum) else v for k, v in self.__dict__.items()}


class RTSPAdapter:
    """RTSP protocol adapter for video stream access."""

    def __init__(self):
        self._devices: Dict[str, CameraDevice] = {}

    def register_device(self, name: str, ip: str, port: int = 554,
                        username: str = "admin", password: str = "",
                        protocol: str = "rtsp") -> CameraDevice:
        """Register an RTSP camera device."""
        device = CameraDevice(
            name=name, protocol=protocol, ip_address=ip,
            port=port, username=username, password=password,
            state="online", registered_at=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
        )
        if protocol == "rtsp":
            device.stream_url = f"rtsp://{username}:{password}@{ip}:{port}/stream1"
        elif protocol == "gb28181":
            device.stream_url = f"gb28181://{ip}:{port}?deviceid={device.device_id}"
        self._devices[device.device_id] = device
        logger.info("Registered %s camera: %s at %s:%d", protocol, name, ip, port)
        return device

    def start_stream(self, device_id: str) -> Dict[str, Any]:
        """Start streaming from a registered device."""
        device = self._devices.get(device_id)
        if not device:
            return {"error": f"Device not found: {device_id}"}
        device.state = "streaming"
        device.last_seen = datetime.now(timezone.utc).isoformat()
        return {
            "device_id": device_id, "status": "streaming",
            "stream_url": device.stream_url,
            "hls_url": f"/live/{device_id}/index.m3u8",  # Converted HLS stream
        }

    def stop_stream(self, device_id: str) -> bool:
        device = self._devices.get(device_id)
        if device:
            device.state = "online"
            return True
        return False

    def get_device(self, device_id: str) -> Optional[CameraDevice]:
        return self._devices.get(device_id)

    def list_devices(self) -> List[Dict]:
        return [d.to_dict() for d in self._devices.values()]

    def get_stats(self) -> dict:
        total = len(self._devices)
        online = sum(1 for d in self._devices.values() if d.state in ("online", "streaming"))
        streaming = sum(1 for d in self._devices.values() if d.state == "streaming")
        return {"total": total, "online": online, "streaming": streaming}


class GB28181Adapter(RTSPAdapter):
    """China GB28181 national standard adapter (extends RTSP)."""

    def __init__(self, sip_port: int = 5060):
        super().__init__()
        self.sip_port = sip_port
        self._sip_devices: Dict[str, Dict] = {}

    def handle_sip_register(self, device_id: str, sip_uri: str) -> Dict:
        """Handle SIP REGISTER request from a GB28181 device."""
        self._sip_devices[device_id] = {
            "device_id": device_id, "sip_uri": sip_uri,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "online",
        }
        logger.info("SIP REGISTER: %s -> %s", device_id, sip_uri)
        return {"status": "ok", "expires": 3600}

    def handle_sip_message(self, device_id: str, message_type: str, content: Dict) -> Dict:
        """Handle SIP MESSAGE (device info, catalog, heartbeat)."""
        if message_type == "heartbeat":
            if device_id in self._sip_devices:
                self._sip_devices[device_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
            return {"status": "ok"}
        elif message_type == "catalog":
            return {"devices": list(self._devices.values())}
        elif message_type == "ptz":
            return {"status": "ok", "command": content.get("command", "unknown")}
        return {"status": "unknown_type"}

    def start_rtp_stream(self, device_id: str, rtp_port: int = 5000) -> Dict:
        """Start RTP stream from device, convert to HLS."""
        device = self._devices.get(device_id)
        if not device:
            return {"error": "Device not found"}
        device.state = "streaming"
        return {
            "device_id": device_id, "status": "streaming",
            "rtp_port": rtp_port, "hls_url": f"/live/{device_id}/index.m3u8",
        }


# Global instances
rtsp_adapter = RTSPAdapter()
gb28181_adapter = GB28181Adapter()

# Register demo devices
for i in range(12):
    rtsp_adapter.register_device(f"Camera-{i+1:02d}", f"192.168.1.{100+i}", protocol="rtsp")

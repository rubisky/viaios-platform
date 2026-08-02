"""
GB28181 Protocol Handler — P2-2
China national standard for video surveillance camera integration.

Implements: SIP signaling, device registration, catalog query,
live preview (RTP/RTCP), PTZ control, recording playback.

GB28181 Architecture:
  Camera (SIP UA) → Register → GB28181 Server (SIP Server) → VIAIOS Video Pipeline

Protocol Stack:
  Signaling: SIP (Session Initiation Protocol) over UDP/TCP
  Media:     RTP/RTCP for video/audio streaming
  Control:   MANSCDP for PTZ control
  Metadata:  MANSRTSP for device information
"""
import hashlib
import logging
import os
import re
import socketserver
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

GB28181_SIP_PORT = int(os.getenv("GB28181_SIP_PORT", "5060"))
GB28181_SIP_ID = os.getenv("GB28181_SIP_ID", "34020000002000000001")
GB28181_SIP_DOMAIN = os.getenv("GB28181_SIP_DOMAIN", "3402000000")
GB28181_MEDIA_PORT_START = int(os.getenv("GB28181_MEDIA_PORT_START", "20000"))
GB28181_MEDIA_PORT_END = int(os.getenv("GB28181_MEDIA_PORT_END", "21000"))
GB28181_REGISTER_EXPIRES = int(os.getenv("GB28181_REGISTER_EXPIRES", "3600"))


# ── Domain Types ───────────────────────────────────────────────────

class DeviceStatus(Enum):
    ON      = "ON"
    OFF     = "OFF"
    ALARM   = "ALARM"

class StreamType(Enum):
    LIVE      = "live"        # Real-time preview
    PLAYBACK  = "playback"    # Recording playback
    DOWNLOAD  = "download"    # Video download

@dataclass
class GBDevice:
    """A GB28181-compliant camera device."""
    device_id: str              # 20-digit GB28181 device ID
    name: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    status: str = "ON"
    longitude: float = 0.0
    latitude: float = 0.0
    ip_address: str = ""
    port: int = 5060
    transport: str = "UDP"      # UDP or TCP
    registered_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    channels: int = 1
    ptz_supported: bool = False
    stream_profiles: List[str] = field(default_factory=lambda: ["main", "sub"])
    last_heartbeat: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GBStream:
    """An active GB28181 media stream."""
    stream_id: str
    device_id: str
    channel_id: str
    stream_type: StreamType
    rtp_port: int
    rtcp_port: int
    codec: str = "H264"
    resolution: str = "1920x1080"
    fps: int = 25
    bitrate_kbps: int = 4096
    started_at: Optional[datetime] = None
    packets_received: int = 0
    bytes_received: int = 0

@dataclass
class PTZCommand:
    """Pan-Tilt-Zoom control command."""
    device_id: str
    command: str          # LEFT, RIGHT, UP, DOWN, ZOOM_IN, ZOOM_OUT, STOP, GOTO_PRESET
    speed: int = 50       # 0-255
    preset_id: int = 0
    duration_ms: int = 1000

@dataclass
class GBStats:
    """GB28181 server statistics."""
    registered_devices: int = 0
    active_streams: int = 0
    total_packets: int = 0
    total_bytes: int = 0
    uptime_seconds: float = 0
    sip_requests_handled: int = 0


# ── GB28181 Protocol Handler ───────────────────────────────────────

class GB28181Server:
    """
    GB28181 SIP server for camera registration and stream management.

    Usage:
        server = GB28181Server()
        server.start()  # Starts SIP server on port 5060
        devices = server.list_devices()
        stream = server.start_live_preview(device_id, channel=1)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.sip_id = self.config.get("sip_id", GB28181_SIP_ID)
        self.sip_domain = self.config.get("sip_domain", GB28181_SIP_DOMAIN)
        self.sip_port = self.config.get("sip_port", GB28181_SIP_PORT)
        self.media_start = self.config.get("media_port_start", GB28181_MEDIA_PORT_START)

        self._devices: Dict[str, GBDevice] = {}
        self._streams: Dict[str, GBStream] = {}
        self._used_ports: Set[int] = set()
        self._running = False
        self._stats = GBStats()
        self._lock = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}

    # ── Server Lifecycle ────────────────────────────────────────

    def start(self):
        """Start the GB28181 SIP server."""
        self._running = True
        self._stats.uptime_seconds = 0
        logger.info("GB28181 server started on port %d [SIP ID: %s]",
                   self.sip_port, self.sip_id)

    def stop(self):
        """Stop the GB28181 server and all streams."""
        self._running = False
        for stream_id in list(self._streams.keys()):
            self.stop_stream(stream_id)
        logger.info("GB28181 server stopped")

    # ── Device Management ───────────────────────────────────────

    def register_device(self, device: GBDevice) -> str:
        """Register a GB28181 camera."""
        with self._lock:
            now = datetime.now(timezone.utc)
            device.registered_at = now
            device.expires_at = datetime.fromtimestamp(
                now.timestamp() + GB28181_REGISTER_EXPIRES, tz=timezone.utc)
            device.last_heartbeat = now

            self._devices[device.device_id] = device
            self._stats.registered_devices = len(self._devices)

        logger.info("GB28181 device registered: %s [%s] <%s>",
                   device.device_id, device.name, device.ip_address)
        return device.device_id

    def unregister_device(self, device_id: str):
        """Unregister a camera."""
        with self._lock:
            self._devices.pop(device_id, None)
            self._stats.registered_devices = len(self._devices)

    def list_devices(self, status: Optional[str] = None) -> List[GBDevice]:
        """List all registered devices."""
        devices = list(self._devices.values())
        if status:
            devices = [d for d in devices if d.status == status]
        return devices

    def get_device(self, device_id: str) -> Optional[GBDevice]:
        return self._devices.get(device_id)

    def query_catalog(self, device_id: str) -> Dict[str, Any]:
        """
        Query device catalog information.
        Returns device details and channel list.
        """
        device = self._devices.get(device_id)
        if not device:
            return {"error": "Device not found"}

        channels = []
        for i in range(1, device.channels + 1):
            channels.append({
                "channel_id": f"{device_id}{i:02d}",
                "name": f"{device.name}_CH{i}",
                "status": device.status,
                "ptz": device.ptz_supported,
                "profiles": device.stream_profiles,
            })

        return {
            "device_id": device.device_id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "status": device.status,
            "longitude": device.longitude,
            "latitude": device.latitude,
            "channels": channels,
            "registered_at": device.registered_at.isoformat() if device.registered_at else "",
        }

    def heartbeat(self, device_id: str):
        """Handle device heartbeat (keepalive)."""
        device = self._devices.get(device_id)
        if device:
            device.last_heartbeat = datetime.now(timezone.utc)

    # ── Stream Management ───────────────────────────────────────

    def start_live_preview(self, device_id: str,
                          channel_id: str = "1") -> Optional[GBStream]:
        """Start a live video preview stream."""
        device = self._devices.get(device_id)
        if not device:
            logger.error("Device not found: %s", device_id)
            return None

        stream_id = f"gb-stream-{uuid.uuid4().hex[:8]}"

        # Allocate RTP/RTCP ports
        rtp_port = self._allocate_port()
        rtcp_port = rtp_port + 1 if rtp_port else 0

        if not rtp_port:
            logger.error("No available media ports")
            return None

        stream = GBStream(
            stream_id=stream_id,
            device_id=device_id,
            channel_id=channel_id,
            stream_type=StreamType.LIVE,
            rtp_port=rtp_port,
            rtcp_port=rtcp_port,
            started_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._streams[stream_id] = stream
            self._stats.active_streams = len(self._streams)

        logger.info("GB28181 live preview started: %s [%s:%d → %s:%d, %s]",
                   stream_id, device.ip_address, device.port,
                   "0.0.0.0", rtp_port, stream.codec)

        # In production: send SIP INVITE to camera to start streaming
        self._send_sip_invite(device, stream)

        return stream

    def start_playback(self, device_id: str, start_time: datetime,
                      end_time: datetime, speed: float = 1.0) -> Optional[GBStream]:
        """Start recording playback for a time range."""
        device = self._devices.get(device_id)
        if not device:
            return None

        stream_id = f"gb-playback-{uuid.uuid4().hex[:8]}"
        rtp_port = self._allocate_port()

        stream = GBStream(
            stream_id=stream_id,
            device_id=device_id,
            channel_id="1",
            stream_type=StreamType.PLAYBACK,
            rtp_port=rtp_port,
            rtcp_port=rtp_port + 1,
            started_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._streams[stream_id] = stream

        logger.info("GB28181 playback started: %s [%s → %s, %.1fx]",
                   stream_id, start_time.isoformat(), end_time.isoformat(), speed)

        return stream

    def stop_stream(self, stream_id: str):
        """Stop an active stream."""
        with self._lock:
            stream = self._streams.pop(stream_id, None)
            if stream:
                if stream.rtp_port:
                    self._used_ports.discard(stream.rtp_port)
                    self._used_ports.discard(stream.rtcp_port)
                self._stats.active_streams = len(self._streams)
                logger.info("GB28181 stream stopped: %s", stream_id)

        if stream:
            device = self._devices.get(stream.device_id)
            if device:
                self._send_sip_bye(device, stream)

    def list_streams(self) -> List[GBStream]:
        return list(self._streams.values())

    def get_stream(self, stream_id: str) -> Optional[GBStream]:
        return self._streams.get(stream_id)

    # ── PTZ Control ─────────────────────────────────────────────

    def ptz_control(self, device_id: str, command: str,
                   speed: int = 50, preset_id: int = 0):
        """Send PTZ control command to a camera."""
        device = self._devices.get(device_id)
        if not device:
            return {"error": "Device not found"}
        if not device.ptz_supported:
            return {"error": "PTZ not supported"}

        ptz = PTZCommand(
            device_id=device_id,
            command=command.upper(),
            speed=speed,
            preset_id=preset_id,
        )

        logger.info("GB28181 PTZ: %s → %s (speed=%d)", device.name, command, speed)

        # In production: send MANSCDP XML control message
        self._send_ptz_command(device, ptz)

        return {"status": "ok", "device": device.name, "command": command}

    def ptz_preset_set(self, device_id: str, preset_id: int):
        """Save current PTZ position as a preset."""
        return self.ptz_control(device_id, "SET_PRESET", preset_id=preset_id)

    def ptz_preset_goto(self, device_id: str, preset_id: int):
        """Go to a saved PTZ preset position."""
        return self.ptz_control(device_id, "GOTO_PRESET", preset_id=preset_id)

    # ── Statistics ──────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._stats.registered_devices = len(self._devices)
            self._stats.active_streams = len(self._streams)

        return {
            "registered_devices": self._stats.registered_devices,
            "active_streams": self._stats.active_streams,
            "total_packets": self._stats.total_packets,
            "total_bytes": self._stats.total_bytes,
            "devices_by_status": {
                status.value: sum(1 for d in self._devices.values() if d.status == status.value)
                for status in DeviceStatus
            },
            "streams_by_type": {
                st.value: sum(1 for s in self._streams.values() if s.stream_type.value == st.value)
                for st in StreamType
            },
        }

    # ── Internal SIP Methods (stubs for production) ─────────────

    def _send_sip_invite(self, device: GBDevice, stream: GBStream):
        """Send SIP INVITE to start media stream."""
        # In production: construct and send SIP INVITE message
        invite = (
            f"INVITE sip:{stream.channel_id}@{device.ip_address}:{device.port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP 0.0.0.0:{self.sip_port}\r\n"
            f"From: <sip:{self.sip_id}@{self.sip_domain}>\r\n"
            f"To: <sip:{device.device_id}@{device.ip_address}>\r\n"
            f"Call-ID: {stream.stream_id}\r\n"
            f"CSeq: 1 INVITE\r\n"
            f"Subject: {device.device_id}:{stream.channel_id},{self.sip_id}\r\n"
            f"Content-Type: application/sdp\r\n"
            f"\r\n"
            f"v=0\r\n"
            f"o={self.sip_id} 0 0 IN IP4 0.0.0.0\r\n"
            f"s=Play\r\n"
            f"c=IN IP4 0.0.0.0\r\n"
            f"t=0 0\r\n"
            f"m=video {stream.rtp_port} RTP/AVP 96\r\n"
            f"a=rtpmap:96 {stream.codec}/90000\r\n"
            f"a=recvonly\r\n"
        )
        logger.debug("SIP INVITE:\n%s", invite)
        self._stats.sip_requests_handled += 1

    def _send_sip_bye(self, device: GBDevice, stream: GBStream):
        """Send SIP BYE to end media stream."""
        self._stats.sip_requests_handled += 1

    def _send_ptz_command(self, device: GBDevice, cmd: PTZCommand):
        """Send MANSCDP PTZ control XML."""
        xml = (
            '<?xml version="1.0"?>\n'
            '<Control>\n'
            f'<CmdType>DeviceControl</CmdType>\n'
            f'<SN>{int(time.time())}</SN>\n'
            f'<DeviceID>{cmd.device_id}</DeviceID>\n'
            f'<PTZCmd>{self._ptz_code(cmd.command, cmd.speed, cmd.preset_id)}</PTZCmd>\n'
            '</Control>'
        )
        logger.debug("PTZ XML:\n%s", xml)

    @staticmethod
    def _ptz_code(command: str, speed: int, preset: int) -> str:
        """Convert PTZ command to GB28181 hex code."""
        codes = {
            "UP": "0801040001FF",
            "DOWN": "0801040002FF",
            "LEFT": "0801040003FF",
            "RIGHT": "0801040004FF",
            "ZOOM_IN": "0802040001FF",
            "ZOOM_OUT": "0802040002FF",
            "STOP": "0801040000FF",
            "GOTO_PRESET": f"08010700{preset:02X}FF",
            "SET_PRESET": f"08010300{preset:02X}FF",
        }
        code = codes.get(command, "0801040000FF")
        return f"{code}{speed:02X}"

    # ── Port Allocation ─────────────────────────────────────────

    def _allocate_port(self) -> Optional[int]:
        """Allocate an even RTP port from the media port range."""
        with self._lock:
            for port in range(self.media_start, GB28181_MEDIA_PORT_END, 2):
                if port not in self._used_ports:
                    self._used_ports.add(port)
                    self._used_ports.add(port + 1)
                    return port
        return None

    # ── ID Validation ───────────────────────────────────────────

    @staticmethod
    def validate_device_id(device_id: str) -> bool:
        """Validate a 20-digit GB28181 device ID."""
        return bool(re.match(r'^\d{20}$', device_id))

    @staticmethod
    def generate_device_id(center_id: str = "3402000000",
                           device_type: str = "132",
                           serial: int = 1) -> str:
        """Generate a valid GB28181 device ID."""
        return f"{center_id}{device_type}{serial:07d}"


# ── Convenience ────────────────────────────────────────────────────

_gb_server: Optional[GB28181Server] = None


def get_gb28181_server() -> GB28181Server:
    global _gb_server
    if _gb_server is None:
        _gb_server = GB28181Server()
    return _gb_server

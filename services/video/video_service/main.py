"""
VIAIOS Video Service — High-performance video processing (P2-3)
Port: 8093 | Runtime: Python 3.11+ | Framework: FastAPI + asyncio

Handles: RTSP/HLS streaming, video decoding, stream lifecycle, GB28181 ingestion.
"""
import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger("viaios-video")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = FastAPI(title="VIAIOS Video Service", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ── Domain Types ───────────────────────────────────────────────────

class StreamType(str, Enum):
    RTSP = "RTSP"; HLS = "HLS"; WebRTC = "WebRTC"; GB28181 = "GB28181"; FILE = "FILE"

class StreamStatus(str, Enum):
    ACTIVE = "ACTIVE"; PAUSED = "PAUSED"; ERROR = "ERROR"; RECONNECTING = "RECONNECTING"

@dataclass
class Stream:
    id: str = field(default_factory=lambda: f"stream-{uuid.uuid4().hex[:8]}")
    name: str = ""; type: StreamType = StreamType.RTSP
    source_uri: str = ""; status: StreamStatus = StreamStatus.ACTIVE
    codec: str = "H264"; resolution: str = "1920x1080"; fps: float = 25.0
    bitrate_kbps: int = 4096; bytes_total: int = 0; packets_total: int = 0
    camera_id: str = ""; decode_session: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_frame_at: Optional[datetime] = None
    error: str = ""

@dataclass
class DecodeSession:
    session_id: str = field(default_factory=lambda: f"dec-{uuid.uuid4().hex[:8]}")
    stream_id: str = ""; source_uri: str = ""; codec: str = "H264"
    resolution: str = "1920x1080"; fps: float = 25.0
    frames_total: int = 0; frames_dropped: int = 0; bitrate_kbps: int = 0
    running: bool = True
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str = ""

# ── In-Memory Store ───────────────────────────────────────────────

streams: Dict[str, Stream] = {}
sessions: Dict[str, DecodeSession] = {}
_active_tasks: Dict[str, asyncio.Task] = {}

# ── Health ─────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/actuator/health")
async def health():
    return {"status": "UP", "service": "viaios-video", "version": "4.0.0",
            "streams": sum(1 for s in streams.values() if s.status == StreamStatus.ACTIVE),
            "sessions": len(sessions)}

# ── Stream API ─────────────────────────────────────────────────────

class StreamRequest(BaseModel):
    name: str = ""; type: StreamType = StreamType.RTSP
    source_uri: str = Field(..., min_length=1)
    max_fps: int = Field(default=25, ge=1, le=60)
    resolution: str = "1920x1080"; hw_accel: str = ""; camera_id: str = ""

@app.get("/api/v1/video/streams")
async def list_streams():
    return {"total": len(streams), "streams": [
        {"id": s.id, "name": s.name, "type": s.type.value, "status": s.status.value,
         "codec": s.codec, "resolution": s.resolution, "fps": s.fps,
         "camera_id": s.camera_id, "uptime_seconds": (datetime.now(timezone.utc) - s.started_at).total_seconds()}
        for s in streams.values()]}

@app.get("/api/v1/video/streams/{stream_id}")
async def get_stream(stream_id: str):
    s = streams.get(stream_id)
    if not s: raise HTTPException(404, "Stream not found")
    return {"id": s.id, "name": s.name, "type": s.type.value, "status": s.status.value,
            "codec": s.codec, "resolution": s.resolution, "fps": s.fps, "source_uri": s.source_uri}

@app.post("/api/v1/video/streams")
async def add_stream(req: StreamRequest):
    s = Stream(name=req.name, type=req.type, source_uri=req.source_uri,
               resolution=req.resolution, fps=float(req.max_fps), camera_id=req.camera_id)
    streams[s.id] = s
    # Start background decode session
    session = DecodeSession(stream_id=s.id, source_uri=req.source_uri,
                           resolution=req.resolution, fps=float(req.max_fps))
    sessions[session.session_id] = session
    s.decode_session = session.session_id
    task = asyncio.create_task(_decode_loop(session.session_id))
    _active_tasks[session.session_id] = task
    logger.info("Stream added: %s [%s] %s", s.id, s.type.value, s.source_uri)
    return {"stream_id": s.id, "decode_session": session.session_id,
            "status": "ACTIVE", "hls_url": f"/api/v1/video/hls/{s.id}/index.m3u8"}

@app.delete("/api/v1/video/streams/{stream_id}")
async def remove_stream(stream_id: str):
    s = streams.pop(stream_id, None)
    if not s: raise HTTPException(404, "Stream not found")
    if s.decode_session:
        ses = sessions.get(s.decode_session)
        if ses: ses.running = False
        task = _active_tasks.pop(s.decode_session, None)
        if task: task.cancel()
    return {"status": "removed"}

@app.get("/api/v1/video/stats")
async def video_stats():
    active = sum(1 for s in streams.values() if s.status == StreamStatus.ACTIVE)
    by_type = {}
    for s in streams.values():
        by_type[s.type.value] = by_type.get(s.type.value, 0) + 1
    return {"total_streams": len(streams), "active_streams": active,
            "by_type": by_type, "decode_sessions": len(sessions)}

# ── Decoder API ────────────────────────────────────────────────────

@app.get("/api/v1/video/decoder/sessions")
async def list_sessions():
    return {"sessions": [{"session_id": s.session_id, "stream_id": s.stream_id,
            "codec": s.codec, "fps": s.fps, "frames_total": s.frames_total,
            "running": s.running} for s in sessions.values()]}

@app.delete("/api/v1/video/decoder/sessions/{session_id}")
async def stop_session(session_id: str):
    ses = sessions.get(session_id)
    if not ses: raise HTTPException(404, "Session not found")
    ses.running = False
    task = _active_tasks.pop(session_id, None)
    if task: task.cancel()
    return {"status": "stopped"}

# ── RTSP Proxy ─────────────────────────────────────────────────────

@app.post("/api/v1/video/rtsp/proxy")
async def rtsp_proxy(req: StreamRequest):
    s = Stream(name="rtsp-proxy", type=StreamType.RTSP, source_uri=req.source_uri,
               fps=float(req.max_fps))
    streams[s.id] = s
    return {"stream_id": s.id, "hls_url": f"/api/v1/video/hls/{s.id}/index.m3u8",
            "ws_url": f"ws://localhost:8093/api/v1/video/ws/{s.id}"}

# ── Decode Loop ────────────────────────────────────────────────────

async def _decode_loop(session_id: str):
    """Background task simulating video decoding."""
    ses = sessions.get(session_id)
    if not ses: return
    logger.info("Decode started: %s", session_id)
    interval = 1.0 / max(ses.fps, 1)
    try:
        while ses.running:
            await asyncio.sleep(interval)
            ses.frames_total += 1
            ses.bitrate_kbps = int(ses.frames_total * interval * 8 / 1000)
    except asyncio.CancelledError:
        pass
    finally:
        ses.running = False
        logger.info("Decode ended: %s (%d frames)", session_id, ses.frames_total)

# ── Main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("VIDEO_PORT", "8093"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")

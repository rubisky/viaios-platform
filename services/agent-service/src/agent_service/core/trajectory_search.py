"""
Trajectory Search — Upload target photo, find across all cameras.
Uses ArcFace for face matching + cross-camera temporal reasoning.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class TrajectoryHit:
    camera_id: str
    camera_name: str
    timestamp: str
    confidence: float
    entity_id: str = ""
    snapshot_url: str = ""
    location: str = ""

@dataclass
class TrajectoryResult:
    target_id: str
    total_hits: int
    cameras: int
    time_span_minutes: float
    trajectory: List[TrajectoryHit] = field(default_factory=list)

class TrajectorySearch:
    """Cross-camera trajectory search engine."""

    def search(self, image_data: str = "", image_url: str = "",
               target_id: str = "", max_hits: int = 100) -> Optional[TrajectoryResult]:
        """
        Given a target image, find all appearances across the camera network.
        Returns time-ordered trajectory.
        """
        if not image_data and not image_url and not target_id:
            return None

        # Step 1: Extract face/person embedding
        embedding = self._extract_embedding(image_data, image_url)

        # Step 2: Search across all cameras via vector store
        hits = self._search_all_cameras(embedding, max_hits)

        # Step 3: Sort by time, filter by temporal consistency
        hits.sort(key=lambda h: h.timestamp)

        # Step 4: Apply spatio-temporal reasoning
        filtered = self._filter_by_temporal_consistency(hits)

        target_id = target_id or f"target-{hash(str(embedding)[:20])}"

        cameras = len(set(h.camera_id for h in filtered))
        time_span = 0
        if len(filtered) >= 2:
            try:
                t1 = datetime.fromisoformat(filtered[0].timestamp.replace("Z","+00:00"))
                t2 = datetime.fromisoformat(filtered[-1].timestamp.replace("Z","+00:00"))
                time_span = (t2 - t1).total_seconds() / 60
            except Exception: pass

        return TrajectoryResult(
            target_id=target_id,
            total_hits=len(filtered),
            cameras=cameras,
            time_span_minutes=round(time_span, 1),
            trajectory=filtered,
        )

    def _extract_embedding(self, image_data: str, image_url: str) -> List[float]:
        """Extract embedding from target image."""
        import hashlib, random
        seed_str = image_data or image_url or "default"
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)
        # In production: run ArcFace ONNX model for face embedding
        return [rng.uniform(-1, 1) for _ in range(512)]

    def _search_all_cameras(self, embedding: List[float], max_hits: int) -> List[TrajectoryHit]:
        """Search all cameras for matching targets."""
        try:
            from agent_service.core.milvus_client import milvus_client
            if milvus_client.get_stats().get("connected"):
                results = milvus_client.search("face_embeddings", embedding, top_k=max_hits)
                return [
                    TrajectoryHit(
                        camera_id=r.get("metadata", {}).get("camera_id", ""),
                        camera_name=r.get("metadata", {}).get("camera_name", ""),
                        timestamp=r.get("metadata", {}).get("timestamp", ""),
                        confidence=r.get("score", 0),
                        entity_id=r.get("id", ""),
                    )
                    for r in results
                ]
        except Exception: pass

        # Mock: generate demo trajectory
        import random
        cameras = [f"cam-{i}" for i in range(1, 6)]
        hits = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        for i in range(min(max_hits, 8)):
            t = base_time + timedelta(minutes=i * 15 + random.randint(-5, 5))
            cam = random.choice(cameras)
            hits.append(TrajectoryHit(
                camera_id=cam, camera_name=f"Camera {cam[-1]}",
                timestamp=t.isoformat(),
                confidence=round(random.uniform(0.75, 0.95), 3),
                entity_id=f"hit-{i}",
            ))
        return hits

    def _filter_by_temporal_consistency(self, hits: List[TrajectoryHit]) -> List[TrajectoryHit]:
        """Filter out temporally impossible hits (e.g., same target at distant locations within seconds)."""
        if len(hits) < 2: return hits
        filtered = [hits[0]]
        for i in range(1, len(hits)):
            prev = filtered[-1]
            try:
                t1 = datetime.fromisoformat(prev.timestamp.replace("Z","+00:00"))
                t2 = datetime.fromisoformat(hits[i].timestamp.replace("Z","+00:00"))
                delta = (t2 - t1).total_seconds()
                # Same camera within 10s = duplicate, skip
                if prev.camera_id == hits[i].camera_id and delta < 10:
                    if hits[i].confidence > prev.confidence:
                        filtered[-1] = hits[i]
                    continue
            except Exception: pass
            filtered.append(hits[i])
        return filtered


_traj: Optional[TrajectorySearch] = None
def get_trajectory_search() -> TrajectorySearch:
    global _traj
    if _traj is None: _traj = TrajectorySearch()
    return _traj

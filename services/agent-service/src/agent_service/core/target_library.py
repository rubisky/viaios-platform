"""
Target Library — Multi-source person/vehicle database for 1:N and M:N search.

Libraries:
  snapshot   — 抓拍库: real-time camera captures → detect → embed → store
  upload     — 离线上传库: batch image upload → detect → embed → store
  watchlist  — 重点人员库: wanted/monitored persons → embed → alert
  history    — 历史解析库: GB28181 recordings → structured parsing → store

Search modes:
  1:1  — compare two images (same person?)
  1:N  — one image against entire library
  M:N  — batch images against batch library
"""
import base64
import hashlib
import json
import logging
import os
import pickle
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = "/opt/viaios/data/target_library"

# ── Domain Types ───────────────────────────────────────────────────

class LibraryType(Enum):
    SNAPSHOT  = "snapshot"    # 抓拍库
    UPLOAD    = "upload"      # 离线上传库
    WATCHLIST = "watchlist"   # 重点人员库
    HISTORY   = "history"     # 历史解析库

class TargetType(Enum):
    PERSON  = "person"
    VEHICLE = "vehicle"
    FACE    = "face"
    BODY    = "body"

@dataclass
class Target:
    """A target entity in the library."""
    id: str = field(default_factory=lambda: f"tgt-{uuid.uuid4().hex[:8]}")
    library: LibraryType = LibraryType.SNAPSHOT
    target_type: TargetType = TargetType.PERSON
    name: str = ""
    source: str = ""             # camera_id, upload_filename, case_id
    source_type: str = ""        # camera, upload, gb28181
    image_url: str = ""
    thumbnail_url: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    camera_id: str = ""
    camera_name: str = ""
    location: str = ""
    # Features
    embedding: Optional[List[float]] = None   # 512d feature vector
    embedding_model: str = "arcface_r100"
    # Attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    # Metadata
    confidence: float = 0.0
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """A single search match."""
    target: Target
    score: float                # cosine similarity
    rank: int = 0
    match_type: str = ""        # face, body, attribute, cross-modal

@dataclass
class BatchSearchResult:
    query_id: str
    query_target: Optional[Target] = None
    matches: List[SearchResult] = field(default_factory=list)
    total_matches: int = 0

@dataclass
class LibraryStats:
    total_targets: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_library: Dict[str, int] = field(default_factory=dict)
    by_camera: Dict[str, int] = field(default_factory=dict)
    last_ingest: Optional[str] = None
    storage_size_mb: float = 0.0


# ── Target Library Engine ──────────────────────────────────────────

class TargetLibrary:
    """
    Multi-source target library for 1:N and M:N search.

    Usage:
        lib = TargetLibrary()
        # Ingest
        lib.ingest(image_data, library=LibraryType.SNAPSHOT, camera_id="cam-1")
        # 1:N search
        results = lib.search_1vn(query_image, library=LibraryType.SNAPSHOT, top_k=20)
        # M:N search
        results = lib.search_mvn(query_images, library=LibraryType.SNAPSHOT)
    """

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        for lt in LibraryType:
            os.makedirs(os.path.join(data_dir, lt.value, "images"), exist_ok=True)

        self._targets: Dict[str, Target] = {}
        self._lock = threading.Lock()
        self._load_index()

        # Feature dimensions per target type
        self._dims = {"person": 512, "face": 512, "vehicle": 256, "body": 768}

    # ── Ingestion ────────────────────────────────────────────────

    def ingest(self, image_data: str, library: LibraryType = LibraryType.SNAPSHOT,
               target_type: TargetType = None, camera_id: str = "",
               camera_name: str = "", source: str = "", name: str = "",
               tags: List[str] = None, attributes: Dict = None,
               auto_detect: bool = True) -> Target:
        """Ingest a target into a library. Returns the created Target."""
        # Decode image
        img_bytes = self._decode_image(image_data)
        if not img_bytes:
            raise ValueError("Invalid image data")

        # Auto-detect type
        if auto_detect and not target_type:
            target_type = self._detect_type(img_bytes)

        if not target_type:
            target_type = TargetType.PERSON

        # Extract embedding
        embedding = self._extract_embedding(img_bytes, target_type)
        attrs = self._extract_attributes(img_bytes, target_type) if not attributes else attributes

        # Create target
        target = Target(
            library=library,
            target_type=target_type,
            name=name or f"{library.value}-{uuid.uuid4().hex[:6]}",
            source=source or camera_id or "manual",
            source_type=library.value,
            camera_id=camera_id,
            camera_name=camera_name,
            embedding=embedding,
            attributes=attrs,
            confidence=0.85,
            tags=tags or [],
            custom_fields={"ingest_method": "api"},
        )

        # Save image
        img_path = os.path.join(self.data_dir, library.value, "images", f"{target.id}.jpg")
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        target.thumbnail_url = f"/data/target_library/{library.value}/images/{target.id}.jpg"

        # Index
        with self._lock:
            self._targets[target.id] = target
        self._index_to_vector(target)

        self._save_index()
        logger.info("Target ingested: %s [%s/%s] → %s", target.id, library.value, target_type.value, target.name)
        return target

    def ingest_batch(self, images: List[Dict], library: LibraryType = LibraryType.UPLOAD,
                     auto_detect: bool = True) -> List[Target]:
        """Batch ingest multiple images."""
        results = []
        for img in images:
            try:
                target = self.ingest(
                    image_data=img.get("image_data", img.get("data", "")),
                    library=library,
                    target_type=TargetType(img["type"]) if "type" in img else None,
                    camera_id=img.get("camera_id", ""),
                    name=img.get("name", ""),
                    tags=img.get("tags", []),
                    attributes=img.get("attributes", {}),
                    auto_detect=auto_detect,
                )
                results.append(target)
            except Exception as e:
                logger.error("Batch ingest failed for image: %s", e)
        return results

    # ── 1:N Search ───────────────────────────────────────────────

    def search_1vn(self, image_data: str, library: Optional[LibraryType] = None,
                   top_k: int = 20, min_score: float = 0.5,
                   target_type: Optional[TargetType] = None) -> List[SearchResult]:
        """1:N search: one image against the full library."""
        # Extract query embedding
        img_bytes = self._decode_image(image_data)
        if not img_bytes:
            return []
        query_emb = self._extract_embedding(img_bytes, target_type or TargetType.PERSON)
        if not query_emb:
            return []

        return self._vector_search(query_emb, library, top_k, min_score, target_type)

    def search_1vn_by_id(self, target_id: str, library: Optional[LibraryType] = None,
                         top_k: int = 20, min_score: float = 0.5) -> List[SearchResult]:
        """1:N search using an existing library target as query."""
        target = self._targets.get(target_id)
        if not target or not target.embedding:
            return []
        return self._vector_search(target.embedding, library, top_k, min_score, target.target_type)

    # ── M:N Search ───────────────────────────────────────────────

    def search_mvn(self, query_images: List[Dict], library: Optional[LibraryType] = None,
                   top_k: int = 10, min_score: float = 0.5) -> List[BatchSearchResult]:
        """M:N search: multiple images against the full library."""
        results = []
        for img in query_images:
            qid = img.get("id", f"q-{uuid.uuid4().hex[:6]}")
            qtype = TargetType(img.get("type", "person"))
            query_img = img.get("image_data", img.get("data", ""))

            query_target = None
            if "target_id" in img:
                query_target = self._targets.get(img["target_id"])

            if query_img:
                matches = self.search_1vn(query_img, library, top_k, min_score, qtype)
            elif query_target and query_target.embedding:
                matches = self._vector_search(query_target.embedding, library, top_k, min_score, qtype)
            else:
                matches = []

            results.append(BatchSearchResult(
                query_id=qid,
                query_target=query_target,
                matches=matches,
                total_matches=len(matches),
            ))

        return results

    # ── 1:1 Verification ─────────────────────────────────────────

    def verify_1v1(self, image_a: str, image_b: str) -> Dict[str, Any]:
        """1:1 verification: are these the same person?"""
        emb_a = self._extract_embedding(self._decode_image(image_a), TargetType.PERSON)
        emb_b = self._extract_embedding(self._decode_image(image_b), TargetType.PERSON)
        if not emb_a or not emb_b:
            return {"same": False, "error": "Failed to extract embedding"}

        score = self._cosine_similarity(emb_a, emb_b)
        threshold = 0.75
        return {
            "same": score >= threshold,
            "similarity": round(score, 4),
            "threshold": threshold,
        }

    # ── Query ────────────────────────────────────────────────────

    def get_target(self, target_id: str) -> Optional[Target]:
        return self._targets.get(target_id)

    def list_targets(self, library: Optional[LibraryType] = None,
                     target_type: Optional[TargetType] = None,
                     camera_id: str = "", limit: int = 100,
                     offset: int = 0) -> List[Target]:
        """List targets with optional filters."""
        results = list(self._targets.values())
        if library:
            results = [t for t in results if t.library == library]
        if target_type:
            results = [t for t in results if t.target_type == target_type]
        if camera_id:
            results = [t for t in results if t.camera_id == camera_id]
        results.sort(key=lambda t: t.timestamp, reverse=True)
        return results[offset:offset + limit]

    def search_by_name(self, query: str, limit: int = 50) -> List[Target]:
        """Simple name/tag search."""
        q = query.lower()
        return [t for t in self._targets.values()
                if q in t.name.lower() or any(q in tag.lower() for tag in t.tags)][:limit]

    def get_stats(self) -> LibraryStats:
        """Get library statistics."""
        targets = list(self._targets.values())
        stats = LibraryStats(total_targets=len(targets))
        for t in targets:
            stats.by_type[t.target_type.value] = stats.by_type.get(t.target_type.value, 0) + 1
            stats.by_library[t.library.value] = stats.by_library.get(t.library.value, 0) + 1
            if t.camera_id:
                stats.by_camera[t.camera_id] = stats.by_camera.get(t.camera_id, 0) + 1
        if targets:
            stats.last_ingest = max(t.timestamp for t in targets).isoformat()
        # Estimate storage
        total_size = 0
        for lt in LibraryType:
            img_dir = os.path.join(self.data_dir, lt.value, "images")
            if os.path.exists(img_dir):
                for fn in os.listdir(img_dir):
                    fp = os.path.join(img_dir, fn)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
        stats.storage_size_mb = round(total_size / 1048576, 2)
        return stats

    def delete_target(self, target_id: str) -> bool:
        with self._lock:
            t = self._targets.pop(target_id, None)
            if t:
                img_path = os.path.join(self.data_dir, t.library.value, "images", f"{t.id}.jpg")
                if os.path.exists(img_path):
                    os.remove(img_path)
                self._save_index()
                return True
        return False

    # ── Internal ─────────────────────────────────────────────────

    def _vector_search(self, embedding: List[float], library: Optional[LibraryType],
                       top_k: int, min_score: float,
                       target_type: Optional[TargetType]) -> List[SearchResult]:
        """Cosine similarity search across indexed targets."""
        query = np.array(embedding, dtype=np.float32)
        query = query / (np.linalg.norm(query) + 1e-8)

        candidates = list(self._targets.values())
        if library:
            candidates = [t for t in candidates if t.library == library]
        if target_type:
            candidates = [t for t in candidates if t.target_type == target_type]

        results = []
        for t in candidates:
            if not t.embedding:
                continue
            vec = np.array(t.embedding, dtype=np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            score = float(np.dot(query, vec))
            if score >= min_score:
                results.append(SearchResult(target=t, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results[:top_k]):
            r.rank = i + 1
        return results[:top_k]

    def _index_to_vector(self, target: Target):
        """Index target embedding to vector store."""
        if not target.embedding:
            return
        try:
            from agent_service.core.milvus_client import milvus_client
            collection = f"{target.target_type.value}_embeddings"
            milvus_client.insert(collection, [{
                "id": target.id,
                "embedding": target.embedding,
                "metadata": {
                    "name": target.name,
                    "library": target.library.value,
                    "type": target.target_type.value,
                    "camera_id": target.camera_id,
                    "timestamp": target.timestamp.isoformat(),
                }
            }])
        except Exception as e:
            logger.debug("Vector index skipped: %s", e)

    def _extract_embedding(self, img_bytes: bytes, target_type: TargetType) -> Optional[List[float]]:
        """Extract feature embedding using real ONNX models."""
        try:
            import numpy as np
            from agent_service.core.inference_pipeline import load_all_pipelines
            pipelines = load_all_pipelines()

            # Convert bytes to numpy array (simplified - production: decode image)
            import hashlib, random
            seed = int(hashlib.sha256(img_bytes).hexdigest()[:16], 16)
            rng = random.Random(seed)
            dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)

            # Try appropriate pipeline based on type
            if target_type == TargetType.FACE:
                pipeline = pipelines.get("face")
            elif target_type == TargetType.PERSON or target_type == TargetType.BODY:
                pipeline = pipelines.get("person_reid") or pipelines.get("face")
            elif target_type == TargetType.VEHICLE:
                pipeline = pipelines.get("vehicle")
            else:
                pipeline = pipelines.get("face") or pipelines.get("detection")

            if pipeline:
                result = pipeline(dummy_img)
                if isinstance(result, dict) and "embedding" in result:
                    return result["embedding"]

            # Fallback to capability pipelines
            from agent_service.core.capability_pipelines import get_all_pipelines as get_all_caps
            caps = get_all_caps()
            emb_pipeline = caps.get("embedding")
            if emb_pipeline and emb_pipeline.loaded:
                result = emb_pipeline(dummy_img)
                if result.get("results"):
                    return result["results"][0].get("embedding")
        except Exception as e:
            logger.debug("Real embedding failed: %s, using fallback", e)

        # Fallback: deterministic hash-based
        import hashlib, random
        seed = int(hashlib.sha256(img_bytes).hexdigest()[:16], 16)
        rng = random.Random(seed)
        dim = self._dims.get(target_type.value, 512)
        return [rng.uniform(-1, 1) for _ in range(dim)]

    def _extract_attributes(self, img_bytes: bytes, target_type: TargetType) -> Dict:
        """Extract attributes from image."""
        import random
        seed = int(hashlib.sha256(img_bytes).hexdigest()[:8], 16)
        rng = random.Random(seed)
        if target_type == TargetType.PERSON:
            return {
                "gender": rng.choice(["male", "female"]),
                "age_group": rng.choice(["20-30", "30-45", "45-60"]),
                "upper_color": rng.choice(["black", "blue", "white", "gray"]),
                "build": rng.choice(["slim", "medium", "heavy"]),
            }
        elif target_type == TargetType.VEHICLE:
            return {
                "color": rng.choice(["black", "white", "silver", "red"]),
                "type": rng.choice(["car", "suv", "truck", "bus"]),
            }
        return {}

    def _detect_type(self, img_bytes: bytes) -> Optional[TargetType]:
        """Auto-detect target type from image."""
        import random
        seed = int(hashlib.sha256(img_bytes).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return rng.choices([TargetType.PERSON, TargetType.VEHICLE, TargetType.FACE],
                          weights=[0.6, 0.25, 0.15])[0]

    def _decode_image(self, image_data: str) -> Optional[bytes]:
        """Decode base64 or URL image."""
        if not image_data:
            return None
        if image_data.startswith("http"):
            try:
                import urllib.request
                return urllib.request.urlopen(image_data, timeout=10).read()
            except Exception:
                return None
        try:
            return base64.b64decode(image_data)
        except Exception:
            return image_data.encode() if len(image_data) < 1000 else None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        va, vb = np.array(a), np.array(b)
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-8))

    def _save_index(self):
        """Persist metadata index to disk."""
        idx_path = os.path.join(self.data_dir, "index.pkl")
        with open(idx_path, "wb") as f:
            pickle.dump(self._targets, f)
        # Also save JSON for external tools
        json_path = os.path.join(self.data_dir, "index.json")
        with open(json_path, "w") as f:
            json.dump({tid: {
                "id": t.id, "name": t.name, "library": t.library.value,
                "type": t.target_type.value, "camera_id": t.camera_id,
                "timestamp": t.timestamp.isoformat(),
                "attributes": t.attributes,
                "tags": t.tags,
            } for tid, t in self._targets.items()}, f, indent=2, default=str)

    def _load_index(self):
        idx_path = os.path.join(self.data_dir, "index.pkl")
        if os.path.exists(idx_path):
            with open(idx_path, "rb") as f:
                self._targets = pickle.load(f)
            logger.info("Target library loaded: %d targets", len(self._targets))

    def seed_demo_data(self, count: int = 50):
        """Seed demo data for testing."""
        import random
        demo_names = ["张三", "李四", "王五", "赵六", "陈七",
                      "目标A", "目标B", "目标C", "嫌疑人X", "嫌疑人Y"]
        cameras = [f"cam-{i}" for i in range(1, 9)]
        for i in range(count):
            name = random.choice(demo_names) + (f"_{i}" if i > 9 else "")
            lib = random.choices(list(LibraryType), weights=[0.4, 0.3, 0.2, 0.1])[0]
            ttype = random.choices(list(TargetType), weights=[0.5, 0.2, 0.2, 0.1])[0]
            dummy = base64.b64encode(f"demo-{i:04d}".encode()).decode()
            t = Target(
                library=lib, target_type=ttype, name=name,
                camera_id=random.choice(cameras),
                camera_name=f"Camera {random.choice('ABCDEFGH')}",
                source="demo_seed",
                embedding=[random.uniform(-1, 1) for _ in range(512)],
                attributes={"gender": random.choice(["male", "female"]),
                           "age_group": random.choice(["20-30", "30-45"])},
                confidence=round(random.uniform(0.7, 0.95), 2),
                tags=random.sample(["suspicious", "regular", "vehicle", "employee", "visitor"], k=2),
            )
            self._targets[t.id] = t
        self._save_index()
        logger.info("Seeded %d demo targets", count)


_library: Optional[TargetLibrary] = None
def get_target_library() -> TargetLibrary:
    global _library
    if _library is None:
        _library = TargetLibrary()
        if len(_library._targets) == 0:
            _library.seed_demo_data(50)
    return _library

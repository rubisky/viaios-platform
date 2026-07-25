"""Intelligent Search Engine — NLU parsing + attribute filtering + relevance scoring."""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Simulated Milvus indices (production: use pymilvus)
SEARCH_INDICES = {
    "person_embeddings": {"count": 100000, "dimension": 512, "index": "IVF_FLAT"},
    "vehicle_features": {"count": 50000, "dimension": 256, "index": "IVF_FLAT"},
    "face_features": {"count": 200000, "dimension": 512, "index": "IVF_FLAT"},
}

class QueryParser:
    """Parse natural language search queries into structured filters."""

    TIME_PATTERNS = [
        (r'(\d+)小时前', lambda m: f"last_{m.group(1)}h"),
        (r'(\d+)分钟前', lambda m: f"last_{m.group(1)}m"),
        (r'今天', 'today'), (r'昨天', 'yesterday'),
        (r'本周', 'this_week'), (r'上周', 'last_week'),
        (r'(\d+)月(\d+)日', lambda m: f"{m.group(1)}-{m.group(2)}"),
    ]

    CLOTHING_PATTERNS = {
        'red': ['red jacket', 'red shirt', 'red coat'],
        'black': ['black jacket', 'black pants', 'black shirt'],
        'white': ['white shirt', 'white coat'],
        'blue': ['blue jacket', 'blue shirt'],
    }

    def parse(self, query: str) -> Dict[str, Any]:
        """Parse query into structured filters."""
        ql = query.lower()
        filters = {"query": query, "modality": "combined"}

        # Detect modality
        if any(w in ql for w in ['图片', 'image', 'photo', '照片']): filters["modality"] = "image"
        if any(w in ql for w in ['车辆', 'vehicle', 'car', '车牌', 'plate']): filters["modality"] = "vehicle"
        if any(w in ql for w in ['人脸', 'face', '人', 'person', '嫌疑人', '人员']): filters["modality"] = "person"

        # Time extraction
        for pattern, result in self.TIME_PATTERNS:
            match = re.search(pattern, ql)
            if match:
                if callable(result): filters["time_range"] = result(match)
                else: filters["time_range"] = result
                break

        # Clothing colors
        for color, items in self.CLOTHING_PATTERNS.items():
            if color in ql:
                filters["attributes"] = {"clothing_color": color, "clothing_items": items}
                break

        # Camera/location
        cam_match = re.search(r'(camera|cam|摄像头)\s*([A-Za-z0-9\-]+)', ql)
        if cam_match: filters["camera"] = cam_match.group(2).upper()

        # Threshold
        threshold_match = re.search(r'相似度\s*[>]\s*(\d+)', ql)
        if threshold_match: filters["threshold"] = int(threshold_match.group(1)) / 100

        return filters


class SearchEngine:
    """Intelligent search across multiple modalities."""

    def __init__(self):
        self.parser = QueryParser()

    def search(self, query: str, top_k: int = 10, filters: Dict = None) -> Dict[str, Any]:
        """Execute search with query parsing and result ranking."""
        parsed = self.parser.parse(query)
        if filters: parsed.update(filters)

        # Determine target indices
        modality = parsed.get("modality", "combined")
        indices = []
        if modality in ("person", "combined"): indices.append("person_embeddings")
        if modality in ("vehicle", "combined"): indices.append("vehicle_features")
        if modality in ("face", "combined"): indices.append("face_features")

        # Generate mock results based on indices
        results = []
        import random
        random.seed(hash(query) % 10000)

        for idx_name in indices:
            info = SEARCH_INDICES.get(idx_name, {})
            count = min(top_k * 3, info.get("count", 1000))
            for i in range(min(top_k, 5)):
                score = round(random.uniform(0.65, 0.98), 3)
                camera = f"cam-{random.randint(1, 12):03d}"
                results.append({
                    "id": f"{idx_name[:6]}-{random.randint(10000, 99999)}",
                    "index": idx_name,
                    "score": score,
                    "type": "person" if "person" in idx_name else "vehicle" if "vehicle" in idx_name else "face",
                    "camera": camera,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attributes": parsed.get("attributes", {}),
                    "thumbnail": f"/snapshots/{camera}_{random.randint(1, 100)}.jpg",
                })

        # Sort by score descending
        results.sort(key=lambda x: -x["score"])
        results = results[:top_k]

        return {
            "query": query,
            "parsed": parsed,
            "total_results": sum(SEARCH_INDICES.get(i, {}).get("count", 0) for i in indices),
            "results_count": len(results),
            "results": results,
            "indices_searched": indices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_indices(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in SEARCH_INDICES.items()]


search_engine = SearchEngine()

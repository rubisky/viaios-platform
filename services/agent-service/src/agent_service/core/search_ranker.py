"""
Search Ranker — Multi-factor result ranking for target search.

Factors: similarity score, time decay, camera weight, confidence,
attribute match bonus, cross-camera penalty, re-id consistency.
"""
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RankFactors:
    similarity: float = 0.0    # Vector cosine similarity
    time_recency: float = 0.0  # Newer = higher
    camera_weight: float = 1.0 # High-traffic cameras weighted lower
    confidence: float = 0.0    # Detection confidence
    attribute_match: float = 0.0 # Attribute filter match bonus
    cross_camera_penalty: float = 0.0  # Same camera repeat penalty

@dataclass
class SearchHit:
    id: str
    entity_id: str = ""
    entity_type: str = ""
    score: float = 0.0
    rank: int = 0
    factors: RankFactors = field(default_factory=RankFactors)
    camera_id: str = ""
    camera_name: str = ""
    timestamp: str = ""
    thumbnail_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SearchRanker:
    """Multi-factor search result ranking engine."""

    def __init__(self):
        # Camera weights: high-traffic cameras have lower weight
        self._camera_weights = {}
        # Time decay half-life in hours
        self.time_half_life = 24.0
        # Weights for each factor
        self.weights = {
            "similarity": 0.40,
            "time_recency": 0.25,
            "confidence": 0.15,
            "attribute_match": 0.15,
            "camera_weight": 0.05,
        }
        # Cross-camera bonus: higher score for diverse cameras
        self.cross_camera_bonus = 0.05

    def rank(self, hits: List[Dict], query_time: Optional[datetime] = None,
             attributes: Optional[Dict] = None,
             max_results: int = 50) -> List[SearchHit]:
        """Rank search results using multi-factor scoring."""
        if not hits:
            return []

        now = query_time or datetime.now(timezone.utc)
        ranked = []

        for i, hit in enumerate(hits):
            factors = self._compute_factors(hit, now, attributes)
            combined = self._combine_factors(factors)
            ranked.append(SearchHit(
                id=hit.get("id", f"hit-{i}"),
                entity_id=hit.get("entity_id", ""),
                entity_type=hit.get("entity_type", hit.get("metadata", {}).get("type", "")),
                score=round(combined, 4),
                factors=factors,
                camera_id=hit.get("camera_id", hit.get("metadata", {}).get("camera_id", "")),
                camera_name=hit.get("camera_name", ""),
                timestamp=hit.get("timestamp", hit.get("metadata", {}).get("timestamp", "")),
                metadata=hit.get("metadata", {}),
            ))

        # Apply cross-camera bonus
        ranked = self._apply_cross_camera(ranked)

        # Sort by score descending
        ranked.sort(key=lambda h: h.score, reverse=True)

        # Assign ranks
        for i, hit in enumerate(ranked[:max_results]):
            hit.rank = i + 1

        return ranked[:max_results]

    def _compute_factors(self, hit: Dict, now: datetime,
                        attributes: Optional[Dict]) -> RankFactors:
        """Compute all ranking factors for a hit."""
        factors = RankFactors()

        # 1. Similarity score (from vector search)
        factors.similarity = float(hit.get("score", hit.get("similarity", 0.5)))

        # 2. Time recency: newer = higher, exponential decay
        ts_str = hit.get("timestamp", hit.get("metadata", {}).get("timestamp", ""))
        if ts_str:
            try:
                if isinstance(ts_str, (int, float)):
                    hit_time = datetime.fromtimestamp(ts_str / 1000, tz=timezone.utc)
                else:
                    hit_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta_hours = (now - hit_time).total_seconds() / 3600
                factors.time_recency = math.exp(-delta_hours * math.log(2) / self.time_half_life)
            except Exception:
                factors.time_recency = 0.5  # Default if can't parse
        else:
            factors.time_recency = 0.3  # No timestamp = low recency

        # 3. Camera weight
        cam_id = hit.get("camera_id", hit.get("metadata", {}).get("camera_id", ""))
        factors.camera_weight = self._camera_weights.get(cam_id, 1.0)

        # 4. Detection confidence
        factors.confidence = float(hit.get("confidence", hit.get("metadata", {}).get("confidence", 0.7)))

        # 5. Attribute match bonus
        if attributes:
            meta = hit.get("metadata", {})
            match_count = 0
            total_attrs = len(attributes)
            for attr_key, attr_val in attributes.items():
                if attr_key in meta and str(meta[attr_key]) == str(attr_val):
                    match_count += 1
            factors.attribute_match = match_count / max(total_attrs, 1)
        else:
            factors.attribute_match = 0.5  # Neutral

        return factors

    def _combine_factors(self, factors: RankFactors) -> float:
        """Weighted combination of all factors."""
        score = (
            self.weights["similarity"] * factors.similarity +
            self.weights["time_recency"] * factors.time_recency +
            self.weights["confidence"] * factors.confidence +
            self.weights["attribute_match"] * factors.attribute_match +
            self.weights["camera_weight"] * factors.camera_weight
        )
        return min(1.0, max(0.0, score))

    def _apply_cross_camera(self, hits: List[SearchHit]) -> List[SearchHit]:
        """Bonus for results from different cameras (diversity)."""
        if len(hits) < 2:
            return hits

        # Group by camera
        cam_groups: Dict[str, List[SearchHit]] = {}
        for hit in hits:
            cam_groups.setdefault(hit.camera_id, []).append(hit)

        # Penalize: only keep top 3 per camera, rest get penalty
        for cam_id, group in cam_groups.items():
            if len(group) > 3:
                for hit in group[3:]:
                    hit.score *= (1.0 - self.cross_camera_bonus * (len(group) - 3))

        return hits

    def update_camera_weight(self, camera_id: str, hit_count: int):
        """Update camera weight based on hit frequency.
        High-traffic cameras get lower weight to promote diversity."""
        # Logarithmic decay: more hits → lower weight
        self._camera_weights[camera_id] = 1.0 / (1.0 + math.log(1 + hit_count) * 0.2)


# Convenience
_ranker: Optional[SearchRanker] = None
def get_search_ranker() -> SearchRanker:
    global _ranker
    if _ranker is None:
        _ranker = SearchRanker()
    return _ranker

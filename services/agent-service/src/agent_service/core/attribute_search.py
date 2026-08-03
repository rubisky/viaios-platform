"""
Attribute Search Backend — Human/vehicle attribute-based filtering.
Connects body analysis + vehicle recognition pipelines to search.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Attribute schemas (matches capability pipelines output)
BODY_ATTRIBUTES = {
    "gender": ["male", "female"],
    "age_group": ["child", "teen", "20-30", "30-45", "45-60", "senior"],
    "upper_clothing": ["jacket", "shirt", "t-shirt", "hoodie", "coat", "sweater"],
    "upper_color": ["black", "white", "red", "blue", "gray", "green", "yellow"],
    "lower_clothing": ["jeans", "trousers", "shorts", "skirt"],
    "lower_color": ["black", "blue", "gray", "white", "brown"],
    "has_backpack": [True, False],
    "has_hat": [True, False],
    "has_mask": [True, False],
    "build": ["slim", "medium", "heavy"],
    "height_cm": None,  # range
}

VEHICLE_ATTRIBUTES = {
    "type": ["car", "truck", "bus", "motorcycle", "bicycle", "suv", "van"],
    "color": ["black", "white", "red", "blue", "silver", "gray", "green"],
    "plate_number": None,  # partial match
    "brand": None,
    "has_passenger": [True, False],
}

@dataclass
class AttributeQuery:
    """Structured attribute search query."""
    entity_type: str = "person"  # person, vehicle, face
    attributes: Dict[str, Any] = field(default_factory=dict)
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    camera_ids: List[str] = field(default_factory=list)
    min_confidence: float = 0.5
    max_results: int = 50

@dataclass
class AttributeMatch:
    """A single attribute match result."""
    entity_id: str
    entity_type: str
    attributes: Dict[str, Any]
    match_score: float
    matched_count: int
    total_attrs: int
    camera_id: str = ""
    timestamp: str = ""

class AttributeSearchEngine:
    """Attribute-based filtering engine."""

    def __init__(self):
        # In-memory attribute index (production: PostgreSQL)
        self._index: Dict[str, List[Dict]] = {"person": [], "vehicle": [], "face": []}

    def index_entity(self, entity_id: str, entity_type: str,
                     attributes: Dict[str, Any], camera_id: str = "",
                     timestamp: str = ""):
        """Add entity to attribute index."""
        if entity_type not in self._index:
            self._index[entity_type] = []
        self._index[entity_type].append({
            "entity_id": entity_id,
            "attributes": attributes,
            "camera_id": camera_id,
            "timestamp": timestamp,
        })

    def search(self, query: AttributeQuery) -> List[AttributeMatch]:
        """Search by attribute filters."""
        candidates = self._index.get(query.entity_type, [])
        results = []

        schema = BODY_ATTRIBUTES if query.entity_type == "person" else VEHICLE_ATTRIBUTES
        query_attrs = {k: v for k, v in query.attributes.items() if v is not None}

        if not query_attrs:
            return []

        for entity in candidates:
            match = self._match_entity(entity, query_attrs, query)
            if match:
                results.append(match)

        # Sort by match score
        results.sort(key=lambda m: m.match_score, reverse=True)
        return results[:query.max_results]

    def _match_entity(self, entity: Dict, query_attrs: Dict,
                      query: AttributeQuery) -> Optional[AttributeMatch]:
        """Score entity against attribute query."""
        attrs = entity["attributes"]
        matched = 0
        total = len(query_attrs)

        for attr_key, attr_val in query_attrs.items():
            entity_val = attrs.get(attr_key)
            if entity_val is None:
                total -= 1
                continue

            if isinstance(attr_val, list):
                # Value in list
                if entity_val in attr_val:
                    matched += 1
            elif isinstance(attr_val, tuple) and len(attr_val) == 2:
                # Range query (e.g., height: (160, 180))
                if attr_val[0] <= entity_val <= attr_val[1]:
                    matched += 1
            elif isinstance(entity_val, str) and isinstance(attr_val, str):
                # Case-insensitive string match
                if attr_val.lower() in entity_val.lower():
                    matched += 1
            elif entity_val == attr_val:
                matched += 1

        if total == 0:
            return None

        score = matched / total

        # Confidence threshold
        entity_conf = entity.get("attributes", {}).get("confidence", 0.5)
        if entity_conf < query.min_confidence:
            return None

        # Time filter
        if query.time_start and entity.get("timestamp", ""):
            if entity["timestamp"] < query.time_start:
                return None
        if query.time_end and entity.get("timestamp", ""):
            if entity["timestamp"] > query.time_end:
                return None

        # Camera filter
        if query.camera_ids and entity.get("camera_id") not in query.camera_ids:
            return None

        return AttributeMatch(
            entity_id=entity["entity_id"],
            entity_type=query.entity_type,
            attributes=attrs,
            match_score=round(score, 3),
            matched_count=matched,
            total_attrs=total,
            camera_id=entity.get("camera_id", ""),
            timestamp=entity.get("timestamp", ""),
        )

    def get_stats(self) -> Dict:
        return {
            "total_indexed": sum(len(v) for v in self._index.values()),
            "by_type": {k: len(v) for k, v in self._index.items()},
        }

    def get_schema(self, entity_type: str) -> Dict[str, List]:
        """Get attribute schema for UI."""
        schema = BODY_ATTRIBUTES if entity_type == "person" else VEHICLE_ATTRIBUTES
        return {k: v for k, v in schema.items() if v is not None}


_attr_engine: Optional[AttributeSearchEngine] = None
def get_attribute_search() -> AttributeSearchEngine:
    global _attr_engine
    if _attr_engine is None:
        _attr_engine = AttributeSearchEngine()
        # Seed demo data
        for i in range(10):
            _attr_engine.index_entity(f"p-{i}", "person", {
                "gender": "male" if i % 2 == 0 else "female",
                "age_group": ["20-30", "30-45", "20-30", "45-60", "20-30"][i % 5],
                "upper_clothing": ["jacket", "hoodie", "shirt", "coat", "t-shirt"][i % 5],
                "upper_color": ["black", "blue", "white", "red", "gray"][i % 5],
                "build": "medium",
                "confidence": 0.85,
            }, camera_id=f"cam-{i % 3 + 1}")
    return _attr_engine

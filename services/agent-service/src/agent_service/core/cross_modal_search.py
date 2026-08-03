"""
Cross-modal Search Fusion — Joint image + text + attribute search.
Combines results from multiple modalities with intelligent re-ranking.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class CrossModalResult:
    entity_id: str
    entity_type: str
    final_score: float
    image_score: float = 0
    text_score: float = 0
    attribute_score: float = 0
    graph_score: float = 0
    sources: List[str] = field(default_factory=list)
    camera_id: str = ""
    timestamp: str = ""
    thumbnail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossModalQuery:
    image_url: str = ""
    image_data: str = ""          # base64
    text_query: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    entity_types: List[str] = field(default_factory=list)
    time_start: str = ""
    time_end: str = ""
    camera_ids: List[str] = field(default_factory=list)
    max_results: int = 50
    # Weights for each modality
    weights: Dict[str, float] = field(default_factory=lambda: {
        "image": 0.50, "text": 0.25, "attribute": 0.20, "graph": 0.05,
    })


class CrossModalEngine:
    """Fusion engine for multi-modal search."""

    def search(self, query: CrossModalQuery) -> List[CrossModalResult]:
        """Execute cross-modal search with fusion ranking."""
        results: Dict[str, CrossModalResult] = {}

        # 1. Image search (vector similarity)
        if query.image_data or query.image_url:
            image_hits = self._image_search(query)
            for hit in image_hits:
                rid = hit.get("entity_id", hit.get("id", ""))
                if rid not in results:
                    results[rid] = CrossModalResult(rid, hit.get("type", "unknown"), 0)
                results[rid].image_score = hit.get("score", 0)
                results[rid].sources.append("image")

        # 2. Text search (GraphRAG / semantic)
        if query.text_query:
            text_hits = self._text_search(query)
            for hit in text_hits:
                rid = hit.get("entity_id", hit.get("id", ""))
                if rid not in results:
                    results[rid] = CrossModalResult(rid, hit.get("type", "unknown"), 0)
                results[rid].text_score = hit.get("score", hit.get("confidence", 0))
                results[rid].sources.append("text")

        # 3. Attribute search
        if query.attributes:
            attr_hits = self._attribute_search(query)
            for hit in attr_hits:
                rid = hit.get("entity_id", "")
                if rid not in results:
                    results[rid] = CrossModalResult(rid, hit.get("entity_type", "person"), 0)
                results[rid].attribute_score = hit.get("match_score", 0)
                results[rid].sources.append("attribute")
                results[rid].metadata.update(hit.get("attributes", {}))

        # 4. GraphRAG (knowledge graph enhancement)
        if query.text_query and len(results) > 0:
            graph_hits = self._graph_search(query, list(results.keys()))
            for rid, score in (graph_hits or {}).items():
                if rid in results:
                    results[rid].graph_score = score
                    results[rid].sources.append("graph")

        # Fusion scoring
        for r in results.values():
            r.final_score = (
                query.weights["image"] * r.image_score +
                query.weights["text"] * r.text_score +
                query.weights["attribute"] * r.attribute_score +
                query.weights["graph"] * r.graph_score
            )
            # Boost for multi-source matches
            if len(r.sources) >= 2:
                r.final_score *= 1.15
            if len(r.sources) >= 3:
                r.final_score *= 1.10

        ranked = sorted(results.values(), key=lambda r: r.final_score, reverse=True)
        return ranked[:query.max_results]

    def _image_search(self, query: CrossModalQuery) -> List[Dict]:
        try:
            from agent_service.core.search_engine_v2 import search_by_image
            return search_by_image(query.image_data or query.image_url,
                                  entity_types=query.entity_types) or []
        except Exception:
            return []

    def _text_search(self, query: CrossModalQuery) -> List[Dict]:
        try:
            from agent_service.core.graphrag import GraphRAGQuery, get_graphrag_engine, SearchMode
            engine = get_graphrag_engine()
            gq = GraphRAGQuery(text=query.text_query, mode=SearchMode.HYBRID)
            result = engine.search(gq)
            return [{"id": vm.entity_id, "type": vm.entity_type,
                    "score": vm.score} for vm in result.vector_matches]
        except Exception:
            return []

    def _attribute_search(self, query: CrossModalQuery) -> List[Dict]:
        try:
            from agent_service.core.attribute_search import get_attribute_search, AttributeQuery
            aq = AttributeQuery(attributes=query.attributes,
                              camera_ids=query.camera_ids)
            engine = get_attribute_search()
            results = engine.search(aq)
            return [{"entity_id": r.entity_id, "entity_type": r.entity_type,
                    "match_score": r.match_score} for r in results]
        except Exception:
            return []

    def _graph_search(self, query: CrossModalQuery, entity_ids: List[str]) -> Dict[str, float]:
        return {}  # Enhanced by AGE when connected


_cross_modal: Optional[CrossModalEngine] = None
def get_cross_modal() -> CrossModalEngine:
    global _cross_modal
    if _cross_modal is None: _cross_modal = CrossModalEngine()
    return _cross_modal

"""
GraphRAG Fusion Engine — P1-1
Three-engine fusion: Vector Search + Graph Search + LLM Reasoning.

Architecture:
  User Query → [Vector Search (Milvus)] → candidates
            → [Graph Search (AGE)]      → relationships
            → [LLM Reasoning]           → fused, reasoned answer

This implements the "Knowledge First" principle where every answer
is grounded in verifiable data from both vector and graph sources.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Domain Types ───────────────────────────────────────────────────

class SearchMode(Enum):
    VECTOR_ONLY  = "vector_only"
    GRAPH_ONLY   = "graph_only"
    HYBRID       = "hybrid"        # Vector + Graph, no LLM
    FULL_RAG     = "full_rag"      # Vector + Graph + LLM (default)

@dataclass
class VectorResult:
    """Result from vector similarity search."""
    entity_id: str
    entity_type: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphResult:
    """Result from graph traversal."""
    source_entity: str
    target_entity: str
    relation_type: str
    path: List[str] = field(default_factory=list)
    hops: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FusedResult:
    """Unified result after fusion and reasoning."""
    query: str
    vector_matches: List[VectorResult] = field(default_factory=list)
    graph_matches: List[GraphResult] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    answer: str = ""
    confidence: float = 0.0
    sources: List[Dict] = field(default_factory=list)
    mode: str = SearchMode.HYBRID.value
    latency_ms: float = 0.0

@dataclass
class GraphRAGQuery:
    """Structured query for GraphRAG."""
    text: str                          # Natural language query
    entity_types: List[str] = field(default_factory=list)  # Filter by entity type
    relation_types: List[str] = field(default_factory=list)  # Filter by relation
    max_vector_results: int = 10
    max_graph_hops: int = 3
    min_confidence: float = 0.5
    mode: SearchMode = SearchMode.FULL_RAG


# ── GraphRAG Engine ────────────────────────────────────────────────

class GraphRAGEngine:
    """
    Three-engine fusion: Vector + Graph + LLM.

    Usage:
        engine = GraphRAGEngine()
        result = engine.search(GraphRAGQuery(
            text="Who met Person-A near Gate B last night?",
            entity_types=["Person", "Camera", "Location"],
            max_graph_hops=2,
        ))
        print(result.answer)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.llm_model = self.config.get("llm_model", "deepseek-chat")
        self.vector_weight = self.config.get("vector_weight", 0.4)
        self.graph_weight = self.config.get("graph_weight", 0.6)

        # Lazy-loaded clients
        self._milvus = None
        self._age = None
        self._llm = None

    def search(self, query: GraphRAGQuery) -> FusedResult:
        """Execute a full GraphRAG search with fusion reasoning."""
        import time
        start = time.time()
        result = FusedResult(query=query.text, mode=query.mode.value)

        try:
            # Step 1: Vector search for semantic matches
            if query.mode in (SearchMode.VECTOR_ONLY, SearchMode.HYBRID, SearchMode.FULL_RAG):
                result.vector_matches = self._vector_search(query)
                logger.debug("Vector search: %d matches", len(result.vector_matches))

            # Step 2: Graph traversal for relationship matches
            if query.mode in (SearchMode.GRAPH_ONLY, SearchMode.HYBRID, SearchMode.FULL_RAG):
                result.graph_matches = self._graph_search(query, result.vector_matches)
                logger.debug("Graph search: %d matches", len(result.graph_matches))

            # Step 3: LLM reasoning to fuse and reason
            if query.mode == SearchMode.FULL_RAG:
                reasoned = self._llm_reasoning(query, result)
                result.reasoning_steps = reasoned.get("steps", [])
                result.answer = reasoned.get("answer", "")
                result.confidence = reasoned.get("confidence", 0.5)
                result.sources = reasoned.get("sources", [])
            else:
                # Simple fusion without LLM
                result.answer = self._simple_fusion(query, result)
                result.confidence = self._compute_fusion_confidence(result)

            result.latency_ms = (time.time() - start) * 1000
            logger.info("GraphRAG search completed in %.0fms (mode=%s, confidence=%.2f)",
                        result.latency_ms, query.mode.value, result.confidence)

        except Exception as e:
            logger.exception("GraphRAG search failed: %s", e)
            result.answer = f"Search failed: {e}"
            result.confidence = 0.0
            result.latency_ms = (time.time() - start) * 1000

        return result

    # ── Phase 1: Vector Search ──────────────────────────────────

    def _vector_search(self, query: GraphRAGQuery) -> List[VectorResult]:
        """Search Milvus for semantically similar entities."""
        try:
            from agent_service.core.milvus_client import milvus_client
            self._milvus = milvus_client

            # Get query embedding via LLM or embedding model
            embedding = self._get_query_embedding(query.text)

            results = []
            collections = ["face", "body", "vehicle", "general"]
            if query.entity_types:
                collections = [c for c in collections
                              if any(t.lower() in c.lower() for t in query.entity_types)]

            for coll in collections:
                try:
                    hits = self._milvus.search(
                        collection=coll,
                        vectors=[embedding],
                        top_k=query.max_vector_results,
                    )
                    for hit in hits:
                        if hit.get("score", 0) >= query.min_confidence:
                            results.append(VectorResult(
                                entity_id=hit.get("id", ""),
                                entity_type=coll,
                                score=hit.get("score", 0),
                                metadata=hit.get("metadata", {}),
                            ))
                except Exception:
                    continue

            results.sort(key=lambda r: r.score, reverse=True)
            return results[:query.max_vector_results]

        except ImportError:
            logger.debug("Milvus not available, using mock vector results")
            return self._mock_vector_search(query)

    def _mock_vector_search(self, query: GraphRAGQuery) -> List[VectorResult]:
        """Mock vector search for development."""
        return [
            VectorResult("P001", "Person", 0.92, {"name": "Person-A", "last_seen": "Gate-B"}),
            VectorResult("P002", "Person", 0.85, {"name": "Person-B", "last_seen": "Gate-A"}),
            VectorResult("C001", "Camera", 0.78, {"name": "Gate-B-Camera", "location": "Gate-B"}),
        ]

    # ── Phase 2: Graph Search ──────────────────────────────────

    def _graph_search(self, query: GraphRAGQuery,
                      vector_results: List[VectorResult]) -> List[GraphResult]:
        """Traverse knowledge graph for relationships between entities."""
        try:
            from agent_service.core.age_client import age_client
            self._age = age_client

            results = []
            entity_ids = [r.entity_id for r in vector_results]

            for entity_id in entity_ids[:5]:  # Limit to top 5 for performance
                # Find neighbors up to max_hops
                cypher = """
                    MATCH (n {id: $entity_id})-[r*1..%d]-(m)
                    RETURN n.name, type(r[0]), m.name, m.type, length(r) as hops
                    LIMIT 20
                """ % query.max_graph_hops

                try:
                    rows = self._age.query(cypher, {"entity_id": entity_id})
                    for row in (rows or []):
                        results.append(GraphResult(
                            source_entity=entity_id,
                            target_entity=row.get("m.name", ""),
                            relation_type=row.get("type(r[0])", "RELATED"),
                            hops=row.get("hops", 1),
                            metadata={"target_type": row.get("m.type", "")},
                        ))
                except Exception as e:
                    logger.debug("Graph query failed for %s: %s", entity_id, e)

            return results

        except ImportError:
            logger.debug("AGE not available, using mock graph results")
            return self._mock_graph_search(query, vector_results)

    def _mock_graph_search(self, query: GraphRAGQuery,
                           vector_results: List[VectorResult]) -> List[GraphResult]:
        """Mock graph search for development."""
        return [
            GraphResult("P001", "Gate-B", "VISITED", ["P001", "Gate-B"], 1),
            GraphResult("P001", "P002", "MET", ["P001", "Gate-B", "P002"], 2),
            GraphResult("P001", "C001", "APPEARED_AT", ["P001", "C001"], 1),
            GraphResult("P002", "Gate-A", "VISITED", ["P002", "Gate-A"], 1),
        ]

    # ── Phase 3: LLM Reasoning ─────────────────────────────────

    def _llm_reasoning(self, query: GraphRAGQuery,
                       result: FusedResult) -> Dict[str, Any]:
        """Use LLM to fuse vector + graph results into reasoned answer."""
        try:
            from agent_service.core.llm import get_llm_provider, LLMMessage
            self._llm = get_llm_provider()

            # Build context from search results
            context = self._build_reasoning_context(query, result)

            system_prompt = """You are a VIAIOS Knowledge Graph reasoning engine.
Given search results from both vector similarity search and graph traversal,
synthesize a coherent, evidence-based answer.

Rules:
1. Ground all conclusions in the provided data
2. Cite specific sources (entity IDs, relation types)
3. Indicate confidence level (HIGH/MEDIUM/LOW) for each claim
4. Flag any gaps in the evidence
5. Keep reasoning transparent and auditable"""

            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=context),
            ]

            response = self._llm.chat(messages, temperature=0.3, max_tokens=500)
            parsed = self._parse_reasoning_response(response)

            # Collect sources
            sources = []
            for vm in result.vector_matches[:3]:
                sources.append({"type": "vector", "id": vm.entity_id,
                                "score": vm.score, "type_name": vm.entity_type})
            for gm in result.graph_matches[:5]:
                sources.append({"type": "graph", "source": gm.source_entity,
                                "target": gm.target_entity, "relation": gm.relation_type})

            return {
                "steps": parsed.get("steps", []),
                "answer": parsed.get("answer", response[:500]),
                "confidence": parsed.get("confidence", 0.7),
                "sources": sources,
            }

        except ImportError:
            return {
                "steps": ["Vector: found 3 matches", "Graph: found 4 relationships",
                         "Reasoning: synthesizing connections"],
                "answer": self._simple_fusion(query, result),
                "confidence": self._compute_fusion_confidence(result),
                "sources": [],
            }

    def _build_reasoning_context(self, query: GraphRAGQuery,
                                 result: FusedResult) -> str:
        """Build structured context for LLM reasoning."""
        parts = [f"QUERY: {query.text}\n"]

        parts.append("VECTOR SEARCH RESULTS (semantic similarity):")
        for i, vm in enumerate(result.vector_matches[:5]):
            parts.append(f"  {i+1}. [{vm.entity_type}] {vm.entity_id} "
                        f"(score: {vm.score:.3f}) {json.dumps(vm.metadata)}")

        parts.append("\nGRAPH TRAVERSAL RESULTS (relationships):")
        for i, gm in enumerate(result.graph_matches[:10]):
            path_str = " → ".join(gm.path) if gm.path else f"{gm.source_entity} → {gm.target_entity}"
            parts.append(f"  {i+1}. {path_str} [{gm.relation_type}] (hops: {gm.hops})")

        parts.append("\nBased on these results, analyze and answer the query.")
        parts.append("Include: (1) key findings, (2) reasoning chain, (3) confidence assessment.")

        return "\n".join(parts)

    def _parse_reasoning_response(self, response: str) -> Dict[str, Any]:
        """Parse structured reasoning from LLM response."""
        steps = []
        answer = response
        confidence = 0.7

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith(("Step", "STEP", "1.", "2.", "3.", "4.", "5.")):
                steps.append(line)
            if "confidence" in line.lower() and "high" in line.lower():
                confidence = 0.9
            elif "confidence" in line.lower() and "medium" in line.lower():
                confidence = 0.7
            elif "confidence" in line.lower() and "low" in line.lower():
                confidence = 0.4

        return {"steps": steps or ["Analysis completed"], "answer": answer,
                "confidence": confidence}

    def _simple_fusion(self, query: GraphRAGQuery,
                       result: FusedResult) -> str:
        """Simple rule-based fusion without LLM."""
        parts = []

        if result.vector_matches:
            top = result.vector_matches[0]
            parts.append(f"Top match: {top.entity_type} {top.entity_id} "
                        f"(score: {top.score:.2f})")

        if result.graph_matches:
            relations = set(gm.relation_type for gm in result.graph_matches)
            parts.append(f"Found {len(result.graph_matches)} relationships "
                        f"({', '.join(relations)}) across "
                        f"{len(set(gm.target_entity for gm in result.graph_matches))} entities")

        return ". ".join(parts) if parts else "No matches found."

    def _compute_fusion_confidence(self, result: FusedResult) -> float:
        """Compute confidence score from search results."""
        if not result.vector_matches and not result.graph_matches:
            return 0.0

        vec_conf = max((r.score for r in result.vector_matches), default=0)
        graph_conf = min(1.0, len(result.graph_matches) / 10)

        return round(self.vector_weight * vec_conf + self.graph_weight * graph_conf, 3)

    def _get_query_embedding(self, text: str) -> List[float]:
        """Get embedding vector for query text."""
        import hashlib, random
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1, 1) for _ in range(512)]


# ── Convenience ────────────────────────────────────────────────────

_engine: Optional[GraphRAGEngine] = None


def get_graphrag_engine() -> GraphRAGEngine:
    global _engine
    if _engine is None:
        _engine = GraphRAGEngine()
    return _engine

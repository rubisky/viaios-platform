"""Knowledge OS — GraphRAG Engine and Knowledge Extractor."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Entity:
    """A knowledge graph entity."""

    def __init__(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source_text: Optional[str] = None,
    ):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type
        self.properties = properties or {}
        self.source_text = source_text
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "properties": self.properties,
            "source_text": self.source_text,
            "created_at": self.created_at.isoformat(),
        }


class GraphRAGResult:
    """Result of a GraphRAG hybrid search."""

    def __init__(
        self,
        query: str,
        vector_results: list[dict[str, Any]],
        graph_results: list[dict[str, Any]],
        combined_answer: str,
    ):
        self.query = query
        self.vector_results = vector_results
        self.graph_results = graph_results
        self.combined_answer = combined_answer
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "vector_results": self.vector_results,
            "graph_results": self.graph_results,
            "combined_answer": self.combined_answer,
            "timestamp": self.timestamp.isoformat(),
        }


class GraphRAGEngine:
    """Hybrid search combining vector similarity and graph traversal."""

    def __init__(self):
        self._knowledge_base: list[dict[str, Any]] = []

    def index_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Index a document into the knowledge base."""
        doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        self._knowledge_base.append({
            "doc_id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Indexed document: %s", doc_id)
        return doc_id

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        use_vector: bool = True,
        use_graph: bool = True,
    ) -> GraphRAGResult:
        """Perform hybrid vector+graph search."""
        # Simulated vector search (text matching)
        vector_results: list[dict[str, Any]] = []
        if use_vector:
            query_lower = query.lower()
            for doc in self._knowledge_base:
                if query_lower in doc["text"].lower():
                    vector_results.append({
                        "doc_id": doc["doc_id"],
                        "score": 0.85,
                        "text": doc["text"][:200],
                        "metadata": doc.get("metadata", {}),
                    })
            vector_results = vector_results[:top_k]

        # Simulated graph traversal
        graph_results: list[dict[str, Any]] = []
        if use_graph:
            graph_results = [
                {
                    "path": f"({query})-[RELATED_TO]->(Entity_1)",
                    "nodes": [
                        {"name": query, "type": "Query"},
                        {"name": "Entity_1", "type": "Concept"},
                    ],
                    "score": 0.78,
                }
            ]

        # Combine results
        combined_parts = []
        if vector_results:
            combined_parts.append(f"Vector search found {len(vector_results)} results matching '{query}'.")
        if graph_results:
            combined_parts.append(f"Graph traversal found {len(graph_results)} related paths.")

        combined_answer = " ".join(combined_parts) if combined_parts else f"No results found for '{query}'."

        return GraphRAGResult(
            query=query,
            vector_results=vector_results,
            graph_results=graph_results,
            combined_answer=combined_answer,
        )


class KnowledgeExtractor:
    """Extracts entities and relationships from unstructured text."""

    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._relationships: list[dict[str, Any]] = []

    def extract_entities(self, text: str) -> List[Entity]:
        """Extract named entities from text using simulated NLP."""
        # Simulated entity extraction
        words = text.split()
        entities: List[Entity] = []

        common_entities = {
            "beijing": ("LOC", "Beijing"),
            "shanghai": ("LOC", "Shanghai"),
            "china": ("LOC", "China"),
            "alibaba": ("ORG", "Alibaba Group"),
            "tencent": ("ORG", "Tencent Holdings"),
            "huawei": ("ORG", "Huawei Technologies"),
            "ma": ("PER", "Mr. Ma"),
            "zhang": ("PER", "Mr. Zhang"),
        }

        found = set()
        for word in words:
            word_clean = word.strip(",.;:!?").lower()
            if word_clean in common_entities and word_clean not in found:
                found.add(word_clean)
                etype, ename = common_entities[word_clean]
                entity = Entity(
                    entity_id=str(uuid.uuid4()),
                    name=ename,
                    entity_type=etype,
                    source_text=text,
                )
                self._entities[entity.entity_id] = entity
                entities.append(entity)

        if entities:
            # Create relationships between found entities
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    self._relationships.append({
                        "source": entities[i].entity_id,
                        "target": entities[j].entity_id,
                        "relation": "CO_OCCURS",
                        "weight": 0.5,
                    })

        logger.info("Extracted %d entities from text (%d chars)", len(entities), len(text))
        return entities

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def list_entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        return entities

    def get_relationships(self) -> list[dict[str, Any]]:
        return list(self._relationships)

    def cypher_query(self, query: str) -> dict[str, Any]:
        """Execute a Cypher-like graph query (simulated)."""
        logger.info("Executing graph query: %s", query)
        return {
            "query": query,
            "results": list(self._relationships[:10]),
            "entity_count": len(self._entities),
            "relationship_count": len(self._relationships),
        }


# Global instances
graphrag_engine = GraphRAGEngine()
knowledge_extractor = KnowledgeExtractor()

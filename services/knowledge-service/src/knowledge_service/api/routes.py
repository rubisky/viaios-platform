"""Knowledge Service API Routes."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from knowledge_service.core.service import graphrag_engine as legacy_engine, knowledge_extractor
from knowledge_service.core.graphrag import GraphRAGEngine, graphrag_engine

logger = logging.getLogger(__name__)

router = APIRouter()


class GraphRAGRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=5, ge=1, le=100)
    use_vector: bool = Field(default=True)
    use_graph: bool = Field(default=True)


class GraphQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096, description="Cypher query string")


class ExtractEntitiesRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class IndexDocumentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/api/v1/knowledge/graphrag")
async def graphrag_query(request: GraphRAGRequest):
    """Perform a hybrid GraphRAG query combining vector search and graph traversal."""
    try:
        result = graphrag_engine.hybrid_search(
            query=request.query,
            top_k=request.top_k,
            use_vector=request.use_vector,
            use_graph=request.use_graph,
        )
        return {"status": "ok", "data": result.to_dict()}
    except Exception as e:
        logger.exception("GraphRAG query failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/knowledge/graph/query")
async def graph_query(request: GraphQueryRequest):
    """Execute a Cypher query on the knowledge graph."""
    try:
        result = knowledge_extractor.cypher_query(request.query)
        return {"status": "ok", "data": result}
    except Exception as e:
        logger.exception("Graph query failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/knowledge/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get a knowledge graph entity by ID."""
    entity = knowledge_extractor.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    return {"status": "ok", "data": entity.to_dict()}


@router.get("/api/v1/knowledge/entities")
async def list_entities(entity_type: Optional[str] = None):
    """List all extracted entities, optionally filtered by type."""
    entities = knowledge_extractor.list_entities(entity_type=entity_type)
    return {"status": "ok", "data": [e.to_dict() for e in entities]}


@router.post("/api/v1/knowledge/extract")
async def extract_entities(request: ExtractEntitiesRequest):
    """Extract entities and relationships from unstructured text."""
    try:
        entities = knowledge_extractor.extract_entities(request.text)
        relationships = knowledge_extractor.get_relationships()
        return {
            "status": "ok",
            "data": {
                "entities": [e.to_dict() for e in entities],
                "relationships": relationships,
                "entity_count": len(entities),
                "relationship_count": len(relationships),
            },
        }
    except Exception as e:
        logger.exception("Entity extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/knowledge/index")
async def index_document(request: IndexDocumentRequest):
    """Index a document into the knowledge base."""
    try:
        doc_id = graphrag_engine.index_document(
            text=request.text,
            metadata=request.metadata,
        )
        return {"status": "ok", "data": {"doc_id": doc_id}}
    except Exception as e:
        logger.exception("Document indexing failed")
        raise HTTPException(status_code=500, detail=str(e))


# ===== GraphRAG Triple Engine =====
from knowledge_service.core.graphrag import graphrag_engine as grag

class LoadRequest(BaseModel):
    entities: list = []
    edges: list = []

@router.post("/api/v1/knowledge/graphrag/load")
async def graphrag_load(request: LoadRequest):
    """Load entities and edges into the GraphRAG engine."""
    grag.load_data(request.entities, request.edges)
    return grag.stats()

@router.post("/api/v1/knowledge/graphrag/query")
async def graphrag_query(request: GraphRAGRequest):
    """Query the GraphRAG engine: vector + graph + LLM fusion."""
    return grag.query(request.query, request.top_k)

@router.get("/api/v1/knowledge/graphrag/query")
async def graphrag_quick_query(q: str = ""):
    """Quick GraphRAG query via GET."""
    if not q: return {"error": "q parameter required"}
    return grag.query(q, top_k=5)

@router.get("/api/v1/knowledge/graphrag/stats")
async def graphrag_stats():
    """Get GraphRAG engine statistics."""
    return grag.stats()

@router.post("/api/v1/knowledge/graphrag/init")
async def graphrag_init():
    """Auto-load entities and edges from knowledge graph API."""
    import requests
    try:
        entities_r = requests.get("http://localhost:8093/api/v1/knowledge/entities", timeout=5)
        graph_r = requests.get("http://localhost:8093/api/v1/knowledge/graph", timeout=5)
        entities = entities_r.json().get("entities", [])
        edges = graph_r.json().get("edges", [])
        grag.load_data(entities, edges)
        return {"loaded": len(entities), "edges": len(edges), "stats": grag.stats()}
    except Exception as e:
        return {"error": str(e)}

"""Tests for Knowledge Service."""

import pytest
from httpx import ASGITransport, AsyncClient

from knowledge_service.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "viaios-knowledge-service"


@pytest.mark.asyncio
async def test_extract_entities(client: AsyncClient):
    response = await client.post(
        "/api/v1/knowledge/extract",
        json={
            "text": "Alibaba and Tencent are major technology companies based in China. Huawei was founded in Shenzhen."
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["data"]["entities"]) >= 1


@pytest.mark.asyncio
async def test_index_and_graphrag(client: AsyncClient):
    # Index a document
    await client.post(
        "/api/v1/knowledge/index",
        json={
            "text": "The VIAIOS platform provides AI-powered video investigation and intelligent analysis for public safety.",
            "metadata": {"source": "test", "category": "product"},
        },
    )

    # Perform GraphRAG query
    response = await client.post(
        "/api/v1/knowledge/graphrag",
        json={
            "query": "video investigation",
            "top_k": 5,
            "use_vector": True,
            "use_graph": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "vector_results" in data["data"]


@pytest.mark.asyncio
async def test_graphrag_no_results(client: AsyncClient):
    response = await client.post(
        "/api/v1/knowledge/graphrag",
        json={
            "query": "xyz_nonexistent_abc_123",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "No results found" in data["data"]["combined_answer"]


@pytest.mark.asyncio
async def test_graph_query(client: AsyncClient):
    # Extract entities first to populate graph
    await client.post(
        "/api/v1/knowledge/extract",
        json={"text": "Alibaba Group operates in China led by Mr. Ma."},
    )

    response = await client.post(
        "/api/v1/knowledge/graph/query",
        json={"query": "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "results" in data["data"]


@pytest.mark.asyncio
async def test_get_entity(client: AsyncClient):
    # Extract entities first
    ext = await client.post(
        "/api/v1/knowledge/extract",
        json={"text": "Tencent Holdings is a major company in China."},
    )
    entities = ext.json()["data"]["entities"]
    if entities:
        entity_id = entities[0]["entity_id"]
        response = await client.get(f"/api/v1/knowledge/entities/{entity_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["entity_id"] == entity_id


@pytest.mark.asyncio
async def test_entity_not_found(client: AsyncClient):
    response = await client.get("/api/v1/knowledge/entities/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_entities_by_type(client: AsyncClient):
    # Ensure there are entities
    await client.post(
        "/api/v1/knowledge/extract",
        json={"text": "Alibaba Group operates in China."},
    )
    response = await client.get("/api/v1/knowledge/entities?entity_type=LOC")
    assert response.status_code == 200
    data = response.json()
    for entity in data["data"]:
        assert entity["entity_type"] == "LOC"


@pytest.mark.asyncio
async def test_empty_extract(client: AsyncClient):
    response = await client.post(
        "/api/v1/knowledge/extract",
        json={"text": "The quick brown fox jumps over the lazy dog."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["data"]["entities"]) == 0

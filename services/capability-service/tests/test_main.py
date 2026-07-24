"""Tests for Capability Service."""

import pytest
from httpx import ASGITransport, AsyncClient

from capability_service.main import app


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
    assert data["service"] == "viaios-capability-service"


@pytest.mark.asyncio
async def test_register_capability(client: AsyncClient):
    response = await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "text-summarizer",
            "description": "Summarizes text using AI",
            "version": "1.0.0",
            "endpoint": "http://localhost:9000/summarize",
            "provider": "viaios",
            "input_schema": {"text": "string"},
            "output_schema": {"summary": "string"},
            "tags": ["nlp", "text"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["name"] == "text-summarizer"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "dup-cap",
            "description": "Test",
            "endpoint": "http://localhost:9000/test",
        },
    )
    response = await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "dup-cap",
            "description": "Test duplicate",
            "endpoint": "http://localhost:9000/test2",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_capabilities(client: AsyncClient):
    await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "list-test-cap",
            "description": "For list test",
            "endpoint": "http://localhost:9000/list",
            "tags": ["test"],
        },
    )
    response = await client.get("/api/v1/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_list_capabilities_with_tag(client: AsyncClient):
    response = await client.get("/api/v1/capabilities?tag=test")
    assert response.status_code == 200
    data = response.json()
    for cap in data["data"]:
        assert "test" in cap["tags"]


@pytest.mark.asyncio
async def test_get_capability(client: AsyncClient):
    await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "get-test-cap",
            "description": "For get test",
            "endpoint": "http://localhost:9000/get",
        },
    )
    response = await client.get("/api/v1/capabilities/get-test-cap")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "get-test-cap"


@pytest.mark.asyncio
async def test_invoke_capability(client: AsyncClient):
    await client.post(
        "/api/v1/capabilities/register",
        json={
            "name": "invoke-test",
            "description": "For invoke test",
            "endpoint": "http://localhost:9000/invoke",
        },
    )
    response = await client.post(
        "/api/v1/capabilities/invoke",
        json={
            "capability_name": "invoke-test",
            "params": {"input": "hello"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["output"]["status"] == "success"


@pytest.mark.asyncio
async def test_select_model(client: AsyncClient):
    response = await client.post(
        "/api/v1/models/select",
        json={
            "task_type": "text",
            "max_cost": "low",
            "max_latency": "low",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient):
    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1

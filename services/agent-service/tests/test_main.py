"""Tests for Agent Service."""

import pytest
from httpx import ASGITransport, AsyncClient

from agent_service.main import app


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
    assert data["service"] == "viaios-agent-service"


@pytest.mark.asyncio
async def test_register_agent(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents/register",
        json={
            "name": "test-agent",
            "description": "A test agent",
            "agent_type": "reasoning",
            "config": {"model": "gpt-4o"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["name"] == "test-agent"
    assert data["data"]["agent_type"] == "reasoning"
    return data["data"]["agent_id"]


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    # Register one first
    await client.post(
        "/api/v1/agents/register",
        json={
            "name": "list-test-agent",
            "description": "Agent for list test",
            "agent_type": "retrieval",
        },
    )
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_list_agents_with_filter(client: AsyncClient):
    response = await client.get("/api/v1/agents?agent_type=retrieval")
    assert response.status_code == 200
    data = response.json()
    for agent in data["data"]:
        assert agent["agent_type"] == "retrieval"


@pytest.mark.asyncio
async def test_execute_agent(client: AsyncClient):
    # Register an agent first
    reg = await client.post(
        "/api/v1/agents/register",
        json={
            "name": "exec-test-agent",
            "description": "Agent for execution test",
            "agent_type": "action",
        },
    )
    agent_id = reg.json()["data"]["agent_id"]

    response = await client.post(
        "/api/v1/agents/execute",
        json={
            "agent_id": agent_id,
            "input": {"query": "What is VIAIOS?"},
            "timeout": 30,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_agent_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents/execute",
        json={
            "agent_id": "nonexistent",
            "input": {},
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_status(client: AsyncClient):
    reg = await client.post(
        "/api/v1/agents/register",
        json={
            "name": "status-test-agent",
            "description": "Agent for status test",
            "agent_type": "reasoning",
        },
    )
    agent_id = reg.json()["data"]["agent_id"]

    response = await client.get(f"/api/v1/agents/{agent_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["agent"]["agent_id"] == agent_id

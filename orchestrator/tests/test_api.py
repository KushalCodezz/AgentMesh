"""
tests/test_api.py — Integration tests for FastAPI endpoints.
Uses TestClient with mocked orchestrator.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.start_conversation = AsyncMock(return_value={
        "conversation_id": "conv-test-001",
        "trace_id": "trace-test-001",
        "status": "planning",
    })
    orch.list_conversations = AsyncMock(return_value=[
        {
            "conversation_id": "conv-test-001",
            "status": "completed",
            "request": "Test request",
            "task_count": 3,
            "created_at": "2024-01-01T00:00:00Z",
        }
    ])
    orch.get_conversation = AsyncMock(return_value={
        "conversation_id": "conv-test-001",
        "trace_id": "trace-test-001",
        "request": "Test request",
        "status": "completed",
        "tasks": [],
        "results": {},
        "deliverable": {
            "summary": "3 tasks completed",
            "avg_confidence": 0.85,
            "task_count": 3,
            "success_count": 3,
        },
        "events": [],
        "created_at": "2024-01-01T00:00:00Z",
        "metadata": {},
    })
    orch.get_agent_stats = MagicMock(return_value=[
        {
            "agent_id": "engineer_agent",
            "reliability_score": 0.95,
            "total_tasks": 42,
            "recent_success_rate": 0.90,
            "avg_confidence": 0.87,
            "avg_latency_ms": 2300,
        }
    ])
    orch.get_adaptive_proposals = MagicMock(return_value=[])
    orch.approve_agent_proposal = AsyncMock(return_value=True)
    orch.reject_agent_proposal = AsyncMock(return_value=True)
    return orch


@pytest.fixture
def client(mock_orchestrator):
    with patch("main.orchestrator", mock_orchestrator):
        from main import app
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestConversationEndpoints:
    def test_start_conversation(self, client):
        r = client.post("/api/v1/conversations", json={"request": "Build a REST API"})
        assert r.status_code == 200
        data = r.json()
        assert "conversation_id" in data
        assert data["status"] == "planning"

    def test_start_conversation_empty_request_fails(self, client):
        r = client.post("/api/v1/conversations", json={"request": "   "})
        assert r.status_code == 400

    def test_list_conversations(self, client):
        r = client.get("/api/v1/conversations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 0

    def test_get_conversation(self, client):
        r = client.get("/api/v1/conversations/conv-test-001")
        assert r.status_code == 200
        data = r.json()
        assert data["conversation_id"] == "conv-test-001"

    def test_get_conversation_not_found(self, client, mock_orchestrator):
        mock_orchestrator.get_conversation = AsyncMock(return_value=None)
        r = client.get("/api/v1/conversations/nonexistent")
        assert r.status_code == 404


class TestAgentEndpoints:
    def test_list_agents(self, client):
        r = client.get("/api/v1/agents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data[0]["agent_id"] == "engineer_agent"


class TestAdaptiveEndpoints:
    def test_list_proposals(self, client):
        r = client.get("/api/v1/adaptive/proposals")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_approve_proposal(self, client):
        r = client.post(
            "/api/v1/adaptive/proposals/prop-001",
            json={"action": "approve"}
        )
        assert r.status_code == 200
        assert r.json()["action"] == "approve"

    def test_reject_proposal(self, client):
        r = client.post(
            "/api/v1/adaptive/proposals/prop-001",
            json={"action": "reject"}
        )
        assert r.status_code == 200

    def test_invalid_action(self, client):
        r = client.post(
            "/api/v1/adaptive/proposals/prop-001",
            json={"action": "delete"}
        )
        assert r.status_code == 400


class TestStatsEndpoint:
    def test_stats(self, client, mock_orchestrator):
        mock_orchestrator.get_adaptive_proposals = MagicMock(return_value=[])
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        data = r.json()
        assert "conversations" in data
        assert "agents" in data
        assert "adaptive" in data

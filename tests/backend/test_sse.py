"""Tests for SSE endpoints and SSEManager"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime


@pytest.fixture
async def client():
    """Create a test client for the FastAPI app"""
    from main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestHealthEndpoint:
    """Test /health endpoint"""

    async def test_health_returns_healthy_status(self, client):
        """Health endpoint should return healthy status"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "hermes-bridge"
        assert "version" in data
        assert "active_connections" in data


class TestRootEndpoint:
    """Test / endpoint"""

    async def test_root_returns_service_info(self, client):
        """Root endpoint should return service information"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Hermès Bridge Service"
        assert data["version"] == "1.1.0"
        assert "endpoints" in data
        assert data["endpoints"]["sse"] == "/sse"
        assert data["endpoints"]["health"] == "/health"
        assert data["endpoints"]["tasks"] == "/tasks"


class TestTasksEndpoint:
    """Test /tasks endpoints"""

    async def test_list_tasks(self, client):
        """GET /tasks should return task list"""
        response = await client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)

    async def test_get_task_by_id(self, client):
        """GET /tasks/{task_id} should return specific task"""
        # Use a real session ID from the list
        list_response = await client.get("/tasks")
        assert list_response.status_code == 200
        tasks = list_response.json().get("tasks", [])
        if not tasks:
            pytest.skip("No tasks available to test")
        task_id = tasks[0].get("task_id") or tasks[0].get("id")
        response = await client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert "name" in data
        assert "status" in data
        assert "progress" in data

    async def test_get_nonexistent_task_returns_404(self, client):
        """GET /tasks/{task_id} with invalid ID should return 404"""
        response = await client.get("/tasks/nonexistent_id_12345")
        assert response.status_code == 404


class TestConnectionsEndpoint:
    """Test /connections endpoints"""

    async def test_list_connections(self, client):
        """GET /connections should return connection list"""
        response = await client.get("/connections")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "connections" in data
        assert isinstance(data["connections"], list)


class TestSSEManager:
    """Test SSEManager class"""

    def test_sse_manager_initialization(self):
        """SSEManager should initialize with empty connections"""
        from sse_manager import SSEManager
        manager = SSEManager()
        assert manager.get_connection_count() == 0
        assert manager.get_all_connections() == []

    def test_get_connection_info_nonexistent(self):
        """Getting info for nonexistent connection should return None"""
        from sse_manager import SSEManager
        manager = SSEManager()
        assert manager.get_connection_info("nonexistent") is None

    def test_disconnect_nonexistent(self):
        """Disconnecting nonexistent connection should not raise"""
        from sse_manager import SSEManager
        manager = SSEManager()
        manager.disconnect("nonexistent")  # Should not raise


class TestBroadcastEndpoint:
    """Test /broadcast endpoint"""

    async def test_broadcast_requires_parameters(self, client):
        """POST /broadcast without parameters should return 422"""
        response = await client.post("/broadcast")
        assert response.status_code == 422

    async def test_broadcast_success(self, client):
        """POST /broadcast with valid parameters should succeed"""
        response = await client.post(
            "/broadcast",
            params={"event_type": "test", "message": "hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "broadcast_sent"
        assert data["event_type"] == "test"


class TestConfigSettings:
    """Test configuration settings"""

    def test_default_settings(self):
        """Settings should have correct defaults"""
        from config import settings
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.heartbeat_interval == 30
        assert settings.event_generation_interval == 1
        assert settings.max_connections == 1000

"""Tests for /health endpoint — health check verification."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from routers.health import _check_database, _check_workers


class TestCheckDatabase:
    def test_connected_with_migration_version(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("abc123",)
        with patch("routers.health.SessionLocal", return_value=mock_db):
            result = _check_database()
        assert result["status"] == "connected"
        assert result["migration_version"] == "abc123"
        assert result["error"] is None

    def test_connected_no_migration_row(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        with patch("routers.health.SessionLocal", return_value=mock_db):
            result = _check_database()
        assert result["status"] == "connected"
        assert result["migration_version"] is None

    def test_error_on_connection_failure(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("connection refused")
        with patch("routers.health.SessionLocal", return_value=mock_db):
            result = _check_database()
        assert result["status"] == "error"
        assert "connection refused" in result["error"]


class TestCheckWorkers:
    def test_alive_heartbeat(self, tmp_path):
        hb = tmp_path / "hermes_scheduler_worker_heartbeat"
        hb.write_text(datetime.now(timezone.utc).isoformat())
        fresh_mtime = hb.stat().st_mtime
        with patch("utils.heartbeat.os.path.getmtime", return_value=fresh_mtime):
            result = _check_workers()
        assert "scheduler-worker" in result
        assert result["scheduler-worker"]["status"] == "alive"
        assert result["scheduler-worker"]["last_seen_seconds_ago"] is not None

    def test_stale_heartbeat(self, tmp_path):
        hb = tmp_path / "heartbeat"
        hb.write_text("stale")
        old_mtime = time.time() - 200
        os.utime(hb, (old_mtime, old_mtime))
        with patch("utils.heartbeat.os.path.getmtime", return_value=old_mtime):
            result = _check_workers()
        for worker in result.values():
            assert worker["status"] == "stale"
            assert worker["last_seen_seconds_ago"] >= 200

    def test_missing_heartbeat(self):
        with patch("utils.heartbeat.os.path.getmtime", side_effect=FileNotFoundError):
            result = _check_workers()
        for worker in result.values():
            assert worker["status"] == "unknown"
            assert worker["last_seen_seconds_ago"] is None

    def test_error_on_unexpected_exception(self):
        with patch("utils.heartbeat.os.path.getmtime", side_effect=PermissionError("denied")):
            result = _check_workers()
        for worker in result.values():
            assert worker["status"] == "error"


class TestHealthEndpointStructure:
    def test_healthy_response_structure(self):
        from fastapi.testclient import TestClient
        from main import app

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("v1",)
        with patch("routers.health.SessionLocal", return_value=mock_db):
            with patch("utils.heartbeat.os.path.getmtime", side_effect=FileNotFoundError):
                client = TestClient(app)
                resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "database" in data
        assert "workers" in data
        assert "timestamp" in data
        assert data["database"]["status"] == "connected"
        assert data["database"]["migration_version"] == "v1"

    def test_degraded_when_db_down(self):
        from fastapi.testclient import TestClient
        from main import app

        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("db down")
        with patch("routers.health.SessionLocal", return_value=mock_db):
            with patch("utils.heartbeat.os.path.getmtime", side_effect=FileNotFoundError):
                client = TestClient(app)
                resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "error"

    def test_degraded_when_worker_error(self):
        from fastapi.testclient import TestClient
        from main import app

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("v1",)
        with patch("routers.health.SessionLocal", return_value=mock_db):
            with patch("utils.heartbeat.os.path.getmtime", side_effect=PermissionError("no access")):
                client = TestClient(app)
                resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        for w in data["workers"].values():
            assert w["status"] == "error"

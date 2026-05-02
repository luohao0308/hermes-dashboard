"""Tests for /api/metrics endpoint and shared heartbeat helper."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from utils.heartbeat import read_heartbeat, read_all_workers, write_heartbeat


class TestReadHeartbeat:
    def test_alive_heartbeat(self, tmp_path):
        hb = tmp_path / "heartbeat"
        hb.write_text(datetime.now(timezone.utc).isoformat())
        with patch("utils.heartbeat.os.path.getmtime", return_value=hb.stat().st_mtime):
            result = read_heartbeat("scheduler_worker")
            assert result["status"] == "alive"
            assert result["age_seconds"] is not None

    def test_missing_heartbeat(self):
        result = read_heartbeat("nonexistent_worker_xyz")
        assert result["status"] == "missing"
        assert result["age_seconds"] is None

    def test_stale_heartbeat(self, tmp_path):
        hb = tmp_path / "heartbeat"
        hb.write_text("stale")
        old_mtime = time.time() - 200
        os.utime(hb, (old_mtime, old_mtime))
        with patch("utils.heartbeat.os.path.getmtime", return_value=old_mtime):
            result = read_heartbeat("scheduler_worker")
            assert result["status"] == "stale"

    def test_error_on_unexpected_exception(self):
        with patch("utils.heartbeat.os.path.getmtime", side_effect=PermissionError("denied")):
            result = read_heartbeat("scheduler_worker")
            assert result["status"] == "error"
            assert "denied" in result["error"]


class TestReadAllWorkers:
    def test_returns_both_workers(self):
        with patch("utils.heartbeat.os.path.getmtime", side_effect=FileNotFoundError):
            result = read_all_workers()
        assert "scheduler_worker" in result
        assert "retention_worker" in result


class TestWriteHeartbeat:
    def test_writes_file(self, tmp_path):
        hb = tmp_path / "hb"
        with patch.dict("utils.heartbeat._WORKER_PATHS", {"test_worker": str(hb)}):
            write_heartbeat("test_worker")
        assert hb.exists()
        content = hb.read_text()
        # Should be a valid ISO timestamp
        assert "T" in content

    def test_unknown_worker_is_noop(self):
        # Should not raise
        write_heartbeat("unknown_worker")


class TestMetricsEndpoint:
    def test_metrics_returns_expected_structure(self):
        from routers.metrics import get_metrics

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 0

        with patch("routers.metrics.SessionLocal", return_value=mock_db):
            with patch("routers.metrics.read_heartbeat", return_value={"status": "missing", "age_seconds": None}):
                result = get_metrics()

        assert "status" in result
        assert "runs" in result
        assert "approvals" in result
        assert "tasks" in result
        assert "connectors" in result
        assert "evals" in result
        assert "workers" in result
        assert "timestamp" in result

        assert "total" in result["runs"]
        assert "running" in result["runs"]
        assert "failed" in result["runs"]
        assert "pending" in result["approvals"]
        assert "dead_letter" in result["tasks"]

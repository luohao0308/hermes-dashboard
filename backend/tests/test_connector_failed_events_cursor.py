"""Tests for connector failed events cursor pagination — OPT-58.

Tests the GET /api/connectors/{id}/failed-events endpoint with cursor-based
and offset-based pagination. Uses mocked DB session so no TEST_DATABASE_URL needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONNECTOR_ID = uuid.uuid4()
AUTH_HEADERS = {"X-User-Role": "operator"}


def _make_failed_event(offset_seconds: int = 0) -> MagicMock:
    """Create a mock FailedEvent row."""
    evt = MagicMock()
    evt.id = str(uuid.uuid4())
    evt.connector_id = str(CONNECTOR_ID)
    evt.event_type = "test.event"
    evt.event_id = f"evt-{evt.id[:8]}"
    evt.run_id = None
    evt.payload = None
    evt.error_message = "something went wrong"
    evt.created_at = datetime.now(timezone.utc) - timedelta(seconds=offset_seconds)
    return evt


def _make_connector() -> MagicMock:
    """Create a mock ConnectorConfig row."""
    conn = MagicMock()
    conn.id = CONNECTOR_ID
    conn.display_name = "Test Connector"
    conn.connector_type = "github"
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """TestClient with mocked DB session."""
    mock_db = MagicMock()
    mock_db.get.return_value = _make_connector()

    def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c, mock_db

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFailedEventsOffsetPagination:
    """Offset-based pagination (no cursor parameter)."""

    def test_first_page(self, client):
        c, mock_db = client
        events = [_make_failed_event(i) for i in range(3)]

        mock_query = MagicMock()
        mock_query.count.return_value = 5
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = events
        mock_db.query.return_value.filter.return_value = mock_query

        resp = c.get(
            f"/api/connectors/{CONNECTOR_ID}/failed-events?limit=3&offset=0",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["next_cursor"] is None
        assert data["has_more"] is True  # offset(0) + limit(3) = 3 < 5

    def test_last_page(self, client):
        c, mock_db = client
        events = [_make_failed_event(i) for i in range(2)]

        mock_query = MagicMock()
        mock_query.count.return_value = 5
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = events
        mock_db.query.return_value.filter.return_value = mock_query

        resp = c.get(
            f"/api/connectors/{CONNECTOR_ID}/failed-events?limit=3&offset=3",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["next_cursor"] is None
        assert data["has_more"] is False  # offset(3) + limit(3) = 6 >= 5

    def test_empty_result(self, client):
        c, mock_db = client

        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value = mock_query

        resp = c.get(
            f"/api/connectors/{CONNECTOR_ID}/failed-events",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["has_more"] is False


class TestFailedEventsCursorPagination:
    """Cursor-based pagination (cursor parameter provided)."""

    def test_cursor_calls_apply_cursor(self, client):
        c, mock_db = client
        events = [_make_failed_event(i) for i in range(3)]

        mock_query = MagicMock()
        mock_query.count.return_value = 10
        mock_db.query.return_value.filter.return_value = mock_query

        with patch("routers.connectors.apply_cursor", return_value=(events, "next-cursor-token", True)) as mock_apply:
            resp = c.get(
                f"/api/connectors/{CONNECTOR_ID}/failed-events?limit=3&cursor=abc123",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["next_cursor"] == "next-cursor-token"
        assert data["has_more"] is True
        mock_apply.assert_called_once()

    def test_cursor_no_more(self, client):
        c, mock_db = client
        events = [_make_failed_event(i) for i in range(2)]

        mock_query = MagicMock()
        mock_query.count.return_value = 10
        mock_db.query.return_value.filter.return_value = mock_query

        with patch("routers.connectors.apply_cursor", return_value=(events, None, False)):
            resp = c.get(
                f"/api/connectors/{CONNECTOR_ID}/failed-events?limit=3&cursor=abc123",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["next_cursor"] is None
        assert data["has_more"] is False


class TestFailedEventsEdgeCases:
    """Edge cases and validation."""

    def test_connector_not_found(self, client):
        c, mock_db = client
        mock_db.get.return_value = None

        resp = c.get(
            f"/api/connectors/{uuid.uuid4()}/failed-events",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404

    def test_default_limit(self, client):
        c, mock_db = client

        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value = mock_query

        resp = c.get(
            f"/api/connectors/{CONNECTOR_ID}/failed-events",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 50

    def test_response_schema_fields(self, client):
        """Verify all expected fields are present in the response."""
        c, mock_db = client
        events = [_make_failed_event()]

        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = events
        mock_db.query.return_value.filter.return_value = mock_query

        resp = c.get(
            f"/api/connectors/{CONNECTOR_ID}/failed-events",
            headers=AUTH_HEADERS,
        )
        data = resp.json()

        # Top-level fields
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "next_cursor" in data
        assert "has_more" in data

        # Item fields
        item = data["items"][0]
        assert "id" in item
        assert "connector_id" in item
        assert "event_type" in item
        assert "error_message" in item
        assert "created_at" in item

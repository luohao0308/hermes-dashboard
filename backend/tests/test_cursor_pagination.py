"""Tests for cursor-based pagination — OPT-50."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from utils.cursor import encode_cursor, decode_cursor, apply_cursor


class TestEncodeDecode:
    def test_roundtrip(self):
        now = datetime.now(timezone.utc)
        row_id = uuid4()
        cursor = encode_cursor(now, row_id)
        decoded = decode_cursor(cursor)
        assert decoded["id"] == row_id
        assert abs((decoded["created_at"] - now).total_seconds()) < 0.001

    def test_invalid_cursor_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-a-valid-cursor")

    def test_malformed_json_raises(self):
        import base64
        bad = base64.urlsafe_b64encode(b"{}").decode()
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor(bad)


class TestApplyCursor:
    def _make_items(self, count, base_time=None):
        if base_time is None:
            base_time = datetime.now(timezone.utc)
        items = []
        for i in range(count):
            item = MagicMock()
            item.created_at = base_time - timedelta(seconds=i * 10)
            item.id = uuid4()
            items.append(item)
        return items

    def test_no_cursor_returns_first_page(self):
        items = self._make_items(3)
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = items

        result_items, next_cursor, has_more = apply_cursor(
            mock_query, MagicMock(), None, limit=10
        )
        assert len(result_items) == 3
        assert next_cursor is None
        assert has_more is False

    def test_has_more_when_extra_items(self):
        items = self._make_items(11)
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = items

        result_items, next_cursor, has_more = apply_cursor(
            mock_query, MagicMock(), None, limit=10
        )
        assert len(result_items) == 10
        assert next_cursor is not None
        assert has_more is True

    def test_cursor_applies_filter(self):
        now = datetime.now(timezone.utc)
        cursor = encode_cursor(now, uuid4())

        items = self._make_items(2)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = items

        # Create a fake column class that supports comparison operators
        class FakeCol:
            def __lt__(self, other): return "lt_expr"
            def __eq__(self, other): return "eq_expr"
            def desc(self): return self

        mock_model = MagicMock()
        mock_model.created_at = FakeCol()
        mock_model.id = FakeCol()

        # Patch or_ and and_ to avoid SQLAlchemy coercion validation
        with patch("utils.cursor.or_", return_value="filter_expr"):
            with patch("utils.cursor.and_", return_value="and_expr"):
                result_items, next_cursor, has_more = apply_cursor(
                    mock_query, mock_model, cursor, limit=10
                )
        mock_query.filter.assert_called_once()
        assert len(result_items) == 2

    def test_empty_result(self):
        mock_query = MagicMock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = []

        result_items, next_cursor, has_more = apply_cursor(
            mock_query, MagicMock(), None, limit=10
        )
        assert len(result_items) == 0
        assert next_cursor is None
        assert has_more is False

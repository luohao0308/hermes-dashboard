"""Cursor-based pagination helpers.

Cursor = base64-encoded JSON {"created_at": ISO string, "id": UUID string}.
The query uses (created_at, id) < (cursor.created_at, cursor.id) for
descending order, which gives stable keyset pagination that doesn't
miss or duplicate rows when new items are inserted between pages.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query


def encode_cursor(created_at: datetime, row_id: UUID) -> str:
    """Encode a cursor from created_at timestamp and row id."""
    payload = {
        "created_at": created_at.isoformat(),
        "id": str(row_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode a cursor string into {"created_at": datetime, "id": UUID}.

    Raises ValueError if the cursor is malformed.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor))
        return {
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "id": UUID(payload["id"]),
        }
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid cursor: {exc}") from exc


def apply_cursor(
    query: Query,
    model: Any,
    cursor: Optional[str],
    limit: int,
) -> tuple[list, Optional[str], bool]:
    """Apply cursor pagination to a SQLAlchemy query.

    Assumes the query already has filters applied and should be ordered
    by (created_at DESC, id DESC).

    Args:
        query: SQLAlchemy query with filters already applied.
        model: The ORM model class (must have created_at and id columns).
        cursor: Optional base64 cursor string from a previous page.
        limit: Number of items to return.

    Returns:
        (items, next_cursor, has_more) tuple.
    """
    if cursor is not None:
        decoded = decode_cursor(cursor)
        query = query.filter(
            or_(
                model.created_at < decoded["created_at"],
                and_(
                    model.created_at == decoded["created_at"],
                    model.id < decoded["id"],
                ),
            )
        )

    # Fetch one extra to determine if there are more pages
    items = query.order_by(
        model.created_at.desc(), model.id.desc()
    ).limit(limit + 1).all()

    has_more = len(items) > limit
    items = items[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return items, next_cursor, has_more

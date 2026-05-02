"""PostgreSQL-backed chat repository.

Manages chat sessions and messages using dedicated ORM models.
Uses per-operation sessions to avoid long-lived session accumulation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.chat import ChatSessionRow, ChatMessageRow
from repositories.base import ChatRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PgChatRepository(ChatRepository):
    """PostgreSQL implementation of ChatRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _run_in_session(self, fn, *, read_only: bool = False):
        db = self._session_factory()
        try:
            result = fn(db)
            if not read_only:
                db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_session(
        self,
        agent_id: str = "main",
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict[str, Any]:
        def _create(db: Session) -> dict[str, Any]:
            row = ChatSessionRow(
                id=uuid.uuid4(),
                agent_id=agent_id,
                title=title,
                linked_session_id=linked_session_id,
                terminal_session_id=terminal_session_id,
            )
            db.add(row)
            db.flush()
            return {
                "session_id": str(row.id), "agent_id": row.agent_id,
                "title": row.title, "linked_session_id": row.linked_session_id,
                "terminal_session_id": row.terminal_session_id,
                "created_at": row.created_at.isoformat(), "message_count": 0,
            }
        return self._run_in_session(_create)

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        def _get(db: Session) -> Optional[dict[str, Any]]:
            try:
                pk = uuid.UUID(session_id)
            except ValueError:
                return None
            row = db.get(ChatSessionRow, pk)
            if not row:
                return None
            msg_count = db.query(func.count(ChatMessageRow.id)).filter(ChatMessageRow.session_id == pk).scalar() or 0
            return {
                "session_id": str(row.id), "agent_id": row.agent_id,
                "title": row.title, "linked_session_id": row.linked_session_id,
                "terminal_session_id": row.terminal_session_id,
                "created_at": row.created_at.isoformat(), "message_count": msg_count,
            }
        return self._run_in_session(_get, read_only=True)

    def close_session(self, session_id: str) -> bool:
        def _close(db: Session) -> bool:
            try:
                pk = uuid.UUID(session_id)
            except ValueError:
                return False
            row = db.get(ChatSessionRow, pk)
            if not row:
                return False
            db.query(ChatMessageRow).filter(ChatMessageRow.session_id == pk).delete()
            db.delete(row)
            return True
        return self._run_in_session(_close)

    def update_session_agent(self, session_id: str, agent_id: str) -> bool:
        def _update(db: Session) -> bool:
            try:
                pk = uuid.UUID(session_id)
            except ValueError:
                return False
            row = db.get(ChatSessionRow, pk)
            if not row:
                return False
            row.agent_id = agent_id
            return True
        return self._run_in_session(_update)

    def update_session_context(
        self,
        session_id: str,
        title: Optional[str] = None,
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
    ) -> bool:
        def _update(db: Session) -> bool:
            try:
                pk = uuid.UUID(session_id)
            except ValueError:
                return False
            row = db.get(ChatSessionRow, pk)
            if not row:
                return False
            if title is not None:
                row.title = title
            if linked_session_id is not None:
                row.linked_session_id = linked_session_id
            if terminal_session_id is not None:
                row.terminal_session_id = terminal_session_id
            return True
        return self._run_in_session(_update)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        def _append(db: Session) -> Optional[dict[str, Any]]:
            try:
                pk = uuid.UUID(session_id)
            except ValueError:
                return None
            session_row = db.get(ChatSessionRow, pk)
            if not session_row:
                return None
            ts = _now()
            if timestamp:
                try:
                    ts = datetime.fromisoformat(timestamp)
                except ValueError:
                    pass
            msg = ChatMessageRow(
                id=uuid.uuid4(), session_id=pk, role=role,
                content=content, timestamp=ts, agent_name=agent_name,
            )
            db.add(msg)
            return {
                "role": msg.role, "content": msg.content,
                "timestamp": msg.timestamp.isoformat(), "agent_name": msg.agent_name,
            }
        return self._run_in_session(_append)

    def list_sessions(self) -> list[dict[str, Any]]:
        def _list(db: Session) -> list[dict[str, Any]]:
            sessions = db.query(ChatSessionRow).order_by(ChatSessionRow.created_at.desc()).all()
            result = []
            for row in sessions:
                msg_count = db.query(func.count(ChatMessageRow.id)).filter(ChatMessageRow.session_id == row.id).scalar() or 0
                result.append({
                    "session_id": str(row.id), "agent_id": row.agent_id,
                    "title": row.title, "linked_session_id": row.linked_session_id,
                    "terminal_session_id": row.terminal_session_id,
                    "created_at": row.created_at.isoformat(), "message_count": msg_count,
                })
            return result
        return self._run_in_session(_list, read_only=True)

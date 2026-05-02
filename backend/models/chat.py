"""Chat session and message ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class ChatSessionRow(UUIDPrimaryKeyMixin, Base):
    """ORM model for the chat_sessions table."""

    __tablename__ = "chat_sessions"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linked_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    terminal_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChatMessageRow(UUIDPrimaryKeyMixin, Base):
    """ORM model for the chat_messages table."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

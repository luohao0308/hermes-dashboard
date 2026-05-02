"""Task model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    node_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    task_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    depends_on_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

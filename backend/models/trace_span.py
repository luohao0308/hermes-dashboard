"""TraceSpan model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class TraceSpan(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "trace_spans"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    parent_span_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trace_spans.id"), nullable=True
    )
    span_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

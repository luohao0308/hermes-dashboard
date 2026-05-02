"""Run model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Run(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runs"

    runtime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runtimes.id"), nullable=False
    )
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

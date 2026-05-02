"""Approval model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class Approval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approvals"

    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True, index=True
    )
    tool_call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tool_calls.id"), nullable=True
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

"""ToolCall model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class ToolCall(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tool_calls"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True
    )
    span_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trace_spans.id"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="read")
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="allow")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    input_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

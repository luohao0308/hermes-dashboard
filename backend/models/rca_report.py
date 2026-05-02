"""RCAReport model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class RCAReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rca_reports"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True
    )
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_actions_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

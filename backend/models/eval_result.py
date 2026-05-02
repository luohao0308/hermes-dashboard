"""EvalResult model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class EvalResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eval_results"

    runtime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runtimes.id"), nullable=False, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True
    )
    config_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sample_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

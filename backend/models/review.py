"""Review ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class ReviewRow(UUIDPrimaryKeyMixin, Base):
    """ORM model for the reviews table."""

    __tablename__ = "reviews"

    repo: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[str] = mapped_column(String(1000), nullable=False)
    pr_author: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    findings_json: Mapped[str] = mapped_column(Text, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0.0)
    models_used_json: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    completed_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""API usage and budget ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class ApiUsageRow(UUIDPrimaryKeyMixin, Base):
    """ORM model for the api_usage table."""

    __tablename__ = "api_usage"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    review_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)


class BudgetLimitRow(UUIDPrimaryKeyMixin, Base):
    """ORM model for the budget_limits table."""

    __tablename__ = "budget_limits"

    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    limit_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    alert_threshold: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=0.8)

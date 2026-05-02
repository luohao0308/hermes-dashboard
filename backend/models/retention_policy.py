"""RetentionPolicy model for data lifecycle management (v3.0)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class RetentionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retention_policies"

    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="run, trace_span, approval, audit_log, eval_result"
    )
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

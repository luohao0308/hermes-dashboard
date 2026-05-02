"""Runbook model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Runbook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runbooks"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, index=True
    )
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

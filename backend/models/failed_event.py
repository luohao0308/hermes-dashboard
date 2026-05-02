"""FailedEvent model — stores connector events that failed ingestion."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class FailedEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "failed_events"

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connector_configs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

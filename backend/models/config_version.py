"""ConfigVersion model — versioned configuration snapshots."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class ConfigVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "config_versions"

    runtime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runtimes.id"), nullable=False, index=True
    )
    config_type: Mapped[str] = mapped_column(String(50), nullable=False, default="workflow")
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evaluation_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

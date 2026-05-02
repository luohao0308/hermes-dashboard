"""ConnectorConfig model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class ConnectorConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connector_configs"

    runtime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runtimes.id"), nullable=False, index=True
    )
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    secret_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    environment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=True, index=True
    )

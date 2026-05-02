"""Runtime model."""

import uuid
from datetime import datetime
from typing import Optional

import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Runtime(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runtimes"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    environment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=True, index=True
    )

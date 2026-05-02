"""User model for multi-tenancy and RBAC (v3.0)."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    sso_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sso_external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    team: Mapped[Optional["Team"]] = relationship(back_populates="users", lazy="selectin")

"""Environment model for dev/staging/prod isolation (v3.0)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class Environment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "environments"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )

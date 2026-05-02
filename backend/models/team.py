"""Team model for multi-tenancy (v3.0)."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class Team(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="team", lazy="selectin")

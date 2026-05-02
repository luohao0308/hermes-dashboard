"""WorkflowVersionHistory model — snapshots workflow definitions before update/rollback."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.base import UUIDPrimaryKeyMixin


class WorkflowVersionHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_version_history"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nodes_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    edges_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_concurrent_tasks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

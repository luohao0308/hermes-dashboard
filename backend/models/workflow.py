"""Workflow definition, node, and edge models for DAG orchestration (v2.0)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.base import UUIDPrimaryKeyMixin, TimestampMixin


class WorkflowDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_definitions"

    runtime_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runtimes.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_concurrent_tasks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    environment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=True, index=True
    )
    is_reusable: Mapped[bool] = mapped_column(default=False, nullable=False)

    nodes: Mapped[list["WorkflowNode"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", lazy="selectin",
        foreign_keys="WorkflowNode.workflow_id"
    )
    edges: Mapped[list["WorkflowEdge"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkflowNode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_nodes"
    __table_args__ = (
        UniqueConstraint("workflow_id", "node_id", name="uq_workflow_node_id"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, default="action")
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    retry_policy: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approval_timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    child_workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["WorkflowDefinition"] = relationship(
        back_populates="nodes", foreign_keys=[workflow_id]
    )
    child_workflow: Mapped[Optional["WorkflowDefinition"]] = relationship(
        foreign_keys=[child_workflow_id]
    )


class WorkflowEdge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_edges"
    __table_args__ = (
        UniqueConstraint("workflow_id", "from_node", "to_node", name="uq_workflow_edge"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    from_node: Mapped[str] = mapped_column(String(100), nullable=False)
    to_node: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    workflow: Mapped["WorkflowDefinition"] = relationship(back_populates="edges")

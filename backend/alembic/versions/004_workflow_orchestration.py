"""Add workflow orchestration tables (v2.0).

Revision ID: 004
Revises: 003
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_definitions_runtime_id", "workflow_definitions", ["runtime_id"])

    op.create_table(
        "workflow_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False, server_default="action"),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("retry_policy", postgresql.JSONB, nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_nodes_workflow_id", "workflow_nodes", ["workflow_id"])
    op.create_unique_constraint("uq_workflow_node_id", "workflow_nodes", ["workflow_id", "node_id"])

    op.create_table(
        "workflow_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_node", sa.String(100), nullable=False),
        sa.Column("to_node", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_edges_workflow_id", "workflow_edges", ["workflow_id"])
    op.create_unique_constraint("uq_workflow_edge", "workflow_edges", ["workflow_id", "from_node", "to_node"])

    op.add_column("runs", sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_definitions.id"), nullable=True))
    op.create_index("ix_runs_workflow_id", "runs", ["workflow_id"])

    op.add_column("tasks", sa.Column("node_id", sa.String(100), nullable=True))
    op.add_column("tasks", sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"))
    op.create_index("ix_tasks_node_id", "tasks", ["node_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_node_id", table_name="tasks")
    op.drop_column("tasks", "retry_count")
    op.drop_column("tasks", "node_id")
    op.drop_index("ix_runs_workflow_id", table_name="runs")
    op.drop_column("runs", "workflow_id")
    op.drop_index("ix_workflow_edges_workflow_id", table_name="workflow_edges")
    op.drop_constraint("uq_workflow_edge", "workflow_edges", type_="unique")
    op.drop_table("workflow_edges")
    op.drop_index("ix_workflow_nodes_workflow_id", table_name="workflow_nodes")
    op.drop_constraint("uq_workflow_node_id", "workflow_nodes", type_="unique")
    op.drop_table("workflow_nodes")
    op.drop_index("ix_workflow_definitions_runtime_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")

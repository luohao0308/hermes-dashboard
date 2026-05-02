"""Add durable execution columns (v2.1).

Revision ID: 006
Revises: 005
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Task execution state for worker coordination
    op.add_column("tasks", sa.Column("locked_by", sa.String(100), nullable=True))
    op.add_column("tasks", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_status_locked", "tasks", ["status", "locked_by"])

    # Workflow-level timeout and concurrency
    op.add_column(
        "workflow_definitions",
        sa.Column("timeout_seconds", sa.Integer, nullable=True),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("max_concurrent_tasks", sa.Integer, nullable=True),
    )

    # Approval timeout on workflow nodes
    op.add_column(
        "workflow_nodes",
        sa.Column("approval_timeout_seconds", sa.Integer, nullable=True),
    )

    # Dead-letter status is handled via task.status = 'dead_letter'
    # No separate table needed — just an index for querying
    op.create_index("ix_tasks_status", "tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_column("workflow_nodes", "approval_timeout_seconds")
    op.drop_column("workflow_definitions", "max_concurrent_tasks")
    op.drop_column("workflow_definitions", "timeout_seconds")
    op.drop_index("ix_tasks_status_locked", table_name="tasks")
    op.drop_column("tasks", "next_retry_at")
    op.drop_column("tasks", "locked_at")
    op.drop_column("tasks", "locked_by")

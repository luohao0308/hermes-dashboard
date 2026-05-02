"""Add task_id and context_json to approvals (v2.0 stabilization).

Revision ID: 005
Revises: 004
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "approvals",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
    )
    op.create_index("ix_approvals_task_id", "approvals", ["task_id"])
    op.add_column(
        "approvals",
        sa.Column("context_json", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approvals", "context_json")
    op.drop_index("ix_approvals_task_id", table_name="approvals")
    op.drop_column("approvals", "task_id")

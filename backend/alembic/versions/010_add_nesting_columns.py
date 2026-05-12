"""Add nesting columns for workflow orchestration.

Revision ID: 010
Revises: 009
Create Date: 2026-05-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # Add is_reusable to workflow_definitions
    op.add_column(
        "workflow_definitions",
        sa.Column("is_reusable", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Add child_workflow_id to workflow_nodes
    op.add_column(
        "workflow_nodes",
        sa.Column(
            "child_workflow_id",
            sa.String(36),
            nullable=True,
        ),
    )
    op.create_index("ix_workflow_nodes_child_workflow_id", "workflow_nodes", ["child_workflow_id"])

    # Add parent_run_id to runs
    op.add_column(
        "runs",
        sa.Column(
            "parent_run_id",
            sa.String(36),
            nullable=True,
        ),
    )
    op.create_index("ix_runs_parent_run_id", "runs", ["parent_run_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_parent_run_id", table_name="runs")
    op.drop_column("runs", "parent_run_id")

    op.drop_index("ix_workflow_nodes_child_workflow_id", table_name="workflow_nodes")
    op.drop_column("workflow_nodes", "child_workflow_id")

    op.drop_column("workflow_definitions", "is_reusable")

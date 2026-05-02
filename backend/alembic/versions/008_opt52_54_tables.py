"""OPT-52/54: failed_events and workflow_version_history tables.

Revision ID: 008
Revises: 007
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Failed Events (OPT-54) ---
    op.create_table(
        "failed_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connector_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=True),
        sa.Column("run_id", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_failed_events_connector_id", "failed_events", ["connector_id"])
    op.create_index("ix_failed_events_event_id", "failed_events", ["event_id"])

    # --- Workflow Version History (OPT-52) ---
    op.create_table(
        "workflow_version_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("nodes_json", postgresql.JSONB, nullable=True),
        sa.Column("edges_json", postgresql.JSONB, nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=True),
        sa.Column("max_concurrent_tasks", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_workflow_version_history_workflow_id",
        "workflow_version_history",
        ["workflow_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_version_history_workflow_id",
        table_name="workflow_version_history",
    )
    op.drop_table("workflow_version_history")

    op.drop_index("ix_failed_events_event_id", table_name="failed_events")
    op.drop_index("ix_failed_events_connector_id", table_name="failed_events")
    op.drop_table("failed_events")

"""Add config_versions table for Eval / Config Optimization (v1.4).

Revision ID: 003
Revises: 002
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "config_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("config_type", sa.String(50), nullable=False, server_default="workflow"),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("config_json", postgresql.JSONB, nullable=True),
        sa.Column("evaluation_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("requires_approval", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_config_versions_runtime_id", "config_versions", ["runtime_id"])
    op.create_index("ix_config_versions_runtime_type", "config_versions", ["runtime_id", "config_type"])


def downgrade() -> None:
    op.drop_index("ix_config_versions_runtime_type", table_name="config_versions")
    op.drop_index("ix_config_versions_runtime_id", table_name="config_versions")
    op.drop_table("config_versions")

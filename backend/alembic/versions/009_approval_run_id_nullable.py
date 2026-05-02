"""make approval run_id nullable

Revision ID: 009
Revises: 008
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "approvals",
        "run_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "approvals",
        "run_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

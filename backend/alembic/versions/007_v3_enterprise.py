"""v3.0 Enterprise: users, teams, environments, retention policies.

Revision ID: 007
Revises: 006
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Teams ---
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("sso_provider", sa.String(50), nullable=True),
        sa.Column("sso_external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_team_id", "users", ["team_id"])

    # --- Environments ---
    op.create_table(
        "environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Seed default environments
    op.execute(
        "INSERT INTO environments (id, name, description, is_default) VALUES "
        "(gen_random_uuid(), 'dev', 'Development environment', true), "
        "(gen_random_uuid(), 'staging', 'Staging environment', false), "
        "(gen_random_uuid(), 'prod', 'Production environment', false)"
    )

    # --- Retention Policies ---
    op.create_table(
        "retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Environment FKs on existing tables ---
    op.add_column(
        "runtimes",
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id"), nullable=True),
    )
    op.create_index("ix_runtimes_environment_id", "runtimes", ["environment_id"])

    op.add_column(
        "connector_configs",
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id"), nullable=True),
    )
    op.create_index("ix_connector_configs_environment_id", "connector_configs", ["environment_id"])

    op.add_column(
        "workflow_definitions",
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id"), nullable=True),
    )
    op.create_index("ix_workflow_definitions_environment_id", "workflow_definitions", ["environment_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_definitions_environment_id", table_name="workflow_definitions")
    op.drop_column("workflow_definitions", "environment_id")

    op.drop_index("ix_connector_configs_environment_id", table_name="connector_configs")
    op.drop_column("connector_configs", "environment_id")

    op.drop_index("ix_runtimes_environment_id", table_name="runtimes")
    op.drop_column("runtimes", "environment_id")

    op.drop_table("retention_policies")
    op.drop_table("environments")
    op.drop_index("ix_users_team_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("teams")

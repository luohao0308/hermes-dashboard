"""Add repository-layer tables: reviews, api_usage, budget_limits, chat_sessions, chat_messages.

Revision ID: 002
Revises: 001
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reviews
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repo", sa.String(500), nullable=False),
        sa.Column("pr_number", sa.Integer, nullable=False),
        sa.Column("pr_title", sa.String(1000), nullable=False),
        sa.Column("pr_author", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("findings_json", sa.Text, nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("models_used_json", sa.Text, nullable=False),
        sa.Column("started_at", sa.String(50), nullable=False),
        sa.Column("completed_at", sa.String(50), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reviews_repo", "reviews", ["repo"])
    op.create_index("ix_reviews_status", "reviews", ["status"])
    op.create_index("ix_reviews_started_at", "reviews", ["started_at"])

    # api_usage
    op.create_table(
        "api_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("review_id", sa.String(255), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
    )
    op.create_index("ix_api_usage_timestamp", "api_usage", ["timestamp"])
    op.create_index("ix_api_usage_provider", "api_usage", ["provider"])
    op.create_index("ix_api_usage_review_id", "api_usage", ["review_id"])

    # budget_limits
    op.create_table(
        "budget_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("limit_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("alert_threshold", sa.Numeric(4, 2), nullable=False, server_default="0.8"),
    )

    # chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("linked_session_id", sa.String(255), nullable=True),
        sa.Column("terminal_session_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_name", sa.String(255), nullable=True),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("budget_limits")
    op.drop_table("api_usage")
    op.drop_table("reviews")

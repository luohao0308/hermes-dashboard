"""Initial schema — all core domain tables.

Revision ID: 001
Revises: None
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # runtimes
    op.create_table(
        "runtimes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("config_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # runs
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runs_runtime_id", "runs", ["runtime_id"])
    op.create_index("ix_runs_status", "runs", ["status"])

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("parent_task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("task_type", sa.String(50), nullable=True),
        sa.Column("depends_on_json", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tasks_run_id", "tasks", ["run_id"])

    # trace_spans
    op.create_table(
        "trace_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("parent_span_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace_spans.id"), nullable=True),
        sa.Column("span_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("agent_name", sa.String(255), nullable=True),
        sa.Column("model_name", sa.String(255), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trace_spans_run_id", "trace_spans", ["run_id"])
    op.create_index("ix_trace_spans_span_type", "trace_spans", ["span_type"])

    # tool_calls
    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("span_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace_spans.id"), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="read"),
        sa.Column("decision", sa.String(20), nullable=False, server_default="allow"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_json", postgresql.JSONB, nullable=True),
        sa.Column("output_json", postgresql.JSONB, nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tool_calls_run_id", "tool_calls", ["run_id"])

    # approvals
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("tool_call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tool_calls.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_note", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    # artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("span_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace_spans.id"), nullable=True),
        sa.Column("artifact_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("content_json", postgresql.JSONB, nullable=True),
        sa.Column("storage_url", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])

    # rca_reports
    op.create_table(
        "rca_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB, nullable=True),
        sa.Column("next_actions_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rca_reports_run_id", "rca_reports", ["run_id"])

    # runbooks
    op.create_table(
        "runbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("steps_json", postgresql.JSONB, nullable=True),
        sa.Column("markdown", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runbooks_run_id", "runbooks", ["run_id"])

    # eval_results
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("config_version", sa.String(100), nullable=True),
        sa.Column("sample_name", sa.String(255), nullable=True),
        sa.Column("success", sa.Boolean, nullable=True),
        sa.Column("score", sa.Numeric(8, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_eval_results_runtime_id", "eval_results", ["runtime_id"])

    # connector_configs
    op.create_table(
        "connector_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config_json", postgresql.JSONB, nullable=True),
        sa.Column("secret_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_configs_runtime_id", "connector_configs", ["runtime_id"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("before_json", postgresql.JSONB, nullable=True),
        sa.Column("after_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("connector_configs")
    op.drop_table("eval_results")
    op.drop_table("runbooks")
    op.drop_table("rca_reports")
    op.drop_table("artifacts")
    op.drop_table("approvals")
    op.drop_table("tool_calls")
    op.drop_table("trace_spans")
    op.drop_table("tasks")
    op.drop_table("runs")
    op.drop_table("runtimes")

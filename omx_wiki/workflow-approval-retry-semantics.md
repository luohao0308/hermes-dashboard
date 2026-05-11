# Workflow Approval Retry Semantics

Category: decision
Tags: workflow, approval, retry, scheduler, verification
Updated: 2026-05-11T15:35:00Z

## Context

Workflow approval nodes can fail by operator rejection. A rejected approval must not be auto-retried by the scheduler's ordinary task retry policy, because restart should require explicit `/retry` on the failed run.

## Decision

- Approval decisions are consumed per task attempt.
- The scheduler identifies a rejected approval by querying the current attempt's `Approval` decision, not by matching `Task.error_summary` text.
- `/retry` for approval tasks supersedes only pending approval rows that could interfere with the retry attempt.
- Historical resolved approval decisions remain immutable; old rejected/approved rows are not rewritten to `superseded`.
- When a terminal task failure blocks pending downstream tasks, descendants are marked `cancelled` with an error summary describing the failed dependency.

## Implementation Anchors

- `backend/routers/workflows.py`
  - `_latest_approval_decision_for_attempt`
  - `_is_rejected_approval_failure`
  - `_supersede_pending_task_approvals`
  - `_cancel_blocked_descendants`
  - `retry_workflow_run`
- `backend/tests/test_workflows_api.py`
  - `test_retry_exhausted_cancels_blocked_downstream_tasks`
  - `test_rejected_approval_cancels_blocked_downstream_tasks`
  - `test_rejected_approval_requires_explicit_retry_and_ignores_stale_decision`

## Verification

Executed with backend venv and a temporary PostgreSQL database that was dropped after the run:

```text
backend/venv/bin/python -m pytest \
  backend/tests/test_workflows_api.py \
  backend/tests/test_durable_execution.py \
  -v
```

Result: 43 passed.

Also verified:

- `py_compile` for changed backend files passed.
- `git diff --check` for changed backend files passed.

## Remaining Watch Items

- `cancelled` currently represents both operator cancellation and dependency-pruned skip. A future state such as `skipped` or structured `cancel_reason_code` would make this contract clearer.
- Approval status constants currently live in the workflow router. If approval semantics continue to expand, move them into an approval/domain layer or enum.

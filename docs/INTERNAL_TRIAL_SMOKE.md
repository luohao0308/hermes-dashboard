# Internal Trial Smoke

Use this checklist before sharing the workflow/worker loop with an internal team.

## Services

1. Start Postgres:
   `ENCRYPTION_KEY=test-key docker compose up -d postgres`
2. Run migrations or start the normal backend stack.
3. Start the backend API.
4. Start the frontend.
5. Start the workflow worker:
   `cd backend && DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow venv/bin/python -m workers.workflow_worker --poll-interval 2`

## Workflow Definition

1. Open `#/workflows`.
2. Create a workflow with the JSON editor.
3. Use `examples/workflows/internal_trial_workflow.json` as the node/edge reference.
4. Set `runtime_id` to an existing runtime id.
5. Save, then reopen the workflow and edit a title or retry policy.

## Run Controls

1. Start a run from Workflow Detail.
2. Confirm the run appears in the run table.
3. Pause the run.
4. Confirm running tasks return to pending and worker locks clear.
5. Resume the run.
6. Fail a running task and retry the failed run.
7. Start a fresh run and cancel it.

## Worker Status

1. Open `#/system`.
2. Confirm worker status, heartbeat age, worker id, pid, and version are visible when heartbeat files exist.
3. Stop the worker and refresh after the stale interval to confirm stale/degraded status.

## Run Observability

1. Select a workflow run.
2. Confirm the task table shows node, status, retry count, worker lock owner, next retry time, duration, and error summary.
3. For failures, confirm the error appears without opening database tools.

## Verification Commands

```bash
python3 -m py_compile backend/routers/workflows.py backend/workers/workflow_worker.py backend/tests/test_workflows_api.py backend/tests/test_example_workflows.py
cd frontend && npm run test:unit -- --run tests/test_workflow_components.spec.ts
cd frontend && npx vue-tsc --noEmit
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test venv/bin/python -m pytest tests/test_workflows_api.py tests/test_durable_execution.py -v
backend/venv/bin/python -m pytest backend/tests/test_example_workflows.py -v
```

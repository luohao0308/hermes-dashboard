# Operations Guide

## Runtime Requirements

- Python 3.9+
- Node.js 20+
- PostgreSQL 14+ recommended, PostgreSQL 16 used by local Docker Compose
- `ENCRYPTION_KEY` required when `ENVIRONMENT=production`

## Local Development

```bash
cp .env.example .env
docker compose up -d postgres

cd backend
alembic upgrade head

cd ..
./start.sh
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

## Database Operations

Run migrations:

```bash
cd backend
alembic upgrade head
```

Create a migration:

```bash
cd backend
alembic revision --autogenerate -m "description"
```

Check current migration:

```bash
cd backend
alembic current
```

Rollback one migration:

```bash
cd backend
alembic downgrade -1
```

## Background Workers

Workflow scheduler:

```bash
cd backend
python -m workers.workflow_worker --poll-interval 2 --stale-lock-seconds 300
```

Retention worker:

```bash
cd backend
python -m workers.retention_worker --dry-run
python -m workers.retention_worker
```

## Security Operations

Generate encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Production must set:

```bash
ENVIRONMENT=production
ENCRYPTION_KEY=<fernet-key>
DATABASE_URL=<postgresql-url>
```

Provider connection tests that require hosted model APIs also need their
provider-specific keys in the runtime environment. For example, Xiaomi Mimo /
MiniMax providers require:

```bash
MINIMAX_API_KEY=<provider-api-key>
```

If `test-mimo` is registered without `MINIMAX_API_KEY`, the Provider connection
test is expected to fail with a clear missing/unavailable key error.

Connector webhooks should use HMAC-SHA256 signatures documented in `docs/CONNECTOR_PROTOCOL.md`.

## Verification

Frontend:

```bash
cd frontend
npx vue-tsc --noEmit
npm run test:unit
npm run build
```

Backend without PostgreSQL integration database:

```bash
cd backend
python -m pytest tests/ -v
```

Backend with PostgreSQL integration database:

```bash
createdb ai_workflow_test
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_test \
  python -m pytest tests/ -v
```

Migration smoke test:

```bash
createdb ai_workflow_migration_check
cd backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_workflow_migration_check \
  alembic upgrade head
```

## Health Checks

| Component | Check |
|---|---|
| API | `GET /health` returns `status: healthy` |
| SSE | `GET /sse` connects |
| PostgreSQL | `/health` → `database.status == "connected"` and `migration_version` present |
| Scheduler worker | `/health` → `workers["scheduler-worker"].status == "alive"` |
| Retention worker | `/health` → `workers["retention-worker"].status == "alive"` |
| Connector ingestion | signed test event accepted and audit logged |
| Metrics | `GET /api/metrics` returns run/approval/task/worker stats |

### Worker Heartbeat Files

Workers write UTC ISO-8601 timestamps to `/tmp` after each cycle. The `/health` and `/api/metrics` endpoints read these files to determine worker liveness.

| Worker | Heartbeat File Path | Config Env Var |
|---|---|---|
| Scheduler worker | `/tmp/hermes_scheduler_worker_heartbeat` | `SCHEDULER_HEARTBEAT_PATH` |
| Retention worker | `/tmp/hermes_retention_worker_heartbeat` | `RETENTION_HEARTBEAT_PATH` |

Stale threshold: `WORKER_HEARTBEAT_STALE_SECONDS` (default: 120).

Heartbeat status classification:

| Status | Meaning |
|---|---|
| `alive` | File exists and was written less than 120 seconds ago |
| `stale` | File exists but was written 120+ seconds ago |
| `unknown` / `missing` | File does not exist (worker never started or was cleaned up) |
| `error` | File exists but could not be read (permissions, etc.) |

The `/health` endpoint returns `status: degraded` when `database.status != "connected"` or any worker has `status: "error"`.

## Data Storage

Primary runtime data belongs in PostgreSQL.

Legacy SQLite files may still exist under `backend/data/` for compatibility with old session/chat/cost/review flows. New platform features must not introduce new SQLite primary stores.

## Backup and Restore

**Detailed runbook:** [BACKUP_RESTORE_RUNBOOK.md](BACKUP_RESTORE_RUNBOOK.md)

Quick backup:

```bash
pg_dump "$DATABASE_URL" --format=custom --compress=9 --file=backup_$(date +%Y%m%d).dump
```

Quick restore:

```bash
pg_restore "$DATABASE_URL" --no-owner backup.dump
```

Before production migration:

1. Take a fresh backup.
2. Run `alembic upgrade head` in staging.
3. Run smoke tests.
4. Apply migration in production.
5. Verify API, workers, connector ingestion, and approval flow.

## Known Operational Gaps

- The scheduler is PostgreSQL-backed but still lightweight; no external queue is used.
- Xiaomi Mimo / MiniMax provider checks require `MINIMAX_API_KEY`; Docker Compose does not ship a real API key by default.
- **Test status:** Both local and Docker suites pass 305/305 (172 skipped, 0 failed). CI/release acceptance uses the same test suite.

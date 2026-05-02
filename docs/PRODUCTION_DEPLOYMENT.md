# Production Deployment Guide

## Purpose

This guide describes a production-oriented deployment for the AI Workflow Control Plane.

## Topology

```
                    ┌─────────────────┐
                    │  Reverse Proxy  │
                    │  (nginx/caddy)  │
                    │  TLS + compress │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────┐
     │  Frontend SPA  │ │  API (WS)  │ │  Static      │
     │  (nginx)       │ │  uvicorn   │ │  Assets      │
     └────────────────┘ └─────┬──────┘ └──────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
             ┌──────▼───┐ ┌──▼───────┐ ┌▼─────────────┐
             │ PostgreSQL│ │ Scheduler│ │ Retention    │
             │  (primary)│ │  Worker  │ │ Worker       │
             └──────────┘ └──────────┘ └──────────────┘
```

All services communicate over an internal Docker network. Only the reverse proxy exposes ports 80/443.

## Required Services

| Service | Purpose |
|---|---|
| web | FastAPI API and frontend hosting/reverse proxy target |
| postgres | Primary database |
| scheduler-worker | Durable workflow execution |
| retention-worker | Data lifecycle cleanup |
| reverse-proxy | TLS, routing, compression, optional static serving |

## Required Environment Variables

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/ai_workflow
ENCRYPTION_KEY=<fernet-key>
VITE_API_BASE_URL=https://your-domain.example
VITE_WS_BASE_URL=wss://your-domain.example
```

Generate encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Never rotate `ENCRYPTION_KEY` without a secret rotation plan. Existing encrypted connector secrets depend on it.

## Production Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ai_workflow
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/ai_workflow
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  scheduler-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: ["python", "-m", "workers.workflow_worker", "--poll-interval", "2", "--stale-lock-seconds", "300"]
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/ai_workflow
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  retention-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: ["python", "-m", "workers.retention_worker", "--poll-interval", "3600"]
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/ai_workflow
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
```

Create a `.env` file (never commit):

```bash
DB_USER=ai_workflow
DB_PASSWORD=<strong-password>
ENCRYPTION_KEY=<fernet-key>
```

## Deployment Steps

1. Provision PostgreSQL.
2. Set production environment variables.
3. Build frontend.
4. Install backend dependencies.
5. Run database migrations.
6. Start web process.
7. Start scheduler worker.
8. Start retention worker in dry-run mode first.
9. Run smoke tests.
10. Enable retention worker production mode after confirming dry-run output.

## Commands

Run migrations:

```bash
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" alembic upgrade head
```

Start API:

```bash
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  uvicorn main:app --host 0.0.0.0 --port 8000
```

Start scheduler worker:

```bash
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  python -m workers.workflow_worker --poll-interval 2 --stale-lock-seconds 300
```

Preview retention:

```bash
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  python -m workers.retention_worker --dry-run
```

Run retention:

```bash
cd backend
ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  python -m workers.retention_worker --poll-interval 3600
```

## Backup and Restore

**Detailed runbook:** [BACKUP_RESTORE_RUNBOOK.md](BACKUP_RESTORE_RUNBOOK.md)

Backup before every migration:

```bash
pg_dump "$DATABASE_URL" --format=custom --compress=9 --file="backup-$(date +%Y%m%d-%H%M%S).dump"
```

Restore:

```bash
pg_restore "$DATABASE_URL" --no-owner backup.dump
```

**Important:** Always back up `ENCRYPTION_KEY` separately. Connector secrets are encrypted with this key and cannot be recovered without it.

## Smoke Test

After deployment:

1. `GET /health` returns healthy.
2. Create or list runtimes.
3. Create run and append span.
4. Open Runs page and verify trace renders.
5. Create connector with masked secret response.
6. Ingest signed connector event.
7. Start workflow run.
8. Scheduler worker advances tasks.
9. Approval appears in Approval Inbox.
10. Generate RCA and Runbook.
11. Run eval summary.
12. Verify audit log rows are written for mutations.

## Health Matrix

| Component | Failure Signal | Action |
|---|---|---|
| API | `/health` fails | restart API, check env and DB |
| PostgreSQL | migration or DB session failure | verify connection string and DB availability |
| Scheduler worker | tasks stay pending | inspect worker logs and stale locks |
| Retention worker | no audit for cleanup | run dry-run and inspect retention policies |
| Connector ingestion | event.error audit logs | verify signature, timestamp and payload schema |

## Rollback

Application rollback:

1. Stop workers first.
2. Deploy previous app version.
3. If migration is incompatible, restore DB backup or run documented Alembic downgrade.
4. Restart API and workers.
5. Run smoke test.

Database rollback:

- Prefer backup restore for major releases.
- Use `alembic downgrade -1` only if the migration explicitly supports rollback without data loss.

## ENCRYPTION_KEY Rotation

Connector secrets are encrypted with Fernet using `ENCRYPTION_KEY`. Rotating the key requires a dual-key migration.

### Rotation Procedure

1. **Generate new key:**

   ```bash
   NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   ```

2. **Add `ENCRYPTION_KEY_PREVIOUS` env var** with the old key value. The secret manager will try the previous key for decryption if the primary key fails.

3. **Deploy with both keys set:**

   ```bash
   ENCRYPTION_KEY=$NEW_KEY
   ENCRYPTION_KEY_PREVIOUS=$OLD_KEY
   ```

4. **Re-encrypt existing secrets** (run once):

   ```bash
   cd backend
   ENVIRONMENT=production DATABASE_URL="$DATABASE_URL" \
     ENCRYPTION_KEY="$NEW_KEY" ENCRYPTION_KEY_PREVIOUS="$OLD_KEY" \
     python -m scripts.rotate_secrets
   ```

5. **Verify** all connectors can still read their secrets.

6. **Remove `ENCRYPTION_KEY_PREVIOUS`** from environment after confirming no decryption failures in logs.

### Key Rotation Checklist

- [ ] Backup database before rotation
- [ ] Generate new Fernet key
- [ ] Set both `ENCRYPTION_KEY` and `ENCRYPTION_KEY_PREVIOUS`
- [ ] Deploy with dual-key config
- [ ] Run re-encryption script
- [ ] Verify connector reads succeed
- [ ] Monitor logs for decryption errors (24h)
- [ ] Remove old key from environment
- [ ] Update secrets manager / vault

## Current Production Gaps

- Real auth/OIDC is not implemented; `X-User-Role` remains a placeholder.
- No external metrics endpoint yet.
- No cursor pagination for very large datasets yet.
- Scheduler is PostgreSQL-backed but not a full distributed workflow engine.


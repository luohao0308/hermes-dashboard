# System Architecture

Category: architecture
Tags: architecture, backend, frontend, postgres, workers, connectors
Confidence: high
Sources: docs/ARCHITECTURE.md, backend/main.py, docker-compose.yml

The system is organized as a Vue SPA talking to a FastAPI control-plane API backed by PostgreSQL. External runtimes send events through connector APIs. Background workers handle scheduled workflow execution and retention cleanup.

Runtime topology:

- Browser: Vue 3 Control Plane UI.
- API: FastAPI app in `backend/main.py`.
- Database: PostgreSQL 16 in Docker Compose, managed through SQLAlchemy and Alembic.
- Scheduler worker: `backend/workers/workflow_worker.py`, responsible for task claiming, execution state updates, retry/backoff, timeout, and dead-letter handling.
- Retention worker: `backend/workers/retention_worker.py`, responsible for retention policy cleanup and dry-run support.
- Connector ingestion: `backend/routers/connectors.py`, where external systems send workflow events.

Backend app setup:

- `backend/main.py` creates the FastAPI app, installs rate limiting, global exception handlers, security headers, CORS, structured logging middleware, and router mounts.
- Router modules currently mounted include health, provider, review, cost, alerts, agent_config, runtimes, runs, tools, approvals, run_analysis, connectors, evals, workflows, users, environments, audit, auth, and metrics.
- Some compatibility endpoints still live directly in `backend/main.py`, especially agent, terminal, session, chat, eval, and legacy-style helper routes.

Security architecture:

- JWT auth is implemented under `backend/security/auth.py`.
- RBAC is implemented under `backend/security/rbac.py` with admin/operator/viewer roles.
- Secret encryption uses Fernet through `backend/security/secret_manager.py`.
- Webhook verification uses HMAC-SHA256 through `backend/security/webhook.py`.
- Audit logging is centralized through `backend/security/audit.py`.
- Structured logging and request IDs are handled in `backend/security/structured_logging.py`.

Deployment topology:

- `docker-compose.yml` runs `postgres`, `migrate`, `backend`, `workflow-worker`, `retention-worker`, and `frontend`.
- Docker Compose requires `ENCRYPTION_KEY` in `.env` so connector secrets survive restarts.
- The backend listens on port 8000 in Compose and local development.
- The production-ish frontend container serves on port 8080 through nginx.

Related pages:

- [[project-overview]]
- [[codebase-map]]
- [[development-and-verification]]

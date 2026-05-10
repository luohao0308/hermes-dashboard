# Development And Verification

Category: convention
Tags: development, verification, tests, docker, local-run
Confidence: high
Sources: README.md, docs/CURRENT_STATE.md, start.sh, .env.example, docker-compose.yml, frontend/package.json, backend/requirements.txt

Local prerequisites:

- Python 3.9 or newer.
- Node.js 20 or newer.
- PostgreSQL 14 or newer for local development, or PostgreSQL 16 via Docker Compose.

Docker Compose workflow:

- Generate and set `ENCRYPTION_KEY` in `.env` before `docker compose up`.
- Start all services with `docker compose up -d --build`.
- Compose starts PostgreSQL, runs Alembic migrations, starts backend, frontend, workflow worker, and retention worker.
- Frontend is exposed at `http://localhost:8080`.
- Backend is exposed at `http://localhost:8000`.

Local development workflow:

- Start PostgreSQL with `docker compose up -d postgres`.
- Run migrations with `cd backend && alembic upgrade head`.
- Start backend and frontend together with `./start.sh`.
- Local frontend is exposed at `http://localhost:5173`.
- Local backend is exposed at `http://localhost:8000`.
- Stop local services with `./stop.sh`.

Backend commands:

- Start backend only: `cd backend && uvicorn main:app --reload --port 8000`.
- Run backend tests: `cd backend && python -m pytest tests/ -v`.
- Run migrations: `cd backend && alembic upgrade head`.
- Create migration: `cd backend && alembic revision --autogenerate -m \"description\"`.

Frontend commands:

- Start dev server: `cd frontend && npm run dev`.
- Build: `cd frontend && npm run build`.
- Unit tests: `cd frontend && npm run test:unit`.
- Type check: `cd frontend && npx vue-tsc --noEmit`.
- Lint: `cd frontend && npm run lint`.

Test coverage map:

- Backend tests live mainly in `backend/tests/`, with additional backend tests under top-level `tests/backend/`.
- Frontend unit tests live in `frontend/tests/`.
- Playwright/e2e tests live in `frontend/e2e/` and `frontend/tests/e2e/`.

Current documented release verification:

- `docs/CURRENT_STATE.md` reports local and Docker suites as full green: 305 passed, 172 skipped, 0 failed.
- Treat this number as historical release evidence, not a live guarantee. Re-run targeted tests and relevant build/typecheck commands before claiming fresh completion after code changes.

Related pages:

- [[project-overview]]
- [[codebase-map]]
- [[current-state-and-risks]]

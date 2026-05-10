# Current State And Risks

Category: decision
Tags: current-state, risks, roadmap, release, limitations
Confidence: high
Sources: docs/CURRENT_STATE.md, docs/ARCHITECTURE.md, README.md

Current documented status:

- `docs/CURRENT_STATE.md` says the project is stabilized for internal pilot as an Optimization Release on top of v3.0.
- The v0 through v3 roadmap is documented as complete.
- The Optimization Release focused on productization, security hardening, production operations, observability, and quality; it did not add a new feature family.

Completed major areas:

- Navigation reorganized around Observe, Govern, Improve, Integrate, Admin, and legacy grouping.
- Auth/RBAC/service-token support exists.
- Health, metrics, structured logging, and worker heartbeat observability exist.
- Cursor pagination exists for key list surfaces.
- Connector failed-event replay exists.
- Workflow version history and rollback exist.
- Batch approval operations exist.
- Recommended eval configs require approval before applying.
- Scheduler heartbeat files include worker identity and PID.

Known limitations and future candidates:

- SSO/OIDC is not implemented; `docs/SSO_OIDC_DESIGN.md` is a design document for a possible v3.1 path.
- Connector SDK examples are a v3.1 candidate, although `examples/connectors/` already contains Python and Node examples.
- RCA evidence scoring is a v3.1 candidate.
- The scheduler uses PostgreSQL advisory locks and a polling worker. It is not a replacement for a distributed workflow engine such as Temporal or Celery.
- No visual workflow editor exists; workflows are API/JSON-defined.
- Provider connection for Xiaomi Mimo / MiniMax depends on `MINIMAX_API_KEY` and is documented as a deployment configuration gap when absent.

Architecture risks to watch:

- `backend/main.py` still contains direct compatibility endpoints even though product routers are mounted from `backend/routers/`.
- Agent/chat/terminal/review compatibility surfaces should not be mistaken for the control-plane product center.
- SQLite fallback and older docs/language are compatibility concerns to keep contained.
- When touching shared API behavior, update docs and tests together because frontend, backend, connector examples, and release docs all describe overlapping contracts.

Related pages:

- [[project-overview]]
- [[system-architecture]]
- [[development-and-verification]]

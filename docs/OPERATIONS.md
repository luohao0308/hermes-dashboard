# Hermès Dashboard Operations

## Runtime Requirements

- Node.js 20+ for frontend development and production builds.
- Python 3.11 for backend development, tests, and Docker parity.
- Hermès Dashboard API reachable at `HERMES_API_URL` (default `http://localhost:9119`).

## Local Verification

```bash
cd frontend
npx vue-tsc --noEmit
npm run test:unit
npm run build

cd ..
python -m py_compile backend/main.py backend/agent/chat_manager.py backend/agent/tracing_store.py backend/agent/tools/hermes_tools.py backend/agent/guardrails.py backend/agent/rca.py
pytest backend/tests/test_hermes_tools.py backend/tests/test_tracing_store.py backend/tests/test_rca.py backend/tests/test_agent_switch.py::TestChatManagerAPI -q
```

## Runtime Data

- Chat sessions persist to SQLite at `backend/data/chat_sessions.sqlite3` by default.
- Override with `CHAT_DB_PATH=/path/to/chat.sqlite3`.
- Agent run traces persist to SQLite at `backend/data/agent_traces.sqlite3` by default.
- Override with `TRACE_DB_PATH=/path/to/agent_traces.sqlite3`.
- RCA reports are stored in the same trace database and can be read with `GET /api/sessions/{session_id}/rca`.
- Runtime database files and PID files are ignored by git.

## Security Notes

- Never commit real `.env` files or Notion/API tokens.
- Browser terminal high-risk commands are blocked before execution unless re-entered with `confirm `.
- The terminal session API supports listing and explicit PTY shutdown:
  - `GET /api/terminal/sessions`
  - `DELETE /api/terminal/sessions/{session_id}`

## Feature Smoke Test

1. Open the Dashboard and confirm AgentOps overview renders.
2. Confirm Alerts panel renders and actions navigate to logs/session/terminal.
3. Open History, click details, and verify `#/sessions/{id}` loads a replay page.
4. On a session replay page, click "一键分析失败原因" and confirm an RCA report appears.
5. On the same replay page, click "继续对话" and confirm Agent Chat opens with the session linked.
6. Open Agent Chat, create a session, send a message, restart backend, and confirm the session appears again.
7. Open System and confirm model/config/skills/plugins/cron sections render.

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
python -m py_compile backend/main.py backend/agent/chat_manager.py backend/agent/tracing_store.py backend/agent/tools/hermes_tools.py backend/agent/guardrails.py backend/agent/rca.py backend/agent/runbook.py backend/agent/config_evaluator.py backend/agent/exporter.py
pytest backend/tests/test_hermes_tools.py backend/tests/test_tracing_store.py backend/tests/test_rca.py backend/tests/test_runbook.py backend/tests/test_config_evaluator.py backend/tests/test_exporter.py backend/tests/test_agent_switch.py::TestChatManagerAPI -q
```

## Runtime Data

- Chat sessions persist to SQLite at `backend/data/chat_sessions.sqlite3` by default.
- Override with `CHAT_DB_PATH=/path/to/chat.sqlite3`.
- Agent run traces persist to SQLite at `backend/data/agent_traces.sqlite3` by default.
- Override with `TRACE_DB_PATH=/path/to/agent_traces.sqlite3`.
- RCA reports and generated runbooks are stored in the same trace database.
- Read them with `GET /api/sessions/{session_id}/rca` and `GET /api/sessions/{session_id}/runbook`.
- Agent run metrics can be read with `GET /api/agent/evals/summary`.
- Markdown exports are written to `backend/data/exports` by default. Override with `HERMES_EXPORT_DIR=/path/to/export`.
- Runtime database files and PID files are ignored by git.

## Security Notes

- Never commit real `.env` files or Notion/API tokens.
- Browser terminal high-risk commands are blocked before execution unless re-entered with `confirm `.
- Agent tool calls with `confirm` policy create dashboard approval events and require `POST /api/agent/guardrails/{event_id}/approve` before execution.
- The terminal session API supports listing and explicit PTY shutdown:
  - `GET /api/terminal/sessions`
  - `DELETE /api/terminal/sessions/{session_id}`

## Feature Smoke Test

1. Open the Dashboard and confirm AgentOps overview renders.
2. Confirm Alerts panel renders and actions navigate to logs/session/terminal.
3. Open History, click details, and verify `#/sessions/{id}` loads a replay page.
4. On a session replay page, click "一键分析失败原因" and confirm an RCA report appears.
5. Click "生成 Runbook" and confirm a Markdown runbook appears.
6. Click "导出 Markdown" and confirm the export toast shows a local path.
7. On the same replay page, click "继续对话" and confirm Agent Chat opens with the session linked.
8. Open Agent Chat, create a session, send a message, restart backend, and confirm the session appears again.
9. Open System and confirm model/config/skills/plugins/guardrail approvals/cron sections render.

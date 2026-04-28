"""SQLite-backed trace store for Agent runs."""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Optional


class TraceStore:
    """Persists Agent run traces and timeline spans."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path
        if self._db_path:
            self._init_db()

    def create_run(
        self,
        session_id: str,
        agent_id: str,
        input_summary: str,
        linked_session_id: Optional[str] = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        conn = self._connect()
        if not conn:
            return run_id
        try:
            conn.execute(
                """
                INSERT INTO agent_runs (
                    run_id, session_id, agent_id, linked_session_id, input_summary,
                    status, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    agent_id,
                    linked_session_id,
                    input_summary[:500],
                    "running",
                    datetime.now().isoformat(),
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return run_id

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute(
                "UPDATE agent_runs SET status = ?, completed_at = ? WHERE run_id = ?",
                (status, datetime.now().isoformat(), run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def add_span(
        self,
        run_id: str,
        span_type: str,
        title: str,
        summary: str = "",
        agent_name: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        span_id = str(uuid.uuid4())
        conn = self._connect()
        if not conn:
            return span_id
        try:
            conn.execute(
                """
                INSERT INTO trace_spans (
                    span_id, run_id, span_type, title, summary, agent_name,
                    status, metadata_json, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span_id,
                    run_id,
                    span_type,
                    title,
                    summary[:2000],
                    agent_name,
                    status,
                    _json_dumps(metadata or {}),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return span_id

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return _row_to_dict(row)
        finally:
            conn.close()

    def find_latest_run(
        self,
        session_id: Optional[str] = None,
        linked_session_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            conn.row_factory = sqlite3.Row
            if session_id:
                row = conn.execute(
                    "SELECT * FROM agent_runs WHERE session_id = ? ORDER BY started_at DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
            elif linked_session_id:
                row = conn.execute(
                    "SELECT * FROM agent_runs WHERE linked_session_id = ? ORDER BY started_at DESC LIMIT 1",
                    (linked_session_id,),
                ).fetchone()
            else:
                row = None
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def list_spans(self, run_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        if not conn:
            return []
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trace_spans WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
            return [_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    def save_rca_report(
        self,
        session_id: str,
        report: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        report_id = str(uuid.uuid4())
        saved = {**report, "report_id": report_id, "session_id": session_id, "run_id": run_id}
        conn = self._connect()
        if not conn:
            return saved
        try:
            conn.execute(
                """
                INSERT INTO rca_reports (
                    report_id, session_id, run_id, category, root_cause, confidence,
                    evidence_json, next_actions_json, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    session_id,
                    run_id,
                    saved.get("category"),
                    saved.get("root_cause"),
                    float(saved.get("confidence") or 0),
                    _json_dumps({"evidence": saved.get("evidence", [])}),
                    _json_dumps({"next_actions": saved.get("next_actions", [])}),
                    _json_dumps(saved),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return saved

    def get_latest_rca_report(self, session_id: str) -> Optional[dict[str, Any]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT report_json FROM rca_reports
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return _json_loads(row["report_json"])
        finally:
            conn.close()

    def save_runbook(
        self,
        session_id: str,
        runbook: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        runbook_id = str(uuid.uuid4())
        saved = {**runbook, "runbook_id": runbook_id, "session_id": session_id, "run_id": run_id}
        conn = self._connect()
        if not conn:
            return saved
        try:
            conn.execute(
                """
                INSERT INTO runbooks (
                    runbook_id, session_id, run_id, rca_report_id, title, severity,
                    summary, markdown, checklist_json, report_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    runbook_id,
                    session_id,
                    run_id,
                    saved.get("rca_report_id"),
                    saved.get("title"),
                    saved.get("severity"),
                    saved.get("summary"),
                    saved.get("markdown"),
                    _json_dumps({"checklist": saved.get("checklist", [])}),
                    _json_dumps(saved),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return saved

    def get_latest_runbook(self, session_id: str) -> Optional[dict[str, Any]]:
        conn = self._connect()
        if not conn:
            return None
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT report_json FROM runbooks
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return _json_loads(row["report_json"])
        finally:
            conn.close()

    def _connect(self):
        if not self._db_path:
            return None
        directory = os.path.dirname(self._db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    linked_session_id TEXT,
                    input_summary TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_spans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    span_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    span_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    agent_name TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(run_id) REFERENCES agent_runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rca_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    run_id TEXT,
                    category TEXT,
                    root_cause TEXT,
                    confidence REAL,
                    evidence_json TEXT,
                    next_actions_json TEXT,
                    report_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    runbook_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    run_id TEXT,
                    rca_report_id TEXT,
                    title TEXT,
                    severity TEXT,
                    summary TEXT,
                    markdown TEXT,
                    checklist_json TEXT,
                    report_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "metadata_json" in data:
        data["metadata"] = _json_loads(data.pop("metadata_json"))
    return data


def _json_dumps(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str]) -> dict[str, Any]:
    import json

    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


_default_trace_db_path = os.environ.get(
    "TRACE_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "agent_traces.sqlite3")),
)
trace_store = TraceStore(db_path=_default_trace_db_path)

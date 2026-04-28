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

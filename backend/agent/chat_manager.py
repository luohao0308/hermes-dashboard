"""Chat session manager for per-session SSE streams."""

import asyncio
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sse_starlette.sse import ServerSentEvent


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_name: Optional[str] = None


class ChatSession:
    """A single chat session with its own message history and SSE event queue."""

    def __init__(
        self,
        session_id: str,
        agent_id: str = "main",
        created_at: Optional[datetime] = None,
        title: Optional[str] = None,
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.title = title
        self.linked_session_id = linked_session_id
        self.terminal_session_id = terminal_session_id
        self.messages: list[ChatMessage] = []
        self.queue: asyncio.Queue[Optional[ServerSentEvent]] = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.created_at = created_at or datetime.now()
        self.is_running = False
        self._run_task: Optional[asyncio.Task] = None

    def set_task(self, task: asyncio.Task) -> None:
        self._run_task = task

    async def stop(self) -> bool:
        """Cancel the running agent task and emit a stop event."""
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self.is_running = False
            self._run_task = None
            return True
        return False


class ChatManager:
    """Manages all active chat sessions."""

    def __init__(self, db_path: Optional[str] = None):
        self._sessions: dict[str, ChatSession] = {}
        self._db_path = db_path
        if self._db_path:
            self._init_db()
            self._load_sessions()

    def create_session(
        self,
        agent_id: str = "main",
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            agent_id=agent_id,
            title=title,
            linked_session_id=linked_session_id,
            terminal_session_id=terminal_session_id,
        )
        self._sessions[session_id] = session
        self._persist_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._delete_session(session_id)
            return True
        return False

    def update_session_agent(self, session_id: str, agent_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.agent_id = agent_id
        self._persist_session(session)
        return True

    def update_session_context(
        self,
        session_id: str,
        title: Optional[str] = None,
        linked_session_id: Optional[str] = None,
        terminal_session_id: Optional[str] = None,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if title is not None:
            session.title = title
        if linked_session_id is not None:
            session.linked_session_id = linked_session_id
        if terminal_session_id is not None:
            session.terminal_session_id = terminal_session_id
        self._persist_session(session)
        return True

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Optional[ChatMessage]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=timestamp or datetime.now().isoformat(),
            agent_name=agent_name,
        )
        session.messages.append(msg)
        self._persist_message(session_id, msg)
        return msg

    async def stop_session(self, session_id: str) -> bool:
        """Stop a running session by cancelling its agent task."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        return await session.stop()

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "agent_id": s.agent_id,
                "title": s.title,
                "linked_session_id": s.linked_session_id,
                "terminal_session_id": s.terminal_session_id,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "is_running": s.is_running,
            }
            for s in sorted(self._sessions.values(), key=lambda item: item.created_at, reverse=True)
        ]

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
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    title TEXT,
                    linked_session_id TEXT,
                    terminal_session_id TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent_name TEXT,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _load_sessions(self) -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC"):
                session = ChatSession(
                    session_id=row["session_id"],
                    agent_id=row["agent_id"],
                    created_at=_parse_datetime(row["created_at"]),
                    title=row["title"],
                    linked_session_id=row["linked_session_id"],
                    terminal_session_id=row["terminal_session_id"],
                )
                messages = conn.execute(
                    """
                    SELECT role, content, timestamp, agent_name
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                    """,
                    (session.session_id,),
                )
                session.messages = [
                    ChatMessage(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg["timestamp"],
                        agent_name=msg["agent_name"],
                    )
                    for msg in messages
                ]
                self._sessions[session.session_id] = session
        finally:
            conn.close()

    def _persist_session(self, session: ChatSession) -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, agent_id, created_at, title, linked_session_id, terminal_session_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    title = excluded.title,
                    linked_session_id = excluded.linked_session_id,
                    terminal_session_id = excluded.terminal_session_id
                """,
                (
                    session.session_id,
                    session.agent_id,
                    session.created_at.isoformat(),
                    session.title,
                    session.linked_session_id,
                    session.terminal_session_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _persist_message(self, session_id: str, msg: ChatMessage) -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, timestamp, agent_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, msg.role, msg.content, msg.timestamp, msg.agent_name),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_session(self, session_id: str) -> None:
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now()


# Global singleton
_default_db_path = os.environ.get(
    "CHAT_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "chat_sessions.sqlite3")),
)
chat_manager = ChatManager(db_path=_default_db_path)

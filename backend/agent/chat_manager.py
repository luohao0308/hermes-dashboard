"""Chat session manager for per-session SSE streams."""

import asyncio
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

    def __init__(self, session_id: str, agent_id: str = "main"):
        self.session_id = session_id
        self.agent_id = agent_id
        self.messages: list[ChatMessage] = []
        self.queue: asyncio.Queue[Optional[ServerSentEvent]] = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.created_at = datetime.now()
        self.is_running = False


class ChatManager:
    """Manages all active chat sessions."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}

    def create_session(self, agent_id: str = "main") -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id, agent_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "agent_id": s.agent_id,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "is_running": s.is_running,
            }
            for s in self._sessions.values()
        ]


# Global singleton
chat_manager = ChatManager()

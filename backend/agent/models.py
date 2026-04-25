"""Pydantic models for Multi-Agent system."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    TRIAGE = "triage"
    MONITOR = "monitor"
    ANALYST = "analyst"
    EXECUTOR = "executor"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DONE = "done"


class AgentInfo(BaseModel):
    id: str
    name: str
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    status_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None
    event_count: int = 0
    last_error: Optional[str] = None


class InvokeRequest(BaseModel):
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    message: str
    context: Optional[dict] = None


class AgentEvent(BaseModel):
    """SSE event payload for agent activity."""

    type: str  # agent_created | agent_status | agent_handoff | agent_output | agent_error | agent_complete | hermes_alert
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    status: Optional[AgentStatus] = None
    message: Optional[str] = None
    delta: Optional[str] = None
    error: Optional[str] = None
    result: Optional[str] = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    hermes_level: Optional[str] = None  # info | warning | error
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

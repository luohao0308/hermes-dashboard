"""Multi-Agent system for hermes_free."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import get_model
    from .models import AgentInfo, AgentStatus, AgentEvent, InvokeRequest
    from .orchestrator import AgentOrchestrator

__all__ = [
    "get_model",
    "AgentInfo",
    "AgentStatus",
    "AgentEvent",
    "InvokeRequest",
    "AgentOrchestrator",
]


def __getattr__(name: str):
    if name == "get_model":
        from .client import get_model
        return get_model
    if name in {"AgentInfo", "AgentStatus", "AgentEvent", "InvokeRequest"}:
        from . import models
        return getattr(models, name)
    if name == "AgentOrchestrator":
        from .orchestrator import AgentOrchestrator
        return AgentOrchestrator
    raise AttributeError(f"module 'agent' has no attribute {name!r}")

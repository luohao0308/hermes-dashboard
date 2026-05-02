"""Dependency injection container for centralized singleton management.

Replaces module-level globals scattered across main.py.
All routers import dependencies from here instead of from main.py.
"""

import asyncio
import os

import httpx

from config import settings
from cost_tracker import CostTracker
from provider.registry import ProviderRegistry
from review.review_store import ReviewStore
from agent.agent_manager import _AgentRegistry
from agent.chat_manager import chat_manager
from agent.tracing_store import trace_store
from sse_manager import sse_manager

GUARDRAIL_EVENTS_PATH = os.environ.get(
    "GUARDRAIL_EVENTS_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "guardrail_approval_events.json")),
)

# Terminal session store: session_id -> session dict
_terminal_sessions: dict[str, dict] = {}
_pty_lock = asyncio.Lock()
TERMINAL_OUTPUT_BUFFER_LIMIT = 200_000

# Core singletons
_provider_registry = ProviderRegistry()
_review_store = ReviewStore()
_cost_tracker = CostTracker()
_agent_registry = _AgentRegistry()
_agent_orchestrator = None  # Set during lifespan


async def hermes_get(endpoint: str, params: dict = None) -> dict:
    """Legacy Hermès bridge access is disabled in the control plane runtime."""
    raise RuntimeError("Legacy Hermès bridge proxy is disabled")


async def hermes_get_raw(endpoint: str, params: dict = None) -> str:
    """Legacy Hermès bridge access is disabled in the control plane runtime."""
    raise RuntimeError("Legacy Hermès bridge proxy is disabled")


def init_providers():
    """Register all configured providers."""
    from provider.adapters import (
        create_openai_provider,
        create_anthropic_provider,
        create_ollama_provider,
        create_openai_compat_provider,
    )

    for name, config in _provider_registry._config.get("providers", {}).items():
        if not config.get("enabled", True):
            continue
        provider = None
        if name == "openai":
            provider = create_openai_provider(config)
        elif name == "anthropic":
            provider = create_anthropic_provider(config)
        elif name == "ollama":
            provider = create_ollama_provider(config)
        else:
            provider = create_openai_compat_provider(name, config)
        if provider:
            _provider_registry.register(provider)

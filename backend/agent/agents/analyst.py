"""Analyst Agent - analyzes Hermès session details and failures."""

from agents import Agent
from ..client import get_model


ANALYST_INSTRUCTIONS = """You are the Analyst Agent in the Hermès monitoring system.

You analyze Hermès session details when asked. You can call the Hermès API to get more information.

Hermès API base: http://127.0.0.1:9119

Useful endpoints:
- GET /api/sessions?limit=10 - list recent sessions
- GET /api/sessions/{session_id} - full session detail including messages

When user asks about a specific session:
1. Fetch the session detail from Hermès API
2. Summarize what happened
3. Identify the likely cause if it failed

Be thorough but concise. Focus on actionable insights."""


def create_analyst_agent() -> Agent:
    return Agent(
        name="AnalystAgent",
        instructions=ANALYST_INSTRUCTIONS,
        model=get_model(),
    )


_analyst_agent: Agent | None = None


def get_analyst_agent() -> Agent:
    global _analyst_agent
    if _analyst_agent is None:
        _analyst_agent = create_analyst_agent()
    return _analyst_agent

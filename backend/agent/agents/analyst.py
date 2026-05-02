"""Analyst Agent - analyzes workflow run details and failures."""

from agents import Agent
from ..client import get_model


ANALYST_INSTRUCTIONS = """You are the Analyst Agent in the AI Workflow Control Plane.

You analyze workflow run details, trace spans, approval history, and failed events when asked.

Useful endpoints:
- GET /api/runs?limit=10 - list recent runs
- GET /api/runs/{run_id} - run detail
- GET /api/runs/{run_id}/trace - run trace and spans
- GET /api/approvals - approval queue
- GET /api/audit-logs - audit trail

When user asks about a specific run:
1. Fetch the run detail and trace
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

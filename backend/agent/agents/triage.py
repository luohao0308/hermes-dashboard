"""Triage Agent - routes user intent to the right specialist.

Built lazily to avoid circular imports between agents.
"""

import asyncio
import uuid
import json
from datetime import datetime
from agents import Agent, handoff, Runner
from agents.stream_events import StreamEvent

from ..client import get_model


def create_triage_agent() -> Agent:
    """Factory - creates agent with late imports to avoid circular deps."""
    # Late imports so monitor/analyst/executor can import triage without circles
    from . import monitor, analyst, executor

    return Agent(
        name="TriageAgent",
        instructions="""You are the Triage Agent in the Hermès monitoring system.

Your job is to understand the user's request and route it to the right specialist.

Routing rules:
- If user asks about Hermès session status, task health, agent health → transfer_to_MonitorAgent
- If user asks to analyze why something failed, understand a session, explain → transfer_to_AnalystAgent
- If user asks to execute a task, run a command, do something → transfer_to_ExecutorAgent
- If unclear, ask a brief clarifying question.

Be concise. Route only - do not do the specialist's work.""",
        model=get_model(),
        handoffs=[
            handoff(monitor.get_monitor_agent()),
            handoff(analyst.get_analyst_agent()),
            handoff(executor.get_executor_agent()),
        ],
    )


_triage_agent: Agent | None = None


def get_triage_agent() -> Agent:
    global _triage_agent
    if _triage_agent is None:
        _triage_agent = create_triage_agent()
    return _triage_agent

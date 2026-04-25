"""AgentOrchestrator - manages agent lifecycle and SSE event broadcasting."""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Optional

from agents import Agent, Runner
from agents.stream_events import StreamEvent

from .models import AgentInfo, AgentStatus, AgentEvent, AgentRole, InvokeRequest
from .agents.triage import get_triage_agent
from .client import get_model


class AgentOrchestrator:
    """Manages multi-agent lifecycle, run execution, and SSE broadcasting."""

    def __init__(self, sse_broadcaster):
        """
        Args:
            sse_broadcaster: a callable that accepts (event_type: str, data: dict)
                             will be sse_manager.broadcast in practice
        """
        self._agents: dict[str, AgentInfo] = {}
        self._broadcast = sse_broadcaster
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._started = False

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def start(self):
        """Start the orchestrator - boot all system agents."""
        if self._started:
            return
        self._started = True

        # Boot triage agent (others boot lazily)
        triage = get_triage_agent()
        await self._register_agent(triage, AgentRole.TRIAGE)

        # Start background monitor loop (polls Hermès every 30s)
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop all agent tasks."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        for task in self._running_tasks.values():
            task.cancel()
        self._started = False

    # -------------------------------------------------------------------------
    # Agent registration
    # -------------------------------------------------------------------------

    async def _register_agent(self, agent: Agent, role: AgentRole) -> AgentInfo:
        """Register an agent and broadcast its creation."""
        info = AgentInfo(
            id=f"agent_{uuid.uuid4().hex[:8]}",
            name=agent.name,
            role=role,
            status=AgentStatus.IDLE,
        )
        self._agents[info.id] = info
        await self._emit(AgentEvent(type="agent_created", agent_id=info.id, agent_name=info.name))
        return info

    # -------------------------------------------------------------------------
    # Invoke
    # -------------------------------------------------------------------------

    async def invoke(self, req: InvokeRequest) -> str:
        """Invoke an agent with a message. Returns task_id."""
        agent = get_triage_agent()
        agent_info = self._find_agent_by_role(AgentRole.TRIAGE)

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self._running_tasks[task_id] = asyncio.create_task(
            self._run_agent_stream(task_id, agent, agent_info, req.message)
        )
        return task_id

    async def _run_agent_stream(
        self, task_id: str, agent: Agent, agent_info: AgentInfo, message: str
    ):
        """Run an agent and stream events back via SSE."""
        # Update status
        agent_info.status = AgentStatus.RUNNING
        agent_info.event_count += 1
        await self._emit(AgentEvent(
            type="agent_status",
            agent_id=agent_info.id,
            agent_name=agent_info.name,
            status=AgentStatus.RUNNING,
            message="running",
        ))

        try:
            result = Runner.run_streamed(agent, message)
            current_agent_name = agent.name
            all_output = []

            async for event in result.stream_events():
                ev_type, payload = self._classify_event(event, agent_info, current_agent_name)

                if ev_type == "agent_handoff":
                    current_agent_name = payload.get("to_agent", current_agent_name)

                if ev_type == "agent_output":
                    all_output.append(payload.get("delta", ""))

                if ev_type and payload:
                    await self._emit(AgentEvent(type=ev_type, **payload))

            # Done
            agent_info.status = AgentStatus.IDLE
            final_text = "".join(all_output)
            await self._emit(AgentEvent(
                type="agent_complete",
                agent_id=agent_info.id,
                agent_name=agent_info.name,
                status=AgentStatus.IDLE,
                result=final_text[:500],
            ))

        except Exception as exc:
            agent_info.status = AgentStatus.ERROR
            agent_info.last_error = str(exc)
            await self._emit(AgentEvent(
                type="agent_error",
                agent_id=agent_info.id,
                agent_name=agent_info.name,
                error=str(exc),
            ))
        finally:
            agent_info.last_active = datetime.utcnow()
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    def _classify_event(
        self, event: StreamEvent, agent_info: AgentInfo, current_agent_name: str
    ):
        """Convert openai-agents stream event to SSE payload dict."""
        if hasattr(event, "type"):
            if event.type == "run_item_stream_event":
                name = getattr(event, "name", None)
                item = getattr(event, "item", None)

                if name == "message_output_created" and item:
                    try:
                        content = item.content
                        if hasattr(content, "first_text"):
                            text = content.first_text or ""
                        elif hasattr(content, "parts"):
                            text = "".join(
                                p.text for p in content.parts if hasattr(p, "text")
                            )
                        else:
                            text = str(content)
                        return "agent_output", {
                            "agent_id": agent_info.id,
                            "agent_name": current_agent_name,
                            "delta": text,
                        }
                    except Exception:
                        return None, None

                elif name in ("tool_called", "tool_output"):
                    return "agent_output", {
                        "agent_id": agent_info.id,
                        "agent_name": current_agent_name,
                        "delta": f"[{name}]",
                    }

                elif name in ("handoff_requested", "handoff_occured"):
                    # Extract target agent name from handoff item if possible
                    to_name = current_agent_name
                    return "agent_handoff", {
                        "agent_id": agent_info.id,
                        "from_agent": current_agent_name,
                        "to_agent": to_name,
                        "message": f"Handoff from {current_agent_name}",
                    }

            elif event.type == "agent_updated_stream_event":
                new_agent = getattr(event, "new_agent", None)
                new_name = new_agent.name if new_agent else current_agent_name
                return "agent_handoff", {
                    "agent_id": agent_info.id,
                    "from_agent": current_agent_name,
                    "to_agent": new_name,
                    "message": f"Handoff to {new_name}",
                }

        return None, None

    # -------------------------------------------------------------------------
    # Background monitor loop
    # -------------------------------------------------------------------------

    async def _monitor_loop(self):
        """Poll Hermès sessions every 30s and emit alerts."""
        import httpx
        HERMES = "http://127.0.0.1:9119"

        while True:
            await asyncio.sleep(30)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{HERMES}/api/sessions", params={"limit": 10})
                    if resp.status_code != 200:
                        continue
                    sessions = resp.json().get("sessions", [])

                now = datetime.utcnow().timestamp()

                for session in sessions:
                    if not session.get("is_active"):
                        continue

                    last_active = session.get("last_active", now)
                    if isinstance(last_active, (int, float)):
                        age_min = (now - last_active) / 60
                    else:
                        age_min = 0

                    if age_min > 5:
                        await self._emit(AgentEvent(
                            type="hermes_alert",
                            hermes_level="warning",
                            message=f"Session {session['id']} idle > {age_min:.0f}min",
                            session_id=session["id"],
                        ))

                    end_reason = session.get("end_reason", "")
                    if end_reason and end_reason not in ("cli_close", "done"):
                        await self._emit(AgentEvent(
                            type="hermes_alert",
                            hermes_level="error",
                            message=f"Session {session['id']} ended: {end_reason}",
                            session_id=session["id"],
                        ))

            except asyncio.CancelledError:
                raise
            except Exception:
                pass  # Silent - monitor should not spam logs

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_agent_by_role(self, role: AgentRole) -> Optional[AgentInfo]:
        for info in self._agents.values():
            if info.role == role:
                return info
        return None

    async def _emit(self, event: AgentEvent):
        """Broadcast an event via SSE."""
        try:
            self._broadcast(event.type, event.model_dump(exclude_none=True))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Public query API
    # -------------------------------------------------------------------------

    def list_agents(self) -> list[AgentInfo]:
        return list(self._agents.values())

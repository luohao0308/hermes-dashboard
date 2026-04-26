"""AgentOrchestrator - manages agent lifecycle and SSE event broadcasting."""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Optional

from agents import Agent, Runner
from agents.stream_events import StreamEvent

from .models import AgentInfo, AgentStatus, AgentEvent, AgentRole, InvokeRequest
from .client import get_model
from . import agent_manager


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
        # Queue decouples SSE broadcast from Runner.run_streamed async-for loop
        self._event_queue: asyncio.Queue = asyncio.Queue()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def start(self):
        """Start the orchestrator - load agents from config."""
        if self._started:
            return
        self._started = True

        # Load all configured agents and register them for SSE listing
        agents = agent_manager.get_all_agents()
        role_map = {
            "dispatcher": AgentRole.DISPATCHER,
            "researcher": AgentRole.RESEARCHER,
            "developer": AgentRole.DEVELOPER,
            "reviewer": AgentRole.REVIEWER,
            "tester": AgentRole.TESTER,
            "devops": AgentRole.DEVOPS,
        }
        for key, agent in agents.items():
            role = role_map.get(key, AgentRole.DISPATCHER)
            await self._register_agent(agent, role)

        # Start SSE event broadcaster (consumes _event_queue in the background)
        self._broadcast_task = asyncio.create_task(self._run_broadcaster())

    async def _run_broadcaster(self):
        """Background task: drain the event queue and broadcast to SSE."""
        print(f"[Broadcaster] Started, queue size: {self._event_queue.qsize()}")
        while True:
            try:
                event_type, data = await self._event_queue.get()
                print(f"[Broadcaster] Got event: type={event_type}, data_keys={list(data.keys())}")
                await self._broadcast(event_type, data)
                print(f"[Broadcaster] Broadcast complete, connections={self._broadcast}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Broadcaster] Error: {e}")

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
        """Invoke the main agent with a message. Returns task_id."""
        agent = agent_manager.get_main_agent()
        task_id = str(uuid.uuid4())

        # Emit running status
        await self._emit(AgentEvent(
            type="agent_status",
            agent_id=task_id,
            agent_name=agent.name,
            status=AgentStatus.RUNNING,
            status_message="正在处理...",
        ))
        self._running_tasks[task_id] = asyncio.create_task(
            self._run_agent_stream(task_id, agent, req.message)
        )
        return task_id

    async def _run_agent_stream(
        self, task_id: str, agent: Agent, message: str
    ):
        """Run an agent and stream events back via SSE."""
        await self._emit(AgentEvent(
            type="agent_status",
            agent_id=task_id,
            agent_name=agent.name,
            status=AgentStatus.RUNNING,
            message="running",
        ))

        try:
            result = Runner.run_streamed(agent, message)
            current_agent_name = agent.name
            all_output = []

            async for event in result.stream_events():
                ev_type, payload = self._classify_event(task_id, current_agent_name, event)

                if ev_type == "agent_handoff":
                    current_agent_name = payload.get("to_agent", current_agent_name)

                if ev_type == "agent_output":
                    all_output.append(payload.get("delta", ""))

                if ev_type and payload:
                    await self._emit(AgentEvent(type=ev_type, **payload))

            # Done
            final_text = "".join(all_output)
            await self._emit(AgentEvent(
                type="agent_complete",
                agent_id=task_id,
                agent_name=agent.name,
                status=AgentStatus.IDLE,
                result=final_text[:500],
            ))

        except Exception as exc:
            await self._emit(AgentEvent(
                type="agent_error",
                agent_id=task_id,
                agent_name=agent.name,
                error=str(exc),
            ))
        finally:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    def _classify_event(
        self, task_id: str, current_agent_name: str, event: StreamEvent
    ):
        """Convert openai-agents stream event to SSE payload dict."""
        if hasattr(event, "type"):
            if event.type == "raw_response_event":
                # MiniMax Responses API — ResponseTextDeltaEvent has .delta attribute
                try:
                    chunk = event.data
                    if hasattr(chunk, "delta") and chunk.delta:
                        # ResponseTextDeltaEvent — delta is the text content
                        delta = chunk.delta
                        if isinstance(delta, str):
                            text = delta
                        elif hasattr(delta, "text"):
                            text = delta.text
                        else:
                            text = str(delta)
                        if text:
                            return "agent_output", {
                                "agent_id": task_id,
                                "agent_name": current_agent_name,
                                "delta": text,
                            }
                    elif hasattr(chunk, "response") and chunk.response:
                        # ResponseCreatedEvent — extract initial content if any
                        resp = chunk.response
                        if hasattr(resp, "output") and resp.output:
                            output = resp.output
                            if hasattr(output, "text") and output.text:
                                return "agent_output", {
                                    "agent_id": task_id,
                                    "agent_name": current_agent_name,
                                    "delta": output.text,
                                }
                except Exception as e:
                    pass
                return None, None

            elif event.type == "run_item_stream_event":
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
                            "agent_id": task_id,
                            "agent_name": current_agent_name,
                            "delta": text,
                        }
                    except Exception:
                        return None, None

                elif name in ("tool_called", "tool_output"):
                    return "agent_output", {
                        "agent_id": task_id,
                        "agent_name": current_agent_name,
                        "delta": f"[{name}]",
                    }

                elif name in ("handoff_requested", "handoff_occured"):
                    # Extract target agent name from handoff item if possible
                    to_name = current_agent_name
                    return "agent_handoff", {
                        "agent_id": task_id,
                        "from_agent": current_agent_name,
                        "to_agent": to_name,
                        "message": f"Handoff from {current_agent_name}",
                    }

            elif event.type == "agent_updated_stream_event":
                new_agent = getattr(event, "new_agent", None)
                new_name = new_agent.name if new_agent else current_agent_name
                return "agent_handoff", {
                    "agent_id": task_id,
                    "from_agent": current_agent_name,
                    "to_agent": new_name,
                    "message": f"Handoff to {new_name}",
                }

        print(f"[_classify_event] event_type={event.type if hasattr(event, 'type') else 'N/A'}, name={name if 'name' in dir() else 'N/A'}")
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
        """Queue an event for broadcast — never blocks the stream iteration."""
        try:
            data = event.model_dump(exclude_none=True)
            # Convert datetime to ISO string for JSON serialization
            for k, v in data.items():
                if hasattr(v, 'isoformat'):
                    data[k] = v.isoformat()
            self._event_queue.put_nowait((event.type, data))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Public query API
    # -------------------------------------------------------------------------

    def list_agents(self) -> list[AgentInfo]:
        return list(self._agents.values())

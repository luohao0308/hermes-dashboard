"""Hermès Bridge Service - FastAPI + SSE Backend
Proxies requests to real Hermès Agent Dashboard API (localhost:9119)
"""

import asyncio
import json
import uuid
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Query, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx

from sse_manager import sse_manager
from config import settings
from agent import AgentOrchestrator
from agent.chat_manager import chat_manager, ChatMessage
from agent.agent_manager import _AgentRegistry
from agents.stream_events import StreamEvent

_agent_registry = _AgentRegistry()

# Global agent orchestrator (started via lifespan)
_agent_orchestrator: AgentOrchestrator | None = None

# Terminal session store: session_id -> session dict
# session dict: {pid, master_fd, alive, is_attached, pending_messages, lock, attach_count}
_terminal_sessions: dict[str, dict] = {}
_pty_lock = asyncio.Lock()

# Hermès Agent Dashboard API base URL (override with HERMES_API_URL env var)
HERMES_API_BASE = os.environ.get("HERMES_API_URL", "http://127.0.0.1:9119")

# Clear proxy env vars for httpx (avoid SOCKS proxy issues)
for _k in list(os.environ.keys()):
    if 'proxy' in _k.lower():
        del os.environ[_k]

# Session token for authenticated API calls
_hermes_session_token = None


def _get_hermes_token():
    """Fetch session token from dashboard page"""
    global _hermes_session_token
    if _hermes_session_token:
        return _hermes_session_token
    try:
        import re
        import urllib.request
        response = urllib.request.urlopen(f"{HERMES_API_BASE}/", timeout=3)
        html = response.read().decode('utf-8')
        match = re.search(r'window\.__HERMES_SESSION_TOKEN__="([^"]+)"', html)
        if match:
            _hermes_session_token = match.group(1)
            return _hermes_session_token
    except Exception:
        pass
    return None


# ============================================================================
# Hermès API Client
# ============================================================================

async def hermes_get(endpoint: str, params: dict = None) -> dict[str, Any]:
    """Proxy GET request to Hermès Agent API"""
    url = f"{HERMES_API_BASE}{endpoint}"
    headers = {}
    token = _get_hermes_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def hermes_get_raw(endpoint: str, params: dict = None) -> str:
    """Proxy GET request to Hermès Agent API, return raw text"""
    url = f"{HERMES_API_BASE}{endpoint}"
    headers = {}
    token = _get_hermes_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.text


# ============================================================================
# SSE Event Generator - Real-time data from Hermès
# ============================================================================

async def generate_events():
    """Generate events by polling Hermès Agent API periodically"""
    counter = 0
    while True:
        try:
            await asyncio.sleep(settings.event_generation_interval)
            counter += 1

            # Poll Hermès status every cycle
            try:
                status = await hermes_get("/api/status")
                sessions = await hermes_get("/api/sessions", {"limit": 5, "offset": 0})
            except Exception as e:
                # Hermes not running, broadcast simulated status
                event_type = "system_status"
                data = {
                    "status": "hermes_offline",
                    "message": "Hermès Agent 未运行或 Dashboard 未启动",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "active_connections": sse_manager.get_connection_count()
                }
                await sse_manager.broadcast(event_type, data)
                continue

            # Every 3 cycles: send system status
            if counter % 3 == 0:
                event_type = "system_status"
                data = {
                    "status": "healthy" if status.get("gateway_running") else "gateway_stopped",
                    "version": status.get("version"),
                    "release_date": status.get("release_date"),
                    "gateway_running": status.get("gateway_running"),
                    "gateway_pid": status.get("gateway_pid"),
                    "active_sessions": status.get("active_sessions"),
                    "gateway_platforms": status.get("gateway_platforms"),
                    "timestamp": datetime.now().isoformat(),
                    "active_connections": sse_manager.get_connection_count()
                }
                await sse_manager.broadcast(event_type, data)

            # Every 5 cycles: send session update
            if counter % 5 == 0:
                event_type = "sessions_update"
                data = {
                    "sessions": sessions.get("sessions", [])[:5],
                    "total": sessions.get("total", 0),
                    "timestamp": datetime.now().isoformat()
                }
                await sse_manager.broadcast(event_type, data)

            # Every heartbeat cycle
            if counter % settings.heartbeat_interval == 0:
                event_type = "heartbeat"
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "hermes_version": status.get("version")
                }
                await sse_manager.broadcast(event_type, data)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error generating events: {e}")
            # Send error event
            try:
                await sse_manager.broadcast("error", {
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                pass


# ============================================================================
# Lifespan & App Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global _agent_orchestrator

    # Startup: start the event generator
    event_task = asyncio.create_task(generate_events())

    # Start agent orchestrator
    _agent_orchestrator = AgentOrchestrator(
        sse_broadcaster=lambda et, d: sse_manager.broadcast(et, d)
    )
    await _agent_orchestrator.start()

    yield

    # Shutdown: cancel the event generator and orchestrator
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass

    if _agent_orchestrator:
        await _agent_orchestrator.stop()


app = FastAPI(
    title="Hermès Bridge Service",
    description="SSE-based bridge service that proxies to Hermès Agent Dashboard API",
    version="1.1.0",
    lifespan=lifespan
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Add CORS middleware (origins controlled by CORS_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================================
# SSE Endpoint
# ============================================================================

@app.get("/sse")
@limiter.limit("30/minute")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for Hermès updates"""

    client_id = str(uuid.uuid4())

    async def event_generator():
        # Register connection — creates a queue for this client
        await sse_manager.connect(client_id, request)
        queue = sse_manager._queues[client_id]
        heartbeat_count = 0

        try:
            # Send initial connection event
            yield ServerSentEvent(
                event="connected",
                data=json.dumps({
                    "client_id": client_id,
                    "message": "Connected to Hermès Bridge Service",
                    "hermes_api": HERMES_API_BASE,
                    "timestamp": datetime.now().isoformat()
                })
            )

            # Keep connection alive and yield events from the queue
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Wait for event from queue OR timeout for heartbeat
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=settings.heartbeat_interval
                    )
                    if event is None:  # Sentinel
                        break
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield ServerSentEvent(
                        event="heartbeat",
                        data=json.dumps({
                            "status": "alive",
                            "timestamp": datetime.now().isoformat()
                        })
                    )

        finally:
            # Cleanup on disconnect — push sentinel to unblock queue.get()
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
            sse_manager.disconnect(client_id)

    return EventSourceResponse(event_generator())


# ============================================================================
# Health & Connection Management
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Try to reach Hermès API
    hermes_reachable = False
    hermes_status = {}
    try:
        hermes_status = await hermes_get("/api/status")
        hermes_reachable = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "hermes-bridge",
        "version": "1.1.0",
        "active_connections": sse_manager.get_connection_count(),
        "hermes_reachable": hermes_reachable,
        "hermes_api_base": HERMES_API_BASE,
        "hermes_version": hermes_status.get("version") if hermes_reachable else None,
        "gateway_running": hermes_status.get("gateway_running") if hermes_reachable else None
    }


@app.get("/connections")
async def list_connections():
    """List all active SSE connections"""
    return {
        "count": sse_manager.get_connection_count(),
        "connections": sse_manager.get_all_connections()
    }


@app.get("/connections/{client_id}")
async def get_connection(client_id: str):
    """Get information about a specific connection"""
    info = sse_manager.get_connection_info(client_id)
    if not info:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"client_id": client_id, **info}


# ============================================================================
# Hermès API Proxy Endpoints
# ============================================================================

@app.get("/api/status")
async def proxy_status():
    """Proxy to Hermès /api/status - Gateway status overview"""
    try:
        return await hermes_get("/api/status")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/sessions")
async def proxy_sessions(
    limit: int = Query(20, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Proxy to Hermès /api/sessions - List sessions"""
    try:
        return await hermes_get("/api/sessions", {"limit": limit, "offset": offset})
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/sessions/search")
async def proxy_search_sessions(q: str = Query(..., description="Search query")):
    """Proxy to Hermès /api/sessions/search - Search sessions"""
    try:
        return await hermes_get("/api/sessions/search", {"q": q})
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/sessions/{session_id}/messages")
async def proxy_session_messages(session_id: str):
    """Proxy to Hermès /api/sessions/{id}/messages - Get session messages"""
    try:
        return await hermes_get(f"/api/sessions/{session_id}/messages")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.delete("/api/sessions/{session_id}")
async def proxy_delete_session(session_id: str):
    """Proxy to Hermès /api/sessions/{id} DELETE - Delete a session"""
    url = f"{HERMES_API_BASE}/api/sessions/{session_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/logs")
async def proxy_logs(
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines"),
    level: str = Query("INFO", description="Log level filter"),
    file: Optional[str] = Query(None, description="Log file path"),
    component: Optional[str] = Query(None, description="Component filter")
):
    """Proxy to Hermès /api/logs - Get log entries"""
    params: dict[str, Any] = {"lines": lines, "level": level}
    if file:
        params["file"] = file
    if component and component != "all":
        params["component"] = component

    try:
        return await hermes_get("/api/logs", params)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/analytics/usage")
async def proxy_analytics(days: int = Query(7, ge=1, le=90, description="Number of days")):
    """Proxy to Hermès /api/analytics/usage - Get usage analytics"""
    try:
        return await hermes_get("/api/analytics/usage", {"days": days})
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/config")
async def proxy_config():
    """Proxy to Hermès /api/config - Get current config"""
    try:
        return await hermes_get("/api/config")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/model/info")
async def proxy_model_info():
    """Proxy to Hermès /api/model/info - Get model info"""
    try:
        return await hermes_get("/api/model/info")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/skills")
async def proxy_skills():
    """Proxy to Hermès /api/skills - Get skills list"""
    try:
        return await hermes_get("/api/skills")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/cron/jobs")
async def proxy_cron_jobs():
    """Proxy to Hermès /api/cron/jobs - Get cron jobs"""
    try:
        return await hermes_get("/api/cron/jobs")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


@app.get("/api/plugins")
async def proxy_plugins():
    """Proxy to Hermès /api/dashboard/plugins - Get dashboard plugins"""
    try:
        return await hermes_get("/api/dashboard/plugins")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Hermès API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Hermès: {e}")


# ============================================================================
# Legacy Endpoints (for backward compatibility with frontend)
# ============================================================================

@app.get("/tasks")
async def list_tasks():
    """List tasks from Hermès sessions (derived from recent sessions)"""
    try:
        sessions = await hermes_get("/api/sessions", {"limit": 20, "offset": 0})
        # Convert sessions to tasks format
        tasks = []
        for session in sessions.get("sessions", []):
            tasks.append({
                "task_id": session.get("id", ""),
                "name": session.get("title") or f"Session {session.get('id', '')[:8]}",
                "status": "running" if session.get("is_active") else "completed",
                "progress": 100 if not session.get("is_active") else 50,
                "message_count": session.get("message_count", 0),
                "model": session.get("model"),
                "started_at": datetime.fromtimestamp(session.get("started_at", 0)/1000).isoformat() if session.get("started_at") else None
            })
        return {"tasks": tasks, "total": len(tasks)}
    except Exception as e:
        # Fallback: return empty
        return {"tasks": [], "total": 0, "error": str(e)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get specific task/session by ID"""
    try:
        # First check if session exists by fetching sessions list
        sessions = await hermes_get("/api/sessions", {"limit": 100, "offset": 0})
        session = next((s for s in sessions.get("sessions", []) if s.get("id") == task_id), None)

        if not session:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get messages for this session
        messages = await hermes_get(f"/api/sessions/{task_id}/messages")

        return {
            "task_id": task_id,
            "name": session.get("title") or f"Session {task_id[:8]}",
            "status": "running" if session.get("is_active") else "completed",
            "progress": 100 if not session.get("is_active") else 50,
            "messages": messages.get("messages", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to get task: {e}")


@app.get("/history")
async def list_history(limit: int = Query(20, ge=1, le=100)):
    """List historical tasks/sessions"""
    try:
        sessions = await hermes_get("/api/sessions", {"limit": limit, "offset": 0})
        history = []
        for session in sessions.get("sessions", []):
            if not session.get("is_active"):
                history.append({
                    "task_id": session.get("id", ""),
                    "name": session.get("title") or f"Session {session.get('id', '')[:8]}",
                    "completed_at": datetime.fromtimestamp(session.get("ended_at", session.get("last_active", 0))/1000).isoformat() if session.get("ended_at") or session.get("last_active") else None,
                    "duration": (session.get("ended_at", 0) - session.get("started_at", 0)) // 1000 if session.get("ended_at") and session.get("started_at") else 0,
                    "message_count": session.get("message_count", 0),
                    "model": session.get("model"),
                    "input_tokens": session.get("input_tokens", 0),
                    "output_tokens": session.get("output_tokens", 0)
                })
        return {"history": history, "total": sessions.get("total", 0)}
    except Exception as e:
        return {"history": [], "total": 0, "error": str(e)}


# ============================================================================
# Broadcast (legacy)
# ============================================================================

@app.post("/broadcast")
async def broadcast_event(
    event_type: str = Query(..., description="Event type for the broadcast"),
    message: str = Query(..., description="Message to broadcast")
):
    """Broadcast a custom event to all connected clients"""
    data = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type
    }
    await sse_manager.broadcast(event_type, data)
    return {
        "status": "broadcast_sent",
        "event_type": event_type,
        "recipient_count": sse_manager.get_connection_count()
    }


@app.post("/tasks/{task_id}/broadcast")
async def broadcast_task_update(task_id: str):
    """Broadcast a task update event"""
    try:
        session = await hermes_get(f"/api/sessions/{task_id}")
        await sse_manager.broadcast("task_update", session)
        return {"status": "broadcast_sent", "task": session}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")


# ============================================================================
# WebSocket Terminal Endpoint
# ============================================================================

async def _create_pty_session(session_id: str):
    """Create a new PTY session and store it. Caller must hold _pty_lock."""
    import pty
    import select as _select
    import fcntl
    import struct
    import termios
    import signal

    env = os.environ.copy()
    env['HUSHLOGIN'] = '/dev/null'  # suppress "Last login" banner
    env['TERM'] = 'xterm-256color'
    env['CLICOLOR'] = '1'          # enable ls color output
    env['COLORTERM'] = 'truecolor'  # true color (24-bit)
    env['LSCOLORS'] = 'ExGxBxDxCxEgEdxbxgxcxd'  # macOS ls colors
    # Use zsh as login shell to match local terminal
    pid, master_fd = pty.fork()

    if pid == 0:
        # Child: exec zsh as login shell (sources /etc/zprofile, ~/.zshrc)
        os.execvp("zsh", ["zsh", "-l"])
        os._exit(1)

    session = {
        "pid": pid,
        "master_fd": master_fd,
        "alive": True,
        "is_attached": False,
    }
    _terminal_sessions[session_id] = session
    return session


def _close_pty_session(session: dict):
    """Close PTY files and kill process. Called without lock."""
    import signal
    pid = session["pid"]
    master_fd = session["master_fd"]
    try:
        import os as _os
        _os.close(master_fd)
    except Exception:
        pass
    try:
        _os.kill(pid, signal.SIGTERM)
        _os.waitpid(pid, 0)
    except Exception:
        pass


async def _expire_session(session_id: str):
    """Remove a session after it has been dead and detached. Runs async."""
    await asyncio.sleep(30)
    async with _pty_lock:
        session = _terminal_sessions.get(session_id)
        if session and not session["alive"] and not session["is_attached"]:
            _close_pty_session(session)
            del _terminal_sessions[session_id]
            print(f"[TERMINAL] Session {session_id} expired and cleaned up", flush=True)


@app.websocket("/ws/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    session_id: str | None = None,
):
    """WebSocket endpoint for terminal emulation using PTY.

    Session routing:
    - No session_id -> create new session (random UUID)
    - Existing alive session -> reuse same PTY, send [Session: session_id]
    - Existing dead session -> create new PTY (old one pending cleanup)

    Disconnect does NOT kill PTY — session persists for reconnects.
    EOF marks session as dead, PTY kept for 30s for potential reconnect.
    """
    import select as _select
    import fcntl
    import struct
    import termios
    import signal

    await websocket.accept()

    # Resolve or create session_id
    if not session_id:
        session_id = str(uuid.uuid4())
    # (no debug print — keep PTY clean)

    async with _pty_lock:
        existing = _terminal_sessions.get(session_id)

        if existing and existing["alive"]:
            # Reuse existing PTY
            session = existing
            session["is_attached"] = True
            session["attach_count"] = session.get("attach_count", 0) + 1
        else:
            # Create new session
            session = await _create_pty_session(session_id)
            session["is_attached"] = True
            session["attach_count"] = 1

    master_fd = session["master_fd"]
    pid = session["pid"]
    loop = asyncio.get_running_loop()
    pending_tasks: list = []

    async def send_pty_output():
        """Called by loop.add_reader when master_fd is readable."""
        try:
            r, _, _ = _select.select([master_fd], [], [], 0.05)
        except Exception:
            return
        if not r:
            return
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            # master_fd was closed (e.g. process died) — unregister ourselves
            try:
                loop.remove_reader(master_fd)
            except Exception:
                pass
            return
        if not data:
            # EOF — bash exited
            async with _pty_lock:
                session["alive"] = False
                session["is_attached"] = False
            try:
                await websocket.send_text("\r\n\x1b[33m[进程已退出]\x1b[0m\r\n")
            except Exception:
                pass
            asyncio.ensure_future(_expire_session(session_id))
            return
        try:
            text = data.decode("utf-8", errors="replace")
            await websocket.send_text(text)
        except Exception:
            pass

    def _on_master_readable():
        """Synchronous callback from loop.add_reader — schedule async task."""
        t = asyncio.create_task(send_pty_output())
        pending_tasks.append(t)
        t.add_done_callback(lambda t: _maybe_remove(t))

    def _maybe_remove(t):
        if t in pending_tasks:
            pending_tasks.remove(t)

    async def _detach():
        """Detach client from session without killing PTY."""
        try:
            loop.remove_reader(master_fd)
        except Exception:
            pass
        async with _pty_lock:
            session["is_attached"] = False
            session["attach_count"] = max(0, session.get("attach_count", 1) - 1)
            alive = session["alive"]
        if not alive:
            asyncio.ensure_future(_expire_session(session_id))
    loop.add_reader(master_fd, _on_master_readable)

    try:
        while True:
            try:
                data = await websocket.receive_text()
            except Exception:
                break

            # Handle window resize: JSON {"type":"resize","cols":80,"rows":24}
            if data.startswith("{"):
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "resize":
                        cols = msg.get("cols", 80)
                        rows = msg.get("rows", 24)
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                        continue
                except Exception:
                    pass

            # Forward keystrokes to PTY master
            cmd = data.encode("utf-8", errors="replace")
            try:
                os.write(master_fd, cmd)
            except OSError as e:
                print(f"[TERMINAL] write error: {e}", flush=True)
                break

    except WebSocketDisconnect:
        print("[TERMINAL] Client disconnected", flush=True)
    except Exception as e:
        print(f"[TERMINAL] error: {e}", flush=True)
    finally:
        await _detach()


# ============================================================================
# Agent Config API
# ============================================================================

from pydantic import BaseModel
from typing import Optional
from agent.config_loader import load_config, save_config
from agent.agent_manager import reload_agents


class AgentToggle(BaseModel):
    enabled: bool


class SetMainRequest(BaseModel):
    main_agent: str


class CustomAgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    instructions: Optional[str] = ""
    enabled: bool = True


@app.get("/api/agent/config")
async def get_agent_config():
    """Return full agent configuration."""
    cfg = load_config()
    return {
        "main_agent": cfg.get("main_agent"),
        "agents": cfg.get("agents", {}),
        "custom_agents": cfg.get("custom_agents", []),
    }


@app.put("/api/agent/config/enabled")
async def toggle_agent(name: str, body: AgentToggle):
    """Enable or disable an agent."""
    cfg = load_config()
    if name in cfg["agents"]:
        cfg["agents"][name]["enabled"] = body.enabled
    else:
        for ca in cfg.get("custom_agents", []):
            if ca["name"].lower().replace(" ", "_") == name:
                ca["enabled"] = body.enabled
                break
        else:
            raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    save_config(cfg)
    reload_agents()
    return {"ok": True, "agent": name, "enabled": body.enabled}


@app.post("/api/agent/config/main")
async def set_main_agent(body: SetMainRequest):
    """Set the main (entry) agent."""
    cfg = load_config()
    key = body.main_agent
    if key not in cfg["agents"] and not any(
        c["name"].lower().replace(" ", "_") == key for c in cfg.get("custom_agents", [])
    ):
        raise HTTPException(status_code=404, detail=f"Agent '{key}' not found")
    cfg["main_agent"] = key
    save_config(cfg)
    reload_agents()
    return {"ok": True, "main_agent": key}


@app.post("/api/agent/config/custom")
async def add_custom_agent(body: CustomAgentCreate):
    """Add a custom agent."""
    cfg = load_config()
    key = body.name.lower().replace(" ", "_")
    if key in cfg["agents"] or any(
        c["name"].lower().replace(" ", "_") == key for c in cfg.get("custom_agents", [])
    ):
        raise HTTPException(status_code=409, detail=f"Agent '{key}' already exists")
    cfg.setdefault("custom_agents", []).append({
        "name": body.name,
        "description": body.description,
        "instructions": body.instructions or f"You are {body.name}.",
        "enabled": body.enabled,
    })
    save_config(cfg)
    reload_agents()
    return {"ok": True, "agent": key}


@app.delete("/api/agent/config/custom/{agent_key}")
async def delete_custom_agent(agent_key: str):
    """Delete a custom agent by key."""
    cfg = load_config()
    original_len = len(cfg.get("custom_agents", []))
    cfg["custom_agents"] = [
        c for c in cfg.get("custom_agents", [])
        if c["name"].lower().replace(" ", "_") != agent_key
    ]
    if len(cfg["custom_agents"]) == original_len:
        raise HTTPException(status_code=404, detail=f"Custom agent '{agent_key}' not found")
    save_config(cfg)
    reload_agents()
    return {"ok": True}


# ============================================================================
# Agent Chat API
# ============================================================================

from pydantic import BaseModel


class ChatCreateRequest(BaseModel):
    agent_id: str = "main"


class ChatMessageRequest(BaseModel):
    message: str


@app.post("/api/agent/chat")
async def create_chat_session(body: ChatCreateRequest):
    """Create a new chat session."""
    session = chat_manager.create_session(agent_id=body.agent_id)
    return {
        "session_id": session.session_id,
        "agent_id": session.agent_id,
        "created_at": session.created_at.isoformat(),
    }


@app.get("/api/agent/chat/{session_id}/stream")
async def chat_session_stream(session_id: str, request: Request):
    """SSE stream for a specific chat session."""

    session = chat_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        # Send chat history as initial events
        for msg in session.messages:
            yield ServerSentEvent(
                event="history",
                data=json.dumps({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "agent_name": msg.agent_name,
                })
            )

        # Stream events from the session queue
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(
                    session.queue.get(),
                    timeout=settings.heartbeat_interval,
                )
                if event is None:
                    break
                yield event
            except asyncio.TimeoutError:
                yield ServerSentEvent(
                    event="heartbeat",
                    data=json.dumps({"status": "alive"}),
                )

    return EventSourceResponse(event_generator())


@app.post("/api/agent/chat/{session_id}/message")
async def send_chat_message(session_id: str, body: ChatMessageRequest):
    """Send a message to a chat session and run the agent."""
    session = chat_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_running:
        raise HTTPException(status_code=409, detail="Agent is already running in this session")

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Append user message
    session.messages.append(ChatMessage(
        role="user",
        content=body.message,
    ))

    # Emit user message to stream
    await session.queue.put(ServerSentEvent(
        event="user_message",
        data=json.dumps({
            "content": body.message,
            "timestamp": datetime.now().isoformat(),
        })
    ))

    session.is_running = True

    # Emit thinking status
    await session.queue.put(ServerSentEvent(
        event="agent_status",
        data=json.dumps({
            "status": "running",
            "message": "正在思考...",
        })
    ))

    # Run agent in background and stream output to session queue
    task = asyncio.create_task(_run_chat_agent(session, body.message))
    session.set_task(task)

    return {"ok": True, "session_id": session_id}


async def _run_chat_agent(session, message: str):
    """Run the agent for a chat session and stream results."""
    from agents import Runner
    from agents.stream_events import StreamEvent

    try:
        # Get agent from session (may have been switched via PATCH)
        agents = _agent_registry.get_all_agents()
        # Case-insensitive lookup: registry keys are lowercase (developer, dispatcher, etc.)
        print(f"[DEBUG] _run_chat_agent: session.agent_id={session.agent_id!r}, looking up {session.agent_id.lower()!r}")
        agent = agents.get(session.agent_id.lower(), agents.get("dispatcher"))

        result = Runner.run_streamed(agent, message)
        current_agent_name = agent.name
        all_output = []

        async for event in result.stream_events():
            ev_type, payload = _classify_chat_event(event, current_agent_name)

            if ev_type == "agent_handoff":
                current_agent_name = payload.get("to_agent", current_agent_name)

            if ev_type == "agent_output":
                all_output.append(payload.get("delta", ""))

            if ev_type and payload:
                await session.queue.put(ServerSentEvent(
                    event=ev_type,
                    data=json.dumps(payload),
                ))

        final_text = "".join(all_output)
        await session.queue.put(ServerSentEvent(
            event="agent_complete",
            data=json.dumps({
                "content": final_text,
                "agent_name": current_agent_name,
            }),
        ))

        # Append assistant message to history
        session.messages.append(ChatMessage(
            role="assistant",
            content=final_text,
            agent_name=current_agent_name,
        ))

    except Exception as exc:
        await session.queue.put(ServerSentEvent(
            event="agent_error",
            data=json.dumps({"error": str(exc)}),
        ))
    finally:
        session.is_running = False


def _classify_chat_event(event: StreamEvent, current_agent_name: str):
    """Convert openai-agents stream event to SSE payload dict (for chat)."""
    if hasattr(event, "type"):
        if event.type == "raw_response_event":
            try:
                chunk = event.data
                if hasattr(chunk, "delta") and chunk.delta:
                    delta = chunk.delta
                    if isinstance(delta, str):
                        text = delta
                    elif hasattr(delta, "text"):
                        text = delta.text
                    else:
                        text = str(delta)
                    if text:
                        return "agent_output", {
                            "agent_name": current_agent_name,
                            "delta": text,
                        }
            except Exception:
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
                        "agent_name": current_agent_name,
                        "delta": text,
                    }
                except Exception:
                    return None, None

            elif name in ("tool_called", "tool_output"):
                return "agent_output", {
                    "agent_name": current_agent_name,
                    "delta": f"[{name}]",
                }

            elif name in ("handoff_requested", "handoff_occurs"):
                return "agent_handoff", {
                    "from_agent": current_agent_name,
                    "to_agent": current_agent_name,
                    "message": f"Handoff from {current_agent_name}",
                }

        elif event.type == "agent_updated_stream_event":
            new_agent = getattr(event, "new_agent", None)
            new_name = new_agent.name if new_agent else current_agent_name
            return "agent_handoff", {
                "from_agent": current_agent_name,
                "to_agent": new_name,
                "message": f"Handoff to {new_name}",
            }

    return None, None


@app.get("/api/agent/chat")
async def list_chat_sessions():
    """List all chat sessions."""
    return {"sessions": chat_manager.list_sessions()}


@app.delete("/api/agent/chat/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    if not chat_manager.close_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@app.patch("/api/agent/chat/{session_id}")
async def patch_chat_session(session_id: str, body: dict | None = None):
    """Update session agent_id."""
    if body is None:
        raise HTTPException(status_code=400, detail="body required")
    agent_id = body.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")
    ok = chat_manager.update_session_agent(session_id, agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "agent_id": agent_id}


@app.post("/api/agent/chat/{session_id}/stop")
async def stop_chat_session(session_id: str):
    """Stop a running agent in a chat session."""
    session = chat_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_running:
        raise HTTPException(status_code=409, detail="No agent running in this session")
    await session.queue.put(ServerSentEvent(
        event="agent_stopped",
        data=json.dumps({"message": "Agent stopped by user"}),
    ))
    stopped = await chat_manager.stop_session(session_id)
    if not stopped:
        raise HTTPException(status_code=500, detail="Failed to stop agent")
    return {"ok": True}



# ============================================================================
# Agent API Endpoints
# ============================================================================

@app.get("/api/agents")
async def list_agents():
    """List all agent instances and their current status."""
    if _agent_orchestrator is None:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    agents = _agent_orchestrator.list_agents()
    return {
        "agents": [a.model_dump() for a in agents],
        "count": len(agents),
    }


@app.post("/api/agents/invoke")
async def invoke_agent(message: dict):
    """Invoke the triage agent with a user message."""
    if _agent_orchestrator is None:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    msg = message.get("message", "")
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")
    from agent.models import InvokeRequest
    req = InvokeRequest(message=msg)
    task_id = await _agent_orchestrator.invoke(req)
    return {"task_id": task_id, "status": "dispatched"}


@app.get("/api/agents/events")
async def agent_events_sse(request: Request):
    """SSE stream for agent events."""

    async def agent_event_generator():
        client_id = str(uuid.uuid4())
        await sse_manager.connect(client_id, request)
        queue = sse_manager._queues[client_id]

        try:
            # Yield initial event
            yield ServerSentEvent(
                event="agent_stream_start",
                data=json.dumps({
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat(),
                })
            )

            # Keep connection alive and yield events from the queue
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=settings.heartbeat_interval
                    )
                    if event is None:
                        break
                    yield event
                except asyncio.TimeoutError:
                    yield ServerSentEvent(
                        event="heartbeat",
                        data=json.dumps({
                            "status": "alive",
                            "timestamp": datetime.now().isoformat(),
                        })
                    )
        finally:
            queue = sse_manager._queues.get(client_id)
            if queue:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            sse_manager.disconnect(client_id)

    return EventSourceResponse(agent_event_generator())


# ============================================================================
# Root
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Hermès Bridge Service",
        "version": "1.1.0",
        "description": "SSE-based bridge service that proxies to Hermès Agent Dashboard API",
        "hermes_api_base": HERMES_API_BASE,
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "connections": "/connections",
            "broadcast": "/broadcast",
            "tasks": "/tasks",
            "history": "/history",
            "api": {
                "status": "/api/status",
                "sessions": "/api/sessions",
                "logs": "/api/logs",
                "analytics": "/api/analytics/usage",
                "config": "/api/config",
                "skills": "/api/skills"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )

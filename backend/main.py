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
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx

from sse_manager import sse_manager
from config import settings

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
    # Startup: start the event generator
    task = asyncio.create_task(generate_events())
    yield
    # Shutdown: cancel the event generator
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


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
    allow_methods=["GET", "POST", "DELETE"],
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
        # Register connection
        await sse_manager.connect(client_id, request)

        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "client_id": client_id,
                    "message": "Connected to Hermès Bridge Service",
                    "hermes_api": HERMES_API_BASE,
                    "timestamp": datetime.now().isoformat()
                })
            }

            # Keep connection alive and handle client disconnect
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send heartbeat to keep connection alive
                await asyncio.sleep(settings.heartbeat_interval)
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "status": "alive",
                        "timestamp": datetime.now().isoformat()
                    })
                }

        finally:
            # Cleanup on disconnect
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

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for terminal emulation - executes commands locally"""
    await websocket.accept()
    
    try:
        # Send welcome message
        await websocket.send_text("\r\n\x1b[36mHermès Terminal\x1b[0m - 终端已连接\r\n")
        await websocket.send_text("输入命令与 Hermès Agent 交互...\r\n\r\n$ ")
        
        while True:
            # Receive command from client
            data = await websocket.receive_text()
            
            # Handle special commands
            if data.strip() == "exit":
                await websocket.send_text("\r\n\x1b[33m再见!\x1b[0m\r\n")
                break
            
            # Execute command locally
            try:
                process = await asyncio.create_subprocess_shell(
                    data,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=os.path.expanduser("~")
                )
                stdout, _ = await process.communicate()
                output = stdout.decode("utf-8", errors="replace") if stdout else ""
                
                if output:
                    # Format output for terminal
                    formatted = output.replace("\n", "\r\n")
                    await websocket.send_text(formatted)
                else:
                    await websocket.send_text("\r\n")
                    
                await websocket.send_text("$ ")
                
            except Exception as e:
                await websocket.send_text(f"\r\n\x1b[31mError: {str(e)}\x1b[0m\r\n$ ")
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f"\r\n\x1b[31mConnection error: {str(e)}\x1b[0m\r\n")
        except:
            pass


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

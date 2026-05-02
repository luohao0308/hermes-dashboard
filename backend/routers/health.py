"""Health, SSE, and connection management endpoints."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from config import settings
from database import SessionLocal
from deps import sse_manager, _provider_registry
from utils.heartbeat import read_all_workers

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _check_database() -> dict:
    """Check DB connectivity and return migration version."""
    result = {"status": "unknown", "migration_version": None, "error": None}
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            result["status"] = "connected"
            row = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            result["migration_version"] = row[0] if row else None
        finally:
            db.close()
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
    return result


def _check_workers() -> dict:
    """Check worker status via file-based heartbeats.

    Uses the shared heartbeat helper. Returns keys with hyphenated
    names for backward compatibility with the /health response format.
    Includes worker_id, pid, and version when available from the
    heartbeat file metadata.
    """
    raw = read_all_workers()
    workers = {}
    for canonical, info in raw.items():
        # Convert underscore name to hyphenated for /health response
        hyphenated = canonical.replace("_", "-")
        entry: dict = {
            "status": info["status"] if info["status"] != "missing" else "unknown",
            "last_seen_seconds_ago": info["age_seconds"],
        }
        if info.get("worker_id"):
            entry["worker_id"] = info["worker_id"]
        if info.get("pid"):
            entry["pid"] = info["pid"]
        if info.get("version"):
            entry["version"] = info["version"]
        workers[hyphenated] = entry
    return workers


@router.get("/sse")
@limiter.limit("30/minute")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for control plane updates."""
    client_id = str(uuid.uuid4())

    async def event_generator():
        await sse_manager.connect(client_id, request)
        queue = sse_manager._queues[client_id]

        try:
            yield ServerSentEvent(
                event="connected",
                data=json.dumps({
                    "client_id": client_id,
                    "message": "Connected to AI Workflow Control Plane",
                    "timestamp": datetime.now().isoformat(),
                }),
            )

            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=settings.heartbeat_interval
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
                        }),
                    )
        finally:
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
            sse_manager.disconnect(client_id)

    return EventSourceResponse(event_generator())


@router.get("/health")
async def health_check():
    """Health check endpoint with DB connectivity and worker status."""
    db_info = _check_database()
    worker_info = _check_workers()

    overall = "healthy"
    if db_info["status"] != "connected":
        overall = "degraded"
    for w in worker_info.values():
        if w["status"] == "error":
            overall = "degraded"

    return {
        "status": overall,
        "service": "ai-workflow-control-plane",
        "version": "3.0.0",
        "active_connections": sse_manager.get_connection_count(),
        "providers": len(_provider_registry.list_providers()),
        "database": db_info,
        "workers": worker_info,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/connections")
async def list_connections():
    """List all active SSE connections."""
    return {
        "count": sse_manager.get_connection_count(),
        "connections": sse_manager.get_all_connections(),
    }


@router.get("/connections/{client_id}")
async def get_connection(client_id: str):
    """Get information about a specific connection."""
    info = sse_manager.get_connection_info(client_id)
    if not info:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"client_id": client_id, **info}

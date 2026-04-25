"""Hermès Bridge Service - FastAPI + SSE Backend"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from sse_manager import sse_manager
from config import settings

# Sample task data for simulation
SAMPLE_TASKS = [
    {"task_id": "1", "name": "示例任务", "status": "running", "progress": 45},
    {"task_id": "2", "name": "数据采集", "status": "pending", "progress": 0},
    {"task_id": "3", "name": "模型推理", "status": "completed", "progress": 100},
]

# Task storage
tasks_db: Dict[str, Dict] = {task["task_id"]: task for task in SAMPLE_TASKS}


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
    description="SSE-based bridge service for Hermès monitoring platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def generate_events():
    """Generate simulated Hermès events periodically"""
    counter = 0
    while True:
        try:
            await asyncio.sleep(settings.event_generation_interval)
            counter += 1

            # Simulate different event types
            if counter % 5 == 0:
                event_type = "task_update"
                data = SAMPLE_TASKS[counter % 3]
            elif counter % 3 == 0:
                event_type = "system_status"
                data = {
                    "status": "healthy",
                    "active_connections": sse_manager.get_connection_count(),
                    "timestamp": datetime.now().isoformat(),
                    "total_tasks": len(tasks_db),
                    "running_tasks": sum(1 for t in tasks_db.values() if t["status"] == "running")
                }
            else:
                event_type = "heartbeat"
                data = {"timestamp": datetime.now().isoformat()}

            # Broadcast to all connected clients
            await sse_manager.broadcast(event_type, data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error generating events: {e}")


@app.get("/sse")
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hermes-bridge",
        "version": "1.0.0",
        "active_connections": sse_manager.get_connection_count()
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


@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return {
        "tasks": list(tasks_db.values()),
        "total": len(tasks_db)
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]


@app.post("/tasks/{task_id}/broadcast")
async def broadcast_task_update(task_id: str):
    """Broadcast a task update event"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    await sse_manager.broadcast("task_update", task)
    
    return {
        "status": "broadcast_sent",
        "task": task
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Hermès Bridge Service",
        "version": "1.0.0",
        "description": "SSE-based bridge service for Hermès monitoring platform",
        "endpoints": {
            "sse": "/sse",
            "health": "/health",
            "connections": "/connections",
            "broadcast": "/broadcast",
            "tasks": "/tasks"
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

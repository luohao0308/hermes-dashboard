"""Hermès Bridge Service - FastAPI + SSE Backend"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

from sse_manager import sse_manager

# Sample task data for simulation
SAMPLE_TASKS = [
    {"task_id": "1", "name": "示例任务", "status": "running"},
    {"task_id": "2", "name": "数据采集", "status": "pending"},
    {"task_id": "3", "name": "模型推理", "status": "completed"},
]

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

app = FastAPI(title="Hermès Bridge Service", lifespan=lifespan)

async def generate_events():
    """Generate simulated Hermès events every second"""
    counter = 0
    while True:
        try:
            await asyncio.sleep(1)
            counter += 1

            # Simulate different event types
            if counter % 5 == 0:
                event_type = "task_update"
                data = SAMPLE_TASKS[counter % 3]
            elif counter % 3 == 0:
                event_type = "system_status"
                data = {
                    "status": "healthy",
                    "active_connections": len(sse_manager.connections),
                    "timestamp": str(asyncio.get_event_loop().time())
                }
            else:
                event_type = "heartbeat"
                data = {"timestamp": str(asyncio.get_event_loop().time())}

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
                    "message": "Connected to Hermès Bridge Service"
                })
            }

            # Keep connection alive and handle client disconnect
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send heartbeat every 30 seconds to keep connection alive
                await asyncio.sleep(30)
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"status": "alive"})
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
        "active_connections": len(sse_manager.connections)
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Hermès Bridge Service",
        "version": "1.0.0",
        "endpoints": {
            "sse": "/sse",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""SSE Connection Manager for Hermès Bridge Service — queue-based broadcast."""

from typing import Dict, Optional
from fastapi import Request
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
import asyncio
import json
from datetime import datetime


class SSEManager:
    """Manages SSE connections via per-client queues and provides broadcast."""

    def __init__(self):
        # client_id -> asyncio.Queue of ServerSentEvent
        self._queues: Dict[str, asyncio.Queue] = {}

    async def connect(self, client_id: str, request: Request) -> str:
        """Register a new SSE connection — create a queue for this client."""
        queue: asyncio.Queue[ServerSentEvent] = asyncio.Queue()
        self._queues[client_id] = queue
        return client_id

    async def event_generator(self, client_id: str):
        """Yield events from this client's queue. Blocks until queue is closed."""
        queue = self._queues.get(client_id)
        if not queue:
            return

        try:
            while True:
                event = await queue.get()
                if event is None:  # Sentinel to signal disconnect
                    break
                yield event
        finally:
            self.disconnect(client_id)

    def disconnect(self, client_id: str):
        """Remove a SSE connection and its queue."""
        if client_id in self._queues:
            del self._queues[client_id]

    def disconnect_sync(self, client_id: str):
        """Synchronous disconnect (for use from non-async contexts)."""
        if client_id in self._queues:
            del self._queues[client_id]

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients by pushing to their queues."""
        if not self._queues:
            print(f"[SSEManager.broadcast] event_type={event_type}, connections=0 — no clients")
            return

        print(f"[SSEManager.broadcast] event_type={event_type}, connections={len(self._queues)}")
        disconnected = []

        for client_id, queue in list(self._queues.items()):
            try:
                queue.put_nowait(ServerSentEvent(
                    event=event_type,
                    data=json.dumps(data, ensure_ascii=False, default=str),
                ))
            except asyncio.QueueFull:
                print(f"[SSEManager.broadcast] Queue full for {client_id}, marking disconnected")
                disconnected.append(client_id)
            except Exception as e:
                print(f"[SSEManager.broadcast] Error for {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    def get_connection_count(self) -> int:
        return len(self._queues)

    def get_connection_info(self, client_id: str):
        return {"client_id": client_id} if client_id in self._queues else None

    def get_all_connections(self):
        return [{"client_id": cid} for cid in self._queues]


# Global SSE manager instance
sse_manager = SSEManager()

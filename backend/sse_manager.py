"""SSE Connection Manager for Hermès Bridge Service"""

from typing import Dict, List
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import json

class SSEManager:
    """Manages all SSE connections and provides broadcast functionality"""

    def __init__(self):
        self.connections: Dict[str, Request] = {}

    async def connect(self, client_id: str, request: Request):
        """Register a new SSE connection"""
        self.connections[client_id] = request

    def disconnect(self, client_id: str):
        """Remove a SSE connection"""
        if client_id in self.connections:
            del self.connections[client_id]

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients"""
        if not self.connections:
            return

        message = self._format_sse_message(event_type, data)
        # Create tasks for all connected clients
        async def send_to_client(client_id: str, request: Request):
            try:
                # Send event to client
                await request.send({
                    "event": event_type,
                    "data": json.dumps(data)
                })
            except Exception as e:
                print(f"Error sending to client {client_id}: {e}")
                self.disconnect(client_id)

        # Note: This is a simplified broadcast - in production you'd want proper client tracking
        for client_id in list(self.connections.keys()):
            asyncio.create_task(send_to_client(client_id, self.connections[client_id]))

    def _format_sse_message(self, event_type: str, data: dict) -> str:
        """Format data as SSE message"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

# Global SSE manager instance
sse_manager = SSEManager()

"""SSE Connection Manager for Hermès Bridge Service"""

from typing import Dict, List, Optional
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
from datetime import datetime

class SSEManager:
    """Manages all SSE connections and provides broadcast functionality"""

    def __init__(self):
        self.connections: Dict[str, Dict] = {}

    async def connect(self, client_id: str, request: Request) -> str:
        """Register a new SSE connection"""
        self.connections[client_id] = {
            "request": request,
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        return client_id

    def disconnect(self, client_id: str):
        """Remove a SSE connection"""
        if client_id in self.connections:
            del self.connections[client_id]

    def update_activity(self, client_id: str):
        """Update last activity timestamp for a client"""
        if client_id in self.connections:
            self.connections[client_id]["last_activity"] = datetime.now().isoformat()

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast an event to all connected clients"""
        if not self.connections:
            return

        disconnected_clients = []

        # Send to all clients concurrently
        tasks = [self._send_to_client(client_id, event_type, data) for client_id in list(self.connections.keys())]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Cleanup disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def _send_to_client(self, client_id: str, event_type: str, data: dict):
        """Send an event to a specific client"""
        conn_info = self.connections.get(client_id)
        if not conn_info:
            return False

        try:
            await conn_info["request"].send({
                "event": event_type,
                "data": json.dumps(data)
            })
            self.update_activity(client_id)
            return True
        except Exception as e:
            print(f"Error sending to client {client_id}: {e}")
            self.disconnect(client_id)
            return False

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)

    def get_connection_info(self, client_id: str) -> Optional[Dict]:
        """Get information about a specific connection"""
        return self.connections.get(client_id)

    def get_all_connections(self) -> List[Dict]:
        """Get information about all connections"""
        return [
            {"client_id": cid, **info}
            for cid, info in self.connections.items()
        ]

    def _format_sse_message(self, event_type: str, data: dict) -> str:
        """Format data as SSE message"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

# Global SSE manager instance
sse_manager = SSEManager()

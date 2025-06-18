from typing import Dict, Set
from fastapi import WebSocket
import json
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_notification(self, user_id: int, notification: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(notification)
                except Exception:
                    # Handle connection errors
                    pass

    async def broadcast_to_group(self, group_member_ids: list, notification: dict):
        for user_id in group_member_ids:
            await self.send_notification(user_id, notification)

    def format_notification(self, notification_type: str, data: dict) -> dict:
        return {
            "type": notification_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

# Create a global instance
websocket_manager = WebSocketManager() 
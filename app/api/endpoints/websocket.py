from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Set
import json

from ...services.redis import redis_service
from ...core.auth import get_current_user_ws
from ...models.user import User
from ...models.group import GroupMember

router = APIRouter()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # group_id -> Set[WebSocket]

    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = set()
        self.active_connections[group_id].add(websocket)

    def disconnect(self, websocket: WebSocket, group_id: int):
        if group_id in self.active_connections:
            self.active_connections[group_id].discard(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]

    async def broadcast_to_group(self, message: str, group_id: int):
        if group_id in self.active_connections:
            for connection in self.active_connections[group_id]:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(connection, group_id)

manager = ConnectionManager()

@router.websocket("/ws/groups/{group_id}/trades")
async def websocket_endpoint(
    websocket: WebSocket,
    group_id: int,
    current_user: User = Depends(get_current_user_ws)
):
    # Check if user is a member of the group
    if not any(m.group_id == group_id for m in current_user.memberships):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    await manager.connect(websocket, group_id)
    
    try:
        # Subscribe to Redis channel for this group
        async for message in redis_service.subscribe(f"group:{group_id}"):
            await websocket.send_text(message)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, group_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, group_id) 
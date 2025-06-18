from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...services.notification import NotificationService
from ...services.websocket import websocket_manager
from ...schemas.notification import (
    NotificationInDB,
    NotificationPreferenceInDB,
    NotificationPreferenceUpdate,
    NotificationCreate
)
from ...core.auth import get_current_user
from ...models.user import User

router = APIRouter()

@router.get("/notifications", response_model=List[NotificationInDB])
async def get_notifications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    return await notification_service.get_user_notifications(current_user.id, skip, limit)

@router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    count = await notification_service.get_unread_count(current_user.id)
    return {"count": count}

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    notification = await notification_service.mark_notification_read(notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    await notification_service.mark_all_notifications_read(current_user.id)
    return {"message": "All notifications marked as read"}

@router.get("/notifications/preferences", response_model=NotificationPreferenceInDB)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    preferences = await notification_service.get_notification_preferences(current_user.id)
    if not preferences:
        raise HTTPException(status_code=404, detail="Notification preferences not found")
    return preferences

@router.put("/notifications/preferences", response_model=NotificationPreferenceInDB)
async def update_notification_preferences(
    preferences: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    return await notification_service.update_notification_preferences(current_user.id, preferences)

@router.websocket("/ws/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Verify token and get user
        user = await get_current_user(token, db)
        await websocket_manager.connect(websocket, user.id)
        
        try:
            while True:
                # Keep connection alive and handle any incoming messages
                data = await websocket.receive_text()
                # Handle any client messages if needed
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket, user.id)
    except Exception as e:
        await websocket.close()
        raise HTTPException(status_code=401, detail="Invalid authentication")

@router.post("/test-notification")
async def create_test_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notification_service = NotificationService(db)
    notification = NotificationCreate(
        user_id=current_user.id,
        type="TEST",
        title="Test Notification",
        message="This is a test notification",
        data={"test": True}
    )
    return await notification_service.create_notification(notification) 
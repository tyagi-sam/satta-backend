from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from ..models.notification import Notification, NotificationPreference
from ..models.group import GroupMember
from ..schemas.notification import NotificationCreate, NotificationUpdate, NotificationPreferenceCreate, NotificationPreferenceUpdate

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, notification: NotificationCreate) -> Notification:
        db_notification = Notification(**notification.dict())
        self.db.add(db_notification)
        await self.db.commit()
        await self.db.refresh(db_notification)
        return db_notification

    async def get_user_notifications(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Notification]:
        query = select(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_notification_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        query = select(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id)
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_notifications_read(self, user_id: int) -> None:
        query = select(Notification).filter(Notification.user_id == user_id, Notification.is_read == False)
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
        
        await self.db.commit()

    async def get_unread_count(self, user_id: int) -> int:
        query = select(Notification).filter(Notification.user_id == user_id, Notification.is_read == False)
        result = await self.db.execute(query)
        return len(result.scalars().all())

    def get_notification_preferences(self, user_id: int) -> Optional[NotificationPreference]:
        return self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).first()

    def create_notification_preferences(
        self, 
        preferences: NotificationPreferenceCreate
    ) -> NotificationPreference:
        db_preferences = NotificationPreference(**preferences.model_dump())
        self.db.add(db_preferences)
        self.db.commit()
        self.db.refresh(db_preferences)
        return db_preferences

    def update_notification_preferences(
        self, 
        user_id: int, 
        preferences: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        db_preferences = self.get_notification_preferences(user_id)
        if not db_preferences:
            raise HTTPException(status_code=404, detail="Notification preferences not found")
        
        for key, value in preferences.model_dump().items():
            setattr(db_preferences, key, value)
        
        self.db.commit()
        self.db.refresh(db_preferences)
        return db_preferences

    async def create_trade_notification(
        self, user_id: int, trade_type: str, symbol: str, quantity: int, price: float
    ) -> Notification:
        notification = NotificationCreate(
            user_id=user_id,
            type="TRADE",
            title=f"{trade_type.title()} Trade Executed",
            message=f"Successfully executed {trade_type.lower()} trade for {quantity} shares of {symbol} at ₹{price:.2f}",
            data={"trade_type": trade_type, "symbol": symbol, "quantity": quantity, "price": price}
        )
        return await self.create_notification(notification)

    async def create_group_trade_notification(
        self,
        group_id: int,
        leader_id: int,
        trade_data: Dict[str, Any]
    ) -> List[Notification]:
        """
        Create notifications for all group members when a leader executes a trade.
        """
        # Get all group members except the leader
        query = select(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id != leader_id
        )
        result = await self.db.execute(query)
        group_members = result.scalars().all()

        notifications = []
        for member in group_members:
            notification = NotificationCreate(
                user_id=member.user_id,
                type="GROUP_TRADE",
                title="New Group Trade",
                message=f"Leader executed a {trade_data['side']} trade for {trade_data['quantity']} shares of {trade_data['symbol']} at ₹{trade_data['price']:.2f}",
                data={
                    "group_id": group_id,
                    "trade_data": trade_data,
                    "leader_id": leader_id
                }
            )
            created_notification = await self.create_notification(notification)
            notifications.append(created_notification)

        return notifications 
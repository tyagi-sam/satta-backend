from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime

from ..models.trade import Trade
from ..models.group import Group, GroupMember
from ..schemas.trade import TradeCreate, TradeUpdate
from .notification import NotificationService
from .websocket import websocket_manager

class TradeService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def create_trade(self, trade: TradeCreate, user_id: int) -> Trade:
        db_trade = Trade(**trade.model_dump(), user_id=user_id)
        self.db.add(db_trade)
        self.db.commit()
        self.db.refresh(db_trade)

        # Get the group members
        group = self.db.query(Group).filter(Group.id == trade.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Create notification for all group members except the trader
        group_members = self.db.query(GroupMember).filter(
            GroupMember.group_id == trade.group_id,
            GroupMember.user_id != user_id
        ).all()

        # Prepare trade data for notification
        trade_data = {
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "trade_id": db_trade.id
        }

        # Create notifications for each group member
        for member in group_members:
            # Create database notification
            self.notification_service.create_trade_notification(
                user_id=member.user_id,
                group_id=trade.group_id,
                trade_data=trade_data
            )

            # Send real-time notification via WebSocket
            websocket_manager.send_notification(
                member.user_id,
                websocket_manager.format_notification(
                    "TRADE_EXECUTED",
                    {
                        "trade": trade_data,
                        "group_name": group.name,
                        "trader_name": db_trade.user.name
                    }
                )
            )

        return db_trade

    def get_trades(
        self,
        user_id: int,
        group_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        query = self.db.query(Trade).filter(Trade.user_id == user_id)
        
        if group_id:
            query = query.filter(Trade.group_id == group_id)
        
        return query.order_by(Trade.created_at.desc()).offset(skip).limit(limit).all()

    def get_trade(self, trade_id: int, user_id: int) -> Trade:
        trade = self.db.query(Trade).filter(
            Trade.id == trade_id,
            Trade.user_id == user_id
        ).first()
        
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return trade

    def update_trade(self, trade_id: int, trade: TradeUpdate, user_id: int) -> Trade:
        db_trade = self.get_trade(trade_id, user_id)
        
        for key, value in trade.model_dump(exclude_unset=True).items():
            setattr(db_trade, key, value)
        
        self.db.commit()
        self.db.refresh(db_trade)
        return db_trade

    def delete_trade(self, trade_id: int, user_id: int) -> None:
        db_trade = self.get_trade(trade_id, user_id)
        self.db.delete(db_trade)
        self.db.commit() 
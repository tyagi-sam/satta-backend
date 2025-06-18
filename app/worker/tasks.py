import json
from typing import List, Dict
from sqlalchemy.orm import Session
from celery import Task
import asyncio

from .celery_app import celery_app
from ..db.session import SessionLocal
from ..services.zerodha import zerodha_service
from ..services.redis import redis_service
from ..models.user import User
from ..models.group import Group
from ..models.trade import Trade
from ..services.trade_executor import trade_executor

class DatabaseTask(Task):
    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
            # Initialize trade executor with DB session
            trade_executor.db = self._db
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None

@celery_app.task(base=DatabaseTask, bind=True)
async def poll_user_trades(self, user_id: int):
    """Poll trades for a specific user and broadcast to their groups"""
    try:
        # Get user and their groups
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.zerodha_access_token:
            return

        # Set up Zerodha client
        zerodha_service.set_access_token(user.zerodha_access_token)
        
        # Get latest trades
        trades_data = zerodha_service.get_trades()
        
        # Process each trade
        for trade_data in trades_data:
            trade = zerodha_service.parse_trade(trade_data)
            if not trade:
                continue
                
            # Set leader and check if trade already exists
            trade.leader_id = user.id
            existing_trade = self.db.query(Trade).filter(
                Trade.zerodha_order_id == trade.zerodha_order_id
            ).first()
            
            if existing_trade:
                continue
            
            # For each group the user leads
            for group in user.led_groups:
                if not group.is_active:
                    continue
                    
                # Create trade copy for this group
                group_trade = Trade(
                    leader_id=trade.leader_id,
                    group_id=group.id,
                    zerodha_order_id=trade.zerodha_order_id,
                    symbol=trade.symbol,
                    side=trade.side,
                    quantity=trade.quantity,
                    price=trade.price,
                    trade_type=trade.trade_type,
                    status=trade.status,
                    trigger_price=trade.trigger_price,
                    executed_at=trade.executed_at
                )
                
                self.db.add(group_trade)
                self.db.commit()
                
                # Execute mirror trades for followers
                mirror_trades = await trade_executor.execute_mirror_trades(group_trade)
                
                # Broadcast to group members via Redis
                trade_message = {
                    "type": "trade",
                    "data": {
                        "id": group_trade.id,
                        "leader_name": user.name,
                        "symbol": trade.symbol,
                        "side": trade.side.value,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "executed_at": trade.executed_at.isoformat(),
                        "mirror_trades": [
                            {
                                "id": mt.id,
                                "follower_id": mt.follower_id,
                                "quantity": mt.quantity,
                                "status": mt.status
                            } for mt in mirror_trades
                        ]
                    }
                }
                
                await redis_service.publish(
                    f"group:{group.id}",
                    json.dumps(trade_message)
                )
                
    except Exception as e:
        print(f"Error polling trades for user {user_id}: {e}")
        self.retry(countdown=5, max_retries=3)

@celery_app.task
def schedule_trade_polling():
    """Schedule individual polling tasks for each active leader"""
    db = SessionLocal()
    try:
        # Get all active users who are group leaders
        leaders = db.query(User).join(Group, User.id == Group.leader_id)\
            .filter(User.is_active == True, Group.is_active == True)\
            .distinct().all()
        
        # Schedule individual polling tasks
        for leader in leaders:
            poll_user_trades.delay(leader.id)
            
    finally:
        db.close()

@celery_app.task(base=DatabaseTask, bind=True)
async def update_trade_status(self, trade_id: int):
    """Update trade status and PnL"""
    try:
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return
            
        # Get user's Zerodha credentials
        user = self.db.query(User).filter(User.id == trade.follower_id or trade.leader_id).first()
        if not user or not user.zerodha_access_token:
            return
            
        # Get trade status from Zerodha
        zerodha_service.set_access_token(user.zerodha_access_token)
        trade_status = zerodha_service.get_order_status(trade.zerodha_order_id)
        
        if trade_status:
            trade.status = trade_status["status"]
            trade.executed_price = trade_status.get("average_price")
            trade.realized_pnl = trade_status.get("pnl")
            self.db.commit()
            
            # Broadcast status update
            trade_message = {
                "type": "trade_update",
                "data": {
                    "id": trade.id,
                    "status": trade.status,
                    "executed_price": trade.executed_price,
                    "realized_pnl": trade.realized_pnl
                }
            }
            
            await redis_service.publish(
                f"group:{trade.group_id}",
                json.dumps(trade_message)
            )
            
    except Exception as e:
        print(f"Error updating trade status for trade {trade_id}: {e}")
        self.retry(countdown=5, max_retries=3) 
from typing import List, Optional
from datetime import datetime
import asyncio
import json

from ..models import Trade, User, Group, GroupMember
from ..services.zerodha import zerodha_service
from ..services.redis import redis_service
from ..core.logger import logger

class TradeExecutor:
    def __init__(self, db_session):
        self.db = db_session
        
    async def execute_mirror_trades(self, leader_trade: Trade) -> List[Trade]:
        """
        Execute mirror trades for all followers in the group
        """
        try:
            # Get the group and its active members
            group = self.db.query(Group).filter(Group.id == leader_trade.group_id).first()
            if not group or not group.is_active:
                logger.warning(f"Group {leader_trade.group_id} not found or inactive")
                return []
                
            members = self.db.query(GroupMember).filter(
                GroupMember.group_id == group.id,
                GroupMember.status == "ACTIVE"
            ).all()
            
            mirror_trades = []
            
            # Execute trade for each member
            for member in members:
                try:
                    # Skip if member is the leader
                    if member.user_id == leader_trade.leader_id:
                        continue
                        
                    # Get member's Zerodha credentials
                    member_user = self.db.query(User).filter(User.id == member.user_id).first()
                    if not member_user or not member_user.zerodha_access_token:
                        logger.warning(f"User {member.user_id} not found or no Zerodha access")
                        continue
                    
                    # Calculate member's position size based on risk settings
                    quantity = self._calculate_position_size(
                        leader_trade.quantity,
                        member.risk_factor or 1.0
                    )
                    
                    if quantity == 0:
                        logger.info(f"Skipping trade for member {member.user_id} due to zero quantity")
                        continue
                    
                    # Execute trade using member's Zerodha account
                    zerodha_service.set_access_token(member_user.zerodha_access_token)
                    order_id = zerodha_service.place_order(
                        symbol=leader_trade.symbol,
                        side=leader_trade.side,
                        quantity=quantity,
                        order_type=leader_trade.order_type,
                        price=leader_trade.price,
                        trigger_price=leader_trade.trigger_price
                    )
                    
                    if not order_id:
                        logger.error(f"Failed to place order for member {member.user_id}")
                        continue
                    
                    # Create mirror trade record
                    mirror_trade = Trade(
                        leader_id=leader_trade.leader_id,
                        follower_id=member.user_id,
                        group_id=group.id,
                        parent_trade_id=leader_trade.id,
                        zerodha_order_id=order_id,
                        symbol=leader_trade.symbol,
                        side=leader_trade.side,
                        quantity=quantity,
                        price=leader_trade.price,
                        trade_type=leader_trade.trade_type,
                        status="PENDING",
                        trigger_price=leader_trade.trigger_price,
                        executed_at=datetime.utcnow()
                    )
                    
                    self.db.add(mirror_trade)
                    self.db.commit()
                    mirror_trades.append(mirror_trade)
                    
                    # Broadcast mirror trade via WebSocket
                    await self._broadcast_mirror_trade(mirror_trade, member_user.name)
                    
                except Exception as e:
                    logger.error(f"Error executing mirror trade for member {member.user_id}: {str(e)}")
                    continue
            
            return mirror_trades
            
        except Exception as e:
            logger.error(f"Error in execute_mirror_trades: {str(e)}")
            return []
    
    def _calculate_position_size(self, leader_quantity: int, risk_factor: float) -> int:
        """Calculate follower's position size based on risk factor"""
        return int(leader_quantity * risk_factor)
    
    async def _broadcast_mirror_trade(self, trade: Trade, member_name: str):
        """Broadcast mirror trade update via WebSocket"""
        try:
            trade_message = {
                "type": "mirror_trade",
                "data": {
                    "id": trade.id,
                    "follower_name": member_name,
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "executed_at": trade.executed_at.isoformat()
                }
            }
            
            await redis_service.publish(
                f"group:{trade.group_id}",
                json.dumps(trade_message)
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting mirror trade: {str(e)}")

trade_executor = TradeExecutor(None)  # Will be initialized with session in worker 
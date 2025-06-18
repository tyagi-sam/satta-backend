from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, date
from ..database import get_db
from ..models import Trade, User, Group, GroupMember
from ..schemas.trade import TradeResponse, TradeCreate, TradeHistoryParams
from ..dependencies import get_current_user, verify_token
from ..services.zerodha import ZerodhaService
from ..services.websocket import WebSocketManager

router = APIRouter(prefix="/trades", tags=["trades"])
ws_manager = WebSocketManager()

@router.get("/leader/{leader_id}", response_model=List[TradeResponse])
async def get_leader_trades(
    leader_id: int,
    params: TradeHistoryParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if current user is a member of any group led by the leader
    member_groups = db.query(GroupMember).join(Group).filter(
        and_(
            GroupMember.user_id == current_user.id,
            Group.leader_id == leader_id
        )
    ).all()
    
    if not member_groups and current_user.id != leader_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these trades")
    
    # Build query filters
    filters = [Trade.leader_id == leader_id]
    
    if params.start_date:
        filters.append(Trade.created_at >= datetime.combine(params.start_date, datetime.min.time()))
    if params.end_date:
        filters.append(Trade.created_at <= datetime.combine(params.end_date, datetime.max.time()))
    if params.instrument_type:
        filters.append(Trade.instrument_type == params.instrument_type)
    if params.status:
        filters.append(Trade.status == params.status)
    
    trades = db.query(Trade).filter(and_(*filters)).order_by(Trade.created_at.desc()).all()
    return trades

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        # Verify token and get user
        user = await verify_token(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        await ws_manager.connect(websocket, client_id)
        
        # Get user's groups (either as leader or member)
        user_groups = (
            db.query(Group)
            .filter(
                or_(
                    Group.leader_id == user.id,
                    Group.id.in_(
                        db.query(GroupMember.group_id)
                        .filter(GroupMember.user_id == user.id)
                        .subquery()
                    )
                )
            )
            .all()
        )
        
        # Register client to their groups
        for group in user_groups:
            ws_manager.register_to_group(client_id, group.id)
        
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages if needed
        except WebSocketDisconnect:
            pass
        finally:
            # Cleanup on disconnect
            for group in user_groups:
                ws_manager.unregister_from_group(client_id, group.id)
            await ws_manager.disconnect(client_id)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

# Helper function to broadcast trade updates
async def broadcast_trade_update(trade: Trade, group_id: int):
    trade_data = TradeResponse.from_orm(trade).dict()
    await ws_manager.broadcast_to_group(group_id, {
        "type": "trade_update",
        "data": trade_data
    }) 
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel
from enum import Enum

from ...core.auth import get_current_user
from ...db.session import get_db
from ...models.user import User
from ...models.group import GroupMember, MemberRole
from ...models.trade import Trade
from ...services.zerodha import zerodha_service
from ...schemas.trade import TradeResponse, TradePnLResponse

class OrderStatus(str, Enum):
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

router = APIRouter()

@router.get("/groups/{group_id}/trades/today", response_model=List[TradeResponse])
async def get_today_trades(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get today's trades for a group"""
    # Check if user is a member
    member = await db.query(GroupMember)\
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        ).first()
        
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group"
        )
    
    # Get today's trades
    today = date.today()
    trades = await db.query(Trade)\
        .filter(
            Trade.group_id == group_id,
            func.date(Trade.executed_at) == today
        )\
        .order_by(Trade.executed_at.desc())\
        .all()
        
    return trades

@router.get("/groups/{group_id}/pnl/today", response_model=TradePnLResponse)
async def get_today_pnl(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get today's PnL for a group"""
    # Check if user is a member
    member = await db.query(GroupMember)\
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        ).first()
        
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group"
        )
    
    # Get today's trades
    today = date.today()
    trades = await db.query(Trade)\
        .filter(
            Trade.group_id == group_id,
            func.date(Trade.executed_at) == today
        )\
        .order_by(Trade.executed_at.asc())\
        .all()
    
    # Calculate PnL per instrument
    pnl_by_symbol = {}
    total_pnl = 0.0
    
    for trade in trades:
        if trade.symbol not in pnl_by_symbol:
            pnl_by_symbol[trade.symbol] = {
                "realized_pnl": 0.0,
                "trades_count": 0
            }
        
        pnl_by_symbol[trade.symbol]["trades_count"] += 1
        if trade.realized_pnl:
            pnl_by_symbol[trade.symbol]["realized_pnl"] += trade.realized_pnl
            total_pnl += trade.realized_pnl
    
    return {
        "total_pnl": total_pnl,
        "pnl_by_symbol": pnl_by_symbol,
        "trade_count": len(trades)
    }

@router.get("/groups/{group_id}/trades/export")
async def export_trades(
    group_id: int,
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export trades to Excel"""
    # Check if user is a member
    member = await db.query(GroupMember)\
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        ).first()
        
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group"
        )
    
    # Get trades for date range
    trades = await db.query(Trade)\
        .filter(
            Trade.group_id == group_id,
            func.date(Trade.executed_at) >= start_date,
            func.date(Trade.executed_at) <= end_date
        )\
        .order_by(Trade.executed_at.asc())\
        .all()
    
    if not trades:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trades found for the specified date range"
        )
    
    # Create Excel file
    import xlsxwriter
    from io import BytesIO
    
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add headers
    headers = [
        "Date", "Time", "Symbol", "Side", "Quantity",
        "Price", "Trade Type", "Status", "Realized PnL"
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    
    # Add trade data
    for row, trade in enumerate(trades, start=1):
        worksheet.write(row, 0, trade.executed_at.strftime("%Y-%m-%d"))
        worksheet.write(row, 1, trade.executed_at.strftime("%H:%M:%S"))
        worksheet.write(row, 2, trade.symbol)
        worksheet.write(row, 3, trade.side.value)
        worksheet.write(row, 4, trade.quantity)
        worksheet.write(row, 5, trade.price)
        worksheet.write(row, 6, trade.trade_type.value)
        worksheet.write(row, 7, trade.status.value)
        worksheet.write(row, 8, trade.realized_pnl or 0.0)
    
    workbook.close()
    output.seek(0)
    
    filename = f"trades_{start_date}_{end_date}.xlsx"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

class OrdersResponse(BaseModel):
    orders: List[Dict[str, Any]]
    note: str

@router.get("/orders", response_model=OrdersResponse)
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    status: Optional[OrderStatus] = Query(None, description="Filter orders by status")
):
    """Get today's orders from Zerodha for the current user.
    Note: Due to Zerodha API limitations, this endpoint can only fetch today's orders."""
    try:
        if not current_user.zerodha_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Zerodha access token found"
            )
            
        # Set up Zerodha client with user's token (decryption handled in service)
        zerodha_service.set_access_token(current_user.zerodha_access_token)
        
        # Get orders from Zerodha
        orders = zerodha_service.get_orders()
        
        # Filter orders by status if specified
        if status:
            orders = [order for order in orders if order.get("status") == status]
        
        # Add a note about data availability
        return OrdersResponse(
            orders=orders,
            note="This endpoint only returns today's orders due to Zerodha API limitations. Historical orders are not available through the API."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}"
        )

class HoldingsResponse(BaseModel):
    holdings: List[Dict[str, Any]]
    total_investment: float
    total_current_value: float
    total_pnl: float
    total_pnl_percentage: float

@router.get("/holdings", response_model=HoldingsResponse)
async def get_user_holdings(
    current_user: User = Depends(get_current_user)
):
    """Get user's current holdings from Zerodha."""
    try:
        if not current_user.zerodha_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Zerodha access token found"
            )
            
        # Set up Zerodha client with user's token (decryption handled in service)
        zerodha_service.set_access_token(current_user.zerodha_access_token)
        
        # Get holdings from Zerodha
        holdings = zerodha_service.get_holdings()
        
        # Calculate totals
        total_investment = sum(float(holding.get('average_price', 0) * holding.get('quantity', 0)) for holding in holdings)
        total_current_value = sum(float(holding.get('last_price', 0) * holding.get('quantity', 0)) for holding in holdings)
        total_pnl = total_current_value - total_investment
        total_pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        return HoldingsResponse(
            holdings=holdings,
            total_investment=total_investment,
            total_current_value=total_current_value,
            total_pnl=total_pnl,
            total_pnl_percentage=total_pnl_percentage
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch holdings: {str(e)}"
        )

class PositionsResponse(BaseModel):
    positions: List[Dict]
    total_pnl: float
    total_day_pnl: float
    total_investment: float
    total_current_value: float

@router.get("/positions", response_model=PositionsResponse)
async def get_user_positions(
    current_user: User = Depends(get_current_user)
):
    """Get user's current positions from Zerodha."""
    try:
        if not current_user.zerodha_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Zerodha access token found"
            )
            
        # Set up Zerodha client with user's token (decryption handled in service)
        zerodha_service.set_access_token(current_user.zerodha_access_token)
        
        # Get positions from Zerodha
        positions = zerodha_service.get_positions()
        
        # Calculate totals
        total_pnl = sum(float(position.get('pnl', 0)) for position in positions)
        total_day_pnl = sum(float(position.get('day_m2m', 0)) for position in positions)
        total_investment = sum(float(position.get('buy_value', 0)) for position in positions)
        total_current_value = sum(float(position.get('sell_value', 0)) for position in positions)
        
        return PositionsResponse(
            positions=positions,
            total_pnl=total_pnl,
            total_day_pnl=total_day_pnl,
            total_investment=total_investment,
            total_current_value=total_current_value
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch positions: {str(e)}"
        ) 
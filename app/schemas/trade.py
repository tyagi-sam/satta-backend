from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, date
from ..models.trade import TradeSide, TradeType, TradeStatus, InstrumentType

class TradeBase(BaseModel):
    symbol: str
    instrument_type: InstrumentType
    side: TradeSide
    quantity: int
    price: float
    trade_type: TradeType
    status: TradeStatus
    
    # Option specific fields
    strike_price: Optional[float] = None
    expiry_date: Optional[date] = None
    option_type: Optional[str] = None
    
    # Additional fields for complex orders
    trigger_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop_loss: Optional[float] = None
    
    # Market data
    current_market_price: Optional[float] = None
    last_updated_at: Optional[datetime] = None
    
    # PnL tracking
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None

class TradeCreate(TradeBase):
    leader_id: int
    group_id: int
    zerodha_order_id: str

class TradeUpdate(BaseModel):
    status: Optional[TradeStatus] = None
    realized_pnl: Optional[float] = None

class TradeResponse(TradeBase):
    id: int
    leader_id: int
    group_id: int
    zerodha_order_id: str
    executed_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TradePnLResponse(BaseModel):
    total_pnl: float
    pnl_by_symbol: Dict[str, Dict[str, float]]  # symbol -> {realized_pnl, trades_count}
    trade_count: int

class TradeHistoryParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    instrument_type: Optional[InstrumentType] = None
    status: Optional[TradeStatus] = None 
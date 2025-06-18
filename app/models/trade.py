from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Date, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime

class TradeSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeType(str, enum.Enum):
    REGULAR = "REGULAR"
    CO = "CO"
    OCO = "OCO"
    BRACKET = "BRACKET"
    COVER = "COVER"

class TradeStatus(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class InstrumentType(str, enum.Enum):
    EQUITY = "EQUITY"
    OPTION = "OPTION"
    FUTURE = "FUTURE"

class Trade(Base, TimestampMixin):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    parent_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    
    # Trade details
    zerodha_order_id = Column(String, unique=True, nullable=False)
    symbol = Column(String, nullable=False)
    instrument_type = Column(Enum(InstrumentType), nullable=False, default=InstrumentType.EQUITY)
    side = Column(Enum(TradeSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=True)
    trade_type = Column(Enum(TradeType), nullable=False, default=TradeType.REGULAR)
    status = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.PENDING)
    
    # Option specific fields
    strike_price = Column(Float, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    option_type = Column(String, nullable=True)  # CE or PE
    
    # Additional fields for complex orders
    trigger_price = Column(Float, nullable=True)
    stop_loss = Column(Float)
    target = Column(Float)
    trailing_stop_loss = Column(Float)
    
    # Market data
    current_market_price = Column(Float, nullable=True)
    last_price_update = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # PnL tracking
    executed_price = Column(Float, nullable=True)
    realized_pnl = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Relationships
    leader = relationship("User", foreign_keys=[leader_id], back_populates="trades")
    follower = relationship("User", foreign_keys=[follower_id], back_populates="followed_trades")
    group = relationship("Group", back_populates="trades")
    parent_trade = relationship("Trade", remote_side=[id], backref="mirror_trades")
    
    def __repr__(self):
        return f"<Trade {self.id}: {self.symbol} {self.side.value} x{self.quantity}>" 
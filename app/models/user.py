from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=True)  # Nullable for OAuth users
    name = Column(String)
    zerodha_user_id = Column(String, unique=True, index=True)
    zerodha_access_token = Column(String)
    zerodha_refresh_token = Column(String)
    zerodha_token_expiry = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    preferences = Column(JSON, nullable=True)  # JSON for user preferences

    # Relationships
    groups = relationship("GroupMember", back_populates="user")
    trades = relationship("Trade", foreign_keys="[Trade.leader_id]", back_populates="leader")
    followed_trades = relationship("Trade", foreign_keys="[Trade.follower_id]", back_populates="follower")
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False) 
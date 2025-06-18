from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    type = Column(String(50), nullable=False)  # TRADE_EXECUTED, TRADE_MIRRORED, etc.
    title = Column(String(255), nullable=False)
    message = Column(String, nullable=False)
    data = Column(JSON, nullable=True)  # Additional data like trade details
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    group = relationship("Group", back_populates="notifications")

class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    trade_notifications = Column(Boolean, default=True)
    group_notifications = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="notification_preferences") 
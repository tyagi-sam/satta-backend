from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin
import enum

class MemberRole(str, enum.Enum):
    LEADER = "leader"
    MEMBER = "member"

class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    invite_code = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    todays_pnl = Column(Float, nullable=False, default=0.0, server_default='0.0')
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    members = relationship("GroupMember", back_populates="group")
    trades = relationship("Trade", back_populates="group")
    invites = relationship("GroupInvite", back_populates="group")
    notifications = relationship("Notification", back_populates="group")

class GroupMember(Base, TimestampMixin):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False, comment="leader or member")
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, server_default=func.now())

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="groups")

class GroupInvite(Base, TimestampMixin):
    __tablename__ = "group_invites"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    email = Column(String, nullable=False)
    invite_token = Column(String, unique=True, nullable=False)
    is_accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime)

    # Relationships
    group = relationship("Group", back_populates="invites") 
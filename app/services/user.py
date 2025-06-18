from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, or_
from ..models.user import User
from ..models.group import GroupMember, Group, GroupInvite
from ..models.trade import Trade
from ..core.security import get_password_hash, encrypt_sensitive_data, decrypt_sensitive_data

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """
    Delete a user and all their associated data.
    Returns True if successful, False otherwise.
    """
    try:
        # Get the user
        user = await db.get(User, user_id)
        if not user:
            return False
            
        # Delete all group invites for this user's email
        await db.execute(
            GroupInvite.__table__.delete().where(GroupInvite.email == user.email)
        )
        
        # Get all groups where user is the only leader
        result = await db.execute(
            select(Group)
            .join(GroupMember)
            .where(
                and_(
                    GroupMember.user_id == user_id,
                    GroupMember.role == "leader"
                )
            )
        )
        leader_groups = result.scalars().all()
        
        for group in leader_groups:
            # Check if this is the only leader
            result = await db.execute(
                select(GroupMember)
                .where(
                    and_(
                        GroupMember.group_id == group.id,
                        GroupMember.role == "leader",
                        GroupMember.user_id != user_id
                    )
                )
            )
            other_leaders = result.scalar_one_or_none()
            
            if not other_leaders:
                # Delete all trades in the group
                await db.execute(
                    Trade.__table__.delete().where(Trade.group_id == group.id)
                )
                # Delete all members
                await db.execute(
                    GroupMember.__table__.delete().where(GroupMember.group_id == group.id)
                )
                # Delete all invites
                await db.execute(
                    GroupInvite.__table__.delete().where(GroupInvite.group_id == group.id)
                )
                # Delete the group
                await db.delete(group)
        
        # Delete all trades where user is leader or follower
        await db.execute(
            Trade.__table__.delete().where(
                or_(
                    Trade.leader_id == user_id,
                    Trade.follower_id == user_id
                )
            )
        )
        
        # Delete all group memberships
        await db.execute(
            GroupMember.__table__.delete().where(GroupMember.user_id == user_id)
        )
        
        # Finally, delete the user
        await db.delete(user)
        await db.commit()
        
        return True
        
    except Exception as e:
        await db.rollback()
        raise e

def create_user(db: Session, email: str, password: str, name: str) -> User:
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        name=name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_zerodha_tokens(
    db: Session, 
    user_id: int, 
    access_token: str, 
    refresh_token: str,
    zerodha_user_id: str
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.zerodha_access_token = encrypt_sensitive_data(access_token)
        user.zerodha_refresh_token = encrypt_sensitive_data(refresh_token)
        user.zerodha_user_id = zerodha_user_id
        db.commit()
        db.refresh(user)
    return user

def get_zerodha_tokens(db: Session, user_id: int) -> tuple[Optional[str], Optional[str]]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None, None
    
    access_token = decrypt_sensitive_data(user.zerodha_access_token) if user.zerodha_access_token else None
    refresh_token = decrypt_sensitive_data(user.zerodha_refresh_token) if user.zerodha_refresh_token else None
    
    return access_token, refresh_token 
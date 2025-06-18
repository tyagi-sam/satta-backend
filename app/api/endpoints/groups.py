from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
import secrets
import string
from datetime import datetime

from ...db.session import get_db
from ...models.group import Group, GroupMember, MemberRole, GroupInvite
from ...models.user import User
from ...schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberCreate,
    GroupMemberUpdate,
    GroupMemberResponse,
    GroupInviteResponse,
    GroupWithMembersResponse,
    GroupInviteCreate,
    PendingInviteResponse
)
from ...core.auth import get_current_user
from ...core.email import send_invite_email

router = APIRouter()

async def is_group_leader(
    group_id: int,
    user_id: int,
    db: AsyncSession
) -> bool:
    """Check if user is a leader of the group"""
    query = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.role == MemberRole.LEADER,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

def generate_invite_code(length: int = 8) -> str:
    """Generate a random invite code"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.post("/", response_model=GroupResponse)
async def create_group(
    group: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new group with the current user as leader"""
    db_group = Group(
        **group.model_dump(),
        invite_code=generate_invite_code()
    )
    db.add(db_group)
    await db.flush()

    # Add the creator as a leader
    group_member = GroupMember(
        group_id=db_group.id,
        user_id=current_user.id,
        role=MemberRole.LEADER
    )
    db.add(group_member)
    await db.commit()
    await db.refresh(db_group)
    
    return db_group

@router.get("/", response_model=List[GroupResponse])
async def get_user_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all groups where the user is a member"""
    query = select(Group).join(GroupMember).where(
        GroupMember.user_id == current_user.id,
        GroupMember.is_active == True
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{group_id}", response_model=GroupWithMembersResponse)
async def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific group with its members"""
    # Check if user is a member of the group
    member_query = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(member_query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or user not a member"
        )

    # Get group with members
    query = select(Group).where(Group.id == group_id)
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Get all active members with their user details
    members_query = select(GroupMember, User).join(User).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        )
    )
    members_result = await db.execute(members_query)
    members_with_users = members_result.all()

    # Construct response with members
    response = GroupWithMembersResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        invite_code=group.invite_code,
        todays_pnl=group.todays_pnl,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            GroupMemberResponse(
                id=member.id,
                user_id=user.id,
                group_id=group_id,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at,
                updated_at=member.updated_at,
                user_name=user.name,
                user_email=user.email
            )
            for member, user in members_with_users
        ]
    )
    return response

@router.post("/{group_id}/members", response_model=GroupMemberResponse | GroupInviteResponse)
async def invite_member(
    group_id: int,
    member_data: GroupMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite a new member to the group (leaders only)"""
    # Check if current user is a leader
    if not await is_group_leader(group_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group leaders can invite members"
        )

    # Get group details for the email
    group_query = select(Group).where(Group.id == group_id)
    result = await db.execute(group_query)
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Find user by email
    query = select(User).where(User.email == member_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create a pending invite for unregistered user
        invite_token = generate_invite_code(32)  # Longer token for security
        invite = GroupInvite(
            group_id=group_id,
            email=member_data.email,
            invite_token=invite_token
        )
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        
        # Send invite email
        await send_invite_email(
            email_to=member_data.email,
            invite_data={
                "group_name": group.name,
                "group_description": group.description,
                "invite_token": invite_token
            }
        )
        
        return GroupInviteResponse(
            id=invite.id,
            group_id=group_id,
            email=invite.email,
            invite_token=invite.invite_token,
            is_accepted=invite.is_accepted,
            accepted_at=invite.accepted_at,
            created_at=invite.created_at,
            updated_at=invite.updated_at
        )

    # Handle registered user case
    # Check if user is already a member
    member_query = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user.id
        )
    )
    result = await db.execute(member_query)
    existing_member = result.scalar_one_or_none()
    
    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this group"
            )
        existing_member.is_active = True
        member = existing_member
    else:
        member = GroupMember(
            group_id=group_id,
            user_id=user.id,
            role=MemberRole.MEMBER
        )
        db.add(member)
    
    await db.commit()
    await db.refresh(member)
    
    # Send notification email to registered user
    await send_invite_email(
        email_to=user.email,
        invite_data={
            "group_name": group.name,
            "group_description": group.description,
            "invite_token": None  # Not needed for registered users
        }
    )
    
    # Construct response with user details
    return GroupMemberResponse(
        id=member.id,
        user_id=user.id,
        group_id=group_id,
        role=member.role,
        is_active=member.is_active,
        created_at=member.created_at,
        updated_at=member.updated_at,
        user_name=user.name,
        user_email=user.email
    )

@router.get("/invites/{token}", response_model=PendingInviteResponse)
async def get_invite_details(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details about a pending invite"""
    query = select(GroupInvite, Group).join(Group).where(
        and_(
            GroupInvite.invite_token == token,
            GroupInvite.is_accepted == False
        )
    )
    result = await db.execute(query)
    invite_with_group = result.first()
    
    if not invite_with_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite"
        )
    
    invite, group = invite_with_group
    return PendingInviteResponse(
        group_name=group.name,
        group_description=group.description,
        invite_token=invite.invite_token,
        created_at=invite.created_at
    )

@router.post("/invites/{token}/accept", response_model=GroupMemberResponse)
async def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept a group invite after registration"""
    # Find and validate the invite
    query = select(GroupInvite).where(
        and_(
            GroupInvite.invite_token == token,
            GroupInvite.is_accepted == False
        )
    )
    result = await db.execute(query)
    invite = result.scalar_one_or_none()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite"
        )
    
    # Verify the invite was for this user's email
    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invite was not meant for you"
        )
    
    # Create the group membership
    member = GroupMember(
        group_id=invite.group_id,
        user_id=current_user.id,
        role=MemberRole.MEMBER
    )
    db.add(member)
    
    # Mark invite as accepted
    invite.is_accepted = True
    invite.accepted_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(member)
    
    return GroupMemberResponse(
        id=member.id,
        user_id=current_user.id,
        group_id=invite.group_id,
        role=member.role,
        is_active=member.is_active,
        created_at=member.created_at,
        updated_at=member.updated_at,
        user_name=current_user.name,
        user_email=current_user.email
    )

@router.put("/{group_id}/members/{member_id}", response_model=GroupMemberResponse)
async def update_member_role(
    group_id: int,
    member_id: int,
    member_update: GroupMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a member's role (leaders only)"""
    # Check if current user is a leader
    if not await is_group_leader(group_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group leaders can update member roles"
        )

    # Get the member to update
    query = select(GroupMember).where(
        and_(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Update role
    member.role = member_update.role
    await db.commit()
    await db.refresh(member)

    # Get user details for response
    user_query = select(User).where(User.id == member.user_id)
    result = await db.execute(user_query)
    user = result.scalar_one()

    # Construct response
    response = GroupMemberResponse(
        id=member.id,
        user_id=user.id,
        group_id=group_id,
        role=member.role,
        is_active=member.is_active,
        created_at=member.created_at,
        updated_at=member.updated_at,
        user_name=user.name,
        user_email=user.email
    )
    return response

@router.delete("/{group_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from the group (leaders only)"""
    # Check if current user is a leader
    if not await is_group_leader(group_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only group leaders can remove members"
        )

    # Get the member to remove
    query = select(GroupMember).where(
        and_(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Can't remove yourself if you're the last leader
    if member.user_id == current_user.id and member.role == MemberRole.LEADER:
        # Check if there are other active leaders
        leaders_query = select(GroupMember).where(
            and_(
                GroupMember.group_id == group_id,
                GroupMember.role == MemberRole.LEADER,
                GroupMember.user_id != current_user.id,
                GroupMember.is_active == True
            )
        )
        result = await db.execute(leaders_query)
        if not result.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself as the last leader"
            )

    member.is_active = False
    await db.commit()

@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def get_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all members of a group"""
    # Check if user is a member of the group
    member_query = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(member_query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or user not a member"
        )

    # Get all active members with their user details
    query = select(GroupMember, User).join(User).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True
        )
    )
    result = await db.execute(query)
    members_with_users = result.all()

    # Construct response
    return [
        GroupMemberResponse(
            id=member.id,
            user_id=user.id,
            group_id=group_id,
            role=member.role,
            is_active=member.is_active,
            created_at=member.created_at,
            updated_at=member.updated_at,
            user_name=user.name,
            user_email=user.email
        )
        for member, user in members_with_users
    ] 
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from ..models.group import MemberRole

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(GroupBase):
    is_active: Optional[bool] = None

class GroupMemberBase(BaseModel):
    role: MemberRole
    is_active: bool = True

class GroupMemberCreate(BaseModel):
    email: EmailStr  # Changed to use email for inviting members

class GroupMemberUpdate(BaseModel):
    role: MemberRole

class GroupMemberResponse(BaseModel):
    id: int
    user_id: int
    group_id: int
    role: MemberRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Include user details
    user_name: str
    user_email: str

    class Config:
        from_attributes = True

class GroupResponse(GroupBase):
    id: int
    is_active: bool
    invite_code: str
    todays_pnl: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class GroupWithMembersResponse(GroupResponse):
    members: List[GroupMemberResponse]

    class Config:
        from_attributes = True

class GroupInviteCreate(BaseModel):
    email: EmailStr

class GroupInviteResponse(BaseModel):
    id: int
    group_id: int
    email: str
    invite_token: str
    is_accepted: bool
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PendingInviteResponse(BaseModel):
    group_name: str
    group_description: Optional[str]
    invite_token: str
    created_at: datetime

    class Config:
        from_attributes = True 
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    user_id: int
    group_id: Optional[int] = None

class NotificationUpdate(BaseModel):
    is_read: bool
    read_at: Optional[datetime] = None

class NotificationInDB(NotificationBase):
    id: int
    user_id: int
    group_id: Optional[int]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NotificationPreferenceBase(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    trade_notifications: bool = True
    group_notifications: bool = True

class NotificationPreferenceCreate(NotificationPreferenceBase):
    user_id: int

class NotificationPreferenceUpdate(NotificationPreferenceBase):
    pass

class NotificationPreferenceInDB(NotificationPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 
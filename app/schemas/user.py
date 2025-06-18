from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: bool = True

class UserCreate(UserBase):
    zerodha_user_id: str
    zerodha_access_token: str
    zerodha_refresh_token: Optional[str] = None
    zerodha_api_key: str
    zerodha_api_secret: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[Dict] = None

class UserResponse(UserBase):
    id: int
    zerodha_user_id: str
    preferences: Dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None 
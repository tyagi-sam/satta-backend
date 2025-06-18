from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from ..db.session import get_db, get_sync_db
from ..models.user import User
from .logger import logger

# JWT token configuration
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}", exc_info=True)
        raise

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user from JWT token for REST endpoints"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))  # Convert string to integer
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError) as e:  # Also catch ValueError for int conversion
        logger.error(f"JWT validation error: {str(e)}", exc_info=True)
        raise credentials_exception
        
    user = await db.get(User, user_id)
    if user is None:
        logger.error(f"User not found for ID: {user_id}")
        raise credentials_exception
        
    return user

async def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_sync_db)
) -> User:
    """Get current user from JWT token for WebSocket connections"""
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            logger.error("No token provided in WebSocket connection")
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            logger.error("No user ID in token payload")
            raise HTTPException(status_code=403, detail="Invalid token")
            
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.error(f"User not found for ID: {user_id}")
            raise HTTPException(status_code=403, detail="User not found")
            
        return user
        
    except JWTError as e:
        logger.error(f"WebSocket JWT validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=403, detail="Invalid token") 
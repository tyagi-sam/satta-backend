from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import uuid
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.auth import create_access_token, get_current_user
from ...core.config import settings
from ...core.logger import logger
from ...db.session import get_db
from ...models.user import User
from ...services.zerodha import zerodha_service
from ...core.security import verify_password, encrypt_sensitive_data, decrypt_sensitive_data
from ...schemas.token import Token

router = APIRouter()

class TestLoginRequest(BaseModel):
    email: str
    name: str

@router.get("/login/zerodha")
async def login_zerodha():
    """Get Zerodha OAuth login URL"""
    logger.info("Generating Zerodha login URL")
    return {"login_url": zerodha_service.get_login_url()}

@router.get("/callback/zerodha")
async def zerodha_callback(
    request_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Zerodha OAuth callback"""
    try:
        logger.info(f"Processing Zerodha callback with request token: {request_token}")
        
        # Generate session from request token
        logger.debug("Generating session from request token")
        session = zerodha_service.generate_session(request_token)
        logger.info("Successfully generated session")
        
        # Get user profile from Zerodha
        logger.debug("Setting access token and getting user profile")
        zerodha_service.set_access_token(session["access_token"])
        profile = zerodha_service.get_profile()
        logger.info(f"Got profile for user: {profile['user_name']}")
        
        # Find or create user
        logger.debug(f"Looking up user with Zerodha ID: {profile['user_id']}")
        query = select(User).where(User.zerodha_user_id == profile["user_id"])
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.info(f"Creating new user for Zerodha ID: {profile['user_id']}")
            user = User(
                email=profile["email"],
                name=profile["user_name"],
                zerodha_user_id=profile["user_id"]
            )
            db.add(user)
        
        # Update tokens with encryption
        logger.debug("Encrypting and updating user tokens")
        user.zerodha_access_token = encrypt_sensitive_data(session["access_token"])
        if session.get("refresh_token"):
            user.zerodha_refresh_token = encrypt_sensitive_data(session["refresh_token"])
        await db.commit()
        await db.refresh(user)
        logger.info("Successfully updated encrypted user tokens")
        
        # Create JWT token
        logger.debug("Creating JWT token")
        access_token = create_access_token(
            data={"sub": str(user.id)}
        )
        logger.info("Authentication successful")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }
        
    except Exception as e:
        logger.error(f"Error during Zerodha authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during Zerodha authentication: {str(e)}"
        )

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """Refresh Zerodha access token"""
    try:
        if not current_user.zerodha_refresh_token:
            logger.error(f"No refresh token available for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token available"
            )
            
        # TODO: Implement Zerodha token refresh when they add support
        # For now, we'll just return a new JWT
        logger.debug(f"Creating new JWT token for user {current_user.id}")
        access_token = create_access_token(
            data={"sub": str(current_user.id)}
        )
        logger.info(f"Successfully refreshed token for user {current_user.id}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error refreshing token: {str(e)}"
        )

@router.post("/test-login")
async def test_login(
    data: TestLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Development-only endpoint to create test users without Zerodha auth"""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test login only available in development environment"
        )
    
    # Generate a unique test Zerodha ID
    test_zerodha_id = f"TEST_{uuid.uuid4().hex[:8]}"
    
    # Find or create user
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        logger.info(f"Creating new test user: {data.email}")
        user = User(
            email=data.email,
            name=data.name,
            zerodha_user_id=test_zerodha_id
        )
        db.add(user)
    
    # Update tokens with test values (encrypted)
    test_access_token = f"test_access_token_{test_zerodha_id}"
    test_refresh_token = f"test_refresh_token_{test_zerodha_id}"
    user.zerodha_access_token = encrypt_sensitive_data(test_access_token)
    user.zerodha_refresh_token = encrypt_sensitive_data(test_refresh_token)
    await db.commit()
    await db.refresh(user)
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer"
    } 
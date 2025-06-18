from fastapi import APIRouter
from .endpoints import auth, trades, groups, users, notifications

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"]) 
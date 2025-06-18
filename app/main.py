from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

from .core.config import settings
from .api.endpoints import auth, groups, trades, websocket, users, notifications
from .db.session import async_engine
from .models.base import Base

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=True
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://localhost:3000"],  # Both frontend and backend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(groups.router, prefix=f"{settings.API_V1_STR}/groups", tags=["groups"])
app.include_router(trades.router, prefix=f"{settings.API_V1_STR}/trades", tags=["trades"])
app.include_router(websocket.router, prefix=f"{settings.API_V1_STR}/ws", tags=["websocket"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Database error occurred, {str(exc)}"}
    )

@app.on_event("startup")
async def startup():
    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    # Close database connections
    await async_engine.dispose()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import AnyHttpUrl, validator
import secrets

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Zerodha Mirror"
    
    # Security
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Zerodha
    ZERODHA_API_KEY: str
    ZERODHA_API_SECRET: str
    ZERODHA_REQUEST_TOKEN: Optional[str] = None
    ZERODHA_REDIRECT_URL: str
    
    # Encryption
    FERNET_KEY: str  # Base64-encoded 32-byte key for encrypting sensitive data
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Email Settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: str
    MAIL_SERVER: str
    FRONTEND_URL: str
    
    # WebSocket
    WS_URL: str
    NEXT_PUBLIC_WS_URL: str
    
    class Config:
        case_sensitive = True
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Construct database URI if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

settings = Settings() 
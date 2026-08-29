import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AP-3 Digital Twin: From Plant to Watershed"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ap3-plant-to-watershed-super-secret-key-2026-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas
    
    # Database
    # Por defecto inicia con SQLite local listo para usar; para producción o PostgreSQL se configura en .env
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./digitaltwin.db"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

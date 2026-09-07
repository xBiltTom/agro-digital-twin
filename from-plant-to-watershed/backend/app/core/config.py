import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_VALUES = {"", "CHANGE_ME", "ap3-plant-to-watershed-super-secret-key-2026-production"}

class Settings(BaseSettings):
    PROJECT_NAME: str = "AP-3 Digital Twin: From Plant to Watershed"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    
    # Security
    APP_ENV: str = "development"
    SECRET_KEY: str = "CHANGE_ME"
    ENABLE_DEMO_SEED: bool = False
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

    def validate_runtime_security(self) -> None:
        """Reject the documented placeholder outside explicitly local environments."""
        environment = self.APP_ENV.lower()
        if environment not in {"development", "test", "testing"} and self.SECRET_KEY in INSECURE_SECRET_VALUES:
            raise RuntimeError("SECRET_KEY must be a non-default secret outside development/test")
        if environment == "production" and self.ENABLE_DEMO_SEED:
            raise RuntimeError("ENABLE_DEMO_SEED must be false in production")

settings = Settings()

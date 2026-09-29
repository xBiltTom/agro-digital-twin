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
    ENABLE_MVP_BOOTSTRAP: bool = False
    MVP_USGS_SNAPSHOT: str = ""
    MVP_EXTERNAL_MODEL: str = ""
    EXTERNAL_MODELS_DIR: str = "models/external"
    SWAT_PLUS_EXECUTABLE: str = ""
    SWAT_PLUS_PROJECT_DIR: str = ""
    SWAT_PLUS_WORKING_DIRECTORY: str = "data/swat-runs"
    SWAT_PLUS_TIMEOUT_SECONDS: int = 3600
    CMIP6_ARTIFACT_DIR: str = "data/climate/cmip6"
    DATA_ARTIFACT_ROOT: str = "data"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas

    # AI / LLM Configuration (LangChain)
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL_NAME: str = "gemini-2.5-flash"
    
    # Database
    # SQLite remains a local/test fallback. Docker Compose sets canonical PostgreSQL.
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

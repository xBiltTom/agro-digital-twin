import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    args = {"check_same_thread": False}

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para inyectar sesión de base de datos asíncrona."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

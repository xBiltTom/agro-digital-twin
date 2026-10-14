import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def engine_options(database_url: str) -> tuple:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return url, {"connect_args": {"check_same_thread": False}}
    args = {}
    # asyncpg uses ssl, while provider URLs often use libpq's sslmode.
    if "sslmode" in url.query:
        args["ssl"] = url.query["sslmode"]
        url = url.difference_update_query(["sslmode"])
    return url, {"connect_args": args, "pool_size": settings.DB_POOL_SIZE,
                 "max_overflow": settings.DB_MAX_OVERFLOW, "pool_timeout": settings.DB_POOL_TIMEOUT,
                 "pool_pre_ping": True, "pool_recycle": 300}


database_url, options = engine_options(settings.DATABASE_URL)
engine: AsyncEngine = create_async_engine(database_url, echo=False, **options)

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

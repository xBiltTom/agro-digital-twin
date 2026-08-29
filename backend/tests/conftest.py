import pytest_asyncio
from backend.app.core.database import engine, Base, AsyncSessionLocal
from backend.app.services.seed_service import seed_initial_data

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_database():
    """Inicializa tablas y seed para la sesión de pruebas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        await seed_initial_data(session)
    
    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

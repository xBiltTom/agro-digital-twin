import sys
from pathlib import Path

# Garantizar que el directorio backend esté en sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest_asyncio
from app.core.database import engine, Base, AsyncSessionLocal
from app.services.seed_service import seed_initial_data

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

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.migrations import apply_pending_migrations
from app.api.v1.router import api_router
from app.services.seed_service import bootstrap_mvp_data, bootstrap_system_reference_data, seed_legacy_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando AP-3 Digital Twin Platform...")
    settings.validate_runtime_security()
    
    # 1. Crear tablas si no existen
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await apply_pending_migrations(engine)
        logger.info("Tablas de base de datos verificadas/creadas.")
    except Exception as exc:
        if "No such file or directory" in str(exc) or "connect" in str(exc).lower():
            logger.error(
                "\n"
                "================================================================================\n"
                "ERROR DE CONEXIÓN A LA BASE DE DATOS:\n"
                f"No se pudo conectar a: {settings.DATABASE_URL}\n\n"
                "Causas comunes y solución:\n"
                "1. Si estás usando PostgreSQL local (puerto 5432):\n"
                "   -> Verifica que el servicio esté iniciado: sudo systemctl start postgresql\n"
                "2. Si deseas usar SQLite local (sin PostgreSQL):\n"
                "   -> Configura en backend/.env: DATABASE_URL=sqlite+aiosqlite:///./digitaltwin.db\n"
                "================================================================================\n"
            )
        raise exc

    # 2. RBAC is structural data; only legacy fixtures are opt-in.
    async with AsyncSessionLocal() as session:
        await bootstrap_system_reference_data(session)
    if settings.ENABLE_DEMO_SEED:
        async with AsyncSessionLocal() as session:
            await seed_legacy_demo_data(session)
    # MVP fixtures include a local demo user; keep non-demo startup structural only.
    if settings.ENABLE_MVP_BOOTSTRAP and settings.ENABLE_DEMO_SEED:
        async with AsyncSessionLocal() as session:
            await bootstrap_mvp_data(session)

    yield

    logger.info("Apagando AP-3 Digital Twin Platform...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Base demostrativa reproducible con modelos simplificados de planta e hidrología y clima sintético. "
        "Puede ejecutar un baseline SWAT+ real si se configura un binario y proyecto SWAT+ válidos; "
        "no implementa FSPM ni NEX-GDDP-CMIP6."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de enrutador v1
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Salud del Sistema"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Bienvenido a la API del Gemelo Digital 3D AP-3 (From Plant to Watershed)",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }

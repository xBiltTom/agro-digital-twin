import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from sqlalchemy import text, select
from sqlalchemy.orm import load_only
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
                "No se pudo conectar a la base PostgreSQL configurada.\n\n"
                "Causas comunes y solución:\n"
                "Verifica que la instancia local PostgreSQL esté iniciada y que DATABASE_URL apunte a digitaltwin.\n"
                "================================================================================\n"
            )
        raise exc

    # Render's single-process profile cannot resume an interrupted scientific engine.
    if settings.SERIALIZE_SIMULATIONS:
        from app.models.simulation import SimulationRun
        async with AsyncSessionLocal() as session:
            interrupted = (await session.scalars(select(SimulationRun).options(load_only(SimulationRun.id, SimulationRun.status)).where(
                SimulationRun.status.in_(["PENDING", "RUNNING"])))).all()
            for run in interrupted:
                run.status = "FAILED"
                run.finished_at = datetime.now(timezone.utc)
                run.error = {"type": "SERVER_RESTARTED", "message": "El servidor reinició antes de completar la corrida; vuelve a ejecutarla."}
            await session.commit()

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
        "Plataforma reproducible con visualizaciones simplificadas y un piloto científico South Fork "
        "Iowa River con baseline/coupled SWAT+ real y FSPM determinista. "
        "Los artefactos NEX-GDDP-CMIP6 requieren disponibilidad explícita y no se sustituyen con datos sintéticos."
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

app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=4)

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

@app.get("/health/ready", tags=["Salud del Sistema"])
async def database_readiness():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(503, "Database unavailable") from exc
    return {"status": "ready"}

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Bienvenido a la API del Gemelo Digital 3D AP-3 (From Plant to Watershed)",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }

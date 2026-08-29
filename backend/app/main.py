import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import engine, Base, AsyncSessionLocal
from backend.app.api.v1.router import api_router
from backend.app.services.seed_service import seed_initial_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando AP-3 Digital Twin Platform...")
    
    # 1. Crear tablas si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tablas de base de datos verificadas/creadas.")

    # 2. Ejecutar seed de datos iniciales
    async with AsyncSessionLocal() as session:
        await seed_initial_data(session)

    yield

    logger.info("Apagando AP-3 Digital Twin Platform...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Plataforma de Gemelo Digital 3D Multiescala (AP-3) que acopla modelos fisiológicos "
        "individuales de planta con la hidrología de cuencas SWAT y proyecciones climáticas downscaled."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite desarrollo ágil local
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

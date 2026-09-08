from pathlib import Path
from importlib.util import find_spec

from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(prefix="/system", tags=["System"])


@router.get("/capabilities")
async def capabilities():
    swat_ready = bool(settings.SWAT_PLUS_EXECUTABLE and settings.SWAT_PLUS_PROJECT_DIR)
    model_root = Path(settings.EXTERNAL_MODELS_DIR)
    cmip_root = Path(settings.CMIP6_ARTIFACT_DIR)
    keras_available = find_spec("tensorflow") is not None
    return {
        "postgresql": {"status": "ACTIVE" if settings.DATABASE_URL.startswith("postgresql") else "TEST_ONLY_SQLITE"},
        "fastapi": {"status": "ACTIVE"}, "nextjs": {"status": "ACTIVE_IN_STACK"},
        "usgs": {"status": "ACTIVE", "evidence_type": "OBSERVED"},
        "dataset_registry": {"status": "ACTIVE", "evidence_type": "METADATA_AND_ARTIFACTS"},
        "plant_population": {"status": "ACTIVE", "evidence_type": "SIMPLIFIED"},
        "plant_to_field": {"status": "ACTIVE", "evidence_type": "DERIVED"},
        "field_to_hru": {"status": "ACTIVE", "evidence_type": "COARSE_HRU_PROXY"},
        "simplified_hydrology": {"status": "ACTIVE", "evidence_type": "SIMPLIFIED"},
        "ml_joblib": {"status": "ACTIVE"},
        "ml_keras": {"status": "ACTIVE" if keras_available else "NOT_AVAILABLE"},
        "ml_hybrid": {"status": "ACTIVE" if keras_available else "NOT_AVAILABLE",
                      "reason": None if keras_available else "TensorFlow/Keras is not installed"},
        "external_ml": {"status": "READY" if model_root.exists() else "NOT_INSTALLED", "path": str(model_root)},
        "swat_plus": {"status": "ACTIVE" if swat_ready else "NOT_AVAILABLE"},
        "cmip6": {"status": "READY_FOR_ARTIFACT" if not cmip_root.exists() else "ACTIVE_FILE_PROVIDER",
                  "evidence_type": "ARTIFACT_REQUIRED"},
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.external_model import ExternalModel
from app.models.user import User
from app.schemas.external_model import ExternalModelRegister, ExternalModelResponse
from app.services.external_model_bundle import ExternalModelBundleAdapter


router = APIRouter(prefix="/models", tags=["External models"])


@router.get("", response_model=list[ExternalModelResponse])
async def list_models(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_active_user)):
    return (await db.execute(select(ExternalModel).order_by(ExternalModel.created_at.desc()))).scalars().all()


@router.get("/{model_id}", response_model=ExternalModelResponse)
async def get_model(model_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_active_user)):
    model = await db.scalar(select(ExternalModel).where(ExternalModel.id == model_id))
    if not model:
        raise HTTPException(404, "Model not found")
    return model


@router.post("/register", response_model=ExternalModelResponse, status_code=201)
async def register_model(payload: ExternalModelRegister, db: AsyncSession = Depends(get_db),
                         _user: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO"))):
    try:
        adapter = ExternalModelBundleAdapter(payload.artifact_path)
        info = adapter.validate_bundle()
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    existing = await db.scalar(select(ExternalModel).where(ExternalModel.artifact_path == str(adapter.path)))
    model = existing or ExternalModel(artifact_path=str(adapter.path))
    model.name = info["metadata"].get("model_name", adapter.path.name)
    model.target, model.framework = info["target"], info["framework"]
    model.version = info["metadata"].get("dataset_version")
    model.feature_schema, model.metrics, model.checksum = adapter.schema, adapter.metrics, info["checksum"]
    model.bundle_contract_version = info["bundle_contract_version"]
    model.learning_mode = info["learning_mode"]
    model.training_data_type = info["training_data_type"]
    model.training_dataset_version = info["metadata"].get("dataset_version")
    model.status = "VALIDATED"
    model.provenance = {"training_data": info["training_data_type"], "source": "external ModelBundle; independent of Streamlit",
                        "requires_tensorflow": info["requires_tensorflow"], "metadata": info["metadata"]}
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.post("/{model_id}/validate", response_model=ExternalModelResponse)
async def validate_model(model_id: str, db: AsyncSession = Depends(get_db),
                         _user: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO"))):
    model = await db.scalar(select(ExternalModel).where(ExternalModel.id == model_id))
    if not model:
        raise HTTPException(404, "Model not found")
    try:
        info = ExternalModelBundleAdapter(model.artifact_path).validate_bundle()
        model.status, model.checksum = "VALIDATED", info["checksum"]
    except (ValueError, OSError) as exc:
        model.status = "INVALID"
        await db.commit()
        raise HTTPException(422, str(exc)) from exc
    await db.commit()
    await db.refresh(model)
    return model

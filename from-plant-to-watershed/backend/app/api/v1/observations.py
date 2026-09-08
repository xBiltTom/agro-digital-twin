from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.observation import Dataset, StreamflowObservation
from app.models.user import User
from app.schemas.observation import DatasetResponse, StreamflowObservationResponse, UsgsIngestRequest
from app.services.observational_registry import register_usgs_streamflow
from app.services.usgs_streamflow import UsgsStreamflowProvider


router = APIRouter(prefix="/datasets", tags=["Datos observacionales"])


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_active_user),
):
    return (await db.execute(select(Dataset).order_by(Dataset.retrieved_at.desc()))).scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_active_user),
):
    dataset = await db.scalar(select(Dataset).where(Dataset.id == dataset_id))
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return dataset


@router.post("/usgs/ingest", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def ingest_usgs_streamflow(
    request: UsgsIngestRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO")),
):
    try:
        source_url, path, checksum, records, qc = await UsgsStreamflowProvider().fetch_parse_and_store(
            request.station_id, request.start_date, request.end_date
        )
        return await register_usgs_streamflow(db, request.station_id, source_url, path, checksum, records, qc)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/streamflow/observations", response_model=list[StreamflowObservationResponse])
async def list_streamflow_observations(
    station_id: str = Query(pattern=r"^\d{8,15}$"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    statement = select(StreamflowObservation).where(StreamflowObservation.station_id == station_id)
    if start_date:
        statement = statement.where(StreamflowObservation.observed_on >= start_date)
    if end_date:
        statement = statement.where(StreamflowObservation.observed_on <= end_date)
    return (await db.execute(statement.order_by(StreamflowObservation.observed_on))).scalars().all()

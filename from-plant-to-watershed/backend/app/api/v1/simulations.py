from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.user import User
from app.models.watershed import Watershed
from app.models.simulation import ClimateScenario, SimulationRun, SimulationResult
from app.schemas.simulation import (
    SimulationRunCreate,
    SimulationRunResponse,
    SimulationResultResponse,
    ClimateScenarioResponse,
    WatershedResponse
)
from app.api.deps import get_current_active_user, require_roles
from app.services.twin_coupling_engine import TwinCouplingEngine
from scientific_core import RunConfig

router = APIRouter(prefix="/simulations", tags=["Simulaciones simplificadas"])

@router.get("/scenarios/all", response_model=List[ClimateScenarioResponse])
async def list_climate_scenarios(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    stmt = select(ClimateScenario)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/watersheds/all", response_model=List[WatershedResponse])
async def list_watersheds(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    # The reference Corn Belt/USGS watershed is the active demo, while any
    # historical seed records remain available for backwards compatibility.
    stmt = select(Watershed).order_by(desc(Watershed.code))
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("", response_model=List[SimulationRunResponse])
async def list_simulations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    stmt = select(SimulationRun).order_by(desc(SimulationRun.created_at)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=SimulationRunResponse, status_code=status.HTTP_201_CREATED)
async def create_and_run_simulation(
    sim_in: SimulationRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"))
):
    # Validar cuenca
    w_stmt = select(Watershed).where(Watershed.id == sim_in.watershed_id)
    w_res = await db.execute(w_stmt)
    watershed = w_res.scalar_one_or_none()
    if not watershed:
        raise HTTPException(status_code=404, detail="Cuenca hidrográfica no encontrada")

    # Validar escenario
    scen_stmt = select(ClimateScenario).where(ClimateScenario.id == sim_in.scenario_id)
    scen_res = await db.execute(scen_stmt)
    scenario = scen_res.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Escenario climático no encontrado")

    requested_config = sim_in.model_dump(exclude_none=True, mode="json")
    try:
        RunConfig(
            run_id="validation", seed=sim_in.seed, duration_days=sim_in.duration_days,
            watershed_area_km2=watershed.area_km2, temp_anomaly_c=scenario.temp_anomaly_c,
            precip_factor=scenario.precip_factor, co2_ppm=scenario.co2_ppm,
            start_date=sim_in.start_date,
            parameters=sim_in.parameters or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    new_sim = SimulationRun(
        user_id=current_user.id,
        watershed_id=sim_in.watershed_id,
        scenario_id=sim_in.scenario_id,
        name=sim_in.name,
        status="PENDING",
        duration_days=sim_in.duration_days,
        irrigation_efficiency=None,
        parameters=sim_in.parameters or {},
        seed=sim_in.seed,
        requested_config=requested_config,
        mode=sim_in.mode,
        plant_count=sim_in.plant_count,
        hydrology_backend=sim_in.hydrology_backend,
        external_model_id=sim_in.external_model_id,
    )
    db.add(new_sim)
    await db.flush()

    try:
        completed_sim = await TwinCouplingEngine.execute_simulation_run(db, new_sim.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Simulation failed", "type": type(exc).__name__}) from exc
    return completed_sim

@router.get("/{sim_id}", response_model=SimulationRunResponse)
async def get_simulation_detail(
    sim_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    stmt = select(SimulationRun).where(SimulationRun.id == sim_id)
    res = await db.execute(stmt)
    sim = res.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    return sim

@router.get("/{sim_id}/results", response_model=List[SimulationResultResponse])
async def get_simulation_results(
    sim_id: str,
    limit: int = Query(365, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    exists = await db.scalar(select(SimulationRun.id).where(SimulationRun.id == sim_id))
    if not exists:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    stmt = (
        select(SimulationResult)
        .where(SimulationResult.simulation_run_id == sim_id)
        .order_by(SimulationResult.day_index)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()

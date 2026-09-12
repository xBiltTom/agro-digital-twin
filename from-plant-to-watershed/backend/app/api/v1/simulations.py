from typing import List
import copy
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.user import User
from app.models.watershed import Watershed
from app.models.simulation import ClimateScenario, SimulationRun, SimulationResult
from app.models.observation import Dataset
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
            end_date=sim_in.end_date,
            parameters=sim_in.parameters or {},
            management_scenario=sim_in.management_scenario,
            climate_source=sim_in.climate_source,
            station_id=sim_in.station_id,
            dataset_ids=tuple(sim_in.dataset_ids),
            dataset_roles=sim_in.dataset_roles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    datasets = []
    if sim_in.dataset_ids:
        datasets = list((await db.execute(select(Dataset).where(Dataset.id.in_(sim_in.dataset_ids)))).scalars().all())
        found = {dataset.id for dataset in datasets}
        missing = set(sim_in.dataset_ids) - found
        if missing:
            raise HTTPException(status_code=422, detail=f"Datasets not found: {', '.join(sorted(missing))}")
    if sim_in.climate_source != "SYNTHETIC" and not any(sim_in.dataset_roles.get(item.id) == "FORCING" for item in datasets):
        raise HTTPException(status_code=422, detail="Selected climate_source requires a registered FORCING dataset")

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
        management_scenario=sim_in.management_scenario,
        climate_source=sim_in.climate_source,
        dataset_ids=sim_in.dataset_ids,
        dataset_roles=sim_in.dataset_roles,
        station_id=sim_in.station_id,
        start_date=sim_in.start_date,
        end_date=sim_in.end_date,
    )
    db.add(new_sim)
    await db.flush()

    try:
        is_coupled = (requested_config.get("swat_plus") or {}).get("run_type") == "SWAT_MULTISCALE_COUPLED"
        if is_coupled:
            # A coupled request always materializes its experimental control first.
            # Both rows preserve the identical source/configuration except run type.
            experiment_id = str(uuid4())
            coupled_config = copy.deepcopy(requested_config)
            coupled_config["swat_plus"].update({"experiment_id": experiment_id})
            baseline_config = copy.deepcopy(coupled_config)
            baseline_config["swat_plus"]["run_type"] = "SWAT_STANDARD_BASELINE"
            baseline = SimulationRun(
                user_id=current_user.id, watershed_id=sim_in.watershed_id, scenario_id=sim_in.scenario_id,
                name=f"{sim_in.name} [baseline]", status="PENDING", duration_days=sim_in.duration_days,
                irrigation_efficiency=None, parameters=sim_in.parameters or {}, seed=sim_in.seed,
                requested_config=baseline_config, mode=sim_in.mode, plant_count=sim_in.plant_count,
                hydrology_backend=sim_in.hydrology_backend, external_model_id=None,
                management_scenario=sim_in.management_scenario, climate_source=sim_in.climate_source,
                dataset_ids=sim_in.dataset_ids, dataset_roles=sim_in.dataset_roles, station_id=sim_in.station_id,
                start_date=sim_in.start_date, end_date=sim_in.end_date,
            )
            db.add(baseline)
            await db.flush()
            coupled_config["swat_plus"].update({"baseline_run_id": baseline.id, "coupled_run_id": new_sim.id})
            baseline_config["swat_plus"].update({"baseline_run_id": baseline.id, "coupled_run_id": new_sim.id})
            new_sim.requested_config, baseline.requested_config = coupled_config, baseline_config
            await db.commit()
            await TwinCouplingEngine.execute_simulation_run(db, baseline.id)
            completed_sim = await TwinCouplingEngine.execute_simulation_run(db, new_sim.id)
            baseline = await db.scalar(select(SimulationRun).where(SimulationRun.id == baseline.id))
            def _delta(coupled, control):
                return {"baseline": control, "coupled": coupled, "delta_absolute": None if coupled is None or control is None else coupled - control, "delta_percentage": None if coupled is None or control in (None, 0) else (coupled - control) / control * 100.0}
            comparison = {"experiment_id": experiment_id, "baseline_run_id": baseline.id, "coupled_run_id": completed_sim.id,
                          "runoff_mm": _delta(completed_sim.summary_metrics.get("total_runoff_mm"), baseline.summary_metrics.get("total_runoff_mm")),
                          "evapotranspiration_mm": _delta(completed_sim.summary_metrics.get("total_evapotranspiration_mm"), baseline.summary_metrics.get("total_evapotranspiration_mm")),
                          "streamflow_m3s": _delta((completed_sim.summary_metrics.get("water_balance") or {}).get("mean_streamflow_m3s"), (baseline.summary_metrics.get("water_balance") or {}).get("mean_streamflow_m3s"))}
            completed_sim.summary_metrics = {**(completed_sim.summary_metrics or {}), "paired_comparison": comparison}
            completed_sim.provenance = {**(completed_sim.provenance or {}), "experiment": comparison}
            baseline.provenance = {**(baseline.provenance or {}), "experiment": comparison}
            await db.commit()
            await db.refresh(completed_sim)
        else:
            completed_sim = await TwinCouplingEngine.execute_simulation_run(db, new_sim.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={
            "message": str(exc), "type": getattr(exc, "code", type(exc).__name__),
            **({"details": exc.details} if hasattr(exc, "details") else {}),
        }) from exc
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

@router.get("/{sim_id}/swat-results")
async def get_swat_results(
    sim_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Return persisted normalized SWAT+ records without proxy/FSPM fields."""
    sim = await db.scalar(select(SimulationRun).where(SimulationRun.id == sim_id))
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    if (sim.provenance or {}).get("evidence_type") not in {"REAL_SWAT_PLUS", "REAL_SWAT_PLUS_COUPLED"}:
        raise HTTPException(status_code=409, detail={"type": "NOT_AVAILABLE", "message": "This run is not a completed real SWAT+ execution"})
    return {
        "status": sim.status, "run_id": sim.id, "records": sim.monthly_outputs or [],
        "hru_results": (sim.hru_aggregates or {}).get("results", []),
        "water_balance": (sim.summary_metrics or {}).get("water_balance"),
        "provenance": sim.provenance,
    }

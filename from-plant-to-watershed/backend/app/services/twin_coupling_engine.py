"""Application adapter between SQLAlchemy persistence and the pure scientific core."""

from datetime import datetime, timezone
import subprocess

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import ClimateScenario, SimulationResult, SimulationRun
from app.models.watershed import Watershed
from scientific_core import RunConfig, SimulationOrchestrator


def _code_version() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=1, check=True
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


class TwinCouplingEngine:
    """Compatibility name for the persistence adapter; formulas live in scientific_core."""

    @staticmethod
    async def execute_simulation_run(db: AsyncSession, simulation_run_id: str) -> SimulationRun:
        sim_run = (await db.execute(select(SimulationRun).where(SimulationRun.id == simulation_run_id))).scalar_one_or_none()
        if not sim_run:
            raise ValueError(f"Simulación con ID {simulation_run_id} no encontrada")
        watershed = (await db.execute(select(Watershed).where(Watershed.id == sim_run.watershed_id))).scalar_one_or_none()
        scenario = (await db.execute(select(ClimateScenario).where(ClimateScenario.id == sim_run.scenario_id))).scalar_one_or_none()
        if not watershed or not scenario:
            raise ValueError("La corrida requiere una cuenca y un escenario sintético válidos")
        sim_run.status = "RUNNING"
        sim_run.started_at = datetime.now(timezone.utc)
        sim_run.error = None
        await db.commit()
        try:
            requested = sim_run.requested_config or {
                "duration_days": sim_run.duration_days, "seed": sim_run.seed, "parameters": sim_run.parameters or {},
            }
            config = RunConfig(
                run_id=sim_run.id, seed=sim_run.seed, duration_days=sim_run.duration_days,
                watershed_area_km2=watershed.area_km2, temp_anomaly_c=scenario.temp_anomaly_c,
                precip_factor=scenario.precip_factor, co2_ppm=scenario.co2_ppm,
                parameters=sim_run.parameters or {},
            )
            core_run = SimulationOrchestrator().execute(config)
            db.add_all([
                SimulationResult(
                    simulation_run_id=sim_run.id, day_index=row["day_index"], date_str=row["date_str"],
                    precip_mm=row["precip_mm"], temp_c=row["temp_c"], solar_rad_mj=row["solar_rad_mj"],
                    potential_et_mm=row["et0_mm"], actual_et_mm=row["actual_et_mm"],
                    surface_runoff_mm=row["surface_runoff_mm"], percolation_mm=row["percolation_mm"],
                    streamflow_m3s=row["streamflow_m3s"], soil_moisture_vol=row["soil_moisture_vol"],
                    soil_water_depth_mm=row["soil_water_depth_mm"], plant_transpiration_mm=row["actual_transpiration_mm"],
                    root_water_uptake_mm=row["root_water_uptake_mm"], cwsi_stress_index=row["cwsi_stress_index"],
                    sap_flow_velocity_cmh=row["sap_flow_velocity_cmh"],
                    water_balance_residual_mm=row["water_balance_residual_mm"],
                ) for row in core_run.results
            ])
            sim_run.requested_config = requested
            sim_run.effective_config = core_run.effective_config
            sim_run.provenance = {
                **core_run.provenance,
                "watershed_snapshot": {"id": watershed.id, "code": watershed.code, "area_km2": watershed.area_km2},
                "scenario_snapshot": {"id": scenario.id, "code": scenario.code, "evidence_type": "SYNTHETIC"},
                "code_version": _code_version(),
            }
            sim_run.summary_metrics = core_run.summary_metrics
            sim_run.status = "COMPLETED"
            sim_run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(sim_run)
            return sim_run
        except Exception as exc:
            await db.rollback()
            sim_run = (await db.execute(select(SimulationRun).where(SimulationRun.id == simulation_run_id))).scalar_one()
            sim_run.status = "FAILED"
            sim_run.finished_at = datetime.now(timezone.utc)
            sim_run.error = {"type": type(exc).__name__, "message": str(exc)}
            await db.commit()
            raise

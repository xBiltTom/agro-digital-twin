"""Application adapter between SQLAlchemy persistence and the pure scientific core."""

from datetime import date, datetime, timezone
import subprocess

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import ClimateScenario, SimulationResult, SimulationRun
from app.models.observation import StreamflowObservation
from app.models.observation import Dataset
from app.models.external_model import ExternalModel
from app.models.watershed import Watershed
from app.services.external_model_bundle import ExternalModelBundleAdapter
from scientific_core import MultiscaleSimulationOrchestrator, RunConfig, SimulationOrchestrator, ValidationEngine


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
                start_date=date.fromisoformat(requested.get("start_date", "2020-01-01")),
                parameters=sim_run.parameters or {},
                management_scenario=sim_run.management_scenario,
                climate_source=sim_run.climate_source,
            )
            if sim_run.climate_source != "SYNTHETIC":
                raise RuntimeError("Selected climate source is registered for provenance but its forcing adapter is not installed")
            if sim_run.hydrology_backend == "SWAT_PLUS" or sim_run.mode == "SWAT_PLUS":
                raise RuntimeError("SWAT_PLUS is NOT_AVAILABLE: executable/project are not configured")
            core_run = MultiscaleSimulationOrchestrator().execute(config, sim_run.plant_count)
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
            dataset_snapshots = []
            if sim_run.dataset_ids:
                datasets = list((await db.execute(select(Dataset).where(Dataset.id.in_(sim_run.dataset_ids)))).scalars().all())
                dataset_snapshots = [{"id": item.id, "provider": item.provider, "dataset_name": item.dataset_name,
                                      "version": item.version, "evidence_type": item.evidence_type,
                                      "role": "CONTEXT_ONLY"} for item in datasets]
            sim_run.provenance = {
                **core_run.provenance,
                "watershed_snapshot": {"id": watershed.id, "code": watershed.code, "area_km2": watershed.area_km2},
                "scenario_snapshot": {"id": scenario.id, "code": scenario.code, "evidence_type": "SYNTHETIC"},
                "code_version": _code_version(),
                "climate_source": sim_run.climate_source,
                "datasets": dataset_snapshots,
            }
            sim_run.summary_metrics = core_run.summary_metrics
            sim_run.field_aggregates = core_run.field_aggregates
            sim_run.hru_aggregates = core_run.hru_aggregates
            sim_run.plant_sample = list(core_run.plant_sample)
            monthly_outputs = [dict(row) for row in core_run.monthly_outputs]
            station_id = requested.get("station_id", "05451210")
            observations = (await db.execute(
                select(StreamflowObservation).where(StreamflowObservation.station_id == station_id)
                .order_by(StreamflowObservation.observed_on)
            )).scalars().all()
            observed_by_month: dict[str, list[float]] = {}
            for observation in observations:
                if observation.value_m3s is not None and observation.value_m3s >= 0:
                    observed_by_month.setdefault(observation.observed_on.strftime("%Y-%m"), []).append(observation.value_m3s)
            aligned = []
            for row in monthly_outputs:
                values = observed_by_month.get(row["month"])
                if values:
                    row["observed_streamflow_m3s"] = sum(values) / len(values)
                    aligned.append(row)
            if len(aligned) >= 2:
                sim_run.validation = ValidationEngine.compare(
                    [row["observed_streamflow_m3s"] for row in aligned],
                    [row["baseline_streamflow_m3s"] for row in aligned],
                    [row["twin_streamflow_m3s"] for row in aligned],
                )
                sim_run.validation["observation_station_id"] = station_id
                sim_run.validation["aligned_months"] = len(aligned)
            else:
                sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "fewer than two aligned observed months",
                                      "observation_station_id": station_id, "aligned_months": len(aligned),
                                      "interpretation": "DEMONSTRATION_ONLY"}
            sim_run.monthly_outputs = monthly_outputs
            if sim_run.external_model_id:
                registry_model = await db.scalar(select(ExternalModel).where(ExternalModel.id == sim_run.external_model_id))
                if not registry_model:
                    raise ValueError("external model is not registered")
                last = monthly_outputs[-1]
                days = [row for row in core_run.results if row["date_str"].startswith(last["month"])]
                payload = {
                    "precip_mm": sum(row["precip_mm"] for row in days),
                    "temp_mean_c": sum(row["temp_c"] for row in days) / len(days),
                    "solar_radiation": sum(row["solar_rad_mj"] for row in days) / len(days),
                    "soil_moisture": sum(row["soil_moisture_vol"] for row in days) / len(days),
                    "infiltration_mm": sum(max(0.0, row["precip_mm"] - row["surface_runoff_mm"]) for row in days),
                    "lai": core_run.field_aggregates["mean_lai"],
                    "root_depth_m": core_run.field_aggregates["mean_root_depth_cm"] / 100,
                    "transpiration_mm": sum(row["actual_transpiration_mm"] for row in days),
                    "water_stress": sum(row["cwsi_stress_index"] for row in days) / len(days),
                    "et_mm": sum(row["actual_et_mm"] for row in days),
                }
                sim_run.ml_result = ExternalModelBundleAdapter(registry_model.artifact_path).predict(payload)
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

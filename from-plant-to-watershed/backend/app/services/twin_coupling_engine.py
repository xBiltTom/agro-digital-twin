"""Application adapter between SQLAlchemy persistence and the pure scientific core."""

from collections import Counter
import copy
from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
import subprocess
from statistics import fmean
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import ClimateScenario, SimulationResult, SimulationRun
from app.models.observation import Dataset, DatasetArtifact, StreamflowObservation
from app.models.external_model import ExternalModel
from app.models.watershed import Watershed
from app.services.external_model_bundle import ExternalModelBundleAdapter
from app.services.swat_plus_adapter import (
    SwatPlusAdapter,
    require_coupled_preflight_ready,
    swat_run_config_from_request,
)
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper, SwatPlantMappingError
from app.services.playback_database import PlaybackDatabaseStore
from app.services.playback_builder import simplified_frames, swat_frames
from app.services.swat_soil_water import read_hru_gis_ids, read_hru_soils
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.core.config import settings
from app.schemas.coupling import CouplingPlantParameterSummary
from scientific_core import MultiscaleSimulationOrchestrator, PlantPopulation, PlantToFieldAggregator, RunConfig, SimulationOrchestrator, ValidationEngine
from scientific_core.climate_file import NormalizedClimateFileProvider
from scientific_core.units import ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT


def _code_version() -> str | None:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=1, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=2, check=True,
        ).stdout.strip()
        return f"{revision}+dirty" if dirty else revision
    except (OSError, subprocess.SubprocessError):
        return None


def _daily_streamflow_volume_hm3(records: list[dict], water_balance: dict, frequency: str) -> tuple[float | None, str | None]:
    """Integrate only complete daily discharge rates; never infer a daily series from coarser output."""
    if frequency != "DAILY":
        return None, "SWAT+ discharge volume is not integrated from MONTHLY or ANNUAL output"
    coverage = (water_balance.get("period_coverage") or {}).get("streamflow_m3s") or {}
    if coverage.get("complete") is not True:
        return None, "Complete daily outlet discharge is unavailable"
    flows = [row.get("streamflow_m3s") for row in records]
    if not flows or any(not isinstance(flow, (int, float)) or not math.isfinite(flow) for flow in flows):
        return None, "One or more daily outlet discharge values are missing or invalid"
    return sum(float(flow) * 86400.0 for flow in flows) / 1_000_000.0, None


def _build_coupling_field_summary(
    dated_fields: list[tuple[str, dict[str, Any]]],
    seasonal_lai_contracts: list[dict[str, Any]],
    seasonal_weights: list[float] | None = None,
) -> CouplingPlantParameterSummary:
    """Build a mapper-only contract with no unrelated dated field statistics."""
    if not dated_fields or not seasonal_lai_contracts:
        raise ValueError("FSPM seasonal field states and LAI contracts are required for SWAT+ coupling")

    peak_lai_date, peak_lai_field = max(dated_fields, key=lambda item: item[1]["mean_LAI"])
    peak_height_date, peak_height_field = max(
        dated_fields, key=lambda item: item[1]["plant_height_mean_m"]
    )
    peak_root_date, peak_root_field = max(
        dated_fields, key=lambda item: item[1]["root_depth_mean_m"]
    )
    weights = seasonal_weights or [1.0] * len(seasonal_lai_contracts)
    if len(weights) != len(seasonal_lai_contracts) or any(not math.isfinite(weight) or weight <= 0 for weight in weights):
        raise ValueError("seasonal LAI contracts require one positive spatial weight per executed crop calendar")
    weight_total = sum(weights)
    lai_contract = {
        key: sum(weight * contract[key] for weight, contract in zip(weights, seasonal_lai_contracts, strict=True)) / weight_total
        for key in ("lai_pot", "frac_hu1", "lai_max1", "frac_hu2", "lai_max2", "hu_lai_decl")
    }
    lai_contract.update({
        "season_count": len(seasonal_lai_contracts),
        "derivation": "SWAT HRU area and CDL-corn-fraction weighted mean of separately dated SWAT-executed-calendar SIMPLIFIED_FSPM seasonal LAI contracts",
    })
    static_traits = ("canopy_extinction_coefficient", "biomass_energy_ratio_kg_ha_per_mj_m2")
    trait_values: dict[str, float] = {}
    for key in static_traits:
        samples = [float(field[key]) for _, field in dated_fields]
        if max(samples) - min(samples) > 1e-12:
            raise ValueError(f"FSPM coupling trait {key} varies by date and cannot enter the static plant-parameter contract")
        trait_values[key] = samples[0]

    return CouplingPlantParameterSummary.model_validate({
        "summary_semantics": "SEASONAL_MAXIMA_FOR_COUPLING_NOT_A_DATED_FSPM_STATE",
        "swat_lai_contract": lai_contract,
        "plant_height_mean_m": peak_height_field["plant_height_mean_m"],
        "root_depth_mean_m": peak_root_field["root_depth_mean_m"],
        **trait_values,
        "peak_dates": {
            "date_of_peak_LAI": peak_lai_date,
            "date_of_peak_height": peak_height_date,
            "date_of_peak_root_depth": peak_root_date,
        },
        "coupling_parameter_provenance": {
            name: copy.deepcopy(peak_lai_field["coupling_parameter_provenance"][name])
            for name in ("ext_co", "bm_e")
        },
    })


def _dated_peak_lai_field_snapshot(dated_fields: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Return one internally consistent dated aggregate for legacy run summaries."""
    peak_lai_date, peak_lai_field = max(dated_fields, key=lambda item: item[1]["mean_LAI"])
    snapshot = copy.deepcopy(peak_lai_field)
    snapshot["field_date"] = peak_lai_date
    snapshot["summary_semantics"] = "DATED_FSPM_FIELD_STATE_AT_PEAK_LAI_DATE"
    return snapshot


class TwinCouplingEngine:
    """Compatibility name for the persistence adapter; formulas live in scientific_core."""

    @staticmethod
    def _baseline_forcing(project: Path, start: date, end: date) -> tuple[list[dict] | None, dict]:
        """Expose direct dated forcing when available; generated SWAT weather is opaque."""
        weather_directory = project / "TxtInOut" if (project / "TxtInOut" / "file.cio").is_file() else project
        try:
            return SwatClimateForcingReader(weather_directory).for_period(start, end, require_fspm=False)
        except SwatPlantMappingError as exc:
            if "weather-sta.cli is required" not in str(exc) and "SWAT_GENERATED_WEATHER_NOT_RECONSTRUCTABLE" not in str(exc):
                raise
            return None, {"status": "NOT_AVAILABLE", "reason": str(exc)}

    @staticmethod
    def _resolve_climate_forcing(sim_run: SimulationRun, datasets: list[Dataset], artifacts: list[DatasetArtifact]) -> tuple[list[dict] | None, dict | None]:
        """Route an explicit forcing artifact without silently substituting synthetic weather."""
        if sim_run.climate_source == "SYNTHETIC":
            return None, None
        if sim_run.climate_source == "SWAT_PROJECT":
            raise RuntimeError("SWAT_PROJECT forcing is only valid for the SWAT_PLUS backend")
        forcing_ids = {dataset_id for dataset_id, role in (sim_run.dataset_roles or {}).items() if role == "FORCING"}
        forcing_datasets = [item for item in datasets if item.id in forcing_ids]
        if len(forcing_datasets) != 1:
            raise RuntimeError("NOT_AVAILABLE: select exactly one FORCING dataset for the chosen climate source")
        dataset = forcing_datasets[0]
        if sim_run.climate_source == "CMIP6_FILE" and dataset.provider != "NEX-GDDP-CMIP6":
            raise RuntimeError("NOT_AVAILABLE: CMIP6_FILE requires a NEX-GDDP-CMIP6 normalized artifact")
        if sim_run.climate_source in {"OBSERVED", "OBSERVED_HYBRID"} and dataset.provider not in {"CHIRPS", "OBSERVED_CLIMATE"}:
            raise RuntimeError("NOT_AVAILABLE: OBSERVED climate requires a CHIRPS or OBSERVED_CLIMATE normalized artifact")
        normalized = [item for item in artifacts if item.dataset_id == dataset.id and item.artifact_kind == "NORMALIZED"]
        if not normalized:
            raise RuntimeError("NOT_AVAILABLE: selected FORCING dataset has no NORMALIZED local artifact")
        artifact = sorted(normalized, key=lambda item: item.retrieved_at)[-1]
        metadata = {**(dataset.metadata_json or {}), **(artifact.metadata_json or {})}
        try:
            weather, provider_metadata = NormalizedClimateFileProvider(Path(artifact.storage_path), metadata=metadata).forcing_for_period(
                sim_run.start_date.isoformat(), sim_run.end_date.isoformat()
            )
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"NOT_AVAILABLE: forcing artifact cannot satisfy the requested period: {exc}") from exc
        return weather, {
            "provider": dataset.provider, "dataset_id": dataset.id, "artifact_id": artifact.id,
            "artifact_kind": artifact.artifact_kind, "checksum_sha256": artifact.checksum_sha256,
            "metadata": provider_metadata, "evidence_type": dataset.evidence_type,
        }

    @staticmethod
    async def _execute_swat_baseline(db: AsyncSession, sim_run: SimulationRun, watershed: Watershed,
                                     observations: dict[str, float] | None = None,
                                     observation_source: str | None = None) -> None:
        """Execute SWAT+ without leaking project/process details into the engine."""
        requested_swat = (sim_run.requested_config or {}).get("swat_plus") or {}
        config = swat_run_config_from_request(
            requested_swat, simulation_start=sim_run.start_date, simulation_end=sim_run.end_date,
            watershed_id=watershed.code, run_id=sim_run.id,
        )
        result = SwatPlusAdapter().run(config)
        climate, climate_provenance = TwinCouplingEngine._baseline_forcing(Path(result.workspace), sim_run.start_date, sim_run.end_date)
        # These normalized rows are persisted exactly as parsed. They are not put in
        # SimulationResult because that legacy entity has required FSPM/proxy fields
        # which a standard SWAT+ baseline does not produce.
        sim_run.effective_config = {
            "backend": "SWAT_PLUS", "run_type": config.run_type,
            "simulation_start": config.simulation_start.isoformat(), "simulation_end": config.simulation_end.isoformat(),
            "warmup_period": config.warmup_period, "output_frequency": config.output_frequency,
            "watershed_id": config.watershed_id, "outlet_unit": config.outlet_unit,
        }
        sim_run.provenance = {
            **result.provenance, "run_id": result.run_id, "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds, "output_files": result.output_files,
            "process_logs": {"stdout": result.stdout, "stderr": result.stderr},
            "watershed_snapshot": {"id": watershed.id, "code": watershed.code, "area_km2": watershed.area_km2},
            "code_version": _code_version(),
        }
        playback = await PlaybackDatabaseStore(db).write(sim_run.id, swat_frames(
            simulation_id=sim_run.id, watershed_id=watershed.id, watershed_code=watershed.code,
            outlet_unit=config.outlet_unit, run_type=config.run_type,
            resolution=config.output_frequency, records=result.records, hru_results=result.hru_results,
            channel_results=result.channel_results,
            forcing=climate, forcing_source="SWAT+ direct station basin mean",
            start_date=sim_run.start_date, end_date=sim_run.end_date,
            observations=observations, observation_source=observation_source),
            provenance={"code_version": sim_run.provenance["code_version"], "model": "SWAT+",
                        "swat_executable_version": result.provenance.get("executable_version"),
                        "swat_executable_sha256": result.provenance.get("executable_sha256"),
                        "swat_output_checksums": result.provenance.get("output_checksums"),
                        "forcing": climate_provenance, "run_type": config.run_type,
                        "requested_interval": [sim_run.start_date.isoformat(), sim_run.end_date.isoformat()],
                        "seed": sim_run.seed, "configuration": sim_run.effective_config},
            limitations=["No FSPM was executed", "SWAT+ soil-water storage in mm is not FSPM volumetric moisture"])
        sim_run.provenance = {**sim_run.provenance, "playback": playback}
        sim_run.monthly_outputs = result.records
        sim_run.hru_aggregates = {"status": "AVAILABLE" if result.hru_results else "NOT_AVAILABLE", "results": result.hru_results}
        sim_run.field_aggregates = {"status": "NOT_AVAILABLE", "reason": "SWAT_STANDARD_BASELINE does not execute the FSPM layer"}
        sim_run.plant_sample = []
        sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "SWAT baseline output integrity only; observational alignment is not part of this run"}
        totals = result.water_balance.get("totals_mm", {})
        discharge_hm3, discharge_limitation = _daily_streamflow_volume_hm3(
            result.records, result.water_balance or {}, config.output_frequency
        )
        precipitation = [row.get("precip_mm", row.get("precipitation_mm")) for row in (climate or ())]
        precip_mm = round(sum(precipitation), 2) if precipitation and all(value is not None for value in precipitation) else None
        sim_run.summary_metrics = {
            "evidence_type": "REAL_SWAT_PLUS",
            "period_count": len(result.records),
            "total_precip_mm": precip_mm,
            "total_discharge_hm3": discharge_hm3,
            "total_discharge_status": "AVAILABLE" if discharge_hm3 is not None else "NOT_AVAILABLE",
            "total_discharge_limitation": discharge_limitation,
            "total_runoff_mm": totals.get("runoff_mm"),
            "total_evapotranspiration_mm": totals.get("evapotranspiration_mm"),
            "total_percolation_mm": totals.get("percolation_mm"),
            "water_balance": result.water_balance,
        }

    @staticmethod
    async def _execute_swat_coupled(db: AsyncSession, sim_run: SimulationRun, watershed: Watershed,
                                    observations: dict[str, float] | None = None,
                                    observation_source: str | None = None) -> None:
        """Couple existing FSPM dynamics to a converged SWAT+ event calendar."""
        from app.services.swat_coupled_runner import run_coupled_swat_with_executed_calendar

        requested_swat = (sim_run.requested_config or {}).get("swat_plus") or {}
        target_crop = requested_swat.get("target_plant_name", "corn")
        config = swat_run_config_from_request(
            requested_swat, simulation_start=sim_run.start_date, simulation_end=sim_run.end_date,
            watershed_id=watershed.code, run_id=sim_run.id, run_type="SWAT_MULTISCALE_COUPLED",
        )
        adapter = SwatPlusAdapter(config.executable_path, config.project_path, config.working_directory)
        initial_preflight = adapter.preflight(config, target_crop=target_crop)
        require_coupled_preflight_ready(initial_preflight)
        coupled = run_coupled_swat_with_executed_calendar(
            adapter, config, target_crop=target_crop, plant_count=sim_run.plant_count,
            seed=sim_run.seed,
        )
        result, fspm, parameter_summary = coupled.result, coupled.fspm, coupled.parameter_summary
        calendar_by_hru = {hru: {"calendar_id": group.calendar_id,
                                 "planting_date": group.planting_date, "harvest_date": group.harvest_date}
                           for group in coupled.calendar.groups for hru in group.hru_ids}
        soil_profiles = read_hru_soils(config.project_path)
        manifest = result.provenance["workspace_modifications"]
        if manifest.get("status") != "APPLIED" or not manifest.get("parameter_updates"):
            raise ValueError("FSPM parameter mapping did not modify the isolated SWAT+ plant record")
        expected_days = (sim_run.end_date - sim_run.start_date).days + 1
        expected_dates = [(sim_run.start_date + timedelta(days=i)).isoformat() for i in range(expected_days)]
        if config.output_frequency == "DAILY" and [row["period"] for row in result.records] != expected_dates:
            raise ValueError("SWAT+ basin outputs do not contain one unique daily record per requested date")
        if len(fspm.fspm_days) != expected_days or sorted(fspm.fspm_days) != expected_dates:
            raise ValueError("FSPM did not produce a complete, unique daily trajectory for the requested interval")
        if result.water_balance.get("warnings"):
            severe = {"DUPLICATE_TIMESTAMPS", "MISSING_PERIODS", "NON_FINITE_VALUE", "UNEXPECTED_UNIT"}
            bad = [warning for warning in result.water_balance["warnings"] if warning.get("code") in severe]
            if bad:
                raise ValueError(f"SWAT+ output integrity warnings prevent publication: {bad}")

        peak_dates = parameter_summary.peak_dates.model_dump(mode="json")
        sim_run.effective_config = {
            "backend": "SWAT_PLUS", "run_type": "SWAT_MULTISCALE_COUPLED",
            "simulation_start": sim_run.start_date.isoformat(), "simulation_end": sim_run.end_date.isoformat(),
            "warmup_period": config.warmup_period, "output_frequency": config.output_frequency,
            "same_source_project": str(config.project_path.resolve()),
            "fspm_version": PlantPopulation.VERSION, "plant_count_per_calendar_group": sim_run.plant_count,
            "seed": sim_run.seed, "calendar_convergence": "CONVERGED",
        }
        sim_run.provenance = {
            **result.provenance,
            "evidence_type": "REAL_SWAT_PLUS_COUPLED",
            "run_id": result.run_id,
            "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds,
            "output_files": result.output_files,
            "process_logs": {"stdout": result.stdout, "stderr": result.stderr},
            "parameter_updates": manifest.get("parameter_updates", []),
            "coupling_parameter_summary": parameter_summary.model_dump(mode="json"),
            "executed_calendar_coupling": result.provenance.get("executed_calendar_coupling"),
            "fspm_calendar_provenance": fspm.provenance,
            "preflight": initial_preflight,
            **peak_dates,
            "code_version": _code_version(),
        }
        playback = await PlaybackDatabaseStore(db).write(sim_run.id, swat_frames(
            simulation_id=sim_run.id, watershed_id=watershed.id, watershed_code=watershed.code,
            outlet_unit=config.outlet_unit, run_type=config.run_type,
            resolution=config.output_frequency, records=result.records, hru_results=result.hru_results,
            plant_results=result.plant_results, channel_results=result.channel_results,
            soil_profiles=soil_profiles, hru_gis_ids=read_hru_gis_ids(config.project_path),
            hru_calendar=calendar_by_hru,
            forcing=fspm.field_climate,
            forcing_source="SWAT+ station forcing, hru.con.wst, HRU area x 2019 CDL corn fraction",
            fspm_days=fspm.fspm_days, start_date=sim_run.start_date, end_date=sim_run.end_date,
            observations=observations, observation_source=observation_source),
            provenance={
                "code_version": sim_run.provenance["code_version"], "swat_model": "SWAT+",
                "swat_executable_version": result.provenance.get("executable_version"),
                "swat_executable_sha256": result.provenance.get("executable_sha256"),
                "swat_output_checksums": result.provenance.get("output_checksums"),
                "fspm_model": PlantPopulation.VERSION, "fspm_climate": fspm.provenance.get("field_climate"),
                "calendar_coupling": result.provenance.get("executed_calendar_coupling"),
                "seed": sim_run.seed, "plant_count_per_calendar_group": sim_run.plant_count,
                "configuration": sim_run.effective_config,
                "requested_interval": [sim_run.start_date.isoformat(), sim_run.end_date.isoformat()],
            },
            limitations=[
                "FSPM moisture is derived from SWAT+ whole-profile storage and soils.sol under a uniform-profile assumption; daily layer and root-zone water are not printed",
                "SWAT+ 61.0.2.61 hru_pw output has LAI, biomass and stress factors but no direct plant-height or root-depth columns; those traits come from FSPM representative plant states",
                "Each distinct SWAT+ HRU planting/harvest calendar is simulated separately and field states are weighted by HRU area and 2019 CDL corn fraction",
            ])
        sim_run.provenance = {**sim_run.provenance, "playback": playback}
        if config.output_frequency != "DAILY":
            daily_manifest = await PlaybackDatabaseStore(db).write(sim_run.id, swat_frames(
                simulation_id=sim_run.id, watershed_id=watershed.id, watershed_code=watershed.code,
                outlet_unit=config.outlet_unit, run_type=config.run_type,
                resolution="DAILY", records=[], hru_results=[], plant_results=[],
                forcing=fspm.field_climate, forcing_source="SWAT+ station forcing weighted over maize HRUs",
                fspm_days=fspm.fspm_days, start_date=sim_run.start_date, end_date=sim_run.end_date,
                missing_hydrology_reason="SWAT+ was requested at a coarser frequency; daily hydrology is not available"),
                provenance={"code_version": sim_run.provenance["code_version"], "seed": sim_run.seed,
                            "fspm_model": PlantPopulation.VERSION, "plant_count": sim_run.plant_count,
                            "calendar": coupled.calendar.as_dict(), "parent_swat_playback_sha256": playback["sha256"]},
                limitations=["Daily FSPM and forcing only; SWAT+ hydrology has a coarser effective frequency",
                             "FSPM moisture is assumed for runs without daily SWAT+ HRU soil-water output"])
            sim_run.provenance = {**sim_run.provenance, "playback_daily_fspm": daily_manifest}
        sim_run.monthly_outputs = result.records
        sim_run.hru_aggregates = {
            "status": "AVAILABLE" if result.hru_results else "NOT_AVAILABLE",
            "results": result.hru_results,
            "plant_results": result.plant_results,
            "channel_results": result.channel_results,
            "management_events": result.management_events,
            "parameter_mapping": manifest,
        }
        peak_lai_date, peak_lai_field = max(fspm.dated_fields, key=lambda item: item[1]["mean_LAI"])
        sim_run.field_aggregates = _dated_peak_lai_field_snapshot(fspm.dated_fields)
        sim_run.field_aggregates["calendar"] = coupled.calendar.as_dict()
        peak_plants = fspm.fspm_days[peak_lai_date].get("plants", [])
        sim_run.plant_sample = [vars(plant) for plant in peak_plants]
        sim_run.provenance = {**sim_run.provenance, "plant_sample_context":
                              fspm.fspm_days[peak_lai_date].get("plant_sample_context")}
        sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "coupled run is an input-response simulation, not observational validation"}
        totals = result.water_balance.get("totals_mm", {})
        discharge_hm3, discharge_limitation = _daily_streamflow_volume_hm3(
            result.records, result.water_balance or {}, config.output_frequency
        )
        stress = [field["mean_stress"] for _, field in fspm.dated_fields if "mean_stress" in field]
        sim_run.summary_metrics = {
            "evidence_type": "REAL_SWAT_PLUS_COUPLED",
            "period_count": len(result.records),
            "total_precip_mm": totals.get("precip_mm"),
            "total_discharge_hm3": discharge_hm3,
            "total_discharge_status": "AVAILABLE" if discharge_hm3 is not None else "NOT_AVAILABLE",
            "total_discharge_limitation": discharge_limitation,
            "mean_fspm_water_stress": round(fmean(stress), 3) if stress else None,
            "total_runoff_mm": totals.get("runoff_mm"),
            "total_evapotranspiration_mm": totals.get("evapotranspiration_mm"),
            "total_percolation_mm": totals.get("percolation_mm"),
            "water_balance": result.water_balance,
        }

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
            requested = sim_run.requested_config or {}
            if sim_run.start_date is None or sim_run.end_date is None:
                if sim_run.hydrology_backend == "SWAT_PLUS" or sim_run.mode == "SWAT_PLUS":
                    raise ValueError("SWAT+ requires explicit start_date/end_date")
                # Legacy persisted proxy demos predate the explicit date contract.
                sim_run.start_date = date(2000, 1, 1)
                sim_run.end_date = sim_run.start_date + timedelta(days=sim_run.duration_days - 1)
            config = RunConfig(
                run_id=sim_run.id, seed=sim_run.seed, duration_days=sim_run.duration_days,
                watershed_area_km2=watershed.area_km2, temp_anomaly_c=scenario.temp_anomaly_c,
                precip_factor=scenario.precip_factor, co2_ppm=scenario.co2_ppm,
                start_date=sim_run.start_date, end_date=sim_run.end_date,
                parameters=sim_run.parameters or {},
                management_scenario=sim_run.management_scenario,
                climate_source=sim_run.climate_source,
                station_id=sim_run.station_id, dataset_ids=tuple(sim_run.dataset_ids or ()),
                dataset_roles=sim_run.dataset_roles or {},
            )
            if sim_run.hydrology_backend == "SWAT_PLUS" or sim_run.mode == "SWAT_PLUS":
                observation_ids = [dataset_id for dataset_id, role in (sim_run.dataset_roles or {}).items()
                                   if role in {"OBSERVATION", "VALIDATION"}]
                swat_observations: dict[str, float] = {}
                observation_source = None
                if sim_run.station_id and observation_ids:
                    observed_rows = (await db.execute(
                        select(StreamflowObservation).where(StreamflowObservation.station_id == sim_run.station_id)
                        .where(StreamflowObservation.dataset_id.in_(observation_ids))
                        .where(StreamflowObservation.observed_on >= sim_run.start_date)
                        .where(StreamflowObservation.observed_on <= sim_run.end_date)
                    )).scalars().all()
                    for observation in observed_rows:
                        if observation.value_m3s is not None and observation.value_m3s >= 0:
                            observed_on = observation.observed_on.isoformat()
                            if observed_on in swat_observations and swat_observations[observed_on] != observation.value_m3s:
                                raise ValueError(f"Conflicting observations for {observed_on}")
                            swat_observations[observed_on] = observation.value_m3s
                    observation_source = f"USGS station {sim_run.station_id}; linked observation datasets"
                if ((sim_run.requested_config or {}).get("swat_plus") or {}).get("run_type") == "SWAT_MULTISCALE_COUPLED":
                    await TwinCouplingEngine._execute_swat_coupled(db, sim_run, watershed, swat_observations, observation_source)
                else:
                    await TwinCouplingEngine._execute_swat_baseline(db, sim_run, watershed, swat_observations, observation_source)
                sim_run.status = "COMPLETED"
                sim_run.finished_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(sim_run)
                return sim_run
            datasets = list((await db.execute(select(Dataset).where(Dataset.id.in_(sim_run.dataset_ids or [])))).scalars().all()) if sim_run.dataset_ids else []
            artifacts = list((await db.execute(select(DatasetArtifact).where(DatasetArtifact.dataset_id.in_([item.id for item in datasets])))).scalars().all()) if datasets else []
            weather, climate_artifact_provenance = TwinCouplingEngine._resolve_climate_forcing(sim_run, datasets, artifacts)
            core_run = MultiscaleSimulationOrchestrator().execute(
                config, sim_run.plant_count, weather=weather, climate_provenance=climate_artifact_provenance
            )
            db.add_all([
                SimulationResult(
                    simulation_run_id=sim_run.id, day_index=row["day_index"], date_str=row["date_str"],
                    precip_mm=row["precip_mm"], temp_c=row["temp_c"], solar_rad_mj=row["solar_rad_mj"],
                    potential_et_mm=row["et0_mm"], actual_et_mm=row["actual_et_mm"],
                    surface_runoff_mm=row["surface_runoff_mm"], percolation_mm=row["percolation_mm"],
                    streamflow_m3s=row["streamflow_m3s"], soil_moisture_vol=row["soil_moisture_vol"],
                    soil_water_depth_mm=row["soil_water_depth_mm"], plant_transpiration_mm=row["actual_transpiration_mm"],
                    root_water_uptake_mm=row["root_water_uptake_mm"], cwsi_stress_index=row["cwsi_stress_index"],
                    sap_flow_velocity_cmh=row.get("sap_flow_velocity_cmh"),
                    water_balance_residual_mm=row["water_balance_residual_mm"],
                ) for row in core_run.results
            ])
            sim_run.requested_config = requested
            sim_run.effective_config = core_run.effective_config
            dataset_snapshots = [{"id": item.id, "provider": item.provider, "dataset_name": item.dataset_name,
                                  "version": item.version, "evidence_type": item.evidence_type,
                                  "role": (sim_run.dataset_roles or {}).get(item.id, "CONTEXT_ONLY"),
                                  "artifact_checksums": [artifact.checksum_sha256 for artifact in artifacts if artifact.dataset_id == item.id]}
                                 for item in datasets]
            sim_run.provenance = {
                **core_run.provenance,
                "watershed_snapshot": {"id": watershed.id, "code": watershed.code, "area_km2": watershed.area_km2},
                "scenario_snapshot": {"id": scenario.id, "code": scenario.code, "evidence_type": scenario.source_type},
                "code_version": _code_version(),
                "climate_source": sim_run.climate_source,
                "station_id": sim_run.station_id,
                "datasets": dataset_snapshots,
            }
            observation_for_playback = {}
            sim_run.summary_metrics = core_run.summary_metrics
            sim_run.field_aggregates = core_run.field_aggregates
            sim_run.hru_aggregates = core_run.hru_aggregates
            sim_run.plant_sample = list(core_run.plant_sample)
            monthly_outputs = [dict(row) for row in core_run.monthly_outputs]
            observation_ids = [dataset_id for dataset_id, role in (sim_run.dataset_roles or {}).items()
                               if role in {"OBSERVATION", "VALIDATION"}]
            observations = []
            if sim_run.station_id and observation_ids:
                observations = (await db.execute(
                    select(StreamflowObservation).where(StreamflowObservation.station_id == sim_run.station_id)
                    .where(StreamflowObservation.dataset_id.in_(observation_ids))
                    .where(StreamflowObservation.observed_on >= sim_run.start_date)
                    .where(StreamflowObservation.observed_on <= sim_run.end_date)
                    .order_by(StreamflowObservation.observed_on)
                )).scalars().all()
            observed_by_month: dict[str, list[float]] = {}
            for observation in observations:
                if observation.value_m3s is not None and observation.value_m3s >= 0:
                    observed_on = observation.observed_on.isoformat()
                    if observed_on in observation_for_playback and observation_for_playback[observed_on] != observation.value_m3s:
                        raise ValueError(f"Conflicting observations for {observed_on}")
                    if observed_on not in observation_for_playback:
                        observed_by_month.setdefault(observation.observed_on.strftime("%Y-%m"), []).append(observation.value_m3s)
                        observation_for_playback[observed_on] = observation.value_m3s
            playback = await PlaybackDatabaseStore(db).write(sim_run.id, simplified_frames(
                simulation_id=sim_run.id, watershed_id=watershed.id, watershed_code=watershed.code,
                rows=core_run.results,
                daily_fields=core_run.playback_daily, climate_source=sim_run.climate_source,
                observations=observation_for_playback,
                observation_source=f"USGS station {sim_run.station_id}" if sim_run.station_id and observation_ids else None),
                provenance={"code_version": sim_run.provenance["code_version"], "model": "SimplifiedPlantModel + SimplifiedHydrologyModel",
                            "fspm_model_version": PlantPopulation.VERSION,
                            "seed": sim_run.seed, "plant_count": sim_run.plant_count, "configuration": core_run.effective_config,
                            "forcing": core_run.provenance.get("climate"),
                            "requested_interval": [sim_run.start_date.isoformat(), sim_run.end_date.isoformat()]},
                limitations=["Simplified hydrology and coarse HRUs are not SWAT+", "Crop management events are not explicitly simulated"])
            sim_run.provenance = {**sim_run.provenance, "playback": playback}
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
                sim_run.validation["observation_station_id"] = sim_run.station_id
                sim_run.validation["aligned_months"] = len(aligned)
            else:
                sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "fewer than two aligned observed months",
                                      "observation_station_id": sim_run.station_id, "aligned_months": len(aligned),
                                      "interpretation": "DEMONSTRATION_ONLY"}
            sim_run.monthly_outputs = monthly_outputs
            if sim_run.external_model_id:
                registry_model = await db.scalar(select(ExternalModel).where(ExternalModel.id == sim_run.external_model_id))
                if not registry_model:
                    raise ValueError("external model is not registered")
                adapter = ExternalModelBundleAdapter(registry_model.artifact_path)
                try:
                    adapter.load()
                    monthly_payloads = []
                    for output in monthly_outputs:
                        days = [row for row in core_run.results if row["date_str"].startswith(output["month"])]
                        monthly_payloads.append({
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
                        })
                    predictions = []
                    for index, payload in enumerate(monthly_payloads):
                        history = monthly_payloads[max(0, index - adapter.timesteps + 1):index]
                        prediction = adapter.predict(payload, history=history)
                        predictions.append(prediction)
                        if prediction["target"] == "monthly_runoff_mm":
                            monthly_outputs[index]["ml_assisted_runoff_mm"] = prediction["value"]
                        elif prediction["target"] == "monthly_streamflow_m3s":
                            monthly_outputs[index]["ml_assisted_streamflow_m3s"] = prediction["value"]
                    sim_run.ml_result = {"status": "PREDICTED", "model_id": registry_model.id,
                                         "target": registry_model.target, "predictions": predictions,
                                         "training_data_type": registry_model.training_data_type}
                except (RuntimeError, ValueError) as exc:
                    status_name = "INSUFFICIENT_HISTORY" if str(exc).startswith("INSUFFICIENT_HISTORY") else "NOT_AVAILABLE"
                    sim_run.ml_result = {"status": status_name, "model_id": registry_model.id,
                                         "target": registry_model.target, "reason": str(exc),
                                         "training_data_type": registry_model.training_data_type}
                sim_run.monthly_outputs = monthly_outputs
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
            sim_run.error = {
                "type": getattr(exc, "code", type(exc).__name__), "message": str(exc),
                **({"details": exc.details} if hasattr(exc, "details") else {}),
            }
            await db.commit()
            raise

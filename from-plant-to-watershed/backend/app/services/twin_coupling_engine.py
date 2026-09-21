"""Application adapter between SQLAlchemy persistence and the pure scientific core."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import subprocess

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import ClimateScenario, SimulationResult, SimulationRun
from app.models.observation import Dataset, DatasetArtifact, StreamflowObservation
from app.models.external_model import ExternalModel
from app.models.watershed import Watershed
from app.services.external_model_bundle import ExternalModelBundleAdapter
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.core.config import settings
from scientific_core import MultiscaleSimulationOrchestrator, PlantPopulation, PlantToFieldAggregator, RunConfig, SimulationOrchestrator, ValidationEngine
from scientific_core.climate_file import NormalizedClimateFileProvider


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
    def _resolve_climate_forcing(sim_run: SimulationRun, datasets: list[Dataset], artifacts: list[DatasetArtifact]) -> tuple[list[dict] | None, dict | None]:
        """Route an explicit forcing artifact without silently substituting synthetic weather."""
        if sim_run.climate_source == "SYNTHETIC":
            return None, None
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
    async def _execute_swat_baseline(sim_run: SimulationRun, watershed: Watershed) -> None:
        """Execute SWAT+ without leaking project/process details into the engine."""
        requested_swat = (sim_run.requested_config or {}).get("swat_plus") or {}
        config = SwatPlusRunConfig(
            project_path=Path(requested_swat.get("project_path") or settings.SWAT_PLUS_PROJECT_DIR),
            executable_path=Path(requested_swat.get("executable_path") or settings.SWAT_PLUS_EXECUTABLE),
            working_directory=Path(requested_swat.get("working_directory") or settings.SWAT_PLUS_WORKING_DIRECTORY),
            simulation_start=sim_run.start_date, simulation_end=sim_run.end_date,
            warmup_period=requested_swat.get("warmup_period", 0),
            output_frequency=requested_swat.get("output_frequency", "DAILY"),
            watershed_id=watershed.code, run_id=sim_run.id,
            timeout_seconds=requested_swat.get("timeout_seconds", settings.SWAT_PLUS_TIMEOUT_SECONDS),
            run_type=requested_swat.get("run_type", "SWAT_STANDARD_BASELINE"),
            outlet_unit=requested_swat.get("outlet_unit"),
        )
        result = SwatPlusAdapter().run(config)
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
        sim_run.monthly_outputs = result.records
        sim_run.hru_aggregates = {"status": "AVAILABLE" if result.hru_results else "NOT_AVAILABLE", "results": result.hru_results}
        sim_run.field_aggregates = {"status": "NOT_AVAILABLE", "reason": "SWAT_STANDARD_BASELINE does not execute the FSPM layer"}
        sim_run.plant_sample = []
        sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "SWAT baseline output integrity only; observational alignment is not part of this run"}
        totals = result.water_balance.get("totals_mm", {})
        sim_run.summary_metrics = {
            "evidence_type": "REAL_SWAT_PLUS", "period_count": len(result.records),
            "total_runoff_mm": totals.get("runoff_mm"), "total_evapotranspiration_mm": totals.get("evapotranspiration_mm"),
            "total_percolation_mm": totals.get("percolation_mm"),
            "water_balance": result.water_balance,
        }

    @staticmethod
    async def _execute_swat_coupled(sim_run: SimulationRun, watershed: Watershed) -> None:
        """One-way FSPM -> documented SWAT+ crop inputs -> real SWAT+ execution."""
        requested_swat = (sim_run.requested_config or {}).get("swat_plus") or {}
        source_project = Path(requested_swat.get("project_path") or settings.SWAT_PLUS_PROJECT_DIR)
        climate, climate_provenance = SwatClimateForcingReader(source_project).for_period(sim_run.start_date, sim_run.end_date)
        population = PlantPopulation(count=sim_run.plant_count, seed=sim_run.seed, crop="maize")
        season = SwatCropChainDiagnostic.auto_management_season(
            source_project, target_crop=requested_swat.get("target_plant_name", "corn")
        )
        season_windows = season.windows(
            sim_run.start_date, sim_run.end_date, (forcing["temp_c"] for forcing in climate),
            thermal_maturity_gdd=population.thermal_maturity_gdd,
        )
        active_by_date = {
            date.fromisoformat(window["start_date"]) + timedelta(days=offset): window
            for window in season_windows
            for offset in range((date.fromisoformat(window["end_date"]) - date.fromisoformat(window["start_date"])).days + 1)
        }
        # Thermal time and absorbed radiation reset only when the traceable
        # auto-management approximation opens a crop season, never at Jan 1.
        gdd, absorbed_par, peak_field, plants = 0.0, 0.0, None, ()
        peak_height, peak_root, peak_dates = None, None, {}
        fields_by_season: dict[str, list[dict[str, Any]]] = {}
        for index, forcing in enumerate(climate, 1):
            current_date = sim_run.start_date + timedelta(days=index - 1)
            window = active_by_date.get(current_date)
            if window is None:
                continue
            if current_date.isoformat() == window["start_date"]:
                gdd, absorbed_par = 0.0, 0.0
            gdd += season.fspm_growth_gdd_increment(forcing["temp_c"])
            daily_forcing = {**forcing, "gdd_c_day": gdd, "cumulative_absorbed_par_mj_m2": absorbed_par}
            current_plants = population.step(index, daily_forcing, soil_moisture_vol=0.24)
            current_field = PlantToFieldAggregator.aggregate(current_plants, soil_moisture_vol=0.24)
            # PAR is 48% of shortwave radiation; green-canopy interception is
            # already represented by the FSPM Beer-Lambert cover calculation.
            absorbed_par += max(0.0, forcing["solar_rad_mj"]) * .48 * current_field["canopy_cover"]
            fields_by_season.setdefault(window["start_date"], []).append(current_field)
            if peak_field is None or current_field["mean_LAI"] > peak_field["mean_LAI"]:
                peak_field, plants = current_field, current_plants
                peak_dates["date_of_peak_LAI"] = current_date.isoformat()
            if peak_height is None or current_field["plant_height_mean_m"] > peak_height["plant_height_mean_m"]:
                peak_height = current_field
                peak_dates["date_of_peak_height"] = current_date.isoformat()
            if peak_root is None or current_field["root_depth_mean_m"] > peak_root["root_depth_mean_m"]:
                peak_root = current_field
                peak_dates["date_of_peak_root_depth"] = current_date.isoformat()
        seasonal_contracts = [PlantToFieldAggregator.seasonal_lai_contract(rows) for rows in fields_by_season.values() if len(rows) >= 3 and max(row["mean_LAI"] for row in rows) > 0]
        if not seasonal_contracts:
            raise ValueError("FSPM produced no seasonal LAI trajectory for SWAT+ coupling")
        field = peak_field
        field["plant_height_mean_m"] = peak_height["plant_height_mean_m"]
        field["root_depth_mean_m"] = peak_root["root_depth_mean_m"]
        field["swat_lai_contract"] = {key: fmean(contract[key] for contract in seasonal_contracts)
                                      for key in ("lai_pot", "frac_hu1", "lai_max1", "frac_hu2", "lai_max2", "hu_lai_decl")}
        field["swat_lai_contract"]["season_count"] = len(seasonal_contracts)
        field["swat_lai_contract"]["derivation"] = "mean of SWAT auto-management PHU-derived SIMPLIFIED_FSPM seasonal LAI contracts"
        field["aggregation_window"] = "SWAT auto-management PHU-derived approximate crop-season trajectories"
        field["peak_dates"] = peak_dates
        field["climate_provenance"] = climate_provenance
        field["season_provenance"] = season.provenance(season_windows)
        field["fspm_growth_temperature_base_c"] = season.crop_temperature_base_c
        field["fspm_growth_temperature_base_source"] = "plants.plt.tmp_base"
        mapper = SwatPlantParameterMapper(requested_swat.get("target_plant_name", "corn"))
        config = SwatPlusRunConfig(
            project_path=source_project, executable_path=Path(requested_swat.get("executable_path") or settings.SWAT_PLUS_EXECUTABLE),
            working_directory=Path(requested_swat.get("working_directory") or settings.SWAT_PLUS_WORKING_DIRECTORY),
            simulation_start=sim_run.start_date, simulation_end=sim_run.end_date, warmup_period=requested_swat.get("warmup_period", 0),
            output_frequency=requested_swat.get("output_frequency", "DAILY"), watershed_id=watershed.code, run_id=sim_run.id,
            timeout_seconds=requested_swat.get("timeout_seconds", settings.SWAT_PLUS_TIMEOUT_SECONDS), run_type="SWAT_MULTISCALE_COUPLED", outlet_unit=requested_swat.get("outlet_unit"),
        )
        result = SwatPlusAdapter().run(config, workspace_mutator=lambda workspace: mapper.apply(workspace, field))
        manifest = result.provenance["workspace_modifications"]
        sim_run.effective_config = {"backend": "SWAT_PLUS", "run_type": "SWAT_MULTISCALE_COUPLED", "simulation_start": sim_run.start_date.isoformat(), "simulation_end": sim_run.end_date.isoformat(), "same_source_project": str(source_project.resolve()), "fspm_version": PlantPopulation.VERSION, "plant_count": sim_run.plant_count}
        sim_run.provenance = {**result.provenance, "evidence_type": "REAL_SWAT_PLUS_COUPLED", "run_id": result.run_id, "exit_code": result.exit_code, "duration_seconds": result.duration_seconds, "output_files": result.output_files, "process_logs": {"stdout": result.stdout, "stderr": result.stderr}, "parameter_updates": manifest.get("parameter_updates", []), **peak_dates, "code_version": _code_version()}
        sim_run.monthly_outputs = result.records
        sim_run.hru_aggregates = {"status": "AVAILABLE" if result.hru_results else "NOT_AVAILABLE", "results": result.hru_results, "parameter_mapping": manifest}
        sim_run.field_aggregates = field
        sim_run.plant_sample = [vars(plant) for plant in plants[:min(10, len(plants))]]
        sim_run.validation = {"status": "NOT_AVAILABLE", "reason": "coupled run is an input-response experiment, not an observational validation"}
        totals = result.water_balance.get("totals_mm", {})
        sim_run.summary_metrics = {"evidence_type": "REAL_SWAT_PLUS_COUPLED", "period_count": len(result.records), "total_runoff_mm": totals.get("runoff_mm"), "total_evapotranspiration_mm": totals.get("evapotranspiration_mm"), "total_percolation_mm": totals.get("percolation_mm"), "water_balance": result.water_balance}

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
                if ((sim_run.requested_config or {}).get("swat_plus") or {}).get("run_type") == "SWAT_MULTISCALE_COUPLED":
                    await TwinCouplingEngine._execute_swat_coupled(sim_run, watershed)
                else:
                    await TwinCouplingEngine._execute_swat_baseline(sim_run, watershed)
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
                    sap_flow_velocity_cmh=row["sap_flow_velocity_cmh"],
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

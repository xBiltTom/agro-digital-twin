"""Read-only scientific availability analysis; never reconstructs missing FSPM."""

from datetime import date, timedelta
import math
from pathlib import Path
import sqlite3

from app.core.config import settings
from app.schemas.playback import PlaybackRecord
from app.schemas.playback_diagnostic import (
    AvailabilityCode as C, DateAvailability, DateInterval,
    ResolutionAvailability, SimulationAvailability,
)
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.simulation_provenance import (
    SimulationProvenanceClass,
    classify_simulation_provenance,
    public_origin,
)


def _present(group: dict, name: str) -> bool:
    state = group.get(name)
    return state is not None and state.availability == "AVAILABLE" and state.value is not None


def _maize(crop: str | None) -> bool:
    return any(name in (crop or "").lower() for name in ("maize", "corn", "maíz", "maiz"))


_SUMMARY_VARIABLES = (
    "mean_LAI", "mean_lai", "lai_mean", "lai", "LAI",
    "plant_height_mean_m", "mean_height_m", "height_mean_m",
    "root_depth_mean_m", "mean_root_depth_m", "mean_root_depth_cm",
    "biomass_g_plant", "mean_biomass_g_plant", "mean_biomass_kg_m2",
    "mean_water_stress", "water_stress", "actual_ET_mm_day",
    "transpiration_mm_day", "mean_transpiration_mm", "canopy_cover",
)
_DATED_FSPM_VARIABLES = (
    "lai", "height_m", "root_depth_m", "biomass_g_plant", "water_stress",
    "actual_transpiration_mm_day", "phenology_fraction", "canopy_cover_fraction",
)


def _has_fspm_summary(values: object) -> bool:
    """Require a finite persisted FSPM variable; status/reason metadata alone is not data."""
    if not isinstance(values, dict):
        return False
    for name in _SUMMARY_VARIABLES:
        value = values.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            return True
    distribution = values.get("LAI_distribution")
    if isinstance(distribution, dict):
        return any(isinstance(distribution.get(key), (int, float))
                   and not isinstance(distribution.get(key), bool)
                   and math.isfinite(distribution[key]) for key in ("p10", "p90", "std"))
    return False


def _has_individual_samples(samples: object) -> bool:
    if not isinstance(samples, list):
        return False
    numeric_variables = (
        "lai", "height_m", "plant_height_m", "root_depth_m", "biomass_g_plant",
        "stress", "water_stress", "actual_transpiration_mm_day", "growing_degree_days_c_day",
    )

    def numeric(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def has_measurement(item: dict) -> bool:
        for name in numeric_variables:
            if numeric(item.get(name)):
                return True
        stage = item.get("phenological_stage")
        if isinstance(stage, str) and stage.strip() and stage.upper() != "NOT_AVAILABLE":
            return True
        variables = item.get("variables")
        if not isinstance(variables, dict):
            return False
        for name, state in variables.items():
            if isinstance(state, dict):
                if state.get("availability", "AVAILABLE") != "AVAILABLE":
                    continue
                value = state.get("value")
            else:
                value = state
            if numeric(value):
                return True
            if name == "phenological_stage" and isinstance(value, str) and value.strip() and value.upper() != "NOT_AVAILABLE":
                return True
        return False

    return any(
        isinstance(item, dict)
        and any(item.get(key) is not None and str(item.get(key)) != "" for key in ("plant_id", "id", "plant_identifier"))
        and has_measurement(item)
        for item in samples
    )


def _has_dated_sample_data(record: PlaybackRecord) -> bool:
    return any(
        any(_present(sample.variables, name) for name in sample.variables)
        for sample in record.plant_samples
    )


def diagnose_record(record: PlaybackRecord) -> DateAvailability:
    codes: list[C] = []
    missing: list[str] = []
    active = record.crop is not None and record.crop.active
    field = record.field
    samples = record.plant_samples
    field_ok = active and _maize(record.crop.crop) and _present(field, "height_m") and _present(field, "lai")
    sample_ok = active and _maize(record.crop.crop) and any(_present(s.variables, "height_m") for s in samples)
    if not active:
        if record.crop is not None:
            codes.append(C.OUTSIDE_CROP_SEASON)
            mode = "SCIENTIFIC_FALLOW"
        elif any(_present(record.hydrology, name) for name in record.hydrology):
            codes.append(C.SWAT_BASELINE_NO_FSPM if record.run_type == "SWAT_STANDARD_BASELINE" else C.HYDROLOGY_ONLY)
            missing.extend(["field.height_m", "field.lai", "plant_samples"])
            mode = "HYDROLOGY_ONLY"
        else:
            codes.append(C.FSPM_STATE_MISSING)
            missing.extend(["field.height_m", "field.lai", "plant_samples"])
            mode = "DATA_UNAVAILABLE"
    else:
        if not _maize(record.crop.crop):
            codes.append(C.UNSUPPORTED_CROP_GEOMETRY)
        if not _present(field, "height_m"):
            codes.append(C.FIELD_HEIGHT_MISSING)
            missing.append("field.height_m")
        if not _present(field, "lai"):
            codes.append(C.FIELD_LAI_MISSING)
            missing.append("field.lai")
        if not samples:
            codes.append(C.NO_PLANT_SAMPLES)
            missing.append("plant_samples")
        elif not sample_ok:
            codes.append(C.SAMPLE_HEIGHT_MISSING)
            missing.append("plant_samples[*].height_m")
        if field_ok or sample_ok:
            codes.append(C.SCIENTIFIC_STATE_AVAILABLE)
        mode = "SCIENTIFIC_ACTIVE" if field_ok or sample_ok else "DATA_UNAVAILABLE"
    return DateAvailability(date=record.date, resolution=record.resolution, mode=mode,
                            codes=codes, field_representable=bool(field_ok),
                            sample_representable=bool(sample_ok), missing_variables=missing)


def diagnose_simulation(sim, *, on: date | None = None,
                        records_by_resolution: dict[str, list[PlaybackRecord]] | None = None) -> SimulationAvailability:
    provenance = sim.provenance or {}
    requested = sim.requested_config or {}
    run_type = (requested.get("swat_plus") or {}).get("run_type") or (sim.effective_config or {}).get("run_type") or "RESEARCH_MULTISCALE"
    provenance_class = classify_simulation_provenance(sim)
    metrics = getattr(sim, "summary_metrics", None) or {}
    hydro_keys = ("total_runoff_mm", "total_evapotranspiration_mm", "mean_streamflow_m3s", "water_balance")
    result = SimulationAvailability(simulation_id=sim.id, simulation_name=sim.name,
        simulation_status=sim.status, run_type=run_type,
        origin=public_origin(provenance_class),
        provenance_class=provenance_class.value,
        stored_hydrology_available=bool(getattr(sim, "monthly_outputs", None) or any(metrics.get(key) is not None for key in hydro_keys)),
        stored_fspm_summary_available=_has_fspm_summary(getattr(sim, "field_aggregates", None)),
        stored_fspm_samples_available=_has_individual_samples(getattr(sim, "plant_sample", None)))
    result.fspm_results_available = result.stored_fspm_summary_available or result.stored_fspm_samples_available
    manifests = [("playback", PlaybackArtifactStore()),
                 ("playback_daily_fspm", PlaybackArtifactStore(Path(settings.DATA_ARTIFACT_ROOT) / "playback" / "v1" / "fspm-daily"))]
    for key, store in manifests:
        manifest = provenance.get(key)
        if not manifest:
            continue
        resolution = manifest.get("resolution")
        if resolution not in {"DAILY", "MONTHLY", "ANNUAL"}:
            result.codes.append(C.ARTIFACT_INVALID)
            continue
        summary = ResolutionAvailability(resolution=resolution, artifact_status="AVAILABLE")
        try:
            previous_active: date | None = None
            current_interval: DateInterval | None = None
            sample_representable_seen = False
            records = (records_by_resolution.get(resolution, []) if records_by_resolution is not None
                       else store.iter_records(sim.id, manifest))
            for record in records:
                summary.record_count += 1
                summary.first_record = summary.first_record or record.date
                summary.last_record = record.date
                state = diagnose_record(record)
                if on == record.date or (on is not None and resolution == "MONTHLY" and on.year == record.date.year and on.month == record.date.month) or (on is not None and resolution == "ANNUAL" and on.year == record.date.year):
                    summary.selected_date = state
                summary.hydrology_available |= any(_present(record.hydrology, name) for name in record.hydrology)
                usable_samples = _has_dated_sample_data(record)
                has_dated_fspm = (record.crop is not None and record.crop.active and
                    (any(_present(record.field, name) for name in _DATED_FSPM_VARIABLES) or usable_samples))
                summary.fspm_trajectory_available |= has_dated_fspm
                summary.plant_samples_available |= usable_samples
                sample_representable_seen |= state.sample_representable
                summary.hru_ids = sorted(set(summary.hru_ids) | {h.hru_id for h in record.hru_results})
                if record.crop and record.crop.active:
                    summary.first_active_crop = summary.first_active_crop or record.date
                    if state.field_representable:
                        summary.first_representable_field = summary.first_representable_field or record.date
                    if usable_samples:
                        summary.first_plant_samples = summary.first_plant_samples or record.date
                    season_id = record.crop.season_id
                    approximate = record.crop.window_status == "APPROXIMATE_PLANTING_WINDOW"
                    if (current_interval is not None and previous_active is not None
                            and record.date == previous_active + timedelta(days=1)
                            and current_interval.season_id == season_id):
                        current_interval.end = record.date
                    else:
                        current_interval = DateInterval(start=record.date, end=record.date,
                                                        season_id=season_id, approximate=approximate)
                        summary.crop_intervals.append(current_interval)
                    previous_active = record.date
                else:
                    current_interval = None
            if summary.record_count != manifest.get("record_count"):
                raise ValueError("Playback record count differs from manifest")
            if resolution not in result.available_resolutions:
                result.available_resolutions.append(resolution)
            if run_type == "SWAT_STANDARD_BASELINE":
                summary.codes.append(C.SWAT_BASELINE_NO_FSPM)
            elif not summary.fspm_trajectory_available:
                summary.codes.append(C.HYDROLOGY_ONLY if summary.hydrology_available else C.FSPM_STATE_MISSING)
            elif summary.first_representable_field or sample_representable_seen:
                summary.codes.append(C.SCIENTIFIC_STATE_AVAILABLE)
            else:
                summary.codes.append(C.FSPM_STATE_MISSING)
            if on is not None and summary.selected_date is None:
                summary.codes.append(C.DATE_NOT_IN_PLAYBACK)
        except (FileNotFoundError, OSError):
            summary.artifact_status = "UNAVAILABLE"
            summary.codes = [C.ARTIFACT_UNAVAILABLE]
        except (ValueError, KeyError, TypeError, sqlite3.DatabaseError):
            summary.artifact_status = "INVALID"
            summary.codes = [C.ARTIFACT_INVALID]
        if summary.artifact_status != "AVAILABLE":
            # A late read/count/integrity failure invalidates the whole artifact.
            # Do not leak dates or availability inferred from rows read before failure.
            summary.record_count = 0
            summary.first_record = None
            summary.last_record = None
            summary.first_active_crop = None
            summary.first_representable_field = None
            summary.first_plant_samples = None
            summary.crop_intervals.clear()
            summary.hydrology_available = False
            summary.fspm_trajectory_available = False
            summary.plant_samples_available = False
            summary.hru_ids.clear()
            summary.selected_date = None
        result.resolutions.append(summary)
        result.stored_fspm_trajectory_available |= summary.fspm_trajectory_available
        result.stored_fspm_samples_available |= summary.plant_samples_available
    result.fspm_results_available = (result.stored_fspm_summary_available or
        result.stored_fspm_trajectory_available or result.stored_fspm_samples_available)
    if not result.resolutions:
        if provenance_class is SimulationProvenanceClass.HISTORICAL_IMPORT:
            result.codes.extend([C.HISTORICAL_REFERENCE, C.NO_PLAYBACK_ARTIFACT])
        else:
            result.codes.append(C.NO_PLAYBACK_ARTIFACT)
        if run_type == "SWAT_STANDARD_BASELINE":
            result.codes.append(C.SWAT_BASELINE_NO_FSPM)
    else:
        result.codes = list(dict.fromkeys(result.codes + [code for item in result.resolutions for code in item.codes]))
    return result

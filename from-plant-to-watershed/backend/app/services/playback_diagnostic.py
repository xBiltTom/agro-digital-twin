"""Read-only scientific availability analysis; never reconstructs missing FSPM."""

from datetime import date, timedelta
from pathlib import Path
import sqlite3

from app.core.config import settings
from app.schemas.playback import PlaybackRecord
from app.schemas.playback_diagnostic import (
    AvailabilityCode as C, DateAvailability, DateInterval,
    ResolutionAvailability, SimulationAvailability,
)
from app.services.playback_artifact import PlaybackArtifactStore


def _present(group: dict, name: str) -> bool:
    state = group.get(name)
    return state is not None and state.availability == "AVAILABLE" and state.value is not None


def _maize(crop: str | None) -> bool:
    return any(name in (crop or "").lower() for name in ("maize", "corn", "maíz", "maiz"))


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


def diagnose_simulation(sim, *, on: date | None = None) -> SimulationAvailability:
    provenance = sim.provenance or {}
    requested = sim.requested_config or {}
    run_type = (requested.get("swat_plus") or {}).get("run_type") or (sim.effective_config or {}).get("run_type") or "RESEARCH_MULTISCALE"
    historical = provenance.get("source_kind") == "HISTORICAL_IMPORT" or provenance.get("experiment_id") == "south-fork-final-coupled-2015-2020"
    metrics = getattr(sim, "summary_metrics", None) or {}
    hydro_keys = ("total_runoff_mm", "total_evapotranspiration_mm", "mean_streamflow_m3s", "water_balance")
    result = SimulationAvailability(simulation_id=sim.id, simulation_name=sim.name,
        simulation_status=sim.status, run_type=run_type,
        origin="HISTORICAL_IMPORT" if historical else "EXECUTED" if provenance.get("evidence_type") else "UNKNOWN",
        stored_hydrology_available=bool(getattr(sim, "monthly_outputs", None) or any(metrics.get(key) is not None for key in hydro_keys)),
        stored_fspm_summary_available=bool(getattr(sim, "field_aggregates", None)))
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
            for record in store.iter_records(sim.id, manifest):
                summary.record_count += 1
                summary.first_record = summary.first_record or record.date
                summary.last_record = record.date
                state = diagnose_record(record)
                if on == record.date or (on is not None and resolution == "MONTHLY" and on.year == record.date.year and on.month == record.date.month) or (on is not None and resolution == "ANNUAL" and on.year == record.date.year):
                    summary.selected_date = state
                summary.hydrology_available |= any(_present(record.hydrology, name) for name in record.hydrology)
                summary.fspm_trajectory_available |= bool(record.field or record.plant_samples)
                sample_representable_seen |= state.sample_representable
                summary.hru_ids = sorted(set(summary.hru_ids) | {h.hru_id for h in record.hru_results})
                if record.crop and record.crop.active:
                    summary.first_active_crop = summary.first_active_crop or record.date
                    if state.field_representable:
                        summary.first_representable_field = summary.first_representable_field or record.date
                    if record.plant_samples:
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
        result.resolutions.append(summary)
    if not result.resolutions:
        result.codes.append(C.HISTORICAL_REFERENCE if historical else C.NO_PLAYBACK_ARTIFACT)
        if run_type == "SWAT_STANDARD_BASELINE":
            result.codes.append(C.SWAT_BASELINE_NO_FSPM)
    else:
        result.codes = list(dict.fromkeys(result.codes + [code for item in result.resolutions for code in item.codes]))
    return result

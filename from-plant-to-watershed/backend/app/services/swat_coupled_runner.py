"""Run the reusable SWAT+ -> executed calendar -> FSPM -> SWAT+ coupling flow."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any

from app.services.executed_calendar_fspm import ExecutedCalendarFspmRun, run_fspm_on_executed_calendar
from app.services.swat_executed_calendar import SwatExecutedCropCalendar
from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig, SwatRunResult
from app.schemas.coupling import CouplingPlantParameterSummary
from scientific_core import PlantPopulation


@dataclass(frozen=True)
class CoupledSwatRun:
    baseline_result: SwatRunResult
    result: SwatRunResult
    fspm: ExecutedCalendarFspmRun
    parameter_summary: CouplingPlantParameterSummary
    calendar: SwatExecutedCropCalendar
    iterations: list[dict[str, Any]]
    cdl_fractions: dict[int, float] | None


def _cdl_fractions(project: Path) -> tuple[dict[int, float] | None, dict[str, Any]]:
    manifest_path = project.parent / "manifest.json"
    if not manifest_path.is_file():
        return None, {"status": "NOT_AVAILABLE", "reason": "No adjacent phase34 manifest.json; HRU area weights will be used"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    evidence = (manifest.get("cdl_mapping") or {}).get("classification_evidence")
    if not isinstance(evidence, list) or not evidence:
        return None, {"status": "NOT_AVAILABLE", "reason": "manifest.json contains no per-HRU CDL classification evidence"}
    fractions: dict[int, float] = {}
    for row in evidence:
        if row.get("coverage_quality") != "VALID" or row.get("cdl_year") != 2019:
            continue
        try:
            hru_id = int(row["hru_id"])
            fraction = float(row["corn_fraction"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("CDL manifest contains an invalid HRU id or corn fraction") from None
        if not 0 < fraction <= 1:
            raise ValueError(f"CDL corn fraction for HRU {hru_id} is outside (0, 1]")
        if hru_id in fractions:
            raise ValueError(f"CDL manifest repeats HRU {hru_id}")
        fractions[hru_id] = fraction
    if not fractions:
        return None, {"status": "NOT_AVAILABLE", "reason": "No valid 2019 CDL HRU fractions; HRU area weights will be used"}
    return fractions, {
        "status": "AVAILABLE", "source_file": str(manifest_path), "classification": "STATIC_CDL_SNAPSHOT",
        "cdl_year": 2019, "valid_hru_count": len(fractions),
        "fractions_by_hru": {str(key): value for key, value in sorted(fractions.items())},
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }


def _calendar_from_result(
    result: SwatRunResult,
    *,
    target_crop: str,
    config: SwatPlusRunConfig,
    hru_weights: dict[int, float],
) -> SwatExecutedCropCalendar:
    return SwatExecutedCropCalendar.from_events(
        result.management_events,
        crop=target_crop,
        start_date=config.simulation_start,
        end_date=config.simulation_end,
        hru_weights=hru_weights,
    )


def _signature(calendar: SwatExecutedCropCalendar) -> dict[int, tuple[str, str]]:
    return {
        hru_id: (group.planting_date, group.harvest_date)
        for group in calendar.groups for hru_id in group.hru_ids
    }


def _verify_effective_weather(
    fspm: ExecutedCalendarFspmRun,
    *,
    workspace: Path,
    calendar: SwatExecutedCropCalendar,
    start_date,
    end_date,
    cdl_fractions: dict[int, float] | None,
) -> dict[str, Any]:
    from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader

    root = workspace / "TxtInOut" if (workspace / "TxtInOut" / "file.cio").is_file() else workspace
    reader = SwatClimateForcingReader(root)
    effective, provenance = reader.for_hrus(
        start_date, end_date, sorted(calendar.hru_calendar), crop_fraction_by_hru=cdl_fractions,
    )
    if len(effective) != len(fspm.field_climate):
        raise ValueError("Effective copied-project SWAT climate does not span the FSPM interval")
    compare_fields = ("date", "temp_c", "precip_mm", "solar_rad_mj", "rh_percent", "wind_speed_ms", "pet_mm")
    differences = []
    for expected, actual in zip(fspm.field_climate, effective, strict=True):
        if any(expected.get(key) != actual.get(key) for key in compare_fields):
            differences.append({"expected_date": expected.get("date"), "actual_date": actual.get("date")})
            break
    if differences:
        raise ValueError("Effective SWAT+ workspace weather differs from the FSPM forcing")
    return {
        "status": "MATCHED", "date_count": len(effective),
        "variables_checked": list(compare_fields),
        "temperature_unit": "degC", "precipitation_unit": "mm/day",
        "solar_radiation_unit": "MJ/m2/day", "relative_humidity_unit": "percent",
        "hru_station_assignment": "hru.con.wst -> weather-sta.cli",
        "field_spatial_weighting": "HRU area x 2019 CDL corn fraction" if cdl_fractions else "HRU area",
        "effective_forcing_provenance": provenance,
    }


def run_coupled_swat_with_executed_calendar(
    adapter: SwatPlusAdapter,
    config: SwatPlusRunConfig,
    *,
    target_crop: str = "corn",
    fspm_crop: str = "maize",
    plant_count: int = 100,
    seed: int = 42,
    max_iterations: int = 3,
) -> CoupledSwatRun:
    """Converge FSPM and real SWAT+ management calendars with copied workspaces.

    The first real SWAT+ pass establishes its executed management calendar. Each
    following pass maps the previous calendar's existing FSPM states to
    ``plants.plt`` and verifies whether the changed crop parameters alter the
    events. The run is accepted only after the per-HRU planting/harvest dates
    match the calendar used by FSPM.
    """
    if config.run_type != "SWAT_MULTISCALE_COUPLED":
        raise ValueError("run_coupled_swat_with_executed_calendar requires SWAT_MULTISCALE_COUPLED config")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    source_project = config.project_path
    cdl_fractions, cdl_provenance = _cdl_fractions(source_project)
    base_hru_weights = SwatExecutedCropCalendar.hru_spatial_weights(source_project, cdl_fractions)

    baseline_config = replace(
        config,
        run_type="SWAT_STANDARD_BASELINE",
        run_id=f"{config.run_id}-event-calendar",
    )
    baseline = adapter.run(baseline_config, target_crop=target_crop)
    calendar = _calendar_from_result(
        baseline, target_crop=target_crop, config=config, hru_weights=base_hru_weights,
    )
    iterations: list[dict[str, Any]] = []
    final_result: SwatRunResult | None = None
    final_fspm: ExecutedCalendarFspmRun | None = None
    final_summary: CouplingPlantParameterSummary | None = None
    final_calendar: SwatExecutedCropCalendar | None = None
    previous_signature = _signature(calendar)

    for iteration in range(1, max_iterations + 1):
        from app.services.twin_coupling_engine import _build_coupling_field_summary

        fspm = run_fspm_on_executed_calendar(
            project=source_project,
            calendar=calendar,
            start_date=config.simulation_start,
            end_date=config.simulation_end,
            plant_count=plant_count,
            seed=seed,
            crop_fraction_by_hru=cdl_fractions,
            crop=fspm_crop,
        )
        summary = _build_coupling_field_summary(
            fspm.dated_fields,
            fspm.seasonal_contracts,
            fspm.seasonal_weights,
        )
        run_config = replace(config, run_id=f"{config.run_id}-coupled-{iteration:02d}")
        mapper = SwatPlantParameterMapper(target_crop)
        result = adapter.run(
            run_config,
            workspace_mutator=lambda workspace, summary=summary: mapper.apply(workspace, summary),
            target_crop=target_crop,
        )
        executed_calendar = _calendar_from_result(
            result, target_crop=target_crop, config=config, hru_weights=base_hru_weights,
        )
        executed_signature = _signature(executed_calendar)
        matches = executed_signature == previous_signature
        effective_weather = _verify_effective_weather(
            fspm,
            workspace=Path(result.workspace),
            calendar=calendar,
            start_date=config.simulation_start,
            end_date=config.simulation_end,
            cdl_fractions=cdl_fractions,
        )
        modifications = result.provenance.get("workspace_modifications") or {}
        parameter_updates = modifications.get("parameter_updates") or []
        if not parameter_updates:
            raise ValueError("FSPM parameters were not applied to the copied SWAT+ project")
        iterations.append({
            "iteration": iteration,
            "input_calendar": calendar.as_dict(),
            "executed_calendar": executed_calendar.as_dict(),
            "per_hru_calendar_match": matches,
            "input_hru_dates": {str(key): list(value) for key, value in sorted(previous_signature.items())},
            "executed_hru_dates": {str(key): list(value) for key, value in sorted(executed_signature.items())},
            "parameter_update_count": len(parameter_updates),
            "effective_climate_match": effective_weather,
            "run_id": result.run_id,
            "workspace": result.workspace,
        })
        final_result, final_fspm, final_summary, final_calendar = result, fspm, summary, executed_calendar
        if matches:
            break
        calendar = executed_calendar
        previous_signature = executed_signature

    if final_result is None or final_fspm is None or final_summary is None or final_calendar is None:
        raise RuntimeError("Coupled SWAT+ run produced no completed iteration")
    if not iterations[-1]["per_hru_calendar_match"]:
        raise RuntimeError(
            f"SWAT+ management calendar did not converge with FSPM after {max_iterations} coupled iterations"
        )
    final_result.provenance["executed_calendar_coupling"] = {
        "status": "CONVERGED",
        "calendar_baseline_run_id": baseline.run_id,
        "calendar_baseline_workspace": baseline.workspace,
        "max_iterations": max_iterations,
        "iterations": iterations,
        "cdl_weights": cdl_provenance,
        "calendar_source": "SWAT+ mgt_out.txt from current executable run",
        "fspm_calendar_source": "Matching per-HRU PLANT and HARV/KILL events",
    }
    return CoupledSwatRun(
        baseline_result=baseline,
        result=final_result,
        fspm=final_fspm,
        parameter_summary=final_summary,
        calendar=final_calendar,
        iterations=iterations,
        cdl_fractions=cdl_fractions,
    )

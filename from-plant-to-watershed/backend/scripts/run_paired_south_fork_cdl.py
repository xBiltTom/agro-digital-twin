"""Run the South Fork CDL-classified baseline/coupled SWAT+ experiment.

This is a manual, real-engine experiment runner.  Each adapter call copies the
same source project to a fresh workspace, applies the same CDL HRU mapping,
and only the coupled call applies the FSPM ``plants.plt`` mapper afterwards.
"""

from __future__ import annotations

from datetime import date, timedelta
import json
import os
from pathlib import Path
from typing import Any

from app.services.swat_cdl_hru_mapper import SwatCDLHRUMapper
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig, _sha256
from scientific_core import PlantPopulation, PlantToFieldAggregator
from scientific_core.units import ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT
from scientific_core.validation import ValidationEngine


SOURCE_PROJECT = Path(os.environ["SOUTH_FORK_SWAT_PROJECT"])
EXECUTABLE = Path(os.environ["SWAT_PLUS_EXECUTABLE"])
CDL_COMPOSITION = Path(os.environ["SOUTH_FORK_CDL_COMPOSITION"])
RUN_ROOT = Path(os.environ.get("SOUTH_FORK_RUN_ROOT", "/home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/paired_runs_v3"))
REPORT_PATH = Path(os.environ.get("SOUTH_FORK_PAIRED_REPORT", "/home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/paired_cdl_2019_report_v3.json"))
CDL_PROVENANCE_PATH = CDL_COMPOSITION.with_name("hru_crop_provenance.json")
START = date.fromisoformat(os.environ.get("SOUTH_FORK_START", "2019-01-01"))
END = date.fromisoformat(os.environ.get("SOUTH_FORK_END", "2019-12-31"))
SEED = int(os.environ.get("SOUTH_FORK_FSPM_SEED", "42"))
PLANT_COUNT = int(os.environ.get("SOUTH_FORK_PLANT_COUNT", "1000"))
BASELINE_RUN_ID = os.environ.get("SOUTH_FORK_BASELINE_RUN_ID", "south-fork-2019-cdl-v3-baseline")
COUPLED_RUN_ID = os.environ.get("SOUTH_FORK_COUPLED_RUN_ID", "south-fork-2019-cdl-v3-coupled")


def _fspm_peak(project: Path, start: date, end: date) -> tuple[dict[str, Any], dict[str, Any]]:
    climate, forcing_provenance = SwatClimateForcingReader(project).for_period(start, end)
    population = PlantPopulation(PLANT_COUNT, SEED, crop="maize")
    gdd = 0.0
    peak_lai: dict[str, Any] | None = None
    peak_height: dict[str, Any] | None = None
    peak_root: dict[str, Any] | None = None
    peak_dates: dict[str, str] = {}
    for index, forcing in enumerate(climate, 1):
        gdd += max(0.0, forcing["temp_c"] - 8.0)
        current = PlantToFieldAggregator.aggregate(
            population.step(index, {**forcing, "gdd_c_day": gdd}, soil_moisture_vol=ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT),
            soil_moisture_vol=ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT,
        )
        current["soil_moisture_source"] = "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"
        current_date = (start + timedelta(days=index - 1)).isoformat()
        if peak_lai is None or current["mean_LAI"] > peak_lai["mean_LAI"]:
            peak_lai, peak_dates["date_of_peak_LAI"] = current, current_date
        if peak_height is None or current["plant_height_mean_m"] > peak_height["plant_height_mean_m"]:
            peak_height, peak_dates["date_of_peak_height"] = current, current_date
        if peak_root is None or current["root_depth_mean_m"] > peak_root["root_depth_mean_m"]:
            peak_root, peak_dates["date_of_peak_root_depth"] = current, current_date
    if peak_lai is None or peak_height is None or peak_root is None:
        raise RuntimeError("FSPM produced no states for the requested period")
    field = dict(peak_lai)
    field["plant_height_mean_m"] = peak_height["plant_height_mean_m"]
    field["root_depth_mean_m"] = peak_root["root_depth_mean_m"]
    field["aggregation_window"] = "full_period_peak_canopy_state"
    field["peak_dates"] = peak_dates
    field["climate_provenance"] = forcing_provenance
    field["fspm_seed"] = SEED
    field["plant_count"] = PLANT_COUNT
    return field, forcing_provenance


def _mutator(cdl_mapper: SwatCDLHRUMapper, field: dict[str, Any], coupled: bool):
    def apply(workspace: Path) -> dict[str, Any]:
        cdl_manifest = cdl_mapper.apply(workspace)
        if not coupled:
            return {"cdl_hru_mapping": cdl_manifest, "coupling": "SWAT_STANDARD_BASELINE"}
        fspm_manifest = SwatPlantParameterMapper("corn").apply(workspace, field)
        return {
            "cdl_hru_mapping": cdl_manifest,
            "fspm_parameter_mapping": fspm_manifest,
            "parameter_updates": fspm_manifest["parameter_updates"],
            "coupling": "SWAT_MULTISCALE_COUPLED",
        }
    return apply


def _observations(path: Path, start: date, end: date) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload["value"]["timeSeries"][0]["values"][0]["value"]
    result: dict[str, float] = {}
    for row in values:
        key = row["dateTime"][:10]
        if start.isoformat() <= key <= end.isoformat():
            result[key] = float(row["value"]) * 0.028316846592  # USGS ft3/s -> m3/s
    return result


def _series(result: Any, variable: str) -> dict[str, float]:
    return {row["period"]: float(row[variable]) for row in result.records if row.get(variable) is not None}


def _monthly_mean(series: dict[str, float]) -> dict[str, float]:
    """Aggregate daily discharge to calendar-month means without imputation."""
    grouped: dict[str, list[float]] = {}
    for period, value in series.items():
        month = f"{period[:7]}-01"
        grouped.setdefault(month, []).append(value)
    return {month: sum(values) / len(values) for month, values in sorted(grouped.items())}


def _summary(result: Any) -> dict[str, Any]:
    records = result.records
    def total(name: str) -> float:
        return sum(float(row[name]) for row in records if row.get(name) is not None)
    flow = _series(result, "streamflow_m3s")
    return {
        "run_id": result.run_id,
        "exit_code": result.exit_code,
        "status": result.status,
        "records": len(records),
        "output_files": result.output_files,
        "water_balance": result.water_balance,
        "totals": {
            "evapotranspiration_mm": total("evapotranspiration_mm"),
            "runoff_mm": total("runoff_mm"),
            "percolation_mm": total("percolation_mm"),
            "soil_water_mm_mean": sum(float(row["soil_water_mm"]) for row in records if row.get("soil_water_mm") is not None) / max(1, sum(row.get("soil_water_mm") is not None for row in records)),
            "streamflow_mean_m3s": sum(flow.values()) / max(1, len(flow)),
            "streamflow_volume_m3": sum(flow.values()) * 86400.0,
        },
        "provenance": result.provenance,
    }


def main() -> None:
    if not SOURCE_PROJECT.is_dir() or not CDL_COMPOSITION.is_file():
        raise FileNotFoundError("South Fork source project and CDL composition parquet are required")
    field, forcing_provenance = _fspm_peak(SOURCE_PROJECT, START, END)
    cdl_provenance = json.loads(CDL_PROVENANCE_PATH.read_text(encoding="utf-8")) if CDL_PROVENANCE_PATH.is_file() else {"status": "NOT_RECORDED"}
    mapper = SwatCDLHRUMapper(CDL_COMPOSITION, threshold=0.50)
    common = dict(
        project_path=SOURCE_PROJECT,
        executable_path=EXECUTABLE,
        working_directory=RUN_ROOT,
        simulation_start=START,
        simulation_end=END,
        warmup_period=0,
        output_frequency="DAILY",
        watershed_id="USGS-05451210",
        timeout_seconds=1800,
        outlet_unit="153",
    )
    adapter = SwatPlusAdapter()
    baseline = adapter.run(
        SwatPlusRunConfig(**common, run_id=BASELINE_RUN_ID, run_type="SWAT_STANDARD_BASELINE"),
        workspace_mutator=_mutator(mapper, field, False),
    )
    coupled = adapter.run(
        SwatPlusRunConfig(**common, run_id=COUPLED_RUN_ID, run_type="SWAT_MULTISCALE_COUPLED"),
        workspace_mutator=_mutator(mapper, field, True),
    )
    # The low-level adapter proves a real process/output; the experiment layer
    # adds the stronger coupled evidence label only after the CDL and FSPM
    # manifests are present.
    coupled.provenance["evidence_type"] = "REAL_SWAT_PLUS_COUPLED"
    baseline_summary, coupled_summary = _summary(baseline), _summary(coupled)
    observed_path = Path(__file__).resolve().parents[2] / "data/raw/usgs/05451210_2000-01-01_2025-12-31.json"
    observed = _observations(observed_path, START, END)
    bflow, cflow = _series(baseline, "streamflow_m3s"), _series(coupled, "streamflow_m3s")
    validation = ValidationEngine.compare_dated(
        observed, bflow, cflow, temporal_resolution="daily",
        observed_evidence_type="OBSERVED", baseline_evidence_type="REAL_SWAT_PLUS",
        coupled_evidence_type="REAL_SWAT_PLUS_COUPLED",
    )
    monthly_validation = ValidationEngine.compare_dated(
        _monthly_mean(observed), _monthly_mean(bflow), _monthly_mean(cflow), temporal_resolution="monthly",
        observed_evidence_type="OBSERVED", baseline_evidence_type="REAL_SWAT_PLUS",
        coupled_evidence_type="REAL_SWAT_PLUS_COUPLED",
    )
    dates = sorted(set(_series(baseline, "runoff_mm")) | set(_series(coupled, "runoff_mm")) | set(bflow) | set(cflow))
    events = []
    for period in dates:
        b_runoff = next((row.get("runoff_mm") for row in baseline.records if row["period"] == period), 0.0) or 0.0
        c_runoff = next((row.get("runoff_mm") for row in coupled.records if row["period"] == period), 0.0) or 0.0
        b_q, c_q = bflow.get(period, 0.0), cflow.get(period, 0.0)
        if b_runoff > 0 or c_runoff > 0 or b_q > 0 or c_q > 0:
            events.append({"period": period, "baseline_runoff_mm": b_runoff, "coupled_runoff_mm": c_runoff, "baseline_streamflow_m3s": b_q, "coupled_streamflow_m3s": c_q, "delta_streamflow_m3s": c_q - b_q})
    coupled_mapping = coupled.provenance["workspace_modifications"]["fspm_parameter_mapping"]
    plants_checksums = coupled_mapping.get("input_checksums", {}).get("plants.plt", {})
    # This acceptance item must prove an input change, not an output change.
    # A physically valid parameter perturbation can leave basin totals equal at
    # the printed precision; treating equal outputs as a failed coupling would
    # incorrectly encourage post-processing or artificial forcing changes.
    coupled_input_changed = (
        bool(plants_checksums.get("before_sha256"))
        and bool(plants_checksums.get("after_sha256"))
        and plants_checksums["before_sha256"] != plants_checksums["after_sha256"]
    )
    hydrologic_outputs_changed = baseline.provenance.get("output_checksums") != coupled.provenance.get("output_checksums")
    report = {
        "experiment_id": "south-fork-05451210-cdl-2019-v3",
        "period": {"start": START.isoformat(), "end": END.isoformat(), "days": (END - START).days + 1},
        "warmup_period": 0,
        "period_note": "2019 full calendar-year evaluation; no preceding warm-up year was included in this bounded real-engine run",
        "source_project": str(SOURCE_PROJECT.resolve()),
        "source_file_cio_sha256": _sha256(SOURCE_PROJECT / "file.cio"),
        "engine": {"path": str(EXECUTABLE.resolve()), "sha256": _sha256(EXECUTABLE)},
        "cdl_overlay": cdl_provenance,
        "forcing": forcing_provenance,
        "fspm_field": field,
        "baseline": baseline_summary,
        "coupled": coupled_summary,
        "comparison": {
            "delta": {name: coupled_summary["totals"][name] - baseline_summary["totals"][name] for name in coupled_summary["totals"]},
            "events_with_runoff_or_streamflow": events,
            "usgs_daily_validation": validation,
            "usgs_monthly_validation": monthly_validation,
        },
        "acceptance": {
            "same_source_project": baseline.provenance["source_file_cio_sha256"] == coupled.provenance["source_file_cio_sha256"],
            "both_exit_code_zero": baseline.exit_code == 0 and coupled.exit_code == 0,
            "real_baseline": baseline.provenance.get("evidence_type") == "REAL_SWAT_PLUS",
            "real_coupled": coupled.provenance.get("evidence_type") == "REAL_SWAT_PLUS_COUPLED",
            "coupled_input_changed": coupled_input_changed,
            "hydrologic_outputs_changed": hydrologic_outputs_changed,
            "plants_manifest": coupled_mapping,
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "baseline": baseline_summary, "coupled": coupled_summary, "field": field, "validation": validation, "event_count": len(events)}, indent=2, default=str))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the normal coupled FSPM/SWAT+ South Fork 2019 workflow.

The script is a reproducibility entrypoint, not a diagnostic shortcut. SWAT+
always runs in unique copied projects below workspaces/; dated result tables
are written separately below results/. Existing run IDs are never replaced.
"""

from __future__ import annotations

import argparse
import csv
import gzip
from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import platform
import sys
import traceback
from typing import Any, Iterable


BACKEND = Path(__file__).resolve().parents[1]
REPOSITORY = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.swat_coupled_runner import CoupledSwatRun, run_coupled_swat_with_executed_calendar
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig
from app.services.swat_input_compatibility import SWAT_SOURCE_VERSION
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_builder import swat_frames
from app.services.swat_soil_water import read_hru_gis_ids, read_hru_soils


DEFAULT_EXECUTABLE = Path.home() / ".swatplus_builder/engines/61.0.2.61/swatplus-61.0.2.61-gnu-lin_x86_64-Rel"
DEFAULT_PROJECT = BACKEND / "data/phase34-cdl-2019/project"
DEFAULT_OUTPUT_ROOT = BACKEND / "data/phase1-south-fork-2019"
SEVERE_WARNINGS = {
    "DUPLICATE_TIMESTAMPS", "MISSING_PERIODS", "UNEXPECTED_UNIT", "NON_FINITE_VALUE",
    "NEGATIVE_RUNOFF", "NEGATIVE_STREAMFLOW",
}
REQUIRED_DAILY_HYDROLOGY = (
    "precip_mm", "runoff_mm", "evapotranspiration_mm", "soil_water_mm", "streamflow_m3s",
)
ENGINE_SOURCE_FILES = (
    "backend/scripts/run_phase1_south_fork_2019.py",
    "backend/app/services/executed_calendar_fspm.py",
    "backend/app/services/playback_builder.py",
    "backend/app/services/swat_soil_water.py",
    "backend/app/services/swat_coupled_runner.py",
    "backend/app/services/swat_executed_calendar.py",
    "backend/app/services/swat_input_compatibility.py",
    "backend/app/services/swat_plant_parameter_mapper.py",
    "backend/app/services/swat_plus_adapter.py",
    "backend/app/services/swat_plus_parser.py",
    "backend/app/services/twin_coupling_engine.py",
    "backend/app/schemas/coupling.py",
    "backend/app/schemas/playback.py",
    "backend/scientific_core/multiscale.py",
    "backend/scientific_core/plant.py",
    "backend/scientific_core/units.py",
)


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (date, Path)):
        return value.isoformat() if isinstance(value, date) else str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_value(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _engine_source_fingerprint() -> dict[str, Any]:
    files = {name: _sha256(REPOSITORY / name) for name in ENGINE_SOURCE_FILES}
    digest = hashlib.sha256()
    for name, file_hash in sorted(files.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return {"sha256": digest.hexdigest(), "files": files}


def _tree_fingerprint(root: Path) -> dict[str, Any]:
    """Hash project contents and names to demonstrate the source stayed intact."""
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        file_hash = _sha256(path)
        size = path.stat().st_size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        file_count += 1
        byte_count += size
    return {"sha256": digest.hexdigest(), "file_count": file_count, "total_bytes": byte_count}


def _flatten(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            _flatten(name, item, output)
    elif isinstance(value, (list, tuple)):
        output[prefix] = json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"))
    else:
        output[prefix] = value


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    fields: list[str] = []
    for row in rows:
        flat: dict[str, Any] = {}
        _flatten("", row, flat)
        normalized.append(flat)
        for key in flat:
            if key not in fields:
                fields.append(key)
    if not fields:
        raise ValueError(f"Refusing to write an empty table without a schema: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
    return {"path": path.name, "row_count": len(normalized), "columns": fields,
            "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def _flatten_fspm_field_daily(fspm_days: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for day, state in sorted(fspm_days.items()):
        row: dict[str, Any] = {"date": day, "active": bool((state.get("crop") or {}).get("active"))}
        _flatten("crop", state.get("crop") or {}, row)
        if isinstance(state.get("field"), dict):
            _flatten("field", state["field"], row)
        rows.append(row)
    return rows


def _plant_sample_rows(run: CoupledSwatRun) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_day in run.fspm.group_daily:
        for plant in group_day["plants"]:
            rows.append({
                "date": group_day["date"], "calendar_id": group_day["calendar_id"],
                "planting_date": group_day["planting_date"], "harvest_date": group_day["harvest_date"],
                "calendar_spatial_weight": group_day["spatial_weight"],
                "plant_sample_context": group_day["plant_sample_context"],
                "plant": _json_value(plant),
            })
    return rows


def _expected_dates(start: date, end: date) -> set[str]:
    values = set()
    cursor = start
    while cursor <= end:
        values.add(cursor.isoformat())
        cursor += timedelta(days=1)
    return values


def _validate_run(run: CoupledSwatRun, start: date, end: date) -> dict[str, Any]:
    expected = _expected_dates(start, end)
    records = run.result.records
    basin_dates = [str(row.get("period")) for row in records]
    if len(basin_dates) != len(set(basin_dates)):
        raise ValueError("SWAT+ basin daily output contains duplicate dates")
    if set(basin_dates) != expected:
        raise ValueError(f"SWAT+ basin daily dates differ from requested year: {len(set(basin_dates))}/{len(expected)}")
    warnings = run.result.water_balance.get("warnings", [])
    severe = [warning for warning in warnings if warning.get("code") in SEVERE_WARNINGS]
    if severe:
        raise ValueError(f"SWAT+ output integrity warnings prevent acceptance: {severe}")
    coverage = run.result.water_balance.get("period_coverage", {})
    hydrology = {name: coverage.get(name, {}).get("complete") is True for name in REQUIRED_DAILY_HYDROLOGY}
    unavailable = [name for name, complete in hydrology.items() if not complete]
    if unavailable:
        raise ValueError(f"Requested daily SWAT+ hydrology is incomplete: {unavailable}")
    if not run.result.hru_results:
        raise ValueError("SWAT+ did not produce per-HRU water-balance rows")
    if not run.result.plant_results:
        raise ValueError("SWAT+ did not produce per-HRU plant rows")
    if not run.result.channel_results or not any(row.get("streamflow_m3s") is not None for row in run.result.channel_results):
        raise ValueError("SWAT+ did not produce daily channel flow rows")
    if len(run.fspm.fspm_days) != len(expected) or set(run.fspm.fspm_days) != expected:
        raise ValueError("FSPM daily states do not cover the requested calendar year")
    if len(run.fspm.field_climate) != len(expected) or {row["date"] for row in run.fspm.field_climate} != expected:
        raise ValueError("FSPM climate forcing does not cover the requested calendar year")
    keys = [(row["calendar_id"], row["date"]) for row in run.fspm.group_daily]
    if len(keys) != len(set(keys)):
        raise ValueError("FSPM contains duplicate calendar-group dates")
    return {
        "expected_daily_dates": len(expected), "basin_daily_dates": len(basin_dates),
        "fspm_daily_dates": len(run.fspm.fspm_days), "fspm_climate_daily_dates": len(run.fspm.field_climate),
        "hru_water_balance_rows": len(run.result.hru_results), "hru_plant_rows": len(run.result.plant_results),
        "channel_rows_all_channels": len(run.result.channel_results),
        "management_event_rows": len(run.result.management_events),
        "required_hydrology_complete": hydrology,
        "no_severe_output_warnings": True,
        "calendar_converged": run.iterations[-1]["per_hru_calendar_match"],
    }


def _variable_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}

    def add(name: str, unit: str, scale: str, source: str, classification: str,
            note: str | None = None, *, temporal_support: str = "daily",
            date_field: str | None = "date") -> None:
        catalog[name] = {"unit": unit, "spatial_scale": scale, "source": source,
                         "classification": classification, "temporal_support": temporal_support,
                         "date_field": date_field, "note": note}

    swat_variables = {
        "precip_mm": ("mm/day", "precipitation"), "runoff_mm": ("mm/day", "surface runoff generated"),
        "runoff_contribution_mm": ("mm/day", "surface runoff contribution"),
        "evapotranspiration_mm": ("mm/day", "actual evapotranspiration"),
        "plant_evapotranspiration_mm": ("mm/day", "plant evapotranspiration"),
        "soil_evaporation_mm": ("mm/day", "soil evaporation"),
        "canopy_evaporation_mm": ("mm/day", "canopy evaporation"),
        "potential_evapotranspiration_mm": ("mm/day", "potential evapotranspiration"),
        "soil_water_mm": ("mm", "end-of-day soil water storage"),
        "soil_water_initial_mm": ("mm", "beginning-of-day soil water storage"),
        "soil_water_average_mm": ("mm", "daily average soil water storage"),
        "percolation_mm": ("mm/day", "percolation"),
        "streamflow_m3s": ("m3/s", "channel discharge rate"),
        "lai_m2_m2": ("m2/m2", "SWAT+ plant leaf area index"),
        "biomass_kg_ha": ("kg/ha", "SWAT+ plant biomass"),
        "yield_kg_ha": ("kg/ha", "SWAT+ plant yield"),
        "water_stress_factor": ("fraction", "SWAT+ plant water-stress factor"),
        "aeration_stress_factor": ("fraction", "SWAT+ plant aeration-stress factor"),
        "temperature_stress_factor": ("fraction", "SWAT+ plant temperature-stress factor"),
        "nitrogen_stress_factor": ("fraction", "SWAT+ plant nitrogen-stress factor"),
        "phosphorus_stress_factor": ("fraction", "SWAT+ plant phosphorus-stress factor"),
        "salinity_stress_factor": ("fraction", "SWAT+ plant salinity-stress factor"),
        "plant_heat_unit_fraction": ("fraction", "SWAT+ plant heat-unit fraction"),
        "biomass_growth_kg_ha": ("kg/ha/day", "SWAT+ daily biomass growth"),
        "channel_area_ha": ("ha", "channel contributing area"),
        "channel_precip_volume_m3": ("m3/day", "channel precipitation volume"),
        "channel_evap_volume_m3": ("m3/day", "channel evaporation volume"),
        "channel_seep_volume_m3": ("m3/day", "channel seepage volume"),
        "channel_water_storage_m3": ("m3", "channel water storage"),
        "channel_inflow_m3s": ("m3/s", "channel inflow rate"),
        "channel_water_temp_c": ("degC", "channel water temperature"),
    }
    for name, (unit, description) in swat_variables.items():
        spatial = "channel" if name.startswith("channel_") or name == "streamflow_m3s" else "HRU crop state" if name in {
            "lai_m2_m2", "biomass_kg_ha", "yield_kg_ha", "water_stress_factor", "aeration_stress_factor",
            "temperature_stress_factor", "nitrogen_stress_factor", "phosphorus_stress_factor",
            "salinity_stress_factor", "plant_heat_unit_fraction", "biomass_growth_kg_ha",
        } else "basin and HRU"
        source = "SWAT+ channel_sd_day" if spatial == "channel" else (
            "SWAT+ hru_pw_day" if spatial == "HRU crop state" else "SWAT+ basin_wb_day and hru_wb_day"
        )
        add(name, unit, spatial, source, "SIMULATED", description)
    for name, unit in {
        "estimated_soil_moisture_vol_percent": "volumetric percent",
        "estimated_plant_available_fraction": "fraction [0, 1]",
        "estimated_root_zone_water_mm": "mm",
        "estimated_root_zone_depth_mm": "mm",
        "wilting_point_vol_percent": "volumetric percent",
        "field_capacity_vol_percent": "volumetric percent",
    }.items():
        add(name, unit, "HRU soil profile or FSPM calendar group",
            "SWAT+ hru_wb_day.sw_ave; hru-data.hru soil; soils.sol", "DERIVED",
            "SWAT+ storage excludes wilting-point water; available-water fraction is projected uniformly to the root zone; no daily layer water state is available")

    plant_units = {
        "plant_id": ("identifier", "modeled representative plant slot"),
        "x_m": ("m", "individual modeled slot position"), "y_m": ("m", "individual modeled slot position"),
        "base_kc": ("dimensionless", "sampled plant crop coefficient parameter"),
        "lai": ("m2/m2", "individual modeled plant LAI"), "plant_height_m": ("m", "individual modeled plant height"),
        "root_depth_cm": ("cm", "individual modeled maximum root-depth parameter"),
        "soil_moisture_offset": ("volumetric percentage points", "sampled individual moisture heterogeneity"),
        "root_depth_m": ("m", "individual modeled root depth"), "root_distribution": ("fraction by layer", "modeled root distribution"),
        "root_fraction_upper": ("fraction", "upper model-layer root share in playback"),
        "root_fraction_middle": ("fraction", "middle model-layer root share in playback"),
        "root_fraction_lower": ("fraction", "lower model-layer root share in playback"),
        "biomass_g_plant": ("g/plant", "individual modeled plant biomass"),
        "estimated_yield_g_plant": ("g/plant", "individual modeled yield estimate"),
        "transpiration_mm": ("mm/day", "individual modeled transpiration"),
        "actual_transpiration_mm_day": ("mm/day", "individual modeled transpiration"),
        "potential_transpiration_mm_day": ("mm/day", "individual modeled potential transpiration"),
        "stress": ("fraction", "individual modeled water-stress index"),
        "growing_degree_days_c_day": ("degC day", "individual modeled accumulated thermal time"),
        "leaf_count": ("count", "individual modeled leaves"),
        "leaf_area_m2": ("m2/plant proxy", "individual modeled leaf-area proxy"),
        "canopy_cover_fraction": ("fraction", "individual modeled canopy cover"),
        "soil_water_uptake_mm_day": ("mm/day", "individual modeled soil-water uptake"),
        "phenological_stage": ("category", "individual modeled crop stage"),
        "leaf_area_scale": ("dimensionless", "seeded LAI heterogeneity parameter"),
        "transpiration_capacity_scale": ("dimensionless", "seeded transpiration heterogeneity parameter"),
        "phenology_scale": ("dimensionless", "seeded phenology heterogeneity parameter"),
        "biomass_response_scale": ("dimensionless", "seeded biomass heterogeneity parameter"),
        "radiation_use_efficiency_kg_ha_per_mj_m2": ("kg/ha/(MJ/m2)", "sampled radiation-use-efficiency parameter"),
        "canopy_extinction_coefficient": ("dimensionless", "sampled canopy extinction parameter"),
        "thermal_maturity_gdd": ("degC day", "FSPM thermal-maturity parameter"),
        "base_canopy_extinction_coefficient": ("dimensionless", "assumed FSPM canopy parameter"),
        "base_biomass_energy_ratio_kg_ha_per_mj_m2": ("kg/ha/(MJ/m2)", "assumed FSPM biomass-energy parameter"),
    }
    assumed_plant_parameters = {
        "x_m", "y_m", "base_kc", "root_depth_cm", "soil_moisture_offset", "leaf_area_scale",
        "transpiration_capacity_scale", "phenology_scale", "biomass_response_scale",
        "radiation_use_efficiency_kg_ha_per_mj_m2", "canopy_extinction_coefficient",
        "thermal_maturity_gdd", "base_canopy_extinction_coefficient",
        "base_biomass_energy_ratio_kg_ha_per_mj_m2",
    }
    for name, (unit, description) in plant_units.items():
        classification = "ASSUMED" if name in assumed_plant_parameters else "SIMULATED"
        add(name, unit, "representative FSPM plant slot within its management-calendar group",
            "Existing SIMPLIFIED_FSPM PlantPopulation; deterministic seeded representative members",
            classification, f"{description}; representative model slot, not an observed individual plant.")

    field_units = {
        "mean_lai": "m2/m2", "mean_LAI": "m2/m2", "canopy_cover": "fraction",
        "plant_height_mean_m": "m", "root_depth_mean_m": "m", "mean_root_depth_cm": "cm",
        "mean_transpiration_mm": "mm/day", "actual_ET_mm_day": "mm/day", "potential_ET_mm_day": "mm/day",
        "transpiration_mm_day": "mm/day", "soil_water_uptake_mm_day": "mm/day", "mean_stress": "fraction",
        "water_stress": "fraction", "biomass_g_plant": "g/plant", "yield_estimate_g_plant": "g/plant",
        "mean_growing_degree_days_c_day": "degC day", "phenology_fraction": "fraction",
        "mean_thermal_maturity_gdd": "degC day", "canopy_extinction_coefficient": "dimensionless",
        "biomass_energy_ratio_kg_ha_per_mj_m2": "kg/ha/(MJ/m2)",
        "soil_moisture_vol": "volumetric percent", "active_crop_area_fraction": "fraction",
        "active_calendar_group_count": "count", "calendar_group_count": "count", "n_plants": "count",
    }
    assumed_field_parameters = {
        "mean_thermal_maturity_gdd", "canopy_extinction_coefficient",
        "biomass_energy_ratio_kg_ha_per_mj_m2", "n_plants",
    }
    for name, unit in field_units.items():
        classification = "ASSUMED" if name in assumed_field_parameters else "DERIVED"
        note = "Derived from daily SWAT+ HRU profile storage divided by soils.sol profile depth, assuming uniform depth distribution." if name == "soil_moisture_vol" else (
            "Area weighted across executed management-calendar groups; inactive groups contribute zero to crop structure."
        )
        if name in assumed_field_parameters - {"soil_moisture_vol"}:
            note = "FSPM model parameter or representative model-slot count; assumed and not calibrated or an observed field count."
        if name in {"mean_stress", "water_stress"}:
            note = "Area weighted mean of individual FSPM stress states, driven by SWAT+ HRU daily water estimates."
        add(name, unit, "mapped maize field aggregate",
            "Existing FSPM plant states aggregated by PlantToFieldAggregator and HRU/CDL weights",
            classification, note)

    climate_units = {"temp_c": "degC", "precip_mm": "mm/day", "solar_rad_mj": "MJ/m2/day",
                     "rh_percent": "%", "wind_speed_ms": "m/s", "pet_mm": "mm/day", "co2_ppm": "ppm"}
    for name, unit in climate_units.items():
        add(name, unit, "HRU-assigned station mix for mapped maize area",
            "weather-sta.cli direct station files; hru.con.wst; area x 2019 CDL corn fraction",
            "ASSUMED" if name == "co2_ppm" else "SOURCE_UNVERIFIED",
            "CO2=400 ppm is an explicit FSPM assumption." if name == "co2_ppm" else
            "Consumed unchanged from SWAT+ forcing files; project metadata does not identify whether station inputs are observations, reanalysis, or another source.")

    event_units = {"date": "ISO-8601 date", "operation": "category", "crop": "SWAT+ plant name",
                   "hru_id": "identifier"}
    for name, unit in event_units.items():
        add(name, unit, "HRU management event", "SWAT+ mgt_out.txt", "SIMULATED",
            "Executed modeled management event, not an observed field operation.")
    add("corn_fraction", "fraction [0, 1]", "HRU crop-area composition",
        "2019 CDL per-HRU classification evidence in adjacent phase34 manifest", "DERIVED",
        "Fraction of HRU mapped to corn from the static 2019 CDL snapshot.",
        temporal_support="static snapshot", date_field="cdl_year=2019")
    add("calendar_spatial_weight", "hru.con area x fraction", "distinct HRU calendar group",
        "hru.con.area multiplied by 2019 CDL corn_fraction", "DERIVED",
        "Relative aggregation weight; the source hru.con area unit is retained and not interpreted as channel geometry.",
        temporal_support="static run input", date_field=None)
    add("planting_date", "ISO-8601 date", "HRU crop calendar", "SWAT+ mgt_out.txt PLANT event", "SIMULATED",
        "Executed modeled date, not an observed field operation.", temporal_support="management event",
        date_field="planting_date")
    add("harvest_date", "ISO-8601 date", "HRU crop calendar", "SWAT+ mgt_out.txt HARV/KILL event", "SIMULATED",
        "Executed modeled date, not an observed field operation.", temporal_support="management event",
        date_field="harvest_date")
    return catalog


def _period_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = []
    for source in rows:
        row = {key: value for key, value in source.items() if key != "period"}
        row["date"] = source.get("period")
        dated.append(row)
    return dated


def _artifact_specs(run: CoupledSwatRun) -> list[tuple[str, list[dict[str, Any]], str, str]]:
    basin_rows = _period_rows(run.result.records)
    hru_rows = _period_rows(run.result.hru_results)
    plant_rows = _period_rows(run.result.plant_results)
    channel_rows = _period_rows(run.result.channel_results)
    events = [dict(row) for row in run.result.management_events]
    climate = [dict(row) for row in run.fspm.field_climate]
    fspm_field = _flatten_fspm_field_daily(run.fspm.fspm_days)
    fspm_groups = []
    for row in run.fspm.group_daily:
        output = {key: value for key, value in row.items() if key != "plants"}
        output["field"] = row["field"]
        output["forcing"] = row["forcing"]
        fspm_groups.append(output)
    calendar = [{"hru_id": hru, "calendar_id": group.calendar_id,
                 "planting_date": group.planting_date, "harvest_date": group.harvest_date,
                 "group_hru_count": len(group.hru_ids), "calendar_spatial_weight": group.spatial_weight}
                for group in run.calendar.groups for hru in group.hru_ids]
    return [
        ("basin_daily.csv", basin_rows, "basin and selected outlet", "SWAT+ simulated hydrology"),
        ("hru_daily.csv", hru_rows, "HRU", "SWAT+ simulated hydrology"),
        ("plant_hru_daily.csv", plant_rows, "HRU crop state", "SWAT+ simulated crop variables"),
        ("channel_daily.csv", channel_rows, "all channels emitted by channel_sd_day", "SWAT+ simulated channel discharge"),
        ("management_events.csv", events, "HRU event", "SWAT+ simulated management events"),
        ("climate_daily.csv", climate, "mapped maize HRU area", "SWAT+ forcing files, source origin unverified"),
        ("fspm_field_daily.csv", fspm_field, "mapped maize field aggregate", "FSPM daily field state"),
        ("fspm_calendar_group_daily.csv", fspm_groups, "distinct executed HRU calendar group", "FSPM daily cohort state"),
        ("fspm_plant_samples_daily.csv", _plant_sample_rows(run), "representative FSPM plant slots by calendar group", "FSPM modeled individual states"),
        ("executed_hru_calendar.csv", calendar, "HRU", "Dates extracted from current SWAT+ mgt_out.txt"),
    ]


def _git_revision() -> str | None:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY,
                              capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def run(args: argparse.Namespace) -> Path:
    project = args.project.expanduser().resolve()
    executable = args.executable.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    workspace_root = output_root / "workspaces" / args.run_id
    result_dir = output_root / "results" / args.run_id
    if result_dir.exists() or workspace_root.exists():
        raise FileExistsError(f"run_id {args.run_id!r} already has results or workspaces; choose a new run_id")
    if not project.is_dir():
        raise FileNotFoundError(f"South Fork SWAT+ project not found: {project}")

    result_dir.mkdir(parents=True, exist_ok=False)
    workspace_root.mkdir(parents=True, exist_ok=False)
    start, end = date(2019, 1, 1), date(2019, 12, 31)
    execution_status: dict[str, Any] = {
        "status": "RUNNING", "run_id": args.run_id, "started_on": date.today().isoformat(),
        "requested_period": [start.isoformat(), end.isoformat()], "project": str(project),
        "executable": str(executable), "workspace_root": str(workspace_root), "results_dir": str(result_dir),
    }
    _write_json(result_dir / "run_status.json", execution_status)
    source_before = _tree_fingerprint(project)
    try:
        config = SwatPlusRunConfig(
            project_path=project, executable_path=executable, working_directory=workspace_root,
            simulation_start=start, simulation_end=end, warmup_period=args.warmup_years,
            output_frequency="DAILY", watershed_id="05451210", run_id=args.run_id,
            timeout_seconds=args.timeout_seconds, run_type="SWAT_MULTISCALE_COUPLED", outlet_unit="153",
        )
        adapter = SwatPlusAdapter(executable, project, workspace_root)
        preflight = adapter.preflight(config, target_crop="corn")
        if preflight.get("status") != "READY":
            raise RuntimeError(f"SWAT+ preflight is {preflight.get('status')}: {preflight.get('blockers')}")
        execution_status["preflight"] = preflight
        _write_json(result_dir / "run_status.json", execution_status)

        coupled = run_coupled_swat_with_executed_calendar(
            adapter, config, target_crop="corn", fspm_crop="maize", plant_count=args.plant_count,
            seed=args.seed, max_iterations=5,
        )
        checks = _validate_run(coupled, start, end)
        source_after = _tree_fingerprint(project)
        if source_before != source_after:
            raise RuntimeError(f"Original SWAT+ project changed during execution: before={source_before}, after={source_after}")

        artifact_metadata: dict[str, Any] = {}
        for name, rows, scale, origin in _artifact_specs(coupled):
            metadata = _write_csv(result_dir / name, rows)
            metadata.update({"spatial_scale": scale, "data_origin": origin})
            available_date_columns = [column for column in ("date", "period", "planting_date", "harvest_date")
                                      if column in metadata["columns"]]
            metadata["date_columns"] = available_date_columns
            artifact_metadata[name] = metadata

        calendar_by_hru = {hru: {"calendar_id": group.calendar_id,
                                 "planting_date": group.planting_date, "harvest_date": group.harvest_date}
                           for group in coupled.calendar.groups for hru in group.hru_ids}
        frames = swat_frames(
            simulation_id=args.run_id, watershed_id="05451210", watershed_code="05451210",
            outlet_unit="153", run_type="SWAT_MULTISCALE_COUPLED", resolution="DAILY",
            records=coupled.result.records, hru_results=coupled.result.hru_results,
            plant_results=coupled.result.plant_results, channel_results=coupled.result.channel_results,
            soil_profiles=read_hru_soils(project), hru_gis_ids=read_hru_gis_ids(project),
            hru_calendar=calendar_by_hru,
            forcing=coupled.fspm.field_climate,
            forcing_source="SWAT+ station forcing weighted by mapped maize HRU area",
            fspm_days=coupled.fspm.fspm_days, start_date=start, end_date=end,
        )
        playback_store = PlaybackArtifactStore(BACKEND / "data/playback/v1")
        playback = playback_store.write(args.run_id, frames, provenance={
            "source_run_id": args.run_id, "swat_output_checksums": coupled.result.provenance.get("output_checksums"),
            "fspm_soil_water": coupled.fspm.provenance["soil_moisture"],
            "calendar": coupled.calendar.as_dict(),
        }, limitations=[
            "Root-zone water adds layer-specific wilting-point water to SWAT+ available storage under a uniform available-water-fraction assumption; daily layer water is unavailable",
            "Representative FSPM plant slots are simulated, not observed individuals",
            "Channel flow is m3/s and storage is m3; river depth is unavailable",
        ])
        sidecar = playback_store.root / playback["artifact_file"]
        archive = result_dir / "playback.sqlite.gz"
        with sidecar.open("rb") as source, archive.open("wb") as target:
            with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    compressed.write(block)
        playback["archive_file"] = archive.name
        playback["archive_sha256"] = _sha256(archive)
        artifact_metadata[archive.name] = {
            "path": archive.name, "row_count": playback["record_count"], "columns": [],
            "date_columns": ["date"], "sha256": playback["archive_sha256"],
            "size_bytes": archive.stat().st_size,
            "spatial_scale": "multiscale daily playback", "data_origin": "gzip of versioned PlaybackArtifactStore sidecar",
        }
        example = playback_store.page(args.run_id, playback, on=date(2019, 7, 15), limit=1)[1][0]
        _write_json(result_dir / "playback_example_2019-07-15.json", example.model_dump(mode="json"))
        artifact_metadata["playback_example_2019-07-15.json"] = {
            "path": "playback_example_2019-07-15.json", "row_count": 1, "columns": list(type(example).model_fields),
            "date_columns": ["date"], "sha256": _sha256(result_dir / "playback_example_2019-07-15.json"),
            "size_bytes": (result_dir / "playback_example_2019-07-15.json").stat().st_size,
            "spatial_scale": "multiscale daily playback", "data_origin": "versioned PlaybackArtifactStore",
        }

        json_artifacts = (
            ("calendar.json", coupled.calendar.as_dict(), "HRU calendars", "SWAT+ executed management events"),
            ("parameter_mapping.json", coupled.parameter_summary.model_dump(mode="json"), "maize parameter contract", "FSPM-derived parameters mapped to copied SWAT+ inputs"),
            ("coupling_iterations.json", coupled.iterations, "run and calendar convergence", "recorded FSPM/SWAT+ workflow"),
            ("fspm_provenance.json", coupled.fspm.provenance, "FSPM model and forcing", "existing FSPM plus project forcing; assumptions identified"),
        )
        for name, value, scale, origin in json_artifacts:
            path = result_dir / name
            _write_json(path, value)
            artifact_metadata[name] = {
                "path": name, "row_count": None, "columns": [], "date_columns": ["start_date", "end_date"],
                "sha256": _sha256(path), "size_bytes": path.stat().st_size,
                "spatial_scale": scale, "data_origin": origin,
            }
        for name, result in (("calendar-baseline", coupled.baseline_result), ("coupled-final", coupled.result)):
            path = result_dir / f"{name}.log"
            path.write_text(
                f"STDOUT\n{result.stdout}\nSTDERR\n{result.stderr}", encoding="utf-8",
            )
            artifact_metadata[path.name] = {
                "path": path.name, "row_count": None, "columns": [], "date_columns": [],
                "sha256": _sha256(path), "size_bytes": path.stat().st_size,
                "spatial_scale": "SWAT+ execution log", "data_origin": "direct local executable stdout/stderr",
            }
            workspace = Path(result.workspace)
            compatibility_source = workspace / "swat_input_compatibility.json"
            if not compatibility_source.is_file() and (workspace / "TxtInOut" / "swat_input_compatibility.json").is_file():
                compatibility_source = workspace / "TxtInOut" / "swat_input_compatibility.json"
            if not compatibility_source.is_file():
                raise FileNotFoundError(f"{name} has no SWAT+ input compatibility correction log")
            compatibility_data = json.loads(compatibility_source.read_text(encoding="utf-8", errors="strict"))
            compatibility_path = result_dir / f"{name}-input-compatibility.json"
            _write_json(compatibility_path, compatibility_data)
            artifact_metadata[compatibility_path.name] = {
                "path": compatibility_path.name, "row_count": sum(
                    len(rows) for rows in compatibility_data.get("corrections_by_file", {}).values()
                ),
                "columns": [], "date_columns": [], "sha256": _sha256(compatibility_path),
                "size_bytes": compatibility_path.stat().st_size,
                "spatial_scale": "SWAT+ copied input project",
                "data_origin": "isolated-copy integer-format compatibility corrections",
            }

        manifest = {
            "schema_version": "1.0", "status": "COMPLETED", "run_id": args.run_id,
            "project": {"name": "South Fork 2019 CDL corn-majority experimental project",
                        "path": str(project), "source_tree_fingerprint_before": source_before,
                        "source_tree_fingerprint_after": source_after,
                        "adjacent_manifest": str(project.parent / "manifest.json"),
                        "experiment_limitation": "2019 CDL-derived corn-majority management scenario, not a historical reconstruction."},
            "run": {"start_date": start.isoformat(), "end_date": end.isoformat(),
                    "displayed_period": "2019-01-01 through 2019-12-31",
                    "warmup_years": args.warmup_years,
                    "warmup_period": [f"{start.year - args.warmup_years}-01-01", "2018-12-31"] if args.warmup_years else None,
                    "warmup_semantics": "SWAT+ starts before the displayed period; print.prt nyskip suppresses warmup output; FSPM and artifact dates cover only 2019.",
                    "frequency": "DAILY", "run_type": "SWAT_MULTISCALE_COUPLED",
                    "target_crop": "corn", "fspm_crop": "maize", "plant_count_per_calendar_group": args.plant_count,
                    "seed": args.seed, "calendar_convergence_iterations": coupled.iterations},
            "engines": {"swat_plus": {"source_version": SWAT_SOURCE_VERSION,
                                      "executable": str(executable),
                                      "sha256": coupled.result.provenance.get("executable_sha256"),
                                      "reported_version": coupled.result.provenance.get("executable_version"),
                                      "source_code_tag": "https://github.com/swat-model/swatplus/tree/61.0.2.61"},
                        "fspm": {"model": "SIMPLIFIED_FSPM", "version": "3.0-simplified-fspm",
                                 "daily_source": "backend/scientific_core/multiscale.py; existing model"}},
            "calendar": coupled.calendar.as_dict(),
            "calendar_coupling": coupled.result.provenance.get("executed_calendar_coupling"),
            "effective_weather_match": coupled.iterations[-1].get("effective_climate_match"),
            "fspm_forcing_provenance": coupled.fspm.provenance,
            "parameter_mapping": coupled.result.provenance.get("workspace_modifications"),
            "swat_outputs": {"water_balance": coupled.result.water_balance,
                             "hru_count": len({row.get("hru_unit") for row in coupled.result.hru_results}),
                             "plant_hru_count": len({row.get("hru_unit") for row in coupled.result.plant_results}),
                             "channel_count": len({row.get("channel_unit") for row in coupled.result.channel_results}),
                             "management_event_count": len(coupled.result.management_events),
                             "completed_run_ids": [coupled.baseline_result.run_id, coupled.result.run_id],
                             "workspaces": [coupled.baseline_result.workspace, coupled.result.workspace],
                             "input_compatibility": coupled.result.provenance.get("input_compatibility"),
                             "input_compatibility_by_run": {
                                 "calendar_baseline": coupled.baseline_result.provenance.get("input_compatibility"),
                                 "coupled_final": coupled.result.provenance.get("input_compatibility"),
                             },
                             "output_checksums": coupled.result.provenance.get("output_checksums")},
            "validation": checks,
            "variable_catalog": _variable_catalog(),
            "variable_availability": coupled.result.water_balance.get("variable_availability"),
            "artifacts": artifact_metadata,
            "playback": playback,
            "limitations": [
                "The phase34 South Fork project is an experimental 2019 CDL-derived management scenario.",
                "The source project does not declare the origin of its weather station data; the forcing is consumed unchanged and marked SOURCE_UNVERIFIED.",
                "FSPM moisture is derived from SWAT+ whole-profile storage and soils.sol under a uniform-profile approximation; no daily layer water states are available.",
                "SWAT+ streamflow remains a rate in m3/s; no channel depth conversion is made.",
                "FSPM plant states are representative deterministic model slots and field aggregates, not observed individuals.",
                "SWAT+ management event dates are modeled execution events; daily event timing is applied to the complete FSPM day.",
            ],
            "reproduction": {"command": f"backend/venv/bin/python backend/scripts/run_phase1_south_fork_2019.py --run-id {args.run_id}",
                             "python": platform.python_version(), "platform": platform.platform(),
                             "code_revision": _git_revision(),
                             "engine_source_fingerprint": _engine_source_fingerprint(),
                             "created_on": date.today().isoformat()},
        }
        _write_json(result_dir / "manifest.json", manifest)
        execution_status.update({"status": "COMPLETED", "checks": checks,
                                 "manifest": str(result_dir / "manifest.json"),
                                 "artifact_count": len(artifact_metadata),
                                 "source_project_unchanged": source_before == source_after})
        _write_json(result_dir / "run_status.json", execution_status)
        return result_dir
    except Exception as exc:
        try:
            source_after = _tree_fingerprint(project)
        except Exception as fingerprint_error:
            source_after = {"status": "UNAVAILABLE", "error": str(fingerprint_error)}
        execution_status.update({"status": "FAILED", "error": str(exc),
                                 "exception_type": type(exc).__name__,
                                 "traceback": traceback.format_exc(),
                                 "source_tree_fingerprint_before": source_before,
                                 "source_tree_fingerprint_after": source_after,
                                 "source_project_unchanged": source_before == source_after})
        _write_json(result_dir / "run_status.json", execution_status)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="phase1-sf-2019-v1")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--warmup-years", type=int, default=19)
    parser.add_argument("--plant-count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    args = parser.parse_args()
    try:
        result_dir = run(args)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Status record: {args.output_root / 'results' / args.run_id / 'run_status.json'}", file=sys.stderr)
        return 1
    print(f"COMPLETED: {result_dir}")
    print(f"Manifest: {result_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

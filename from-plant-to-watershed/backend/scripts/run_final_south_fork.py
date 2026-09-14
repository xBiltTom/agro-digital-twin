"""Reproducible final South Fork Iowa River pilot experiment.

The runner never adjusts SWAT+ outputs.  It creates isolated workspaces, keeps
the historical reference unchanged, and records unavailable optional CMIP6/NASS
items rather than substituting synthetic values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

from app.services.swat_cdl_hru_mapper import SwatCDLHRUMapper
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig, SwatRunResult
from scientific_core import PlantPopulation, PlantToFieldAggregator, ValidationEngine


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PROJECT = Path(os.environ.get("SOUTH_FORK_SWAT_PROJECT", "/home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/project/Scenarios/Default/TxtInOut"))
EXECUTABLE = Path(os.environ.get("SWAT_PLUS_EXECUTABLE", "/home/bilton/.swatplus_builder/bin/swatplus_exe"))
CDL_COMPOSITION = Path(os.environ.get("SOUTH_FORK_CDL_COMPOSITION", "/home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/cdl/hru_crop_composition.parquet"))
RUN_ROOT = Path(os.environ.get("SOUTH_FORK_FINAL_RUN_ROOT", "/home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/final_runs"))
START, END, WARMUP_YEARS = date(2015, 1, 1), date(2020, 12, 31), 3
EVALUATION_START, EVALUATION_END = date(2018, 1, 1), date(2020, 12, 31)
FSPM_SEED, PLANT_COUNT = 42, 1000
WATERSHED_ID, OUTLET = "USGS-05451210", "153"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _observations(start: date, end: date) -> dict[str, float]:
    payload = json.loads((ROOT / "data/raw/usgs/05451210_2000-01-01_2025-12-31.json").read_text(encoding="utf-8"))
    rows = payload["value"]["timeSeries"][0]["values"][0]["value"]
    return {row["dateTime"][:10]: float(row["value"]) * 0.028316846592 for row in rows if start.isoformat() <= row["dateTime"][:10] <= end.isoformat()}


def _series(run: SwatRunResult, variable: str) -> dict[str, float]:
    return {row["period"]: float(row[variable]) for row in run.records if row.get(variable) is not None and EVALUATION_START.isoformat() <= row["period"] <= EVALUATION_END.isoformat()}


def _monthly(values: dict[str, float]) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for day, value in values.items():
        grouped.setdefault(f"{day[:7]}-01", []).append(value)
    return {month: fmean(rows) for month, rows in sorted(grouped.items())}


def _fspm_field() -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
    forcing, provenance = SwatClimateForcingReader(SOURCE_PROJECT).for_period(START, END)
    population, gdd = PlantPopulation(PLANT_COUNT, FSPM_SEED, crop="maize"), 0.0
    peak_lai: dict[str, Any] | None = None
    peak_height: dict[str, Any] | None = None
    peak_root: dict[str, Any] | None = None
    daily: dict[str, dict[str, float]] = {}
    for index, weather in enumerate(forcing, 1):
        gdd += max(0.0, weather["temp_c"] - 8.0)
        aggregate = PlantToFieldAggregator.aggregate(population.step(index, {**weather, "gdd_c_day": gdd}, soil_moisture_vol=0.24), soil_moisture_vol=0.24)
        day = date.fromordinal(START.toordinal() + index - 1).isoformat()
        daily[day] = {"precipitation_mm": weather["precip_mm"], "temperature_min": weather["temp_c"], "temperature_max": weather["temp_c"], "FSPM_LAI": aggregate["mean_LAI"], "FSPM_root_depth": aggregate["root_depth_mean_m"], "FSPM_biomass": aggregate["biomass_g_plant"], "FSPM_water_stress": aggregate["water_stress"]}
        if peak_lai is None or aggregate["mean_LAI"] > peak_lai["mean_LAI"]:
            peak_lai = aggregate
        if peak_height is None or aggregate["plant_height_mean_m"] > peak_height["plant_height_mean_m"]:
            peak_height = aggregate
        if peak_root is None or aggregate["root_depth_mean_m"] > peak_root["root_depth_mean_m"]:
            peak_root = aggregate
    assert peak_lai and peak_height and peak_root
    return {**peak_lai, "plant_height_mean_m": peak_height["plant_height_mean_m"], "root_depth_mean_m": peak_root["root_depth_mean_m"], "fspm_seed": FSPM_SEED, "plant_count": PLANT_COUNT, "forcing": provenance}, daily


def _weather_rows(path: Path) -> list[list[str]]:
    return [line.split() for line in path.read_text(encoding="utf-8", errors="strict").splitlines()[2:] if line.split()]


def _change_weather(workspace: Path, *, temp_offset_c: float = 0.0, precip_factor: float = 1.0, cmip_rows: dict[str, dict[str, float]] | None = None) -> dict[str, Any]:
    changed: list[str] = []
    for station in _weather_rows(workspace / "weather-sta.cli"):
        for column, kind, count in ((2, "pcp", 3), (3, "tmp", 4)):
            path = workspace / station[column]
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
            updated = lines[:3]
            for line in lines[3:]:
                fields = line.split()
                if len(fields) < count:
                    updated.append(line)
                    continue
                current = date(int(fields[0]), 1, 1).fromordinal(date(int(fields[0]), 1, 1).toordinal() + int(fields[1]) - 1).isoformat()
                future = cmip_rows.get(current) if cmip_rows else None
                if kind == "pcp":
                    fields[2] = f"{(future['precip_mm'] if future else float(fields[2]) * precip_factor):.5f}"
                else:
                    offset = (future["temp_c"] - (float(fields[2]) + float(fields[3])) / 2.0) if future else temp_offset_c
                    fields[2], fields[3] = f"{float(fields[2]) + offset:.5f}", f"{float(fields[3]) + offset:.5f}"
                updated.append("    ".join(fields))
            path.write_text("\n".join(updated) + "\n", encoding="utf-8")
            changed.append(path.name)
    return {"weather_files": sorted(changed), "temperature_offset_c": temp_offset_c, "precipitation_factor": precip_factor, "method": "forcing files edited before SWAT+ execution"}


def _no_till(workspace: Path) -> dict[str, Any]:
    path = workspace / "management.sch"
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    index = next(index for index, line in enumerate(lines) if line.split() and line.split()[0] == "corn_rot")
    header = lines[index].split()
    header[1] = "1"  # one scheduled SWAT+ tillage operation plus auto planting/harvest.
    lines[index] = "  ".join(header)
    # SWAT+ requires decision-table names before scheduled operations.
    # ``null`` is the unused string op_data2 field; op_data3 is numeric.
    lines.insert(index + 2, " " * 51 + "till                 4        15       0.00000          zerotill       null       0.00000")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"management_file": "management.sch", "operation": "till", "operation_date": "April 15", "tillage_record": "zerotill", "rationale": "Official SWAT+ tillage.til record zerotill (mix_eff=0.05, mix_dp=25 mm) replaces no outputs."}


def _sorghum(workspace: Path) -> dict[str, Any]:
    replacements = (("corn_lum", "sorghum_lum"), ("corn_comm", "sorghum_comm"), ("corn_rot", "sorghum_rot"), ("corn", "grsg"))
    for name in ("hru-data.hru", "landuse.lum", "plant.ini", "management.sch"):
        path = workspace / name
        text = path.read_text(encoding="utf-8", errors="strict")
        for old, new in replacements:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    return {"target_plant": "grsg", "plant_table_description": "grain_sorghum", "method": "CDL corn-majority HRU community/rotation replaced by existing SWAT+ grsg tabulated record"}


def _run(name: str, field: dict[str, Any], *, coupled: bool = False, scenario: str = "HISTORICAL_REFERENCE", weather: dict[str, Any] | None = None) -> SwatRunResult:
    mapper = SwatCDLHRUMapper(CDL_COMPOSITION, threshold=0.50)
    def mutator(workspace: Path) -> dict[str, Any]:
        cdl = mapper.apply(workspace)
        change: dict[str, Any] = {"cdl_hru_mapping": cdl}
        if coupled:
            change["fspm_parameter_mapping"] = SwatPlantParameterMapper("corn").apply(workspace, field)
        if weather:
            change["climate_forcing_change"] = _change_weather(workspace, **weather)
        if scenario == "NO_TILL":
            change["management_change"] = _no_till(workspace)
        if scenario == "MAIZE_TO_SORGHUM":
            change["crop_change"] = _sorghum(workspace)
        crop = "grsg" if scenario == "MAIZE_TO_SORGHUM" else "corn"
        change["crop_chain_input"] = SwatCropChainDiagnostic.input_chain(workspace, cdl["target_hrus"], crop=crop)
        return change
    result = SwatPlusAdapter().run(SwatPlusRunConfig(
        project_path=SOURCE_PROJECT, executable_path=EXECUTABLE, working_directory=RUN_ROOT,
        simulation_start=START, simulation_end=END, warmup_period=WARMUP_YEARS, output_frequency="DAILY",
        watershed_id=WATERSHED_ID, run_id=name, run_type="SWAT_MULTISCALE_COUPLED" if coupled else "SWAT_STANDARD_BASELINE",
        timeout_seconds=3600, outlet_unit=OUTLET), workspace_mutator=mutator)
    if coupled:
        result.provenance["evidence_type"] = "REAL_SWAT_PLUS_COUPLED"
    result.provenance["workspace_modifications"]["crop_chain_output"] = SwatCropChainDiagnostic.output_chain(result.workspace, crop="grsg" if scenario == "MAIZE_TO_SORGHUM" else "corn")
    return result


def _totals(run: SwatRunResult) -> dict[str, float | None]:
    records = [row for row in run.records if EVALUATION_START.isoformat() <= row["period"] <= EVALUATION_END.isoformat()]
    return {"runoff_mm": sum(row.get("runoff_mm") or 0.0 for row in records), "streamflow_m3s_mean": fmean(row["streamflow_m3s"] for row in records if row.get("streamflow_m3s") is not None), "et_mm": sum(row.get("evapotranspiration_mm") or 0.0 for row in records), "soil_water_mm": fmean(row["soil_water_mm"] for row in records if row.get("soil_water_mm") is not None), "yield_estimated": None}


def _delta(reference: dict[str, float | None], scenario: dict[str, float | None]) -> dict[str, dict[str, float | None]]:
    return {name: {"absolute": None if reference[name] is None or scenario[name] is None else scenario[name] - reference[name], "percent": None if reference[name] in {None, 0} or scenario[name] is None else (scenario[name] - reference[name]) / reference[name] * 100.0} for name in reference}


def _ks(observed: list[float], simulated: list[float]) -> dict[str, Any]:
    if len(observed) < 2 or len(simulated) < 2:
        return {"status": "INSUFFICIENT_EVIDENCE"}
    values = sorted(set(observed + simulated)); n, m = len(observed), len(simulated)
    statistic = max(abs(sum(value <= x for value in observed) / n - sum(value <= x for value in simulated) / m) for x in values)
    effective_n = n * m / (n + m)
    p_value = min(1.0, 2.0 * math.exp(-2.0 * effective_n * statistic * statistic))
    return {"status": "COMPUTED", "statistic": statistic, "p_value_asymptotic": p_value, "n_observed": n, "n_simulated": m}


def _wilcoxon(baseline_error: list[float], coupled_error: list[float]) -> dict[str, Any]:
    differences = [c - b for b, c in zip(baseline_error, coupled_error) if not math.isclose(b, c, abs_tol=1e-12)]
    if len(differences) < 2:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "all monthly paired absolute errors are tied or fewer than two pairs"}
    ordered = sorted(enumerate(differences), key=lambda pair: abs(pair[1])); ranks = [0.0] * len(ordered); index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and math.isclose(abs(ordered[end][1]), abs(ordered[end + 1][1]), abs_tol=1e-12): end += 1
        rank = (index + 1 + end + 1) / 2.0
        for cursor in range(index, end + 1): ranks[cursor] = rank
        index = end + 1
    positive = sum(ranks[index] for index, (_, value) in enumerate(ordered) if value > 0)
    negative = sum(ranks[index] for index, (_, value) in enumerate(ordered) if value < 0)
    return {"status": "COMPUTED", "n_pairs": len(differences), "statistic_min_rank_sum": min(positive, negative), "interpretation": "single-watershed temporal paired comparison; temporal dependence limits population inference"}


def _write_dataset(baseline: SwatRunResult, coupled: SwatRunResult, observed: dict[str, float], fspm_daily: dict[str, dict[str, float]]) -> tuple[str, str]:
    import pyarrow as pa
    import pyarrow.parquet as pq
    b_records, c_records = {row["period"]: row for row in baseline.records}, {row["period"]: row for row in coupled.records}
    rows = []
    for day in sorted(set(b_records) & set(c_records) & set(observed)):
        if not EVALUATION_START.isoformat() <= day <= EVALUATION_END.isoformat(): continue
        b, c, field = b_records[day], c_records[day], fspm_daily[day]
        rows.append({"date": day, "watershed_id": WATERSHED_ID, "hru_id": "WATERSHED_OUTLET", "split": "VALIDATION", "scenario": "HISTORICAL", "observed_streamflow_m3s": observed[day], "baseline_streamflow_m3s": b.get("streamflow_m3s"), "coupled_streamflow_m3s": c.get("streamflow_m3s"), "baseline_runoff_mm": b.get("runoff_mm"), "coupled_runoff_mm": c.get("runoff_mm"), "baseline_et_mm": b.get("evapotranspiration_mm"), "coupled_et_mm": c.get("evapotranspiration_mm"), "soil_water_mm": b.get("soil_water_mm"), "precipitation_mm": field["precipitation_mm"], "temperature_min": field["temperature_min"], "temperature_max": field["temperature_max"], "FSPM_LAI": field["FSPM_LAI"], "FSPM_root_depth": field["FSPM_root_depth"], "FSPM_biomass": field["FSPM_biomass"], "FSPM_water_stress": field["FSPM_water_stress"], "yield_estimated": None, "yield_observed": None, "data_classification": "REAL_SWAT_PLUS_AND_USGS_WITH_DERIVED_FSPM", "usgs_provenance_id": "05451210_2000-01-01_2025-12-31", "swat_baseline_run_id": baseline.run_id, "swat_coupled_run_id": coupled.run_id})
    out = ROOT / "data/final"; out.mkdir(parents=True, exist_ok=True)
    data_path, schema_path = out / "experiment_dataset.parquet", out / "experiment_dataset.schema.json"
    pq.write_table(pa.Table.from_pylist(rows), data_path, compression="zstd")
    schema_path.write_text(json.dumps({"schema_version": "south-fork-final-v1", "row_count": len(rows), "data_file": data_path.name, "units": {"streamflow_m3s": "m3/s", "runoff_mm": "mm/day", "et_mm": "mm/day", "soil_water_mm": "mm", "precipitation_mm": "mm/day", "temperature": "degC", "FSPM_LAI": "m2_leaf/m2_ground", "FSPM_root_depth": "m", "FSPM_biomass": "g/plant"}, "synthetic_data": False, "limitations": ["FSPM variables are derived model states, not observations.", "hru_id is watershed outlet because this export joins outlet-level SWAT+ and USGS series."]}, indent=2) + "\n", encoding="utf-8")
    return str(data_path), str(schema_path)


def main() -> None:
    for path in (SOURCE_PROJECT, EXECUTABLE, CDL_COMPOSITION):
        if not path.exists(): raise FileNotFoundError(path)
    field, fspm_daily = _fspm_field()
    baseline = _run("south-fork-final-baseline-2015-2020", field)
    coupled = _run("south-fork-final-coupled-2015-2020", field, coupled=True)
    observed, bflow, cflow = _observations(EVALUATION_START, EVALUATION_END), _series(baseline, "streamflow_m3s"), _series(coupled, "streamflow_m3s")
    daily = ValidationEngine.compare_dated(observed, bflow, cflow, temporal_resolution="daily", observed_evidence_type="OBSERVED", baseline_evidence_type="REAL_SWAT_PLUS", coupled_evidence_type="REAL_SWAT_PLUS_COUPLED")
    monthly = ValidationEngine.compare_dated(_monthly(observed), _monthly(bflow), _monthly(cflow), temporal_resolution="monthly", observed_evidence_type="OBSERVED", baseline_evidence_type="REAL_SWAT_PLUS", coupled_evidence_type="REAL_SWAT_PLUS_COUPLED")
    reference_totals = _totals(baseline)
    definitions: dict[str, dict[str, Any]] = {"TEMPERATURE_PLUS_2C": {"weather": {"temp_offset_c": 2.0}}, "PRECIPITATION_MINUS_15PCT": {"weather": {"precip_factor": 0.85}}, "NO_TILL": {"scenario": "NO_TILL"}, "MAIZE_TO_SORGHUM": {"scenario": "MAIZE_TO_SORGHUM"}}
    scenarios: dict[str, Any] = {}
    for name, options in definitions.items():
        run = _run(f"south-fork-final-{name.lower()}", field, scenario=options.get("scenario", "HISTORICAL_REFERENCE"), weather=options.get("weather"))
        values = _totals(run)
        scenarios[name] = {"status": "COMPLETED", "run_id": run.run_id, "values": values, "delta_from_historical_baseline": _delta(reference_totals, values), "provenance": run.provenance}
    monthly_dates = monthly["alignment"]["matched_dates"]
    b_month, c_month, o_month = _monthly(bflow), _monthly(cflow), _monthly(observed)
    b_errors, c_errors = [abs(b_month[day] - o_month[day]) for day in monthly_dates], [abs(c_month[day] - o_month[day]) for day in monthly_dates]
    dataset_path, schema_path = _write_dataset(baseline, coupled, observed, fspm_daily)
    output_identical = baseline.provenance["output_checksums"] == coupled.provenance["output_checksums"]
    report = {"report_version": "south-fork-final-v1", "created_at": datetime.now(timezone.utc).isoformat(), "scope": {"watershed": "South Fork Iowa River", "usgs_gauge": "05451210", "huc8": "07080207", "statement": "Multi-watershed validation remains future work; this implementation performs a reproducible pilot validation on one real agricultural watershed."}, "experiment": {"simulation_period": [START.isoformat(), END.isoformat()], "warm_up": [START.isoformat(), "2017-12-31"], "evaluation": [EVALUATION_START.isoformat(), EVALUATION_END.isoformat()], "calibration": {"status": "LIMITED_CALIBRATION", "procedure": "No hydrological parameters were changed. The existing uncalibrated builder parameterization was retained identically for baseline and coupled runs.", "objective_function": "NOT_OPTIMIZED", "seed": None, "parameters": []}}, "problem": {"plant_field_hru_watershed_connection": "VERIFIED_INPUT_CHAIN_AND_REAL_SWAT_OUTPUT"}, "fspm": {"field_aggregate": field, "plant_count": PLANT_COUNT, "seed": FSPM_SEED}, "baseline": {"run_id": baseline.run_id, "totals": reference_totals, "provenance": baseline.provenance}, "coupled": {"run_id": coupled.run_id, "totals": _totals(coupled), "provenance": coupled.provenance}, "coupling_effect": "ZERO_WITH_CURRENT_PARAMETERIZATION" if output_identical else "NONZERO_WITH_CURRENT_PARAMETERIZATION", "validation": {"daily": daily, "monthly_primary": monthly}, "hypothesis": {"h0": "coupling does not improve prediction", "h1": "coupling reduces monthly RMSE by at least 15%", "conclusion": monthly["hypothesis_status"]}, "scenarios": scenarios, "cmip6": {"SSP2-4.5": "NOT_AVAILABLE: no normalized NASA NEX-GDDP-CMIP6 artifact was supplied; no synthetic substitute was used.", "SSP5-8.5": "NOT_AVAILABLE: no normalized NASA NEX-GDDP-CMIP6 artifact was supplied; no synthetic substitute was used."}, "statistics": {"ks_baseline_vs_observed": _ks(list(observed.values()), [bflow[day] for day in observed if day in bflow]), "ks_coupled_vs_observed": _ks(list(observed.values()), [cflow[day] for day in observed if day in cflow]), "wilcoxon_monthly_absolute_errors": _wilcoxon(b_errors, c_errors), "bootstrap_ssp585_yield_ic95": {"status": "INSUFFICIENT_EVIDENCE", "reason": "No SSP5-8.5 yield series exists."}, "sobol": {"status": "IMPLEMENTED_BUT_NOT_FULLY_EXECUTED", "parameters": ["transpiration_capacity_scale", "root_depth_mean_m", "mean_LAI"], "reason": "A Sobol run would require repeated real SWAT+ executions; it was not used to fabricate sensitivity results."}}, "nass_yield_validation": {"status": "LIMITED", "reason": "No documented Hardin County-to-watershed/HRU yield crosswalk is included; county yield is not a direct watershed measurement."}, "dataset": {"path": dataset_path, "schema": schema_path, "sha256": _sha256(Path(dataset_path))}, "limitations": ["Single-watershed pilot only.", "Static 2019 CDL snapshot.", "Simplified FSPM and basin-mean forcing summary.", "Limited hydrological calibration.", "FSPM ET, uptake and yield are NOT_COUPLED.", "NASS county/watershed spatial mismatch.", "CMIP6 artifacts unavailable in this execution."]}
    target = ROOT / "research_domain/final_report.json"; target.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(target), "dataset": dataset_path, "h1": monthly["hypothesis_status"], "coupling_effect": report["coupling_effect"]}, indent=2))


if __name__ == "__main__": main()

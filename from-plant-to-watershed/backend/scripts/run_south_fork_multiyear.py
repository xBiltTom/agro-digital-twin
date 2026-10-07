#!/usr/bin/env python3
"""Bounded calibration and annual A/B publications on existing pglocal.

TEST outcomes are never queried. Candidate records and metrics are persisted;
the normal execution path publishes dated playback for the final daily arms.
"""
from __future__ import annotations

import argparse
import asyncio
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timezone
import csv
import gc
import hashlib
import json
import math
from pathlib import Path
import shutil
from statistics import fmean
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.simulation import SimulationRun, ClimateScenario, PlaybackFrame
from app.models.observation import Dataset, StreamflowObservation
from app.models.watershed import Watershed
from app.models.user import User
from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig
from app.services.swat_meteorology_diagnostic import grid, nearest, sha256, station_inputs
from app.services.swat_baseline_diagnostic import read_table
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from app.services.twin_coupling_engine import TwinCouplingEngine
from scientific_core import ValidationEngine

OWNER = "d89d1912-2ee3-4228-b4bb-8448104851d4"
WATERSHED = "eaf625b7-f1ae-499d-8563-149a85de5167"
SCENARIO = "026d6545-dae8-4dba-991b-d57c7eb45dd4"
SOURCE = BACKEND / "data/baseline-diagnostic-physical-v1/corrected-project"
EXECUTABLE = BACKEND / "data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research"
PROTOCOL = ROOT / "research_domain/south_fork_multiyear_protocol_v1.json"
ARCHIVE = BACKEND / "data/baseline-diagnostic-meteorology-v1/calendar-edges"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def copy_inputs(source, destination):
    if destination.exists():
        raise ValueError(f"Preserve existing input project: {destination}")
    destination.mkdir(parents=True)
    hashes = {}
    for path in sorted(source.iterdir()):
        if path.is_file() and path.suffix.lower() not in {".txt", ".out", ".fin", ".json"}:
            shutil.copy2(path, destination / path.name)
            hashes[path.name] = sha256(path)
    for line in (source / "file.cio").read_text().splitlines()[1:]:
        for token in line.split()[1:]:
            if (source / token).is_file() and not (destination / token).is_file():
                raise ValueError(f"Copy omitted a declared input: {token}")
    return hashes


def prepare_inputs(root):
    destination = root / "forcing-project"
    manifest_path = root / "forcing-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if any(sha256(destination / name) != value for name, value in manifest["after_sha256"].items()):
            raise ValueError("Prepared forcing inputs changed")
        return destination
    before = copy_inputs(SOURCE, destination)
    stations, _, _ = station_inputs(SOURCE)
    manifest = json.loads((ARCHIVE / "manifest.json").read_text())
    changes, receipts = [], {}
    for year in (2020, 2024):
        day = date(year, 12, 31)
        data = {}
        for kind in ("pr", "tmmx", "tmmn", "srad", "rmin", "rmax", "vs"):
            filename = f"calendar-{kind}-{year}.nc"
            receipt = next(row for row in manifest["artifacts"] if row["file"] == filename)
            if sha256(ARCHIVE / filename) != receipt["sha256"]:
                raise ValueError("Calendar archive changed")
            data[kind] = grid(ARCHIVE / filename)
            if data[kind]["dates"] != [day]:
                raise ValueError("Calendar edge has unexpected dates")
            receipts[filename] = receipt
        for station in stations:
            v = {kind: float(nearest(dataset, station)[0][0]) for kind, dataset in data.items()}
            values = {"pcp": [round(v["pr"], 2)], "tmp": [round(v["tmmx"] - 273.15, 2), round(v["tmmn"] - 273.15, 2)],
                      "slr": [round(v["srad"] * .0864, 2)], "hmd": [round((v["rmin"] + v["rmax"]) / 200, 3)], "wnd": [round(v["vs"], 2)]}
            for extension, replacement in values.items():
                path = destination / f"{station['name']}.{extension}"
                lines = path.read_text().splitlines(keepends=True)
                found = False
                for index, line in enumerate(lines[3:], 3):
                    tokens = line.split()
                    if tokens[:2] != [str(year), "366"]:
                        continue
                    found = True
                    old = list(map(float, tokens[2:]))
                    if old != replacement:
                        lines[index] = f"{year}  366 " + " ".join(f"{value:10.5f}" for value in replacement) + "  \n"
                        changes.append({"file": path.name, "date": day.isoformat(), "before": old, "after": replacement})
                    break
                if not found:
                    raise ValueError("Leap-year edge absent from forcing")
                path.write_text("".join(lines))
    station_inputs(destination)
    after = {name: sha256(destination / name) for name in before}
    if any(sha256(SOURCE / name) != value for name, value in before.items()):
        raise ValueError("Source inputs changed during preparation")
    write_json(manifest_path, {"schema_version": "south-fork-multiyear-forcing/v1", "source": str(SOURCE),
        "inherited_correction_manifest_sha256": sha256(SOURCE.parent / "corrected-project-manifest.json"),
        "source_unchanged": True, "before_sha256": before, "after_sha256": after, "changes": changes,
        "calendar_receipts": receipts, "archive_manifest_sha256": sha256(ARCHIVE / "manifest.json"),
        "scope": "All audited leap-year ends corrected through 2024; 2024 forcing repair does not examine TEST streamflow."})
    return destination


def parameter_project(source, destination, values):
    before = copy_inputs(source, destination)
    changed = {}
    for filename, field, value in (("hydrology.hyd", "esco", values["esco"]),
                                    ("aquifer.aqu", "flo_min", values["shallow_flo_min_m"]),
                                    ("tiledrain.str", "t_fc", values["tile_t_fc_h"])):
        header, rows = read_table(destination / filename)
        for row in rows:
            if filename == "aquifer.aqu" and "deep" in row["name"]:
                continue
            row[field] = f"{value:.5f}"
        lines = (destination / filename).read_text().splitlines()[:2]
        (destination / filename).write_text("\n".join(lines + [" ".join(row[key] for key in header) for row in rows]) + "\n")
        changed[filename] = {"before": before[filename], "after": sha256(destination / filename), "field": field, "value": value}
    write_json(destination.parent / "parameter-manifest.json", {"settings": values, "changed_inputs": changed,
        "unchanged_input_sha256": {name: value for name, value in before.items() if name not in changed}})


async def observations(db, protocol, start, end):
    if end >= date.fromisoformat(protocol["partitions"]["TEST"][0]):
        raise ValueError("TEST observation access is reserved for delivery 4")
    rows = (await db.execute(select(StreamflowObservation).where(
        StreamflowObservation.dataset_id == protocol["observations"]["dataset_id"],
        StreamflowObservation.station_id == protocol["station_id"],
        StreamflowObservation.observed_on.between(start, end)))).scalars().all()
    accepted = set(protocol["observations"]["accepted_qualifiers"])
    result = {}
    for row in rows:
        quality = (row.quality_status or "").replace(";", ",")
        if quality in accepted and row.value_m3s is not None and math.isfinite(row.value_m3s) and row.value_m3s >= 0:
            day = row.observed_on.isoformat()
            if day in result:
                raise ValueError("Duplicate observed day")
            result[day] = {"q": row.value_m3s, "quality": quality}
    return result


def monthly_observations(observed, minimum):
    groups = defaultdict(list)
    for day, row in observed.items():
        groups[day[:7]].append(row["q"])
    return {month: fmean(values) for month, values in groups.items()
            if len(values) / monthrange(*map(int, month.split("-")))[1] >= minimum}


def new_run(run_id, protocol, protocol_sha, project, root, start, end, run_type, *, role, frozen=None):
    config = {"project_path": str(project.resolve()), "executable_path": str(EXECUTABLE.resolve()),
              "working_directory": str((root / "workspaces").resolve()), "warmup_period": start.year - 2000,
              "output_frequency": "MONTHLY" if role == "CALIBRATION_CANDIDATE" else "DAILY",
              "outlet_unit": protocol["outlet_gis_id"], "run_type": run_type}
    if frozen:
        config["frozen_parameter_summary"] = frozen
    return SimulationRun(id=run_id, user_id=OWNER, watershed_id=WATERSHED, scenario_id=SCENARIO,
        name=f"South Fork · {role} · {start.year}–{end.year}", status="PENDING",
        duration_days=(end - start).days + 1, seed=42, plant_count=1000, mode="SWAT_PLUS",
        hydrology_backend="SWAT_PLUS", climate_source="SWAT_PROJECT", management_scenario="BASELINE",
        station_id=protocol["station_id"], start_date=start, end_date=end,
        dataset_ids=[protocol["observations"]["dataset_id"]],
        dataset_roles={protocol["observations"]["dataset_id"]: "OBSERVATION"},
        requested_config={"swat_plus": config, "research_experiment": {"protocol_sha256": protocol_sha,
            "experiment_id": protocol["experiment_id"], "role": role,
            "recipe_sha256": sha256(Path(__file__)), "test_observations_accessed": False}})


async def candidate(db, protocol, protocol_sha, source, root, index, values, observed):
    run_id = f"sf-multi-v1-cal-{index:02d}"
    previous = await db.get(SimulationRun, run_id)
    if previous:
        if previous.status != "COMPLETED" or previous.requested_config["research_experiment"]["protocol_sha256"] != protocol_sha or previous.parameters != values:
            raise ValueError(f"Preserve incompatible or unfinished candidate: {run_id}")
        return {"run_id": run_id, "settings": values, "metrics": previous.validation["calibration_metrics"]}
    project = root / run_id / "project"
    parameter_project(source, project, values)
    start, end = map(date.fromisoformat, protocol["partitions"]["CALIBRATION"])
    sim = new_run(run_id, protocol, protocol_sha, project, root, start, end, "SWAT_STANDARD_BASELINE", role="CALIBRATION_CANDIDATE")
    sim.parameters = values
    sim.status, sim.started_at = "RUNNING", datetime.now(timezone.utc)
    db.add(sim)
    await db.commit()
    print(f"CALIBRATION {run_id} {values}", flush=True)
    try:
        config = SwatPlusRunConfig(project, EXECUTABLE, root / "workspaces", start, end, 5,
                                  "MONTHLY", "USGS-05451210", run_id, outlet_unit="153")
        result = SwatPlusAdapter().run(config)
        predicted = {row["period"][:7]: row["streamflow_m3s"] for row in result.records}
        target = monthly_observations(observed, protocol["observations"]["minimum_monthly_paired_fraction"])
        if len(predicted) != 96 or any(not math.isfinite(v) or v < 0 for v in predicted.values()):
            raise ValueError("Incomplete or invalid calibration hydrograph")
        # All calibration months have complete approved daily observations;
        # require that before comparing native full-month mean Q.
        if len(observed) != (end - start).days + 1 or set(target) != set(predicted):
            raise ValueError("Native monthly calibration requires complete observed months")
        months = sorted(target)
        metrics = ValidationEngine.evaluate([target[m] for m in months], [predicted[m] for m in months])
        sim.effective_config = {"run_type": config.run_type, "output_frequency": "MONTHLY", "simulation_start": str(start),
                                "simulation_end": str(end), "warmup_period": 5, "outlet_unit": "153"}
        sim.provenance = {**result.provenance, "research_experiment": sim.requested_config["research_experiment"],
                          "parameter_manifest": json.loads((project.parent / "parameter-manifest.json").read_text())}
        sim.monthly_outputs = result.records
        sim.summary_metrics = {"period_count": len(result.records), "water_balance": result.water_balance}
        sim.validation = {"classification": "CALIBRATION_ONLY", "calibration_metrics": metrics,
            "evaluation": protocol["partitions"]["CALIBRATION"], "test_accessed": False, "hypothesis_status": "NOT_EVALUATED"}
        sim.status, sim.finished_at = "COMPLETED", datetime.now(timezone.utc)
        await db.commit()
        write_json(root / run_id / "result.json", {"run_id": run_id, "settings": values, "metrics": metrics, "provenance": sim.provenance})
        print(f"RESULT {run_id} RMSE={metrics['rmse']['value']:.6f} NSE={metrics['nse']['value']:.6f}", flush=True)
        del result
        gc.collect()
        return {"run_id": run_id, "settings": values, "metrics": metrics}
    except Exception as exc:
        sim.status = "FAILED"
        sim.error = {"code": "MULTIYEAR_CALIBRATION_FAILED", "message": str(exc)}
        sim.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise


async def calibrate(db, protocol, protocol_sha, source, root):
    destination = root / "calibration.json"
    if destination.exists():
        return json.loads(destination.read_text())
    start, end = map(date.fromisoformat, protocol["partitions"]["CALIBRATION"])
    observed = await observations(db, protocol, start, end)
    rows = []
    for esco in protocol["calibration"]["first_stage"]["esco"]:
        for depth in protocol["calibration"]["first_stage"]["shallow_flo_min_m"]:
            rows.append(await candidate(db, protocol, protocol_sha, source, root, len(rows) + 1,
                {"esco": esco, "shallow_flo_min_m": depth, "tile_t_fc_h": 24.}, observed))
    winner = min(rows, key=lambda row: (row["metrics"]["rmse"]["value"], row["run_id"]))
    for timing in protocol["calibration"]["second_stage"]["tile_t_fc_h"]:
        rows.append(await candidate(db, protocol, protocol_sha, source, root, len(rows) + 1,
            {**winner["settings"], "tile_t_fc_h": timing}, observed))
    winner = min(rows, key=lambda row: (row["metrics"]["rmse"]["value"], row["run_id"]))
    acceptance = protocol["calibration"]["acceptance"]
    accepted = winner["metrics"]["nse"]["value"] >= acceptance["monthly_nse_minimum"] and abs(winner["metrics"]["pbias"]["value"]) <= acceptance["monthly_absolute_pbias_maximum_percent"]
    selected = root / "selected-project"
    parameter_project(source, selected, winner["settings"])
    result = {"protocol_sha256": protocol_sha, "budget_used": len(rows), "budget_limit": 12,
              "candidates": rows, "winner": winner, "acceptance_passed": accepted,
              "reference_status": "CALIBRATED_DEVELOPMENT_REFERENCE" if accepted else "BUDGET_EXHAUSTED_EXPLORATORY_REFERENCE",
              "selected_project": str(selected), "test_accessed": False, "hypothesis_status": "NOT_EVALUATED"}
    write_json(destination, result)
    return result


async def publish_one(db, protocol, protocol_sha, project, root, year, arm, frozen=None):
    run_id = f"sf-multi-v1-{arm.lower()}-{year}"
    previous = await db.get(SimulationRun, run_id)
    if previous:
        if previous.status != "COMPLETED" or previous.requested_config["research_experiment"]["protocol_sha256"] != protocol_sha:
            raise ValueError(f"Preserve unfinished/incompatible publication: {run_id}")
        return previous
    start, end = date(year, 1, 1), date(year, 12, 31)
    if start >= date.fromisoformat(protocol["partitions"]["TEST"][0]):
        raise ValueError("TEST publication is reserved for delivery 4")
    sim = new_run(run_id, protocol, protocol_sha, project, root, start, end,
        "SWAT_MULTISCALE_COUPLED" if arm in {"B", "B-PARAMETERS"} else "SWAT_STANDARD_BASELINE", role=arm, frozen=frozen)
    db.add(sim)
    await db.commit()
    print(f"PUBLISH {run_id}", flush=True)
    sim = await TwinCouplingEngine.execute_simulation_run(db, run_id)
    count = await db.scalar(select(func.count()).select_from(PlaybackFrame).where(PlaybackFrame.simulation_id == run_id))
    if count != (end - start).days + 1 or len(sim.monthly_outputs) != count:
        raise ValueError("Final arm publication has incomplete daily coverage")
    write_json(root / "publications" / f"{run_id}.json", {"run_id": run_id, "frames": count, "provenance": sim.provenance,
        "effective_config": sim.effective_config, "summary": sim.summary_metrics, "validation": sim.validation})
    print(f"PUBLISHED {run_id} frames={count}", flush=True)
    return sim


def field_value(frame, key):
    item = (frame.get("field") or {}).get(key)
    return item.get("value") if item and item.get("availability") == "AVAILABLE" else None


async def export_pair(db, protocol, project, root, year, a, b):
    observed = await observations(db, protocol, date(year, 1, 1), date(year, 12, 31))
    daily = {arm: {row["period"]: row for row in sim.monthly_outputs} for arm, sim in (("A", a), ("B", b))}
    if daily["A"].keys() != daily["B"].keys():
        raise ValueError("A/B daily coverage differs")
    checksums = [sim.provenance["input_checksums_after_mutator"] for sim in (a, b)]
    if sorted(name for name in checksums[0].keys() | checksums[1].keys() if checksums[0].get(name) != checksums[1].get(name)) != ["plants.plt"]:
        raise ValueError("A/B differ beyond the plant parameter record")
    forcing, weather_provenance = SwatClimateForcingReader(project).for_hrus(date(year, 1, 1), date(year, 12, 31), require_fspm=False)
    weather = {row["date"]: row for row in forcing}
    frames = (await db.execute(select(PlaybackFrame.payload).where(PlaybackFrame.simulation_id == b.id, PlaybackFrame.resolution == "DAILY").order_by(PlaybackFrame.date))).scalars().all()
    framed = {frame["date"]: frame for frame in frames}
    partition = "TRAIN" if year <= 2017 else "VALIDATION"
    months = sorted({day[:7] for day in daily["A"]})
    exports = []
    for month in months:
        days = sorted(day for day in daily["A"] if day.startswith(month))
        paired = [day for day in days if day in observed]
        complete = len(paired) / len(days) >= protocol["observations"]["minimum_monthly_paired_fraction"]
        obs_q = fmean(observed[day]["q"] for day in paired) if complete else None
        for arm, sim in (("A", a), ("B", b)):
            physical = fmean(daily[arm][day]["streamflow_m3s"] for day in paired) if complete else None
            row = {"station_id": protocol["station_id"], "month": month, "arm": arm, "partition": partition,
                "simulation_id": sim.id, "expected_days": len(days), "paired_days": len(paired), "coverage_fraction": len(paired) / len(days),
                "estimated_days": sum("e" in observed[day]["quality"].split(",") for day in paired),
                "observed_streamflow_m3s": obs_q, "physical_streamflow_m3s": physical,
                "residual_streamflow_m3s": obs_q - physical if complete else None,
                "precipitation_mm": sum(weather[day]["precip_mm"] for day in days),
                "temperature_c": fmean(weather[day]["temp_c"] for day in days),
                "solar_radiation_mj_m2": sum(weather[day]["solar_rad_mj"] for day in days),
                "relative_humidity_percent": fmean(weather[day]["rh_percent"] for day in days),
                "wind_speed_ms": fmean(weather[day]["wind_speed_ms"] for day in days)}
            for output, source, operation in (("et_mm", "evapotranspiration_mm", sum), ("pet_mm", "potential_evapotranspiration_mm", sum),
                    ("percolation_mm", "percolation_mm", sum), ("tile_drainage_mm", "tile_drainage_mm", sum),
                    ("runoff_mm", "runoff_mm", sum), ("soil_water_profile_mm", "soil_water_average_mm", fmean)):
                values = [daily[arm][day].get(source) for day in days]
                row[output] = operation(values) if all(value is not None for value in values) else None
            active_days = [day for day in days if (framed[day].get("crop") or {}).get("active") is True]
            row["fspm_active_days"] = len(active_days) if arm == "B" else None
            for output, source, flux in (("fspm_lai", "lai", False), ("fspm_root_depth_m", "root_depth_m", False),
                    ("fspm_biomass_g_plant", "biomass_g_plant", False), ("fspm_transpiration_mm", "actual_transpiration_mm_day", True),
                    ("fspm_water_stress", "water_stress", False)):
                values = []
                for day in days:
                    active = day in active_days
                    value = field_value(framed[day], source) if active and arm == "B" else (0. if arm == "B" and output != "fspm_water_stress" else None)
                    values.append(value)
                available = [value for value in values if value is not None]
                row[f"{output}_available_days"] = len(available)
                if output == "fspm_water_stress":
                    row[output] = fmean(available) if available else None
                else:
                    row[output] = (sum(available) if flux else fmean(available)) if len(available) == len(days) else None
            exports.append(row)
    write_json(root / "exports" / f"paired-{year}-lineage.json", {"A": a.id, "B": b.id,
        "core_inputs_differ_only_plants_plt": True, "common_forcing": weather_provenance,
        "frozen_B_contract_sha256": hashlib.sha256(json.dumps(b.requested_config["swat_plus"]["frozen_parameter_summary"], sort_keys=True).encode()).hexdigest()})
    write_csv(root / "exports" / f"paired-{year}.csv", exports)
    return exports


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


async def run(args):
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use the existing local PostgreSQL digitaltwin database")
    protocol = json.loads(PROTOCOL.read_text())
    protocol_sha = sha256(PROTOCOL)
    if sha256(EXECUTABLE) != protocol["executable_sha256"]:
        raise ValueError("Research engine changed")
    root = args.output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    frozen_protocol = root / "protocol.json"
    if frozen_protocol.exists() and sha256(frozen_protocol) != protocol_sha:
        raise ValueError("Frozen protocol changed; use a new experiment version")
    if not frozen_protocol.exists():
        shutil.copy2(PROTOCOL, frozen_protocol)
    shutil.copy2(Path(__file__), root / f"recipe-{sha256(Path(__file__))}.py")
    source = prepare_inputs(root)
    async with AsyncSessionLocal() as db:
        for model, identifier in ((User, OWNER), (Watershed, WATERSHED), (ClimateScenario, SCENARIO), (Dataset, protocol["observations"]["dataset_id"])):
            if await db.get(model, identifier) is None:
                raise ValueError("Existing owner, basin, neutral scenario and observations required")
        calibration = await calibrate(db, protocol, protocol_sha, source, root)
        project = Path(calibration["selected_project"])
        if args.phase == "calibrate":
            return
        contract_path = root / "frozen-plant-contract.json"
        if not contract_path.exists():
            derivation = await publish_one(db, protocol, protocol_sha, project, root, 2010, "B-PARAMETERS")
            write_json(contract_path, {"source_simulation_id": derivation.id, "derivation_year": 2010,
                "summary": derivation.provenance["coupling_parameter_summary"], "protocol_sha256": protocol_sha})
        contract = json.loads(contract_path.read_text())
        all_rows, publications = [], []
        for year in range(2013, 2021):
            a = await publish_one(db, protocol, protocol_sha, project, root, year, "A")
            b = await publish_one(db, protocol, protocol_sha, project, root, year, "B", contract["summary"])
            all_rows.extend(await export_pair(db, protocol, project, root, year, a, b))
            publications.append({"year": year, "A": a.id, "B": b.id})
            db.expunge_all()
            del a, b
            gc.collect()
        write_csv(root / "exports/monthly-ab.csv", all_rows)
        import pandas as pd
        pd.DataFrame(all_rows).to_parquet(root / "exports/monthly-ab.parquet", index=False)
        metrics = {}
        for partition in ("TRAIN", "VALIDATION"):
            for arm in ("A", "B"):
                rows = [row for row in all_rows if row["partition"] == partition and row["arm"] == arm and row["physical_streamflow_m3s"] is not None]
                metrics[f"{partition}_{arm}"] = ValidationEngine.evaluate([row["observed_streamflow_m3s"] for row in rows], [row["physical_streamflow_m3s"] for row in rows])
        report = {"schema_version": "south-fork-multiyear-delivery/v1", "protocol_sha256": protocol_sha,
            "recipe_sha256": sha256(Path(__file__)), "calibration": calibration, "frozen_plant_contract": contract,
            "publications": publications, "monthly_row_count": len(all_rows), "paired_months": len(all_rows) // 2,
            "development_metrics": metrics, "test_observations_accessed": False, "hypothesis_status": "NOT_EVALUATED",
            "artifacts_sha256": {path.name: sha256(path) for path in sorted((root / "exports").iterdir()) if path.is_file()},
            "forcing_manifest_sha256": sha256(root / "forcing-manifest.json")}
        write_json(root / "exports/schema.json", {"schema_version": "south-fork-monthly-ab/v1", "protocol": protocol,
            "data_sha256": sha256(root / "exports/monthly-ab.parquet"), "columns": list(all_rows[0]),
            "units": {"observed_streamflow_m3s": "m3/s", "physical_streamflow_m3s": "m3/s", "residual_streamflow_m3s": "m3/s",
                "precipitation_mm": "mm/month", "et_mm": "mm/month", "percolation_mm": "mm/month", "soil_water_profile_mm": "mm",
                "fspm_lai": "m2/m2", "fspm_root_depth_m": "m", "fspm_biomass_g_plant": "g/plant", "fspm_transpiration_mm": "mm/month", "fspm_water_stress": "fraction"}})
        report["artifacts_sha256"] = {path.name: sha256(path) for path in sorted((root / "exports").iterdir()) if path.is_file()}
        write_json(ROOT / "research_domain/south_fork_multiyear_delivery_2_v1.json", report)
        print(json.dumps({"paired_months": report["paired_months"], "metrics": metrics, "test_accessed": False}), flush=True)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("calibrate", "all"), default="all")
    parser.add_argument("--output-root", type=Path, default=BACKEND / "data/baseline-diagnostic-multiyear-v1")
    args = parser.parse_args()
    try:
        await run(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

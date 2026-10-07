#!/usr/bin/env python3
"""Publish reserved A/B years and evaluate frozen monthly C/D in existing pglocal."""
from __future__ import annotations

import asyncio
from calendar import monthrange
from collections import Counter
from datetime import date, datetime, timezone
import gc
import json
import math
from pathlib import Path
import shutil
from statistics import fmean
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
REPO = ROOT.parent
sys.path.insert(0, str(BACKEND))

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.external_model import ExternalModel
from app.models.observation import Dataset, DatasetArtifact, StreamflowObservation
from app.models.simulation import PlaybackFrame, SimulationRun
from app.services.external_model_bundle import ExternalModelBundleAdapter
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from app.services.swat_water_path import diagnose_water_path
from scientific_core.monthly_hypothesis import SERIES, evaluate_monthly
from run_south_fork_multiyear import EXECUTABLE, PROTOCOL, TwinCouplingEngine, field_value, new_run, sha256, write_json

DEVELOPMENT = BACKEND / "data/baseline-diagnostic-multiyear-v1"
PROJECT = DEVELOPMENT / "selected-project"
RUNTIME = BACKEND / "data/south-fork-test-v1"
OUTPUT = ROOT / "research_domain/test_v1"
ML = REPO / "agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1"
CONTRACT = ROOT / "research_domain/south_fork_test_evaluation_contract_v1.json"
REPORT = ROOT / "research_domain/south_fork_test_delivery_4_v1.json"
DATASET_ID = "sf-test-v1-monthly"


def features(row, arm, ml_protocol):
    """Apply the frozen recipe to any dated monthly row, without fitting."""
    month = int(row["month"][-2:])
    result = {name: row[name] for name in ml_protocol["common_features"] if name not in {
        ml_protocol["baseline_feature"], "month_sin", "month_cos"}}
    result.update({ml_protocol["baseline_feature"]: row["physical_streamflow_m3s"],
        "month_sin": float(np.sin(2 * np.pi * (month - 1) / 12)),
        "month_cos": float(np.cos(2 * np.pi * (month - 1) / 12))})
    if arm == "D":
        stress = row["fspm_water_stress"]
        available = row["fspm_water_stress_available_days"]
        if (stress is not None and not pd.isna(stress)) != (available > 0):
            raise ValueError("Stress availability changed")
        result.update({name: row[name] for name in ml_protocol["fspm_features"] if name not in {
            "fspm_water_stress", "fspm_active_fraction", "fspm_stress_available_fraction"}})
        result.update(fspm_water_stress=0.0 if stress is None or pd.isna(stress) else stress,
            fspm_active_fraction=row["fspm_active_days"] / row["expected_days"],
            fspm_stress_available_fraction=available / row["expected_days"])
        if not 0 <= result["fspm_stress_available_fraction"] <= result["fspm_active_fraction"] <= 1:
            raise ValueError("Invalid FSPM support")
    if any(value is None or not math.isfinite(float(value)) for value in result.values()):
        raise ValueError("Unknown model input; never replace structural features with defaults")
    return result


def verify_freeze(protocol):
    ml_protocol = json.loads((ML / "protocol.json").read_text())
    contract = json.loads(CONTRACT.read_text())
    if sha256(PROTOCOL) != contract["parent_protocol_sha256"] or sha256(ML / "protocol.json") != contract["ml_protocol_sha256"]:
        raise ValueError("Parent/ML protocol changed")
    if sha256(EXECUTABLE) != protocol["executable_sha256"]:
        raise ValueError("Research executable changed")
    manifest = json.loads((ML / "artifact-manifest.json").read_text())
    for name, checksum in manifest["sha256"].items():
        if sha256(ML / name) != checksum:
            raise ValueError(f"Frozen development artifact changed: {name}")
    receipt = json.loads((ML / "freeze-receipt.json").read_text())
    for name, checksum in receipt["implementation_sha256"].items():
        if sha256(REPO / name) != checksum:
            raise ValueError(f"Frozen ML implementation changed: {name}")
    parameters = json.loads((DEVELOPMENT / "parameter-manifest.json").read_text())
    inputs = {**parameters["unchanged_input_sha256"], **{name: item["after"] for name,item in parameters["changed_inputs"].items()}}
    if any(sha256(PROJECT / name) != checksum for name, checksum in inputs.items()):
        raise ValueError("Selected physical inputs changed")
    plants = json.loads((DEVELOPMENT / "frozen-plant-contract.json").read_text())
    delivery2 = json.loads((ROOT / "research_domain/south_fork_multiyear_delivery_2_v1.json").read_text())
    if plants != delivery2["frozen_plant_contract"]:
        raise ValueError("2010 plant contract changed")
    adapters = {arm: ExternalModelBundleAdapter(ML / arm).load() for arm in ("C", "D")}
    # The TEST feature builder must reproduce the already frozen development results.
    frame = pd.read_csv(ROOT / "research_domain/multiyear_v1/monthly-ab.csv", dtype={"station_id": str})
    predictions = pd.read_csv(ML / "development-predictions.csv")
    replay = {}
    for arm, physical in (("C", "A"), ("D", "B")):
        work = frame[frame.arm == physical].sort_values("month")
        actual = [adapters[arm].predict(features(row, arm, ml_protocol))["value"] for row in work.to_dict("records")]
        expected = predictions[predictions.series == arm].sort_values("month").predicted_streamflow_m3s.to_numpy()
        error = float(np.max(abs(np.array(actual) - expected)))
        if error > 1e-10:
            raise ValueError("TEST feature recipe differs from frozen development inference")
        replay[arm] = {"months": len(work), "max_absolute_error_m3s": error}
    frozen = {"parent_protocol_sha256": sha256(PROTOCOL), "ml_protocol_sha256": sha256(ML / "protocol.json"),
        "evaluation_contract_sha256": sha256(CONTRACT), "executable_sha256": sha256(EXECUTABLE),
        "physical_parameter_manifest_sha256": sha256(DEVELOPMENT / "parameter-manifest.json"),
        "plant_contract_sha256": sha256(DEVELOPMENT / "frozen-plant-contract.json"),
        "ml_artifact_manifest_sha256": sha256(ML / "artifact-manifest.json"),
        "model_checksums": {arm: adapter.checksum() for arm, adapter in adapters.items()},
        "implementation_sha256": {str(p.relative_to(REPO)): sha256(p) for p in (
            Path(__file__), BACKEND / "scientific_core/monthly_hypothesis.py", BACKEND / "scientific_core/validation.py")},
        "development_feature_replay": replay}
    return ml_protocol, plants, adapters, frozen


async def publish(db, protocol, plants, year, arm):
    identifier = f"sf-test-v1-{arm.lower()}-{year}"
    sim = await db.get(SimulationRun, identifier)
    if sim is not None:
        if sim.status != "COMPLETED" or sim.requested_config["research_experiment"]["evaluation_contract_sha256"] != sha256(CONTRACT):
            raise ValueError(f"Preserve unfinished/incompatible TEST run: {identifier}")
        print(f"REUSE {identifier}", flush=True)
    else:
        sim = new_run(identifier, protocol, sha256(PROTOCOL), PROJECT, RUNTIME,
            date(year, 1, 1), date(year, 12, 31), "SWAT_MULTISCALE_COUPLED" if arm == "B" else "SWAT_STANDARD_BASELINE",
            role=f"TEST_{arm}", frozen=plants["summary"] if arm == "B" else None)
        # Defer observational scoring to the dedicated common-support evaluator.
        sim.dataset_roles = {protocol["observations"]["dataset_id"]: "CONTEXT_ONLY"}
        sim.requested_config = {**sim.requested_config, "research_experiment": {
            **sim.requested_config["research_experiment"], "experiment_id": "sf-test-v1",
            "evaluation_contract_sha256": sha256(CONTRACT), "recipe_sha256": sha256(Path(__file__)),
            "observation_policy": "Dedicated paired monthly evaluation after publication"}}
        db.add(sim)
        await db.commit()
        print(f"RUN {identifier}; replay from 2000, frozen inputs", flush=True)
        sim = await TwinCouplingEngine.execute_simulation_run(db, identifier)
    count = await db.scalar(select(func.count()).select_from(PlaybackFrame).where(PlaybackFrame.simulation_id == identifier))
    if count != sim.duration_days or len(sim.monthly_outputs) != sim.duration_days or sim.effective_config["warmup_period"] != year - 2000:
        raise ValueError("Incomplete daily TEST run or changed warm-up")
    if sim.provenance["executable_sha256"] != protocol["executable_sha256"]:
        raise ValueError("Published executable changed")
    if arm == "B" and sim.provenance["coupling_parameter_summary"] != plants["summary"]:
        raise ValueError("TEST derived new plant parameters")
    audit_path = RUNTIME / "audits" / f"{identifier}-water.json"
    if not audit_path.exists():
        write_json(audit_path, diagnose_water_path(Path(sim.provenance["workspace"]), outlet_gis_id=protocol["outlet_gis_id"], start=sim.start_date, end=sim.end_date))
    audit = json.loads(audit_path.read_text())
    if audit.get("status") != "DIAGNOSTIC_AVAILABLE" or any(sha256(Path(sim.provenance["workspace"]) / name) != checksum for name, checksum in audit["output_checksums"].items()):
        raise ValueError("TEST native output audit changed")
    print(f"PUBLISHED {identifier}: {count} frames", flush=True)
    return sim, {"simulation_id": identifier, "frames": count, "water_audit_sha256": sha256(audit_path),
        "network": audit["network"]["status"], "network_residual_m3": audit["network"]["residual_m3"],
        "catchment": audit["catchment_accounting"]["status"], "catchment_residual_mm": audit["catchment_accounting"]["residual_mm"]}


async def read_observations(db, protocol):
    path = OUTPUT / "observed-daily.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"date": str, "quality": str}).to_dict("records")
    write_json(RUNTIME / "test-access-receipt.json", {"first_access_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_contract_sha256": sha256(CONTRACT), "scope": protocol["partitions"]["TEST"], "purpose": "Frozen delivery 4 evaluation, no tuning"})
    start, end = map(date.fromisoformat, protocol["partitions"]["TEST"])
    rows = (await db.execute(select(StreamflowObservation).where(
        StreamflowObservation.dataset_id == protocol["observations"]["dataset_id"], StreamflowObservation.station_id == protocol["station_id"],
        StreamflowObservation.observed_on.between(start, end)).order_by(StreamflowObservation.observed_on))).scalars().all()
    records = [{"date": row.observed_on.isoformat(), "q_m3s": row.value_m3s,
        "quality": (row.quality_status or "").replace(";", ",")} for row in rows]
    if len({row["date"] for row in records}) != len(records):
        raise ValueError("Duplicate TEST observation dates")
    pd.DataFrame(records).to_csv(path, index=False)
    return records


async def export_pair(db, protocol, observations, year, a, b):
    daily = {arm: {row["period"]: row for row in sim.monthly_outputs} for arm,sim in (("A",a),("B",b))}
    expected = pd.date_range(f"{year}-01-01", f"{year}-12-31").strftime("%Y-%m-%d").tolist()
    if sorted(daily["A"]) != expected or sorted(daily["B"]) != expected:
        raise ValueError("A/B daily dates differ")
    if any(not math.isfinite(row["streamflow_m3s"]) or row["streamflow_m3s"] < 0 for arm in daily.values() for row in arm.values()):
        raise ValueError("Invalid physical Q")
    checksums = [sim.provenance["input_checksums_after_mutator"] for sim in (a,b)]
    if sorted(name for name in checksums[0].keys() | checksums[1].keys() if checksums[0].get(name) != checksums[1].get(name)) != ["plants.plt"]:
        raise ValueError("A/B inputs differ beyond frozen plants.plt")
    forcing, weather_provenance = SwatClimateForcingReader(PROJECT).for_hrus(date(year,1,1),date(year,12,31),require_fspm=False)
    weather = {row["date"]: row for row in forcing}
    payloads = (await db.execute(select(PlaybackFrame.payload).where(PlaybackFrame.simulation_id == b.id,
        PlaybackFrame.resolution == "DAILY").order_by(PlaybackFrame.date))).scalars().all()
    framed = {frame["date"]: frame for frame in payloads}
    if sorted(framed) != expected or sorted(weather) != expected:
        raise ValueError("Incomplete dated FSPM/weather support")
    rows, lineage = [], {"year": year, "A": a.id, "B": b.id, "core_inputs_differ_only_plants_plt": True,
        "common_forcing": weather_provenance, "monthly_support": []}
    for number in range(1,13):
        month = f"{year}-{number:02d}"
        days = [day for day in expected if day.startswith(month)]
        for variant in ("PRIMARY", "EXCLUDE_ESTIMATED"):
            paired = [day for day in days if day in observations and (variant == "PRIMARY" or observations[day]["quality"] == "A")]
            eligible = len(paired) / len(days) >= protocol["observations"]["minimum_monthly_paired_fraction"]
            observed = fmean(observations[day]["q_m3s"] for day in paired) if eligible else None
            lineage["monthly_support"].append({"month":month,"variant":variant,"eligible":eligible,"paired_dates":paired,
                "excluded_dates":[day for day in days if day not in paired]})
            for arm,sim in (("A",a),("B",b)):
                physical = fmean(daily[arm][day]["streamflow_m3s"] for day in paired) if eligible else None
                row = {"station_id":protocol["station_id"],"month":month,"arm":arm,"partition":"TEST","variant":variant,
                    "simulation_id":sim.id,"expected_days":len(days),"paired_days":len(paired),"eligible":eligible,
                    "coverage_fraction":len(paired)/len(days),"estimated_days":sum(observations[day]["quality"] == "A,e" for day in paired),
                    "observed_streamflow_m3s":observed,"physical_streamflow_m3s":physical,
                    "residual_streamflow_m3s":observed-physical if eligible else None,
                    "precipitation_mm":sum(weather[day]["precip_mm"] for day in days),
                    "temperature_c":fmean(weather[day]["temp_c"] for day in days),
                    "solar_radiation_mj_m2":sum(weather[day]["solar_rad_mj"] for day in days),
                    "relative_humidity_percent":fmean(weather[day]["rh_percent"] for day in days),
                    "wind_speed_ms":fmean(weather[day]["wind_speed_ms"] for day in days)}
                for output,source,operation in (("et_mm","evapotranspiration_mm",sum),("pet_mm","potential_evapotranspiration_mm",sum),
                    ("percolation_mm","percolation_mm",sum),("tile_drainage_mm","tile_drainage_mm",sum),("runoff_mm","runoff_mm",sum),
                    ("soil_water_profile_mm","soil_water_average_mm",fmean)):
                    values = [daily[arm][day].get(source) for day in days]
                    row[output] = operation(values) if all(value is not None for value in values) else None
                active = {day for day in days if (framed[day].get("crop") or {}).get("active") is True}
                row["fspm_active_days"] = len(active) if arm == "B" else None
                for output,source,flux in (("fspm_lai","lai",False),("fspm_root_depth_m","root_depth_m",False),
                    ("fspm_biomass_g_plant","biomass_g_plant",False),("fspm_transpiration_mm","actual_transpiration_mm_day",True),
                    ("fspm_water_stress","water_stress",False)):
                    values = [field_value(framed[day],source) if day in active and arm == "B" else
                        (0.0 if arm == "B" and output != "fspm_water_stress" else None) for day in days]
                    available = [value for value in values if value is not None]
                    row[f"{output}_available_days"] = len(available)
                    row[output] = (fmean(available) if available else None) if output == "fspm_water_stress" else (
                        (sum(available) if flux else fmean(available)) if len(available) == len(days) else None)
                rows.append(row)
    return rows,lineage


def predict(rows, adapters, ml_protocol):
    references = json.loads((ML / "selection.json").read_text())["simple_references"]
    result = []
    for row in rows:
        physical = row["physical_streamflow_m3s"]
        arm = "C" if row["arm"] == "A" else "D"
        correction = adapters[arm].predict(features(row,arm,ml_protocol)) if row["eligible"] else None
        values = {row["arm"]: physical, arm: correction["value"] if correction else None,
            f"AFFINE_{row['arm']}": max(0,references["affine"][row["arm"]]["slope"] * physical + references["affine"][row["arm"]]["intercept"]) if physical is not None else None}
        if row["arm"] == "A":
            values["CLIMATOLOGY"] = references["climatology"][row["month"][-2:]] if row["eligible"] else None
        for series,value in values.items():
            result.append({"station_id":row["station_id"],"month":row["month"],"partition":"TEST","variant":row["variant"],
                "series":series,"eligible":row["eligible"],"paired_days":row["paired_days"],"estimated_days":row["estimated_days"],
                "observed_streamflow_m3s":row["observed_streamflow_m3s"],"predicted_streamflow_m3s":value,
                "predicted_residual_m3s":correction["predicted_residual"] if correction and series == arm else None})
    return sorted(result,key=lambda row:(row["variant"],row["month"],row["series"]))


async def register(db, report):
    provenance = {"protocol_sha256":report["parent_protocol_sha256"],"evaluation_contract_sha256":sha256(CONTRACT),
        "hypothesis_status":report["primary"]["hypothesis_status"],"reference_status":report["reference_status"],
        "test_accessed":True,"fit_on_test":False}
    dataset = await db.get(Dataset,DATASET_ID)
    if dataset is None:
        db.add(Dataset(id=DATASET_ID,provider="LOCAL_RESEARCH",dataset_name="South Fork reserved monthly TEST A/B/C/D v1",version="1",
            variable="monthly_outlet_Q_test_evaluation",unit="m3/s",temporal_resolution="MONTHLY",spatial_support="USGS 05451210 / South Fork",
            coverage_start=date(2021,1,1),coverage_end=date(2025,12,31),source_reference=str(OUTPUT),evidence_type="DERIVED",
            quality_control={"minimum_paired_fraction":0.9,"variants":["PRIMARY","EXCLUDE_ESTIMATED"]},metadata_json=provenance))
        await db.flush()
    for index,path in enumerate(sorted(p for p in OUTPUT.iterdir() if p.is_file())):
        identifier = f"sf-test-v1-artifact-{index:02d}"
        existing = await db.get(DatasetArtifact,identifier)
        if existing and (existing.storage_path != str(path) or existing.checksum_sha256 != sha256(path)):
            raise ValueError("Persisted TEST artifact changed")
        if existing is None:
            db.add(DatasetArtifact(id=identifier,dataset_id=DATASET_ID,artifact_kind="NORMALIZED" if path.suffix in {".csv",".parquet"} else "DERIVED",
                storage_path=str(path),checksum_sha256=sha256(path),byte_size=path.stat().st_size,
                content_type={".csv":"text/csv",".json":"application/json",".parquet":"application/vnd.apache.parquet"}.get(path.suffix,"application/octet-stream"),metadata_json=provenance))
    for pair in report["publications"]:
        for physical,ml_arm in (("A","C"),("B","D")):
            sim = await db.get(SimulationRun,pair[physical])
            sim.validation = {**(sim.validation or {}),"research_test_evaluation": {**provenance,"scope":"Full 2021–2025 paired monthly TEST; not a per-year hypothesis",
                "report":str(REPORT),"report_sha256":sha256(REPORT),"primary_contrast":report["primary"]["contrasts"]["D_vs_A"]}}
            sim.dataset_roles = {**(sim.dataset_roles or {}), report["observation_dataset_id"]:"OBSERVATION"}
            sim.dataset_ids = list(dict.fromkeys([*(sim.dataset_ids or []),DATASET_ID]))
            sim.dataset_roles = {**sim.dataset_roles,DATASET_ID:"VALIDATION"}
            series = [row for row in report["monthly_ml_predictions"] if row["series"] == ml_arm and row["month"].startswith(str(pair["year"]))]
            sim.ml_result = {"status":"PREDICTED_FROZEN_MONTHLY_TEST","model_id":f"sf-ml-v1-{ml_arm.lower()}",
                "target":"monthly_streamflow_m3s","temporal_support":"MONTHLY_RETROSPECTIVE","predictions":series,
                "physical_daily_outputs_preserved":True,"model_checksum":report["model_checksums"][ml_arm]}
    await db.commit()


async def run():
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None,"localhost","127.0.0.1","::1"}:
        raise ValueError("Use existing pglocal digitaltwin")
    protocol = json.loads(PROTOCOL.read_text())
    ml_protocol,plants,adapters,frozen = verify_freeze(protocol)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    receipt_path = OUTPUT / "freeze-receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if any(receipt[key] != value for key,value in frozen.items()):
            raise ValueError("TEST freeze changed; preserve results and investigate")
    else:
        receipt = {**frozen,"frozen_at_utc":datetime.now(timezone.utc).isoformat(),"stage":"BEFORE_TEST_RUNS_OR_OUTCOME_QUERIES"}
        write_json(receipt_path,receipt)
        shutil.copy2(CONTRACT,OUTPUT / "evaluation-contract.json")
    async with AsyncSessionLocal() as db:
        for arm in ("C","D"):
            model = await db.get(ExternalModel,f"sf-ml-v1-{arm.lower()}")
            if model is None or model.checksum != frozen["model_checksums"][arm]:
                raise ValueError("Frozen C/D must already be registered in pglocal")
        manifest_path = OUTPUT / "artifact-manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            if any(sha256(OUTPUT / name) != checksum for name,checksum in manifest["sha256"].items()) or sha256(REPORT) != manifest["report_sha256"]:
                raise ValueError("Completed TEST artifacts changed")
            report = json.loads(REPORT.read_text())
            await register(db,report)
            print("REUSE frozen TEST results; no new runs, observations or evaluation",flush=True)
            return
        publications,audits = [],[]
        for year in range(2021,2026):
            for arm in ("A","B"):
                sim,audit = await publish(db,protocol,plants,year,arm)
                audits.append(audit)
                db.expunge_all()
                del sim
                gc.collect()
            publications.append({"year":year,"A":f"sf-test-v1-a-{year}","B":f"sf-test-v1-b-{year}"})
        raw = await read_observations(db,protocol)
        accepted = set(protocol["observations"]["accepted_qualifiers"])
        observations = {row["date"]:row for row in raw if row["quality"] in accepted and row["q_m3s"] is not None and math.isfinite(row["q_m3s"]) and row["q_m3s"] >= 0}
        monthly,lineages = [],[]
        for pair in publications:
            a,b = [await db.get(SimulationRun,pair[arm]) for arm in ("A","B")]
            rows,lineage = await export_pair(db,protocol,observations,pair["year"],a,b)
            monthly.extend(rows)
            lineages.append(lineage)
            db.expunge_all()
            del a,b
            gc.collect()
        pd.DataFrame(monthly).to_csv(OUTPUT / "monthly-ab.csv",index=False)
        pd.DataFrame(monthly).to_parquet(OUTPUT / "monthly-ab.parquet",index=False)
        write_json(OUTPUT / "lineage.json",{"publications":publications,"annual_support":lineages,"native_audits":audits})
        predictions = predict(monthly,adapters,ml_protocol)
        pd.DataFrame(predictions).to_csv(OUTPUT / "monthly-predictions.csv",index=False)
        evaluation = {}
        for variant in ("PRIMARY","EXCLUDE_ESTIMATED"):
            evaluation[variant],replicates = evaluate_monthly([row for row in predictions if row["variant"] == variant],protocol["evaluation"]["uncertainty"])
            pd.DataFrame(replicates).to_csv(OUTPUT / f"bootstrap-{variant.lower()}.csv",index=False)
        report = {"schema_version":"south-fork-test-delivery-4/v1",**frozen,"experiment_id":"sf-test-v1","dataset_id":DATASET_ID,
            "observation_dataset_id":protocol["observations"]["dataset_id"],"test_interval":protocol["partitions"]["TEST"],
            "publications":publications,"native_audits":audits,"freeze_receipt":receipt,
            "test_access_receipt":json.loads((RUNTIME / "test-access-receipt.json").read_text()),
            "observation_qc":{"rows":len(raw),"accepted_days":len(observations),"approved_estimated_days":sum(row["quality"] == "A,e" for row in observations.values()),
                "qualifier_counts":dict(Counter(row["quality"] for row in raw)),"missing_or_rejected_days":1826-len(observations)},
            "primary":evaluation["PRIMARY"],"exclude_estimated_sensitivity":evaluation["EXCLUDE_ESTIMATED"],
            "reference_status":protocol["evaluation"] and ml_protocol["reference_status"],"fit_on_test":False,"test_accessed":True,
            "monthly_ml_predictions":[row for row in predictions if row["series"] in {"C","D"} and row["variant"] == "PRIMARY"],
            "metric_convention":"Canonical ValidationEngine; PBIAS simulated minus observed; modified KGE CV ratio",
            "limitations":protocol["limitations"] + ml_protocol["limitations"],
            "interpretation":"Held-out monthly outlet-flow comparison under fixed experimental management and exploratory physical calibration. Does not validate FSPM physiology or water balance; D/C changes baseline and features.",
            "artifact_directory":str(OUTPUT.relative_to(REPO))}
        write_json(REPORT,report)
        write_json(manifest_path,{"report_sha256":sha256(REPORT),"sha256":{p.name:sha256(p) for p in sorted(OUTPUT.iterdir()) if p.is_file() and p != manifest_path}})
        await register(db,report)
        print(json.dumps({"hypothesis_status":report["primary"]["hypothesis_status"],"primary":report["primary"]["contrasts"]["D_vs_A"],
            "rmse":{name:value["rmse"]["value"] for name,value in report["primary"]["metrics"].items()},"estimated_sensitivity":report["exclude_estimated_sensitivity"]["hypothesis_status"]}),flush=True)


async def main():
    try:
        await run()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

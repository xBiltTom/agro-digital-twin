#!/usr/bin/env python3
"""Package completed sf-multi-v1 publications without rerunning SWAT or reading TEST."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import shutil
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.observation import Dataset, DatasetArtifact
from app.models.simulation import SimulationRun, PlaybackFrame
from app.schemas.playback import CropState
from app.services.playback_database import _digest
from app.services.swat_meteorology_diagnostic import sha256
from app.services.swat_water_path import diagnose_water_path
from run_south_fork_multiyear import write_json, ROOT, PROTOCOL

RUNTIME = BACKEND / "data/baseline-diagnostic-multiyear-v1"
BUNDLE = ROOT / "research_domain/multiyear_v1"
REPORT = ROOT / "research_domain/south_fork_multiyear_delivery_2_v1.json"
DATASET_ID = "sf-multi-v1-monthly-ab"


async def annotate_inactive(db, sim):
    """Restore known inactive annual seasons; preserve every numerical variable."""
    receipt = RUNTIME / "audits" / f"{sim.id}-inactive-crop.json"
    if receipt.exists():
        return json.loads(receipt.read_text())
    groups = sim.provenance["fspm_calendar_provenance"]["calendar"]["groups"]
    by_hru = {str(hru): group for group in groups for hru in group["hru_ids"]}
    frames = (await db.execute(select(PlaybackFrame).where(
        PlaybackFrame.simulation_id == sim.id).order_by(PlaybackFrame.date))).scalars().all()
    if len(frames) != sim.duration_days:
        raise ValueError("Daily playback coverage changed since publication")
    changes = []
    for frame in frames:
        payload = deepcopy(frame.payload)
        changed = []
        for hru in payload["hru_results"]:
            group = by_hru.get(hru["hru_id"])
            if group is None or hru.get("crop") is not None:
                continue
            day = frame.date.isoformat()
            if group["planting_date"] <= day <= group["harvest_date"]:
                raise ValueError("An active HRU lacks its crop annotation")
            hru["calendar_id"] = group["calendar_id"]
            hru["crop"] = CropState(active=False, season_id=group["calendar_id"],
                window_status="NO_ACTIVE_EXECUTED_CROP_CALENDAR",
                source="SWAT+ mgt_out.txt PLANT and HARV/KILL").model_dump(mode="json")
            changed.append(hru["hru_id"])
        if changed:
            # Compare complete payloads after removing exactly the changed annotations.
            restored = deepcopy(payload)
            for hru in restored["hru_results"]:
                if hru["hru_id"] in changed:
                    hru["crop"], hru["calendar_id"] = None, None
            if restored != frame.payload or _digest(frame.payload) != frame.sha256:
                raise ValueError("Annotation repair altered other playback content")
            after = _digest(payload)
            changes.append({"date": frame.date.isoformat(), "resolution": frame.resolution,
                "hru_ids": changed, "before_sha256": frame.sha256, "after_sha256": after})
            frame.payload, frame.sha256 = payload, after
    audit = {"simulation_id": sim.id, "changed_frames": len(changes), "changes": changes,
        "scope": "Only crop/calendar_id on previously null inactive maize HRUs; numerical payloads unchanged.",
        "calendar_source": "Persisted native executed calendar", "script_sha256": sha256(Path(__file__))}
    sim.provenance = {**sim.provenance, "inactive_crop_annotation": audit}
    await db.commit()
    write_json(receipt, audit)
    db.expunge_all()
    return audit


async def package():
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use existing pglocal digitaltwin")
    report = json.loads(REPORT.read_text())
    protocol = json.loads(PROTOCOL.read_text())
    if report["protocol_sha256"] != sha256(PROTOCOL):
        raise ValueError("Frozen protocol changed")
    manifest = json.loads((RUNTIME / "parameter-manifest.json").read_text())
    selected = RUNTIME / "selected-project"
    expected_inputs = {**manifest["unchanged_input_sha256"],
        **{name: item["after"] for name, item in manifest["changed_inputs"].items()}}
    if any(sha256(selected / name) != digest for name, digest in expected_inputs.items()):
        raise ValueError("Selected input project changed after calibration")
    data = pd.read_csv(RUNTIME / "exports/monthly-ab.csv", dtype={"station_id": str})
    if len(data) != 192 or data.duplicated(["station_id", "month", "arm"]).any():
        raise ValueError("Expected 96 unique paired months")
    if set(data.partition) != {"TRAIN", "VALIDATION"} or data.month.max() != "2020-12":
        raise ValueError("Unexpected publication interval")
    if data.physical_streamflow_m3s.isna().any() or (data.physical_streamflow_m3s < 0).any():
        raise ValueError("Invalid physical monthly Q")
    for _, pair in data.groupby("month"):
        if set(pair.arm) != {"A", "B"} or pair.paired_days.nunique() != 1 or pair.observed_streamflow_m3s.nunique() != 1:
            raise ValueError("A/B support differs")
    units = {"observed_streamflow_m3s": "m3/s", "physical_streamflow_m3s": "m3/s",
        "residual_streamflow_m3s": "m3/s", "temperature_c": "degC",
        "solar_radiation_mj_m2": "MJ/m2/month", "relative_humidity_percent": "percent",
        "wind_speed_ms": "m/s", "soil_water_profile_mm": "mm",
        "fspm_lai": "m2_leaf/m2_ground", "fspm_root_depth_m": "m",
        "fspm_biomass_g_plant": "g/plant", "fspm_water_stress": "fraction [0,1]"}
    units.update({name: "mm/month" for name in ("precipitation_mm", "et_mm", "pet_mm",
        "percolation_mm", "tile_drainage_mm", "runoff_mm", "fspm_transpiration_mm")})
    units.update({name: "days" for name in data.columns if name.endswith("_days")})
    units["coverage_fraction"] = "fraction [0,1]"
    schema = {"schema_version": "south-fork-monthly-ab/v1", "protocol_sha256": sha256(PROTOCOL),
        "key": ["station_id", "month", "arm"], "columns": list(data.columns), "units": units,
        "aggregation": {"Q": "Mean on identical approved paired daily dates",
            "fluxes": "Sum over all calendar days", "states_and_climate": "Mean over calendar days except stress",
            "stress": "Mean over available active days; null without active crop"},
        "evidence": {"observed_Q": "USGS approved A/A,e; estimated values retained and counted",
            "physical_Q_and_water": "MODELLED_SWAT_PLUS", "weather": "Derived gridMET inputs weighted by all basin HRU areas",
            "FSPM": "SIMPLIFIED_FSPM/DERIVED; selected maize HRU area weights, no fractional CDL weights available"},
        "FSPM_support": "LAI includes inactive maize area; root depth/biomass/transpiration are active-group means, set to zero when all groups inactive",
        "missing": "A has null FSPM values and zero available_days; unknown is null; inactive living crop is zero except stress",
        "use": "Retrospective monthly residual learning; full-month inputs are not advance forecasts",
        "not_predictors": ["observed_streamflow_m3s", "residual_streamflow_m3s", "simulation_id", "arm", "partition", "station_id",
            "paired_days", "coverage_fraction", "estimated_days"],
        "checksums_sha256": {name: sha256(RUNTIME / "exports" / name) for name in ("monthly-ab.csv", "monthly-ab.parquet")}}
    write_json(RUNTIME / "exports/schema.json", schema)
    audits, repairs = [], []
    async with AsyncSessionLocal() as db:
        for pair in report["publications"]:
            sims = [await db.get(SimulationRun, pair[arm]) for arm in ("A", "B")]
            if any(sim is None or sim.status != "COMPLETED" for sim in sims):
                raise ValueError("All final arms must be completed")
            contract = report["frozen_plant_contract"]["summary"]
            if sims[1].requested_config["swat_plus"]["frozen_parameter_summary"] != contract or sims[1].provenance["coupling_parameter_summary"] != contract:
                raise ValueError("B plant parameters differ from the frozen 2010 contract")
            workspaces = [Path(sim.provenance["workspace"]) for sim in sims]
            weather_names = sorted(path.name for path in workspaces[0].iterdir() if path.suffix in {".pcp", ".tmp", ".slr", ".hmd", ".wnd"} or path.name == "weather-sta.cli")
            if not weather_names or any(sha256(workspaces[0] / name) != sha256(workspaces[1] / name) for name in weather_names):
                raise ValueError("A/B weather inputs differ")
            for sim, workspace in zip(sims, workspaces):
                if sim.provenance["executable_sha256"] != protocol["executable_sha256"]:
                    raise ValueError("Published arm uses a different research engine")
                if sim.effective_config["warmup_period"] != pair["year"] - 2000:
                    raise ValueError("Annual publication does not replay from 2000")
                path = RUNTIME / "audits" / f"{sim.id}-water.json"
                if not path.exists():
                    trace = diagnose_water_path(workspace, outlet_gis_id="153", start=sim.start_date, end=sim.end_date)
                    write_json(path, trace)
                trace = json.loads(path.read_text())
                if trace.get("status") != "DIAGNOSTIC_AVAILABLE" or any(sha256(workspace / name) != digest for name, digest in trace["output_checksums"].items()):
                    raise ValueError("Native trace unavailable or outputs changed")
                sim.validation = {**(sim.validation or {}), "research_reference": {
                    "status": report["calibration"]["reference_status"],
                    "calibration_acceptance_passed": report["calibration"]["acceptance_passed"],
                    "protocol_sha256": sha256(PROTOCOL), "hypothesis_status": "NOT_EVALUATED",
                    "test_accessed": False}}
                audits.append({"simulation_id": sim.id, "network": trace["network"]["status"],
                    "network_residual_m3": trace["network"]["residual_m3"],
                    "catchment": trace["catchment_accounting"]["status"],
                    "catchment_residual_mm": trace["catchment_accounting"]["residual_mm"],
                    "weather_files": len(weather_names), "daily_records": len(sim.monthly_outputs), "trace_sha256": sha256(path)})
            repairs.append(await annotate_inactive(db, sims[1]))
            print(f"PACKAGED {pair['year']}", flush=True)
        derived = await db.get(SimulationRun, "sf-multi-v1-b-parameters-2010")
        repairs.append(await annotate_inactive(db, derived))
        BUNDLE.mkdir(parents=True, exist_ok=True)
        for name in ("monthly-ab.csv", "monthly-ab.parquet", "schema.json"):
            shutil.copy2(RUNTIME / "exports" / name, BUNDLE / name)
        write_json(BUNDLE / "lineage.json", {"protocol_sha256": sha256(PROTOCOL), "publications": report["publications"],
            "audits": audits, "inactive_annotation_receipts": [{k:v for k,v in r.items() if k != "changes"} for r in repairs],
            "test_accessed": False, "source_outputs_preserved": True})
        dataset = await db.get(Dataset, DATASET_ID)
        metadata = {"protocol_sha256": sha256(PROTOCOL), "rows": 192, "paired_months": 96,
            "reference_status": report["calibration"]["reference_status"], "test_accessed": False}
        if dataset is None:
            dataset = Dataset(id=DATASET_ID, provider="LOCAL_RESEARCH", dataset_name="South Fork paired monthly A/B v1",
                version="1", variable="monthly_outlet_Q_and_model_features", unit="mixed; see schema",
                temporal_resolution="MONTHLY", spatial_support="USGS 05451210 / South Fork model basin / maize HRUs",
                coverage_start=date(2013,1,1), coverage_end=date(2020,12,31), source_reference=str(BUNDLE),
                evidence_type="DERIVED", quality_control=schema["aggregation"], metadata_json=metadata)
            db.add(dataset)
            await db.flush()
        for name, mime in (("monthly-ab.csv", "text/csv"), ("monthly-ab.parquet", "application/vnd.apache.parquet"),
                           ("schema.json", "application/json"), ("lineage.json", "application/json")):
            path = BUNDLE / name
            identifier = f"sf-multi-v1-{name.replace('.', '-')}"
            artifact = await db.get(DatasetArtifact, identifier)
            if artifact is None:
                artifact = DatasetArtifact(id=identifier, dataset_id=DATASET_ID,
                    artifact_kind="NORMALIZED" if name.startswith("monthly-ab.") else "DERIVED",
                    storage_path=str(path), checksum_sha256=sha256(path), content_type=mime,
                    byte_size=path.stat().st_size, metadata_json=metadata)
                db.add(artifact)
            else:
                artifact.checksum_sha256, artifact.byte_size = sha256(path), path.stat().st_size
        await db.commit()
    report.update({"dataset_id": DATASET_ID, "native_audits": audits,
        "package_script_sha256": sha256(Path(__file__)), "bundle": str(BUNDLE.relative_to(ROOT)),
        "implementation_sha256_at_packaging": {name: sha256(BACKEND / "app/services" / name) for name in (
            "swat_executed_calendar.py", "executed_calendar_fspm.py", "swat_coupled_runner.py",
            "twin_coupling_engine.py", "playback_builder.py")},
        "bundle_sha256": {p.name: sha256(p) for p in sorted(BUNDLE.iterdir()) if p.is_file()},
        "artifacts_sha256": {p.name: sha256(p) for p in sorted((RUNTIME / 'exports').iterdir()) if p.is_file()}})
    write_json(REPORT, report)


async def main():
    try:
        await package()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

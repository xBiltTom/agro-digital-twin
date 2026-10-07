"""Frozen South Fork reproduction profile; physical daily and ML monthly remain separate."""
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean
from uuid import uuid4
import numpy as np
import pandas as pd
from sqlalchemy import select
from app.models.simulation import SimulationRun, PlaybackFrame
from app.models.external_model import ExternalModel
from app.models.observation import StreamflowObservation
from app.services.external_model_bundle import ExternalModelBundleAdapter
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from app.services.twin_coupling_engine import TwinCouplingEngine

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
DOMAIN = ROOT / "research_domain"
PROJECT = BACKEND / "data/baseline-diagnostic-multiyear-v1/selected-project"
RUNTIME = BACKEND / "data/south-fork-user-v1"
EXECUTABLE = BACKEND / "data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research"
ML = ROOT.parent / "agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1"
REPORT = DOMAIN / "south_fork_test_delivery_4_v1.json"


class ProfileNotPending(ValueError):
    """Do not change an existing run owned by another worker."""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_report():
    report = json.loads(REPORT.read_text())
    manifest = json.loads((DOMAIN / "test_v1/artifact-manifest.json").read_text())
    if sha256(REPORT) != manifest["report_sha256"]:
        raise ValueError("Frozen TEST report checksum changed")
    return report


def profile_inputs():
    report = frozen_report()
    if not PROJECT.is_dir() or not EXECUTABLE.is_file():
        raise ValueError("El proyecto SWAT+ y el ejecutable congelados no están instalados.")
    if sha256(EXECUTABLE) != report["executable_sha256"]:
        raise ValueError("Frozen executable changed")
    contract = BACKEND / "data/baseline-diagnostic-multiyear-v1/frozen-plant-contract.json"
    parameters = BACKEND / "data/baseline-diagnostic-multiyear-v1/parameter-manifest.json"
    if sha256(contract) != report["plant_contract_sha256"] or sha256(parameters) != report["physical_parameter_manifest_sha256"]:
        raise ValueError("Frozen physical parameters changed")
    manifest = json.loads(parameters.read_text())
    expected_inputs = {**manifest["unchanged_input_sha256"], **{
        name: value["after"] for name, value in manifest["changed_inputs"].items()}}
    if any(sha256(PROJECT / name) != checksum for name, checksum in expected_inputs.items()):
        raise ValueError("Frozen SWAT+ project inputs changed")
    return json.loads(contract.read_text())["summary"]


async def create_profile(db, user_id, year, arm, monthly_ml):
    if year not in range(2021,2026) or arm not in {"A", "B"}:
        raise ValueError("Unsupported reproduction year or physical arm")
    summary = profile_inputs()
    active = await db.scalar(select(SimulationRun.id).where(SimulationRun.user_id == user_id,
        SimulationRun.status.in_(["PENDING","RUNNING"]), SimulationRun.name.like("South Fork · reproducción%")))
    if active:
        raise ValueError("Ya tienes una reproducción en ejecución; consulta su estado antes de iniciar otra.")
    start, end = date(year,1,1), date(year,12,31)
    identifier = str(uuid4())
    config = {"project_path":str(PROJECT),"executable_path":str(EXECUTABLE),"working_directory":str(RUNTIME / "workspaces"),
        "warmup_period":year-2000,"output_frequency":"DAILY","outlet_unit":json.loads((DOMAIN / "south_fork_multiyear_protocol_v1.json").read_text())["outlet_gis_id"],
        "run_type":"SWAT_MULTISCALE_COUPLED" if arm == "B" else "SWAT_STANDARD_BASELINE"}
    if arm == "B":
        config["frozen_parameter_summary"] = summary
    report = frozen_report()
    sim = SimulationRun(id=identifier,user_id=user_id,watershed_id="eaf625b7-f1ae-499d-8563-149a85de5167",
        scenario_id="026d6545-dae8-4dba-991b-d57c7eb45dd4",name=f"South Fork · reproducción {arm} · {year}",
        status="PENDING",duration_days=(end-start).days+1,seed=42,plant_count=1000,mode="SWAT_PLUS",hydrology_backend="SWAT_PLUS",
        climate_source="SWAT_PROJECT",management_scenario="BASELINE",station_id="05451210",start_date=start,end_date=end,
        dataset_ids=[report["observation_dataset_id"]],dataset_roles={report["observation_dataset_id"]:"CONTEXT_ONLY"},
        requested_config={"swat_plus":config,"research_profile":{"version":"south-fork-user/v1","arm":arm,"monthly_ml":monthly_ml,
        "report_sha256":sha256(REPORT),"purpose":"USER_REPRODUCTION_NOT_NEW_HYPOTHESIS_TEST"}})
    db.add(sim)
    await db.commit()
    return sim


def field_value(frame, key):
    item = (frame.get("field") or {}).get(key)
    return item.get("value") if item and item.get("availability") == "AVAILABLE" else None


async def monthly_rows(db, sim):
    protocol = json.loads((DOMAIN / "south_fork_multiyear_protocol_v1.json").read_text())
    year = sim.start_date.year
    arm = sim.requested_config["research_profile"]["arm"]
    outputs = {row["period"]:row for row in sim.monthly_outputs}
    expected = pd.date_range(sim.start_date,sim.end_date).strftime("%Y-%m-%d").tolist()
    if sorted(outputs) != expected:
        raise ValueError("Incomplete physical daily outputs")
    daily = {arm:outputs}
    forcing, _ = SwatClimateForcingReader(PROJECT).for_hrus(sim.start_date,sim.end_date,require_fspm=False)
    weather = {row["date"]:row for row in forcing}
    payloads = (await db.execute(select(PlaybackFrame.payload).where(PlaybackFrame.simulation_id == sim.id,
        PlaybackFrame.resolution == "DAILY").order_by(PlaybackFrame.date))).scalars().all()
    framed = {frame["date"]:frame for frame in payloads}
    if sorted(framed) != expected or sorted(weather) != expected:
        raise ValueError("Incomplete daily weather/playback support")
    observations_raw = (await db.execute(select(StreamflowObservation).where(
        StreamflowObservation.dataset_id == protocol["observations"]["dataset_id"],StreamflowObservation.station_id == sim.station_id,
        StreamflowObservation.observed_on.between(sim.start_date,sim.end_date)))).scalars().all()
    if len({row.observed_on for row in observations_raw}) != len(observations_raw):
        raise ValueError("Duplicate observations")
    observations = {row.observed_on.isoformat():{"quality":row.quality_status.replace(";",","),"q_m3s":row.value_m3s}
        for row in observations_raw if (row.quality_status or "").replace(";",",") in protocol["observations"]["accepted_qualifiers"]
        and row.value_m3s is not None and math.isfinite(row.value_m3s) and row.value_m3s >= 0}
    rows, lineage = [], {"monthly_support":[]}
    for number in range(1,13):
        month = f"{year}-{number:02d}"
        days = [day for day in expected if day.startswith(month)]
        for variant in ("PRIMARY",):
            paired = [day for day in days if day in observations and (variant == "PRIMARY" or observations[day]["quality"] == "A")]
            eligible = len(paired) / len(days) >= protocol["observations"]["minimum_monthly_paired_fraction"]
            observed = fmean(observations[day]["q_m3s"] for day in paired) if eligible else None
            lineage["monthly_support"].append({"month":month,"variant":variant,"eligible":eligible,"paired_dates":paired,
                "excluded_dates":[day for day in days if day not in paired]})
            for arm,sim in ((arm,sim),):
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
    return rows

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



async def execute_profile(db, identifier):
    sim = await db.scalar(select(SimulationRun).where(SimulationRun.id == identifier).with_for_update())
    if sim is None or not (sim.requested_config or {}).get("research_profile") or sim.status != "PENDING":
        raise ProfileNotPending("Only pending user profiles can be executed")
    profile_inputs()
    sim = await TwinCouplingEngine.execute_simulation_run(db,identifier)
    if sim.status != "COMPLETED":
        raise ValueError("Physical execution did not complete")
    profile = sim.requested_config["research_profile"]
    sim.ml_result = {"status":"NOT_REQUESTED","temporal_support":"MONTHLY_RETROSPECTIVE","physical_daily_outputs_preserved":True}
    if profile["monthly_ml"]:
        try:
            rows = await monthly_rows(db,sim)
            arm = "C" if profile["arm"] == "A" else "D"
            adapter = ExternalModelBundleAdapter(ML / arm)
            expected = frozen_report()["model_checksums"][arm]
            model = await db.get(ExternalModel,f"sf-ml-v1-{arm.lower()}")
            if model is None or model.checksum != expected or adapter.checksum() != expected:
                raise ValueError("Frozen registered model changed")
            ml_protocol = json.loads((DOMAIN / "south_fork_ml_protocol_v1.json").read_text())
            predictions = []
            for row in rows:
                correction = adapter.predict(features(row,arm,ml_protocol)) if row["eligible"] else None
                predictions.append({"month":row["month"],"series":arm,"eligible":row["eligible"],"paired_days":row["paired_days"],
                    "estimated_days":row["estimated_days"],"observed_streamflow_m3s":row["observed_streamflow_m3s"],
                    "physical_streamflow_m3s":row["physical_streamflow_m3s"],"predicted_streamflow_m3s":correction["value"] if correction else None,
                    "predicted_residual_m3s":correction["predicted_residual"] if correction else None})
            sim.ml_result = {"status":"PREDICTED_FROZEN_MONTHLY_REPRODUCTION","model_id":model.id,"model_checksum":expected,
                "temporal_support":"MONTHLY_RETROSPECTIVE","target":"monthly_streamflow_m3s","unit":"m3/s",
                "physical_daily_outputs_preserved":True,"predictions":predictions,"hypothesis_status":"NOT_A_NEW_HYPOTHESIS_TEST"}
        except Exception as error:
            # Keep completed physical outputs available even if monthly postprocessing fails.
            sim.ml_result = {"status":"FAILED","message":str(error),"physical_daily_outputs_preserved":True}
    sim.validation = {**(sim.validation or {}),"research_profile":{"purpose":"USER_REPRODUCTION_NOT_NEW_HYPOTHESIS_TEST",
        "official_hypothesis_status":frozen_report()["primary"]["hypothesis_status"],"report_sha256":sha256(REPORT)}}
    await db.commit()
    return sim

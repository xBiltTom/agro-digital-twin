"""Read-only audit by default; optional explicit v2 historical reference import.

Never executes SWAT+, publishes playback, repairs stored rows, or changes v2 files.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "research_domain/final_report_v2.json"
DATASET = ROOT / "data/final/experiment_dataset.parquet"
SCHEMA = ROOT / "data/final/experiment_dataset.schema.json"
LEGACY_NAME = "SWAT+ Físico Calibrado — Cuenca South Fork Iowa (2018–2020 Multi-Escala)"
NAME = "South Fork v2 — referencia histórica importada (2018–2020)"


def _number(value):
    return round(float(value), 4) if pd.notna(value) else None


def build_historical_payload(report: dict, df: pd.DataFrame, schema: dict) -> dict:
    required = {"date", "coupled_streamflow_m3s", "coupled_runoff_mm", "coupled_et_mm",
                "precipitation_mm", "observed_streamflow_m3s", "soil_water_mm",
                "FSPM_LAI", "FSPM_root_depth", "FSPM_biomass"}
    if missing := required - set(df.columns):
        raise ValueError(f"Missing v2 source columns: {sorted(missing)}")
    units = schema.get("units", {})
    if units.get("soil_water_mm") != "mm" or units.get("FSPM_biomass") != "g/plant":
        raise ValueError("Unexpected v2 source units")
    grouped = df.groupby(df.date.str[:7]).agg({
        "coupled_streamflow_m3s": "mean", "coupled_runoff_mm": "sum",
        "coupled_et_mm": "sum", "precipitation_mm": "sum",
        "observed_streamflow_m3s": "mean", "soil_water_mm": "mean"}).reset_index()
    monthly = [{"period": f"{row['date']}-01",
                "precip_mm": _number(row.precipitation_mm),
                "runoff_mm": _number(row.coupled_runoff_mm),
                "evapotranspiration_mm": _number(row.coupled_et_mm),
                "soil_water_mm": _number(row.soil_water_mm),
                "streamflow_m3s": _number(row.coupled_streamflow_m3s),
                "observed_streamflow_m3s": _number(row.observed_streamflow_m3s),
                "percolation_mm": None} for _, row in grouped.iterrows()]
    primary = report.get("validation", {}).get("monthly_primary", {})
    return {"monthly_outputs": monthly,
            "field_aggregates": {
                "mean_lai": _number(df.FSPM_LAI.mean()),
                "mean_root_depth_m": _number(df.FSPM_root_depth.mean()),
                "mean_biomass_g_plant": _number(df.FSPM_biomass.mean()),
                "mean_water_stress": _number(df.FSPM_water_stress.mean()) if "FSPM_water_stress" in df else None},
            "summary_metrics": {
                "period_count": len(monthly),
                "total_runoff_mm": _number(df.coupled_runoff_mm.sum()),
                "total_evapotranspiration_mm": _number(df.coupled_et_mm.sum()),
                "total_percolation_mm": None, "mean_soil_moisture_percent": None,
                "water_balance": {"status": "NOT_COMPUTED", "closure_error_mm": None,
                    "mean_streamflow_m3s": _number(df.coupled_streamflow_m3s.mean()),
                    "totals_mm": {"runoff_mm": _number(df.coupled_runoff_mm.sum()),
                                  "evapotranspiration_mm": _number(df.coupled_et_mm.sum()),
                                  "percolation_mm": None}},
                "unavailable_reasons": {
                    "total_percolation_mm": "No percolation series in v2 dataset schema",
                    "mean_soil_moisture_percent": "SWAT+ storage mm has no validated volumetric conversion",
                    "water_balance.closure_error_mm": "Complete balance terms unavailable"}},
            "validation": {"status": "HISTORICAL_REPORT_ASSESSMENT",
                           "interpretation": "South Fork v2; hydrological calibration was not performed",
                           "hypothesis_status": primary.get("hypothesis_status"),
                           "temporal_resolution": "monthly", "twin": primary.get("twin", {})}}


def audit_row(row: SimulationRun) -> dict:
    metrics, fields = row.summary_metrics or {}, row.field_aggregates or {}
    balance = metrics.get("water_balance") or {}
    flags = [key for key, present in {
        "invented_percolation": metrics.get("total_percolation_mm") == 142.5,
        "invented_closure": balance.get("status") == "CHECKED" and balance.get("closure_error_mm") == 0,
        "invalid_moisture_conversion": metrics.get("mean_soil_moisture_percent") is not None,
        "biomass_unit_mismatch": "mean_biomass_kg_m2" in fields,
        "false_calibration_label": "Calibrado" in row.name or "CALIBRADO" in str((row.validation or {}).get("interpretation", "")),
    }.items() if present]
    return {"simulation_id": row.id, "has_playback_manifest": bool((row.provenance or {}).get("playback")),
            "suspected_legacy_fields": flags}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main(import_historical: bool = False):
    async with AsyncSessionLocal() as db:
        existing = list((await db.execute(select(SimulationRun).where(SimulationRun.name.in_([LEGACY_NAME, NAME])))).scalars())
        print(json.dumps([audit_row(row) for row in existing], ensure_ascii=False, indent=2))
        if not import_historical:
            return
        if existing:
            raise ValueError("Historical reference already exists; no existing row is overwritten")
        if not all(path.is_file() for path in (REPORT, DATASET, SCHEMA)):
            raise FileNotFoundError("Immutable v2 source files required")
        user = await db.scalar(select(User).where(User.email == "investigador@digitaltwin.org"))
        watershed = await db.scalar(select(Watershed).where(Watershed.code.like("%05451210%")))
        scenario = await db.scalar(select(ClimateScenario).where(ClimateScenario.code == "HISTORICAL"))
        if not all((user, watershed, scenario)):
            raise ValueError("Explicit owner, South Fork watershed and HISTORICAL scenario required")
        payload = build_historical_payload(json.loads(REPORT.read_text()), pd.read_parquet(DATASET), json.loads(SCHEMA.read_text()))
        run = SimulationRun(id=str(uuid4()), user_id=user.id, watershed_id=watershed.id,
            scenario_id=scenario.id, name=NAME, status="COMPLETED", duration_days=1096,
            start_date=date(2018, 1, 1), end_date=date(2020, 12, 31), seed=42,
            mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", climate_source="SWAT_PROJECT",
            station_id="05451210", finished_at=datetime.now(timezone.utc),
            requested_config={"swat_plus": {"run_type": "SWAT_MULTISCALE_COUPLED", "output_frequency": "MONTHLY"}},
            effective_config={"backend": "SWAT_PLUS", "run_type": "SWAT_MULTISCALE_COUPLED", "output_frequency": "MONTHLY"},
            provenance={"source_kind": "HISTORICAL_IMPORT", "schema_version": "south-fork-final-v2",
                        "report_sha256": _hash(REPORT), "dataset_sha256": _hash(DATASET),
                        "schema_sha256": _hash(SCHEMA),
                        "limitation": "No dated FSPM trajectory; no new SWAT+ execution"},
            hru_aggregates={"status": "NOT_AVAILABLE", "reason": "v2 export is outlet-level"}, **payload)
        db.add(run)
        await db.commit()
        print(json.dumps({"created_historical_import_id": run.id}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-historical", action="store_true")
    asyncio.run(main(parser.parse_args().import_historical))

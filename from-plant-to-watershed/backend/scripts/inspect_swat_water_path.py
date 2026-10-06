#!/usr/bin/env python3
"""Read completed local PostgreSQL runs and export reproducible water traces."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.simulation import SimulationRun, PlaybackFrame
from app.models.watershed import Watershed
from app.services.swat_water_path import diagnose_water_path


async def run(args):
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use the existing local PostgreSQL digitaltwin database")
    if args.output.exists():
        raise ValueError("Preserve previous traces; choose a new output path")
    result = {"schema_version": "south-fork-water-path-comparison/v1",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "classification": "DEVELOPMENT_DIAGNOSTIC", "hypothesis_status": "NOT_EVALUATED",
              "database": "existing local PostgreSQL digitaltwin", "runs": {},
              "code_sha256": {str(path.relative_to(BACKEND)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in [BACKEND / f"app/services/{name}.py" for name in
                                ("swat_water_path", "swat_plus_parser", "swat_plus_adapter", "twin_coupling_engine", "playback_builder")]
                              + [Path(__file__).resolve()]}}
    async with AsyncSessionLocal() as db:
        for run_id in args.simulation_id:
            sim = await db.get(SimulationRun, run_id)
            if not sim or sim.status != "COMPLETED" or sim.hydrology_backend != "SWAT_PLUS":
                raise ValueError(f"Completed SWAT+ simulation required: {run_id}")
            watershed = await db.get(Watershed, sim.watershed_id)
            workspace = Path(sim.provenance["workspace"])
            effective = sim.effective_config or {}
            if effective.get("output_frequency") != "DAILY":
                raise ValueError("Water-path accounting requires daily outputs")
            diagnostic = diagnose_water_path(workspace, outlet_gis_id=str(effective["outlet_unit"]),
                start=sim.start_date, end=sim.end_date, reference_area_km2=watershed.area_km2)
            frames = await db.scalar(select(func.count()).select_from(PlaybackFrame).where(PlaybackFrame.simulation_id == run_id))
            baseline = (sim.validation or {}).get("baseline_diagnostic") or {}
            daily = baseline.get("daily_comparison", [])
            persisted_volume = (sim.summary_metrics or {}).get("total_discharge_hm3")
            result["runs"][run_id] = {"status": sim.status, "persisted_frames": frames,
                "observed_dataset_ids": sim.dataset_ids, "station_id": sim.station_id,
                "executable_version": sim.provenance["executable_version"],
                "executable_sha256": sim.provenance["executable_sha256"],
                "source_project_sha256": (sim.requested_config or {}).get("development_diagnostic", {}).get("source_project_sha256"),
                "intervention": (sim.requested_config or {}).get("development_diagnostic", {}).get("intervention"),
                "monthly": baseline.get("monthly"), "coverage": baseline.get("coverage"),
                "observed_volume_m3": sum(row["observed_streamflow_m3s"] for row in daily) * 86400
                    if len(daily) == (sim.end_date - sim.start_date).days + 1 else None,
                "persisted_volume_m3": persisted_volume * 1e6 if persisted_volume is not None else None,
                "water_path": diagnostic}
            print(json.dumps({"run_id": run_id, "frames": frames,
                "network": diagnostic.get("network"),
                "catchment_residual_mm": diagnostic.get("catchment_accounting", {}).get("residual_mm")}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation-id", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        await run(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

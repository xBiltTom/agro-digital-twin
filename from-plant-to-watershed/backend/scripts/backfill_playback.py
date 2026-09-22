"""Publish a new playback sidecar for one completed persisted SWAT+ baseline.

No SWAT+ executable is invoked. Coupled legacy runs cannot regain discarded
daily FSPM trajectories and are deliberately rejected.
"""

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.simulation import SimulationRun
from app.models.watershed import Watershed
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_builder import swat_frames
from app.services.twin_coupling_engine import TwinCouplingEngine, _code_version


async def backfill(run_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
        if run is None:
            raise ValueError("Simulation not found")
        if run.status != "COMPLETED" or (run.provenance or {}).get("evidence_type") != "REAL_SWAT_PLUS":
            raise ValueError("Only a completed persisted SWAT+ baseline can be backfilled")
        if (run.provenance or {}).get("playback"):
            raise ValueError("A versioned playback artifact already exists")
        if not run.monthly_outputs or not run.start_date or not run.end_date:
            raise ValueError("Persisted dated SWAT+ output and requested interval are required")
        watershed = await db.scalar(select(Watershed).where(Watershed.id == run.watershed_id))
        if watershed is None:
            raise ValueError("Watershed not found")
        workspace = (run.provenance or {}).get("workspace")
        climate, climate_provenance = (
            TwinCouplingEngine._baseline_forcing(Path(workspace), run.start_date, run.end_date)
            if workspace and Path(workspace).is_dir()
            else (None, {"status": "NOT_AVAILABLE", "reason": "Original isolated SWAT+ workspace is absent"})
        )
        resolution = (run.provenance or {}).get("output_frequency") or (run.effective_config or {}).get("output_frequency", "DAILY")
        manifest = PlaybackArtifactStore().write(run.id, swat_frames(
            simulation_id=run.id, watershed_id=watershed.id, watershed_code=watershed.code,
            outlet_unit=(run.effective_config or {}).get("outlet_unit"), run_type="SWAT_STANDARD_BASELINE",
            resolution=resolution, records=run.monthly_outputs,
            hru_results=(run.hru_aggregates or {}).get("results", []),
            forcing=climate, forcing_source="SWAT+ direct station basin mean",
            start_date=run.start_date, end_date=run.end_date),
            provenance={"backfill_code_version": _code_version(), "original_run_provenance": {
                "workspace": workspace, "output_checksums": (run.provenance or {}).get("output_checksums"),
                "executable_version": (run.provenance or {}).get("executable_version"),
                "executable_sha256": (run.provenance or {}).get("executable_sha256"),
                "input_checksums_after_mutator": (run.provenance or {}).get("input_checksums_after_mutator")},
                "forcing": climate_provenance, "seed": run.seed, "configuration": run.effective_config},
            limitations=["Backfilled from persisted SWAT+ baseline only; no FSPM trajectory exists",
                         "Missing historical forcing remains null when the isolated workspace is absent"])
        run.provenance = {**run.provenance, "playback": manifest}
        await db.commit()
        return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Completed SWAT+ baseline simulation UUID")
    args = parser.parse_args()
    print(asyncio.run(backfill(args.run_id)))

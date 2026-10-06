#!/usr/bin/env python3
"""Audit existing local PostgreSQL SWAT+ runs and optionally attach the evidence."""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.simulation import PlaybackFrame, SimulationRun
from app.models.watershed import Watershed
from app.services.swat_meteorology_diagnostic import diagnose_meteorology, sha256


async def run(args):
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use the existing local PostgreSQL digitaltwin database")
    if url.query.get("host") not in {"/run/postgresql", "/var/run/postgresql", "localhost", "127.0.0.1", "::1", None} or url.port not in {5432, None} or url.query.get("port") not in {"5432", None}:
        raise ValueError("Only the local PostgreSQL socket is allowed")
    if args.output.exists() or len(set(args.simulation_id)) != len(args.simulation_id):
        raise ValueError("Use unique run IDs and preserve existing audit reports")
    result = {"schema_version": "south-fork-meteorology-comparison/v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "database": "existing local PostgreSQL digitaltwin",
              "audit_id": args.output.stem, "runs": {},
              "code_sha256": {str(path.relative_to(BACKEND)): sha256(path) for path in
                  [Path(__file__).resolve(), BACKEND / "scripts/fetch_south_fork_weather_benchmarks.py",
                   BACKEND / "app/services/swat_meteorology_diagnostic.py",
                   BACKEND / "app/services/swat_plant_parameter_mapper.py", BACKEND / "app/services/twin_coupling_engine.py"]}}
    async with AsyncSessionLocal() as db:
        simulations = []
        diagnostic = None
        for run_id in args.simulation_id:
            sim = await db.get(SimulationRun, run_id, with_for_update=args.persist)
            if not sim or sim.status != "COMPLETED" or sim.hydrology_backend != "SWAT_PLUS":
                raise ValueError(f"Completed SWAT+ simulation required: {run_id}")
            if sim.start_date != date(2019, 1, 1) or sim.end_date != date(2019, 12, 31) or sim.effective_config.get("output_frequency") != "DAILY":
                raise ValueError("This development audit requires full daily 2019 runs")
            workspace = Path(sim.provenance["workspace"])
            if diagnostic is None:
                diagnostic = diagnose_meteorology(workspace, args.builder_archive, args.benchmarks, args.calendar_edges, args.cache_reference)
                diagnostic.update({"audit_id": result["audit_id"], "created_at": result["created_at"], "code_sha256": result["code_sha256"]})
            for name, expected in {**diagnostic["input_checksums"], **diagnostic["output_checksums"]}.items():
                if sha256(workspace / name) != expected:
                    raise ValueError(f"Compared runs have different forcing/land evidence: {run_id}/{name}")
            for actual_key, stored_key in (("input_checksums", "input_checksums_after_mutator"), ("output_checksums", "output_checksums")):
                stored = sim.provenance.get(stored_key) or {}
                if actual_key == "input_checksums":
                    weather_hashes = (((sim.provenance.get("playback") or {}).get("provenance") or {}).get("forcing") or {}).get("file_checksums_sha256") or {}
                    if any(stored[name] != weather_hashes[name] for name in set(stored) & set(weather_hashes)):
                        raise ValueError("Input and playback weather provenance disagree")
                    stored = {**stored, **weather_hashes}
                required = set(diagnostic[actual_key]) - {"swat_engine_manifest.json"}
                if not required <= set(stored) or any(stored[name] != diagnostic[actual_key][name] for name in required):
                    raise ValueError(f"Weather audit inputs/outputs differ from persisted provenance: {run_id}")
            saved_manifest = json.loads((workspace / "swat_engine_manifest.json").read_text())
            if saved_manifest != sim.provenance.get("source_build"):
                raise ValueError("Source engine manifest differs from persisted provenance")
            frames = await db.scalar(select(func.count()).select_from(PlaybackFrame).where(PlaybackFrame.simulation_id == run_id))
            if frames != 365:
                raise ValueError(f"Existing daily playback must contain 365 frames: {run_id}")
            baseline = (sim.validation or {}).get("baseline_diagnostic") or {}
            result["runs"][run_id] = {"status": sim.status, "workspace": str(workspace), "persisted_frames": frames,
                "weather_and_basin_output_checksums_verified": True, "observed_dataset_ids": sim.dataset_ids,
                "original_summary_metrics": sim.summary_metrics, "monthly_streamflow_metrics": baseline.get("monthly"),
                "original_provenance_preserved": True, "playback_preserved": True}
            if args.persist:
                existing = (sim.validation or {}).get("meteorology_diagnostic")
                if existing is not None:
                    if not args.append_audit or existing.get("audit_id") == diagnostic["audit_id"]:
                        raise ValueError(f"Preserve the previously attached meteorology audit: {run_id}")
                    history = dict((sim.validation or {}).get("meteorology_diagnostic_history") or {})
                    previous_id = existing["audit_id"]
                    if diagnostic["audit_id"] in history or (previous_id in history and history[previous_id] != existing):
                        raise ValueError("Meteorology audit history would be overwritten")
                    sim.validation = {**(sim.validation or {}), "meteorology_diagnostic_history": {**history, previous_id: existing}}
                sim.validation = {**(sim.validation or {}), "meteorology_diagnostic": diagnostic}
            simulations.append(sim)
        result["diagnostic"] = diagnostic
        result["attached_to_local_pg"] = False
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Build the reviewable report before the optional database commit.
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        if args.persist:
            await db.commit()
            result["attached_to_local_pg"] = True
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "runs": list(result["runs"]), "attached_to_local_pg": args.persist,
                      "weather_source": diagnostic["weather_source"]["status"], "annual_mm": diagnostic["annual_mm"]}))


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation-id", action="append", required=True)
    parser.add_argument("--builder-archive", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    parser.add_argument("--calendar-edges", type=Path, required=True)
    parser.add_argument("--cache-reference", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true", help="Append the new audit to validation; preserve provenance/results/playback")
    parser.add_argument("--append-audit", action="store_true", help="Archive the previous attached audit by its ID before attaching a new revision")
    try:
        await run(parser.parse_args())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

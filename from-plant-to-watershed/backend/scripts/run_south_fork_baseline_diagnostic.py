#!/usr/bin/env python3
"""Run a 2019 reference and optional drainage probe in the existing PostgreSQL.

Source inputs and existing simulation IDs are preserved. Both new runs use
the production execution/persistence path and are development diagnostics.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.user import User
from app.models.watershed import Watershed
from app.models.observation import Dataset, StreamflowObservation
from app.models.simulation import ClimateScenario, SimulationRun
from app.services.swat_baseline_diagnostic import inspect_project, link_drainage_probe, route_drainage_probe
from app.services.twin_coupling_engine import TwinCouplingEngine
from app.services.swat_channel_geometry import restore_channel_lengths, zero_channel_kinetics
from app.services.swat_runtime_diagnostic import prepare_underflow_diagnostic


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


async def run(args) -> dict:
    args.output_root = args.output_root.resolve()
    args.project = args.project.resolve()
    args.executable = args.executable.resolve()
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin":
        raise ValueError("Use the existing digitaltwin PostgreSQL database")
    if url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("This development diagnostic requires local PostgreSQL")
    if args.output_root.exists():
        raise ValueError("Output root already exists; choose a new experiment ID")
    if args.output_root == args.project or args.project in args.output_root.parents:
        raise ValueError("Diagnostic output must be outside the source project")
    if args.warmup_years < 0 or not args.project.is_dir() or not args.executable.is_file():
        raise ValueError("Existing project/executable and nonnegative warmup are required")
    if bool(args.channel_geometry) != bool(args.routing_graph) or (args.channel_geometry and not args.routing_probe):
        raise ValueError("Channel geometry and routing graph must be supplied together with --routing-probe")
    if args.zero_channel_kinetics and not args.routing_probe:
        raise ValueError("Zero channel kinetics requires an explicit copied routing probe")
    ids = [args.experiment_id + ("-geom-routed" if args.channel_geometry else "-tile-routed" if args.routing_probe else "-reference")]
    if args.drainage_probe and not args.routing_probe:
        ids.append(args.experiment_id + "-tile-probe")
    if any(len(value) > 36 for value in ids):
        raise ValueError("Run IDs must fit the existing 36-character database key")
    async with AsyncSessionLocal() as db:
        owner = await db.get(User, args.owner_id)
        watershed = await db.get(Watershed, args.watershed_id)
        scenario = await db.get(ClimateScenario, args.scenario_id)
        dataset = await db.get(Dataset, args.dataset_id)
        if not owner or not owner.is_active or not watershed or not scenario or not dataset:
            raise ValueError("Existing active owner, watershed, scenario and USGS dataset are required")
        if "05451210" not in watershed.code or scenario.temp_anomaly_c != 0 or scenario.precip_factor != 1:
            raise ValueError("South Fork and a neutral scenario are required")
        if dataset.evidence_type != "OBSERVED" or dataset.variable != "streamflow":
            raise ValueError("Dataset must be observed streamflow")
        observed = await db.scalar(select(StreamflowObservation.id).where(
            StreamflowObservation.dataset_id == args.dataset_id,
            StreamflowObservation.station_id == "05451210",
            StreamflowObservation.observed_on.between(date(2019, 1, 1), date(2019, 12, 31))).limit(1))
        if observed is None:
            raise ValueError("Registered dataset has no South Fork 2019 observations")
        for run_id in ids:
            if await db.get(SimulationRun, run_id):
                raise ValueError(f"Simulation ID already exists: {run_id}")
        args.output_root.mkdir(parents=True)
        runtime_diagnostic = None
        if args.underflow_diagnostic:
            runtime_diagnostic = prepare_underflow_diagnostic(args.executable,
                args.output_root / "engine/swatplus-61.0.2.61-underflow-diagnostic")
            args.executable = Path(runtime_diagnostic["executable"])
        before = fingerprint(args.project)
        projects = [] if args.routing_probe else [(ids[0], args.project, None)]
        if args.drainage_probe or args.routing_probe:
            probe_project = args.output_root / "drainage-probe-project"
            shutil.copytree(args.project, probe_project)
            intervention = link_drainage_probe(probe_project, landuse_name="corn_lum", tile_name="mw24_1000")
            if args.routing_probe:
                intervention["routing"] = route_drainage_probe(probe_project)
            if args.channel_geometry:
                intervention["channel_geometry"] = restore_channel_lengths(probe_project,
                    channels=args.channel_geometry, routing_graph=args.routing_graph)
            if args.zero_channel_kinetics:
                intervention["channel_kinetics"] = zero_channel_kinetics(probe_project)
            projects.append((ids[0] if args.routing_probe else ids[1], probe_project, intervention))
        report = {"schema_version": "south-fork-baseline-diagnostic/v1",
                  "experiment_id": args.experiment_id, "classification": "DEVELOPMENT_DIAGNOSTIC",
                  "evaluation": ["2019-01-01", "2019-12-31"], "warmup_years": args.warmup_years,
                  "station_id": "05451210", "outlet_gis_id": "153", "runs": {},
                  "observed_dataset_id": args.dataset_id,
                  "hypothesis_status": "NOT_EVALUATED",
                  "limitations": ["2019 was already explored; this is development evidence.",
                                   "A corn-landuse drainage probe is not a historical drainage-mask reconstruction.",
                                   "Neither reference nor probe is calibrated or evidence of the research H1."]}
        for run_id, project, intervention in projects:
            print(f"Running {run_id} on existing PostgreSQL", flush=True)
            sim = SimulationRun(
                id=run_id, user_id=args.owner_id, watershed_id=args.watershed_id,
                scenario_id=args.scenario_id,
                name="South Fork 2019 · " + ("longitudes delineadas y drenaje conectado" if args.channel_geometry else "drenaje con ruteo" if args.routing_probe else "diagnóstico de drenaje" if intervention else "referencia física"),
                status="PENDING", duration_days=365, seed=42, plant_count=1000,
                mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", climate_source="SWAT_PROJECT",
                management_scenario="BASELINE", station_id="05451210",
                start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
                dataset_ids=[args.dataset_id], dataset_roles={args.dataset_id: "OBSERVATION"},
                requested_config={"swat_plus": {"project_path": str(project.resolve()),
                    "executable_path": str(args.executable.resolve()),
                    "working_directory": str((args.output_root / "workspaces").resolve()),
                    "warmup_period": args.warmup_years, "output_frequency": "DAILY",
                    "outlet_unit": "153", "run_type": "SWAT_STANDARD_BASELINE"},
                    "development_diagnostic": {"experiment_id": args.experiment_id,
                        "classification": "CONTROLLED_CHANNEL_LENGTH_PROBE" if args.channel_geometry else "CONTROLLED_DRAINAGE_PROBE" if intervention else "DEVELOPMENT_REFERENCE",
                        "intervention": intervention, "source_project_sha256": before}},
            )
            if runtime_diagnostic:
                sim.requested_config["development_diagnostic"]["runtime_diagnostic"] = runtime_diagnostic
            db.add(sim)
            await db.commit()
            completed = await TwinCouplingEngine.execute_simulation_run(db, run_id)
            diagnostic = (completed.validation or {}).get("baseline_diagnostic") or {}
            workspace = Path(completed.provenance["workspace"])
            # Standalone artifacts accompany the database record for reproducibility.
            output = args.output_root / f"{run_id}.json"
            output.write_text(json.dumps({"run_id": run_id, "configuration": completed.effective_config,
                "provenance": completed.provenance, "validation": completed.validation,
                "records": completed.monthly_outputs}, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            report["runs"][run_id] = {"simulation_id": run_id, "status": completed.status,
                "intervention": intervention, "artifact": str(output.relative_to(BACKEND.parent)),
                "artifact_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "diagnostic": {key: value for key, value in diagnostic.items() if key != "daily_comparison"},
                "output_checksums": completed.provenance.get("output_checksums"),
                "input_checksums": completed.provenance.get("input_checksums_after_mutator"),
                "workspace": str(workspace.relative_to(BACKEND.parent))}
            print(json.dumps({"run_id": run_id, "monthly": diagnostic.get("monthly"),
                              "physical": (diagnostic.get("physical") or {}).get("totals_mm")}), flush=True)
        after = fingerprint(args.project)
        if before != after:
            raise ValueError("Source project changed during the experiment")
        report["source_project"] = {"before_sha256": before, "after_sha256": after, "unchanged": True,
                                    "inspection": inspect_project(args.project)}
        destination = args.output_root / "report.json"
        destination.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(f"Report: {destination}", flush=True)
        return report


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--watershed-id", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--project", type=Path, default=BACKEND / "data/phase34-cdl-2019/project")
    parser.add_argument("--executable", type=Path, default=Path.home() / ".swatplus_builder/engines/61.0.2.61/swatplus-61.0.2.61-gnu-lin_x86_64-Rel")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--warmup-years", type=int, default=19)
    parser.add_argument("--drainage-probe", action="store_true")
    parser.add_argument("--routing-probe", action="store_true", help="Run only the drainage probe with explicit til routing")
    parser.add_argument("--channel-geometry", type=Path, help="Existing delineation channels.gpkg; read-only GIS source")
    parser.add_argument("--routing-graph", type=Path, help="Existing delineation routing_graph.graphml")
    parser.add_argument("--zero-channel-kinetics", action="store_true", help="Reproduce the failed zero-input probe; the engine substitutes nonzero defaults, so this does not disable reactions")
    parser.add_argument("--underflow-diagnostic", action="store_true", help="Explicit copy of the audited binary allowing underflow; invalid/zero/overflow traps remain active")
    args = parser.parse_args()
    try:
        await run(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

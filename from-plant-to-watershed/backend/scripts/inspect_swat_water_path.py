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
              "database": "existing local PostgreSQL digitaltwin", "runs": {}, "failed_runs": {},
              "code_sha256": {str(path.relative_to(BACKEND)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in [BACKEND / f"app/services/{name}.py" for name in
                                ("swat_water_path", "swat_channel_geometry", "swat_runtime_diagnostic", "swat_research_engine", "swat_plus_parser", "swat_plus_adapter", "twin_coupling_engine", "playback_builder")]
                              + [Path(__file__).resolve(), BACKEND / "scripts/run_south_fork_baseline_diagnostic.py",
                                 BACKEND / "scripts/build_swat_research_engine.py", BACKEND / "scripts/fetch_swat_research_sources.py",
                                 BACKEND / "scripts/swat_research_source.lock.json", BACKEND / "scripts/swat_research_toolchain.lock.json"]}}
    daily_records = {}
    async with AsyncSessionLocal() as db:
        for run_id in args.failed_run_id:
            sim = await db.get(SimulationRun, run_id)
            if not sim or sim.status != "FAILED" or sim.hydrology_backend != "SWAT_PLUS":
                raise ValueError(f"Failed SWAT+ simulation required: {run_id}")
            config = (sim.requested_config or {}).get("swat_plus", {})
            workspace = Path(config["working_directory"]) / run_id
            status_path = workspace / "swat_run_status.json"
            status = json.loads(status_path.read_text())
            result["failed_runs"][run_id] = {"status": sim.status,
                "development_diagnostic": (sim.requested_config or {}).get("development_diagnostic"),
                "exit_code": status.get("exit_code"), "reason": status.get("reason"),
                "stderr_tail": status.get("stderr_tail"),
                "status_artifact_sha256": hashlib.sha256(status_path.read_bytes()).hexdigest(),
                "configuration_caveat": "Zero nutrient inputs, if present, are replaced by nonzero defaults in ch_read_nut; the attempted profile does not disable reactions.",
                "interpretation": "No completed hydrograph or observational metrics are available."}
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
            lineage = {}
            for kind, stored_key in (("input", "input_checksums_after_mutator"), ("output", "output_checksums")):
                actual = diagnostic.get(f"{kind}_checksums", {})
                stored = sim.provenance.get(stored_key) or {}
                shared = sorted(set(actual) & set(stored))
                if any(actual[name] != stored[name] for name in shared):
                    raise ValueError(f"Water-path {kind} artifact differs from persisted execution: {run_id}")
                lineage[kind] = {"verified": shared, "not_in_original_provenance": sorted(set(actual) - set(stored))}
            if diagnostic.get("storage_instrumentation"):
                saved_manifest = json.loads((workspace / "swat_engine_manifest.json").read_text())
                if saved_manifest != sim.provenance.get("source_build"):
                    raise ValueError("Storage manifest differs from persisted engine provenance")
            frames = await db.scalar(select(func.count()).select_from(PlaybackFrame).where(PlaybackFrame.simulation_id == run_id))
            baseline = (sim.validation or {}).get("baseline_diagnostic") or {}
            daily_records[run_id] = {row["period"]: row["streamflow_m3s"] for row in sim.monthly_outputs}
            daily = baseline.get("daily_comparison", [])
            persisted_volume = (sim.summary_metrics or {}).get("total_discharge_hm3")
            result["runs"][run_id] = {"status": sim.status, "persisted_frames": frames,
                "observed_dataset_ids": sim.dataset_ids, "station_id": sim.station_id,
                "executable_version": sim.provenance["executable_version"],
                "executable_sha256": sim.provenance["executable_sha256"],
                "source_project_sha256": (sim.requested_config or {}).get("development_diagnostic", {}).get("source_project_sha256"),
                "effective_config": sim.effective_config,
                "input_checksums": sim.provenance.get("input_checksums_after_mutator"),
                "intervention": (sim.requested_config or {}).get("development_diagnostic", {}).get("intervention"),
                "runtime_diagnostic": (sim.requested_config or {}).get("development_diagnostic", {}).get("runtime_diagnostic"),
                "source_build": sim.provenance.get("source_build"),
                "artifact_lineage": lineage,
                "monthly": baseline.get("monthly"), "coverage": baseline.get("coverage"),
                "observed_volume_m3": sum(row["observed_streamflow_m3s"] for row in daily) * 86400
                    if len(daily) == (sim.end_date - sim.start_date).days + 1 else None,
                "persisted_volume_m3": persisted_volume * 1e6 if persisted_volume is not None else None,
                "water_path": diagnostic}
            print(json.dumps({"run_id": run_id, "frames": frames,
                "network": diagnostic.get("network"),
                "catchment_residual_mm": diagnostic.get("catchment_accounting", {}).get("residual_mm")}))
    if args.compare:
        control_id, treatment_id = args.compare
        control, treatment = result["runs"][control_id], result["runs"][treatment_id]
        if control["executable_sha256"] != treatment["executable_sha256"] or control["source_project_sha256"] != treatment["source_project_sha256"]:
            raise ValueError("Controlled comparison requires identical engine and source project")
        control_inputs, treatment_inputs = control["input_checksums"], treatment["input_checksums"]
        differing = sorted(name for name in set(control_inputs) | set(treatment_inputs)
                           if control_inputs.get(name) != treatment_inputs.get(name))
        if differing != ["hyd-sed-lte.cha"]:
            raise ValueError(f"Channel-length comparison changed other traceable inputs: {differing}")
        for key in ("simulation_start", "simulation_end", "warmup_period", "output_frequency", "outlet_unit", "run_type"):
            if control["effective_config"].get(key) != treatment["effective_config"].get(key):
                raise ValueError(f"Controlled comparison requires matching {key}")
        if control["observed_dataset_ids"] != treatment["observed_dataset_ids"] or control["coverage"] != treatment["coverage"]:
            raise ValueError("Controlled comparison requires matching observations and coverage")
        if control["water_path"]["annual_land_terms_mm"] != treatment["water_path"]["annual_land_terms_mm"]:
            raise ValueError("Channel-length comparison unexpectedly changed land water terms")
        result["controlled_comparison"] = {"control_id": control_id, "treatment_id": treatment_id,
            "differing_traceable_inputs": differing, "changed_fields": treatment["intervention"]["channel_geometry"]["changed_fields"],
            "identical_engine": True, "identical_land_water_terms": True,
            "outlet_volume_change_m3": treatment["persisted_volume_m3"] - control["persisted_volume_m3"],
            "monthly_rmse_change_m3s": treatment["monthly"]["rmse"]["value"] - control["monthly"]["rmse"]["value"],
            "interpretation": "Controlled development sensitivity to channel lengths; no calibration or H1 claim."}
    if args.forensic_log:
        log = args.forensic_log.read_text()
        result["failure_forensics"] = {"file": str(args.forensic_log),
            "sha256": hashlib.sha256(args.forensic_log.read_bytes()).hexdigest(),
            "debugger_tail": "\n".join(log.splitlines()[-16:]),
            "interpretation": "Linux si_code=5 (FPE_FLTUND) identifies the sediment failure as floating-point underflow."}
    result["engine_reproduction"] = []
    for old_id, new_id in args.engine_reference:
        old, new = result["runs"][old_id], result["runs"][new_id]
        if old["input_checksums"] != new["input_checksums"] or old["source_project_sha256"] != new["source_project_sha256"]:
            raise ValueError("Engine reproduction requires identical traceable inputs and source project")
        if old["effective_config"] != new["effective_config"] or old["coverage"] != new["coverage"] or old["observed_dataset_ids"] != new["observed_dataset_ids"]:
            raise ValueError("Engine reproduction requires matching effective configuration and observations")
        old_daily, new_daily = daily_records[old_id], daily_records[new_id]
        if set(old_daily) != set(new_daily):
            raise ValueError("Engine reproduction requires identical daily coverage")
        differences = [abs(new_daily[day] - old_daily[day]) for day in old_daily]
        result["engine_reproduction"].append({"previous_run": old_id, "source_build_run": new_id,
            "identical_traceable_inputs": True, "paired_days": len(differences),
            "identical_daily_streamflow": not any(differences),
            "max_daily_streamflow_difference_m3s": max(differences),
            "outlet_volume_difference_m3": new["persisted_volume_m3"] - old["persisted_volume_m3"],
            "monthly_rmse_difference_m3s": new["monthly"]["rmse"]["value"] - old["monthly"]["rmse"]["value"],
            "identical_annual_land_terms": old["water_path"]["annual_land_terms_mm"] == new["water_path"]["annual_land_terms_mm"],
            "interpretation": "Compiler/runtime reproduction on explored 2019 inputs; no calibration or H1 claim."})
    if args.build_reproduction:
        manifests = [json.loads(path.read_text()) for path in args.build_reproduction]
        for manifest in manifests:
            if hashlib.sha256(Path(manifest["executable"]).read_bytes()).hexdigest() != manifest["executable_sha256"]:
                raise ValueError("Build reproduction executable differs from its manifest")
        for key in ("builder_sha256", "compiler_launcher_sha256", "source_date_epoch", "compiler_sha256", "compiler_frontend_sha256", "cmake_sha256", "patches", "numerical_policy", "gcc_support", "dynamic_libraries_sha256", "toolchain_packages"):
            if manifests[0][key] != manifests[1][key]:
                raise ValueError(f"Build reproduction changed {key}")
        if manifests[0]["source"]["archive_sha256"] != manifests[1]["source"]["archive_sha256"]:
            raise ValueError("Build reproduction changed its source archive")
        result["build_reproduction"] = {"manifest_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.build_reproduction],
            "executable_sha256": [manifest["executable_sha256"] for manifest in manifests],
            "identical_executables": manifests[0]["executable_sha256"] == manifests[1]["executable_sha256"],
            "identical_recipe_and_toolchain": True, "manifests": manifests,
            "scope": "Two clean build directories on the recorded local compiler/runtime; not cross-platform reproducibility."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation-id", action="append", required=True)
    parser.add_argument("--failed-run-id", action="append", default=[], help="Retain failures alongside the completed comparison")
    parser.add_argument("--compare", nargs=2, metavar=("CONTROL_ID", "TREATMENT_ID"), help="Audit a controlled channel-length comparison included in --simulation-id")
    parser.add_argument("--forensic-log", type=Path, help="Existing debugger transcript to retain by checksum")
    parser.add_argument("--engine-reference", nargs=2, action="append", default=[], metavar=("PREVIOUS_RUN", "SOURCE_BUILD_RUN"))
    parser.add_argument("--build-reproduction", nargs=2, type=Path, metavar=("MANIFEST_A", "MANIFEST_B"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        await run(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

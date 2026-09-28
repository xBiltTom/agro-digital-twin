"""Run a bounded real SWAT+ baseline/FSPM pair and verify playback via FastAPI.

The project passed to this command must be a separately prepared 2019 CDL
experiment bundle. This runner never modifies that bundle or the source
project. API verification uses a disposable SQLite database; no PostgreSQL
simulation row is created by this command.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import Base
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import Role, User
from app.models.watershed import Watershed
from app.schemas.playback import PlaybackPage
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_diagnostic import diagnose_simulation
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plus_adapter import SwatPlusAdapter, swat_run_config_from_request
from app.services.twin_coupling_engine import TwinCouplingEngine


EXPERIMENT_ID = "phase34-south-fork-cdl-2019-verification"
BASELINE_ID = "phase34-sf19-baseline"
COUPLED_ID = "phase34-sf19-coupled"
PERIOD_START = date(2019, 1, 1)
PERIOD_END = date(2019, 12, 31)
REQUIRED_INPUTS = (
    "hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl",
    "plants.plt", "file.cio", "time.sim", "print.prt", "weather-sta.cli",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_hashes(project: Path) -> dict[str, str]:
    return {name: _sha256(project / name) for name in REQUIRED_INPUTS if (project / name).is_file()}


def _run_record(run_id: str, run_type: str, config: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=run_id,
        name=f"{EXPERIMENT_ID} {run_type}",
        status="RUNNING",
        requested_config={"swat_plus": {**config, "run_type": run_type}},
        effective_config=None,
        provenance=None,
        summary_metrics=None,
        field_aggregates=None,
        hru_aggregates=None,
        plant_sample=None,
        monthly_outputs=None,
        validation=None,
        seed=42,
        plant_count=1000,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        duration_days=(PERIOD_END - PERIOD_START).days + 1,
        hydrology_backend="SWAT_PLUS",
        mode="SWAT_PLUS",
        management_scenario="BASELINE",
        climate_source="SWAT_PROJECT",
        dataset_ids=[],
        dataset_roles={},
        station_id=None,
    )


def _attach_experiment_pair_metadata(baseline: SimpleNamespace, coupled: SimpleNamespace) -> None:
    """Persist the same experiment and peer IDs on both local verification rows."""
    for run, role, peer in (
        (baseline, "BASELINE", coupled),
        (coupled, "COUPLED", baseline),
    ):
        requested = dict(run.requested_config or {})
        swat = dict(requested.get("swat_plus") or {})
        swat.update({
            "experiment_id": EXPERIMENT_ID,
            "baseline_run_id": baseline.id,
            "coupled_run_id": coupled.id,
        })
        requested["swat_plus"] = swat
        run.requested_config = requested
        run.provenance = {
            **(run.provenance or {}),
            "experiment_id": EXPERIMENT_ID,
            "experiment": {
                "experiment_id": EXPERIMENT_ID,
                "baseline_run_id": baseline.id,
                "coupled_run_id": coupled.id,
                "role": role,
                "peer_run_id": peer.id,
            },
        }


def _model_json(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=False)


async def _verify_fastapi_artifacts(
    output_root: Path,
    runs: list[SimpleNamespace],
    watershed: SimpleNamespace,
    coupled_dates: dict[str, str],
) -> dict[str, Any]:
    db_path = output_root / "verification-only.sqlite"
    if db_path.exists():
        raise FileExistsError(f"Refusing to overwrite verification database {db_path}")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def local_db():
        async with session_factory() as session:
            yield session

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            role = Role(name="INVESTIGADOR_HIDROLOGO", description="Disposable local API playback verification")
            owner = User(
                id="phase34-owner", email="phase34-owner@fixture.invalid", hashed_password="unused",
                full_name="Disposable playback owner", is_active=True, roles=[role],
            )
            other = User(
                id="phase34-other", email="phase34-other@fixture.invalid", hashed_password="unused",
                full_name="Disposable unrelated user", is_active=True, roles=[role],
            )
            db_watershed = Watershed(
                id=watershed.id, code=watershed.code, name="South Fork Iowa River (local verification)",
                country="United States", area_km2=watershed.area_km2,
                outlet_lat=watershed.outlet_lat, outlet_lon=watershed.outlet_lon,
            )
            scenario = ClimateScenario(
                id="phase34-scenario", code="PHASE34_NEUTRAL", name="Neutral SWAT project forcing",
                pathway="local verification", description="Metadata only; SWAT project supplies forcing",
                temp_anomaly_c=0.0, precip_factor=1.0, co2_ppm=400.0, source_type="LOCAL_VERIFICATION",
            )
            db.add_all([owner, other, db_watershed, scenario])
            await db.flush()
            for run in runs:
                db.add(SimulationRun(
                    id=run.id, user_id=owner.id, watershed_id=db_watershed.id, scenario_id=scenario.id,
                    name=run.name, status="COMPLETED", duration_days=run.duration_days,
                    seed=run.seed, requested_config=run.requested_config,
                    effective_config=run.effective_config, provenance=run.provenance,
                    summary_metrics=run.summary_metrics, field_aggregates=run.field_aggregates,
                    hru_aggregates=run.hru_aggregates, plant_sample=run.plant_sample,
                    monthly_outputs=run.monthly_outputs, validation=run.validation,
                    mode="SWAT_PLUS", plant_count=run.plant_count, hydrology_backend="SWAT_PLUS",
                    management_scenario="BASELINE", climate_source="SWAT_PROJECT",
                    dataset_ids=[], dataset_roles={}, start_date=PERIOD_START, end_date=PERIOD_END,
                ))
            await db.commit()

        app.dependency_overrides[get_db] = local_db
        owner_headers = {"Authorization": f"Bearer {create_access_token("phase34-owner")}"}
        other_headers = {"Authorization": f"Bearer {create_access_token("phase34-other")}"}
        from httpx import ASGITransport, AsyncClient

        requests = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://phase34.local") as client:
            for run in runs:
                response = await client.get(f"/api/v1/simulations/{run.id}/availability", headers=owner_headers)
                if response.status_code != 200:
                    raise AssertionError(f"/availability failed for {run.id}: {response.status_code} {response.text}")
                requests.append({"endpoint": "availability", "simulation_id": run.id, "status_code": response.status_code,
                                 "response": response.json()})

            dates_to_check = {
                "first_active": coupled_dates["first_active"],
                "peak_lai": coupled_dates["peak_lai"],
                "outside_season": PERIOD_START.isoformat(),
            }
            for name, day in dates_to_check.items():
                response = await client.get(
                    f"/api/v1/simulations/{COUPLED_ID}/playback",
                    params={"date": day, "resolution": "DAILY", "limit": 2}, headers=owner_headers,
                )
                if response.status_code != 200:
                    raise AssertionError(f"/playback {name} failed: {response.status_code} {response.text}")
                page = PlaybackPage.model_validate(response.json())
                if page.total != 1 or len(page.records) != 1 or page.records[0].date.isoformat() != day:
                    raise AssertionError(f"/playback returned an unexpected date selection for {day}")
                requests.append({"endpoint": "playback", "selection": name,
                                 "simulation_id": COUPLED_ID, "date": day,
                                 "status_code": response.status_code,
                                 "record": _model_json(page.records[0])})

            outsider = await client.get(
                f"/api/v1/simulations/{COUPLED_ID}/playback", headers=other_headers,
            )
            if outsider.status_code != 404:
                raise AssertionError("A different user could read the verification simulation")

        baseline_availability = next(item["response"] for item in requests
                                     if item.get("endpoint") == "availability" and item["simulation_id"] == BASELINE_ID)
        coupled_availability = next(item["response"] for item in requests
                                    if item.get("endpoint") == "availability" and item["simulation_id"] == COUPLED_ID)
        if "SWAT_BASELINE_NO_FSPM" not in {code for code in baseline_availability.get("codes", [])}:
            raise AssertionError("Baseline availability did not report the absence of FSPM")
        coupled_resolution = next(row for row in coupled_availability.get("resolutions", [])
                                  if row["resolution"] == "DAILY")
        if not coupled_resolution.get("first_representable_field") or not coupled_resolution.get("first_plant_samples"):
            raise AssertionError("Coupled availability did not discover representable field and sample dates")
        if not any(item.get("endpoint") == "playback" and item.get("selection") == "first_active"
                   and item["record"].get("crop", {}).get("active") for item in requests):
            raise AssertionError("The first active date did not return an active scientific crop state")
        if not any(item.get("endpoint") == "playback" and item.get("selection") == "outside_season"
                   and item["record"].get("crop", {}).get("active") is False for item in requests):
            raise AssertionError("The outside-season date did not remain fallow")
        return {
            "database": "disposable SQLite integration database; no PostgreSQL rows created",
            "database_path": str(db_path),
            "availability": {
                BASELINE_ID: baseline_availability,
                COUPLED_ID: coupled_availability,
            },
            "endpoint_checks": requests,
            "unowned_run_status_code": outsider.status_code,
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    bundle = Path(args.experiment_bundle).resolve()
    output_root = Path(args.output_root).resolve()
    manifest_path = bundle / "manifest.json"
    project = bundle / "project"
    if not manifest_path.is_file() or not project.is_dir():
        raise FileNotFoundError("Expected a prepared bundle with manifest.json and project/")
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite verification outputs at {output_root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("configuration_status") != "PREPARED_AND_VALIDATED" or manifest.get("cdl_year") != 2019:
        raise ValueError("Only the explicitly prepared 2019 CDL experimental variant is accepted")
    watershed_metadata_path = Path(args.watershed_metadata).resolve()
    watershed_metadata = json.loads(watershed_metadata_path.read_text(encoding="utf-8"))
    watershed_stats = watershed_metadata.get("stats", {})
    try:
        watershed_area = float(watershed_stats["total_area_km2"])
        outlet_lat = float(watershed_stats["outlet_lat"])
        outlet_lon = float(watershed_stats["outlet_lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Watershed metadata must record modeled area and snapped outlet coordinates") from exc

    output_root.parent.mkdir(parents=True, exist_ok=True)
    working_directory = output_root / "swat-runs"
    request_swat = {
        "experiment_id": EXPERIMENT_ID,
        "project_path": str(project),
        "executable_path": str(settings.SWAT_PLUS_EXECUTABLE),
        "working_directory": str(working_directory),
        "warmup_period": 0,
        "output_frequency": "DAILY",
        "outlet_unit": "153",
        "timeout_seconds": args.timeout_seconds,
        "target_plant_name": "corn",
    }
    watershed = SimpleNamespace(
        id="phase34-watershed-local-verification", code="USGS-05451210", area_km2=watershed_area,
        outlet_lat=outlet_lat, outlet_lon=outlet_lon,
    )
    baseline_config = swat_run_config_from_request(
        {**request_swat, "run_type": "SWAT_STANDARD_BASELINE"},
        simulation_start=PERIOD_START, simulation_end=PERIOD_END,
        watershed_id=watershed.code, run_id=BASELINE_ID,
    )
    coupled_config = swat_run_config_from_request(
        {**request_swat, "run_type": "SWAT_MULTISCALE_COUPLED"},
        simulation_start=PERIOD_START, simulation_end=PERIOD_END,
        watershed_id=watershed.code, run_id=COUPLED_ID,
    )
    adapter = SwatPlusAdapter(coupled_config.executable_path, project, working_directory)
    baseline_preflight = adapter.preflight(baseline_config)
    coupled_preflight = adapter.preflight(coupled_config, target_crop="corn")
    if baseline_preflight["status"] != "READY" or coupled_preflight["status"] != "READY":
        raise RuntimeError(json.dumps({"baseline": baseline_preflight, "coupled": coupled_preflight}, indent=2))

    before_variant = _input_hashes(project)
    expected_variant = manifest.get("experiment_project_input_checksums_after_sha256", {})
    if any(before_variant.get(name) != digest for name, digest in expected_variant.items()):
        raise ValueError("Prepared variant inputs no longer match its manifest checksums")
    storage = coupled_preflight["storage_estimate"]
    required_bytes = 2 * int(storage["source_project_bytes"]) + 512 * 1024 * 1024
    free_before = shutil.disk_usage(output_root.parent).free
    if free_before < required_bytes:
        raise RuntimeError(f"Insufficient disk for two isolated workspaces plus 512 MiB reserve; need {required_bytes} bytes, have {free_before}")
    plan = {
        "period": [PERIOD_START.isoformat(), PERIOD_END.isoformat()],
        "days": (PERIOD_END - PERIOD_START).days + 1,
        "baseline_preflight": baseline_preflight,
        "coupled_preflight": coupled_preflight,
        "estimated_additional_workspace_bytes": required_bytes,
        "free_bytes_before": free_before,
        "memory_available_bytes": _available_memory_bytes(),
        "prior_paired_workspace_size_bytes": 144 * 1024 * 1024,
        "prior_runtime_basis": "Existing 2019 v6 paired reports completed; the output logs span about ten seconds between baseline and coupled. No peak RSS was retained.",
        "scientific_scope": manifest["classification"],
    }
    print(json.dumps({"preflight_and_resource_plan": plan}, indent=2, sort_keys=True), flush=True)
    output_root.mkdir(parents=True)

    original_artifact_root = settings.DATA_ARTIFACT_ROOT
    settings.DATA_ARTIFACT_ROOT = str(Path(args.artifact_root).resolve())
    try:
        coupled = _run_record(COUPLED_ID, "SWAT_MULTISCALE_COUPLED", request_swat)
        baseline = _run_record(BASELINE_ID, "SWAT_STANDARD_BASELINE", request_swat)
        await TwinCouplingEngine._execute_swat_baseline(baseline, watershed)
        await TwinCouplingEngine._execute_swat_coupled(coupled, watershed)
        _attach_experiment_pair_metadata(baseline, coupled)
        baseline.status = coupled.status = "COMPLETED"
    finally:
        settings.DATA_ARTIFACT_ROOT = original_artifact_root

    after_variant = _input_hashes(project)
    if before_variant != after_variant:
        raise RuntimeError("The prepared input variant changed during the SWAT+ executions")
    baseline_hashes = _input_hashes(Path(baseline.provenance["workspace"]))
    coupled_hashes = _input_hashes(Path(coupled.provenance["workspace"]))
    differing_inputs = sorted(
        name for name in set(baseline_hashes) | set(coupled_hashes)
        if baseline_hashes.get(name) != coupled_hashes.get(name)
    )
    if differing_inputs != ["plants.plt"]:
        raise RuntimeError(f"Baseline and coupled workspaces differ beyond intended FSPM parameters: {differing_inputs}")
    mapping = coupled.provenance.get("workspace_modifications", {})
    changed_inputs = coupled.provenance.get("input_checksum_diff", {}).get("changed", [])
    if not mapping.get("parameter_updates") or "plants.plt" not in changed_inputs:
        raise RuntimeError("FSPM parameters were not confirmed in the actual coupled SWAT+ input copy")

    crop_chain = SwatCropChainDiagnostic.input_chain(
        Path(coupled.provenance["workspace"]), manifest["selected_hru_ids"], crop="corn"
    )
    output_chain = SwatCropChainDiagnostic.output_chain(Path(coupled.provenance["workspace"]), crop="corn")
    if crop_chain["status"] != "PASS" or output_chain["status"] != "PASS":
        raise RuntimeError(f"The executed run no longer confirms its crop chain: {crop_chain} / {output_chain}")

    store = PlaybackArtifactStore(Path(args.artifact_root).resolve() / "playback" / "v1")
    coupled_manifest = coupled.provenance["playback"]
    total, records = store.page(COUPLED_ID, coupled_manifest, limit=500)
    if total != 365 or len(records) != 365 or any(row.resolution != "DAILY" for row in records):
        raise RuntimeError("Persisted coupled playback does not contain all 365 dated daily frames")
    active_records = [row for row in records if row.crop is not None and row.crop.active]
    if not active_records:
        raise RuntimeError("The executed period contains no persisted active FSPM trajectory")
    first_active = active_records[0]
    first_sample = next((row for row in active_records if row.plant_samples), None)
    if first_sample is None:
        raise RuntimeError("No individual FSPM samples were persisted in the daily playback")
    peak_lai_date = coupled.provenance.get("date_of_peak_LAI")
    if not peak_lai_date:
        raise RuntimeError("The coupled run did not persist a date for its maximum FSPM LAI")
    peak = next((row for row in records if row.date.isoformat() == peak_lai_date), None)
    if peak is None or not peak.field.get("lai") or not peak.plant_samples:
        raise RuntimeError("The peak-LAI date does not retain its field state and stable representative samples")
    first_ids = {sample.plant_id for sample in first_sample.plant_samples}
    peak_ids = {sample.plant_id for sample in peak.plant_samples}
    if first_ids != peak_ids:
        raise RuntimeError("Representative plant IDs changed across dates within one FSPM season")
    if first_active.crop.season_id != peak.crop.season_id:
        raise RuntimeError("The sampled crop trajectory crossed season identifiers unexpectedly")

    api_result = await _verify_fastapi_artifacts(
        output_root, [baseline, coupled], watershed,
        {"first_active": first_active.date.isoformat(), "peak_lai": peak_lai_date},
    )
    base_checksums = baseline.provenance.get("output_checksums", {})
    coupled_checksums = coupled.provenance.get("output_checksums", {})
    output_equal = base_checksums == coupled_checksums
    report = {
        "experiment_id": EXPERIMENT_ID,
        "classification": manifest["classification"],
        "persistence_scope": "Local real-engine artifacts plus disposable API SQLite metadata; no PostgreSQL simulation records were written",
        "source_project": manifest["source_project"],
        "watershed_metadata_source": str(watershed_metadata_path),
        "watershed_snapshot": {
            "code": watershed.code, "area_km2": watershed_area,
            "outlet_lat": outlet_lat, "outlet_lon": outlet_lon,
            "id_semantics": "temporary verification identifier; not a production PostgreSQL watershed id",
        },
        "source_project_unchanged": manifest.get("source_input_checksums_before_sha256") == manifest.get("source_input_checksums_after_sha256"),
        "variant_manifest": str((bundle / "manifest.json").resolve()),
        "variant_manifest_sha256": _sha256(manifest_path),
        "variant_input_hashes_unchanged": before_variant == after_variant,
        "period": {"start": PERIOD_START.isoformat(), "end": PERIOD_END.isoformat(), "days": 365},
        "preflight_and_resource_plan": plan,
        "baseline": {
            "simulation_id": BASELINE_ID, "run_type": "SWAT_STANDARD_BASELINE",
            "experiment_id": baseline.provenance["experiment_id"],
            "pair_lineage": baseline.provenance["experiment"],
            "exit_code": baseline.provenance.get("exit_code"),
            "duration_seconds": baseline.provenance.get("duration_seconds"),
            "output_checksums": base_checksums,
            "playback_manifest": baseline.provenance.get("playback"),
            "summary_metrics": baseline.summary_metrics,
        },
        "coupled": {
            "simulation_id": COUPLED_ID, "run_type": "SWAT_MULTISCALE_COUPLED",
            "experiment_id": coupled.provenance["experiment_id"],
            "pair_lineage": coupled.provenance["experiment"],
            "exit_code": coupled.provenance.get("exit_code"),
            "duration_seconds": coupled.provenance.get("duration_seconds"),
            "output_checksums": coupled_checksums,
            "playback_manifest": coupled_manifest,
            "crop_chain_input": crop_chain,
            "crop_chain_output": output_chain,
            "parameter_mapping": mapping,
            "field_summary": coupled.field_aggregates,
            "plant_sample_context": coupled.provenance.get("plant_sample_context"),
        },
        "pairing": {
            "experiment_id": EXPERIMENT_ID,
            "same_project_variant": True,
            "same_period": True,
            "same_forcing_checksums": (
                baseline.provenance["playback"]["provenance"].get("forcing")
                == coupled.provenance["playback"]["provenance"].get("forcing")
            ),
            "workspace_input_files_different": differing_inputs,
            "hydrologic_output_checksums_equal": output_equal,
            "scientific_interpretation": (
                "Hydrological equality is reported as observed; it is not treated as a gain or corrected by changing outputs."
                if output_equal else "Hydrological outputs differ under the paired inputs; no validation claim follows from this bounded experiment."
            ),
        },
        "playback_verification": {
            "artifact_status": "AVAILABLE_AND_CHECKSUM_VERIFIED",
            "resolution": coupled_manifest.get("resolution"),
            "record_count": total,
            "first_active_crop_date": first_active.date.isoformat(),
            "first_date_with_individual_samples": first_sample.date.isoformat(),
            "peak_lai_date": peak_lai_date,
            "outside_season_date": PERIOD_START.isoformat(),
            "representative_sample_count": len(first_sample.plant_samples),
            "stable_sample_ids_across_first_and_peak_dates": sorted(first_ids) == sorted(peak_ids),
            "api_endpoint_verification": api_result,
        },
    }
    report_path = output_root / "phase34-real-engine-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return {"report_path": str(report_path), "report": report}


def _available_memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-bundle", required=True)
    parser.add_argument("--watershed-metadata", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--artifact-root", default=settings.DATA_ARTIFACT_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    result = asyncio.run(_run(args))
    playback = result["report"]["playback_verification"]
    api = playback["api_endpoint_verification"]
    endpoint_checks = []
    for check in api["endpoint_checks"]:
        summary = {
            "endpoint": check["endpoint"],
            "simulation_id": check.get("simulation_id"),
            "status_code": check["status_code"],
        }
        if check.get("date"):
            summary["date"] = check["date"]
        response = check.get("response") or {}
        if check["endpoint"] == "availability":
            summary["provenance_class"] = response.get("provenance_class")
            summary["codes"] = response.get("codes", [])
            resolutions = response.get("resolutions") or []
            summary["first_representable_field"] = next(
                (item.get("first_representable_field") for item in resolutions
                 if item.get("first_representable_field")), None
            )
        elif check["endpoint"] == "playback":
            record = check.get("record") or {}
            summary["record_date"] = record.get("date")
            summary["crop_active"] = (record.get("crop") or {}).get("active")
            summary["plant_sample_count"] = len(record.get("plant_samples") or [])
        endpoint_checks.append(summary)
    print(json.dumps({
        "report_path": result["report_path"],
        "pairing": result["report"]["pairing"],
        "playback_verification": {
            key: value for key, value in playback.items() if key != "api_endpoint_verification"
        },
        "api": {
            "database": api["database"],
            "unowned_run_status_code": api["unowned_run_status_code"],
            "endpoint_checks": endpoint_checks,
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

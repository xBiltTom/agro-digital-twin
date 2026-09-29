"""Register a checksum-verified phase 3.4 SWAT+ pair in development PostgreSQL.

The command is read-only with ``--check-only`` or ``--verify-existing``. Writing
requires both ``--database-scope development`` and the explicit ``--apply``
flag, and is limited to loopback PostgreSQL while ``APP_ENV=development``.
"""

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.migrations import apply_pending_migrations
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_database import PlaybackDatabaseStore


DEFAULT_DATA = BACKEND_DIR / "data"
EXPERIMENT_CLASSIFICATION = "EXPERIMENTAL_CDL_CORN_MAJORITY_MANAGEMENT_NOT_HISTORICAL_RECONSTRUCTION"
FORBIDDEN_LABELS = {"VALIDATED", "CALIBRATED", "HISTORICAL_RECONSTRUCTION", "OBSERVED", "FIXTURE"}
PLAYBACK_KEYS = ("schema_version", "artifact_file", "sha256", "record_count", "first_date", "last_date", "resolution")
ROW_JSON_FIELDS = (
    "parameters", "summary_metrics", "requested_config", "effective_config", "provenance", "error",
    "field_aggregates", "hru_aggregates", "plant_sample", "monthly_outputs", "validation",
    "dataset_ids", "dataset_roles",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(path: Path, expected: str, context: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise ValueError(f"{context} checksum mismatch: {path.name}")


def _reject_existing_ids(requested_ids: list[str], existing_ids: set[str]) -> None:
    duplicates = sorted(set(requested_ids) & existing_ids)
    if duplicates:
        raise ValueError(f"Simulation IDs already exist; refusing overwrite: {duplicates}")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return value


def _decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return deepcopy(default)
    if isinstance(value, str):
        return json.loads(value)
    return deepcopy(value)


def _forbidden_values(value: Any, path: str = "root") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            found.extend(_forbidden_values(nested, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_forbidden_values(nested, f"{path}[{index}]"))
    elif isinstance(value, str):
        label = value.strip().upper()
        if label in FORBIDDEN_LABELS:
            found.append(f"{path}={value}")
    return found


def _check_playback_manifest_match(report_manifest: dict[str, Any], row_manifest: dict[str, Any], run_id: str) -> None:
    for key in PLAYBACK_KEYS:
        if report_manifest.get(key) != row_manifest.get(key):
            raise ValueError(f"{run_id}: playback manifest field {key} differs between provenance report and source row")
    artifact_name = report_manifest.get("artifact_file", "")
    if not isinstance(artifact_name, str) or not re.fullmatch(rf"{re.escape(run_id)}(?:\.[0-9a-f]{{32}})?\.sqlite", artifact_name):
        raise ValueError(f"{run_id}: playback artifact filename is incompatible with simulation_id")
    if report_manifest.get("schema_version") != "twin-playback-v1" or report_manifest.get("resolution") != "DAILY":
        raise ValueError(f"{run_id}: only versioned DAILY phase 3.4 playback is accepted")


def _read_source_rows(source_database: Path, run_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not source_database.is_file():
        raise FileNotFoundError(f"Disposable phase 3.4 verification database is missing: {source_database}")
    connection = sqlite3.connect(f"file:{source_database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows: dict[str, dict[str, Any]] = {}
        for run_id in run_ids:
            row = connection.execute("SELECT * FROM simulation_runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise ValueError(f"Source verification database has no simulation row {run_id}")
            data = dict(row)
            for field in ROW_JSON_FIELDS:
                defaults = {
                    "plant_sample": [], "monthly_outputs": [], "dataset_ids": [],
                    "dataset_roles": {},
                }
                data[field] = _decode_json(data.get(field), defaults.get(field))
            rows[run_id] = data
        return rows
    finally:
        connection.close()


def _validate_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    experiment_manifest_path = Path(args.experiment_manifest).resolve()
    provenance_path = Path(args.provenance_report).resolve()
    playback_report_path = Path(args.playback_manifest_report).resolve()
    source_database = Path(args.source_verification_db).resolve()
    artifact_root = Path(args.playback_root).resolve()
    project = experiment_manifest_path.parent / "project"
    manifest = _read_json(experiment_manifest_path)
    provenance = _read_json(provenance_path)
    playback_report = _read_json(playback_report_path)

    if manifest.get("classification") != EXPERIMENT_CLASSIFICATION:
        raise ValueError("Experiment manifest classification is not the approved phase 3.4 experimental label")
    if provenance.get("classification") != EXPERIMENT_CLASSIFICATION:
        raise ValueError("Provenance report does not preserve the approved experimental classification")
    if provenance.get("experiment_id") != args.experiment_id or playback_report.get("experiment_id") != args.experiment_id:
        raise ValueError("Requested experiment_id does not match both supplied reports")
    manifest_sha = _sha256(experiment_manifest_path)
    if provenance.get("variant_manifest_sha256") != manifest_sha:
        raise ValueError("Variant manifest checksum does not match the provenance report")
    if playback_report.get("variant_manifest_sha256") != manifest_sha:
        raise ValueError("Variant manifest checksum does not match the playback manifest report")
    if manifest.get("configuration_status") != "PREPARED_AND_VALIDATED" or manifest.get("cdl_year") != 2019:
        raise ValueError("Only the verified phase 3.4 2019 CDL experiment can be registered")
    if not project.is_dir():
        raise FileNotFoundError(f"Experiment manifest has no adjacent project/ directory: {project}")
    project_hashes = manifest.get("experiment_project_input_checksums_after_sha256") or {}
    if not project_hashes:
        raise ValueError("Experiment manifest lacks project input checksums")
    for name, expected in project_hashes.items():
        path = project / name
        _require_sha256(path, expected, "Experimental project")

    if provenance.get("source_project_unchanged") is not True or provenance.get("variant_input_hashes_unchanged") is not True:
        raise ValueError("Phase 3.4 provenance does not confirm immutable source and variant inputs")
    pair = provenance.get("pairing") or {}
    if not all(pair.get(key) is True for key in ("same_forcing_checksums", "same_period", "same_project_variant")):
        raise ValueError("Phase 3.4 baseline/coupled pair does not satisfy forcing, period, and variant invariance")
    if pair.get("experiment_id") != args.experiment_id:
        raise ValueError("Provenance report does not confirm the requested experiment pair")

    expected_ids = {
        "baseline": args.baseline_run_id,
        "coupled": args.coupled_run_id,
    }
    for role, run_id in expected_ids.items():
        run_report = provenance.get(role) or {}
        playback_run = playback_report.get(role) or {}
        if run_report.get("simulation_id") != run_id or playback_run.get("simulation_id") != run_id:
            raise ValueError(f"Requested {role} simulation_id does not match both reports")
        expected_type = "SWAT_STANDARD_BASELINE" if role == "baseline" else "SWAT_MULTISCALE_COUPLED"
        if run_report.get("run_type") != expected_type or run_report.get("exit_code") != 0:
            raise ValueError(f"The {role} execution is not a completed real SWAT+ {expected_type} run")
        run_dir = provenance_path.parent / "swat-runs" / run_id
        if not (run_dir / "success.fin").is_file():
            raise ValueError(f"Missing SWAT+ success.fin for {role} run")
        log = run_dir / "simulation.out"
        if not log.is_file() or "Execution successfully completed" not in log.read_text(encoding="utf-8", errors="replace"):
            raise ValueError(f"SWAT+ completion marker is missing for {role} run")
        checksums = run_report.get("output_checksums") or {}
        if not checksums:
            raise ValueError(f"The {role} run has no output checksums")
        for name, expected in checksums.items():
            path = run_dir / name
            _require_sha256(path, expected, f"SWAT+ output for {role}")

    baseline_dir = provenance_path.parent / "swat-runs" / args.baseline_run_id
    coupled_dir = provenance_path.parent / "swat-runs" / args.coupled_run_id
    controlled_outputs = {"time.sim", "print.prt"}
    for name, expected in project_hashes.items():
        baseline_path, coupled_path = baseline_dir / name, coupled_dir / name
        if not baseline_path.is_file() or not coupled_path.is_file():
            raise ValueError(f"A paired workspace is missing declared input {name}")
        if name not in controlled_outputs and _sha256(baseline_path) != expected:
            raise ValueError(f"Baseline does not use the checked experimental input {name}")
        if name in controlled_outputs:
            if _sha256(baseline_path) != _sha256(coupled_path):
                raise ValueError(f"Paired SWAT+ output controls differ unexpectedly: {name}")
        elif name != "plants.plt" and _sha256(coupled_path) != expected:
            raise ValueError(f"Coupled workspace changes a non-plants.plt input: {name}")
    if _sha256(baseline_dir / "plants.plt") == _sha256(coupled_dir / "plants.plt"):
        raise ValueError("Baseline and coupled plants.plt checksums are identical")
    changed_files = provenance.get("pairing", {}).get("workspace_input_files_different")
    if changed_files != ["plants.plt"]:
        raise ValueError(f"Paired workspaces differ in unexpected inputs: {changed_files}")

    source_rows = _read_source_rows(source_database, [args.baseline_run_id, args.coupled_run_id])
    playback_store = PlaybackArtifactStore(artifact_root)
    playback_manifest_by_role: dict[str, dict[str, Any]] = {}
    playback_integrity: dict[str, Any] = {}
    for role, run_id in expected_ids.items():
        report_manifest = (playback_report[role].get("playback_manifest") or {})
        row = source_rows[run_id]
        row_provenance = row.get("provenance") or {}
        row_playback = row_provenance.get("playback") or {}
        expected_evidence = "REAL_SWAT_PLUS" if role == "baseline" else "REAL_SWAT_PLUS_COUPLED"
        if row.get("status") != "COMPLETED" or row_provenance.get("evidence_type") != expected_evidence:
            raise ValueError(f"Source {role} row is incomplete or is not a real SWAT+ result")
        if row_provenance.get("run_id") != run_id:
            raise ValueError(f"Source {role} provenance run_id does not match simulation_id")
        _check_playback_manifest_match(report_manifest, row_playback, run_id)
        iterator = playback_store.iter_records(run_id, report_manifest)
        count = 0
        first = last = None
        expected_day = date.fromisoformat(report_manifest["first_date"])
        for record in iterator:
            if record.simulation_id != run_id or record.run_type != ("SWAT_STANDARD_BASELINE" if role == "baseline" else "SWAT_MULTISCALE_COUPLED"):
                raise ValueError(f"Playback record identity or run_type mismatch for {run_id}")
            if record.resolution != "DAILY" or record.date != expected_day:
                raise ValueError(f"Playback artifact for {run_id} is not a contiguous DAILY series")
            if _forbidden_values(record.model_dump(mode="json")):
                raise ValueError(f"Playback artifact {run_id} contains a prohibited fixture/validation evidence label")
            first = first or record.date.isoformat()
            last = record.date.isoformat()
            expected_day = date.fromordinal(expected_day.toordinal() + 1)
            count += 1
        if count != report_manifest.get("record_count") or count != 365:
            raise ValueError(f"Playback artifact for {run_id} has unexpected record_count={count}")
        if first != report_manifest.get("first_date") or last != report_manifest.get("last_date"):
            raise ValueError(f"Playback dates do not match manifest for {run_id}")
        if _forbidden_values(row_provenance) or _forbidden_values(report_manifest):
            raise ValueError(f"Provenance for {run_id} contains a prohibited fixture/validation evidence label")
        playback_manifest_by_role[role] = report_manifest
        playback_integrity[run_id] = {
            "artifact_file": report_manifest["artifact_file"],
            "sha256": report_manifest["sha256"], "record_count": count,
            "first_date": first, "last_date": last,
        }

    baseline_forcing = (provenance["baseline"].get("playback_manifest") or {}).get("provenance", {}).get("forcing") or {}
    coupled_forcing = (provenance["coupled"].get("playback_manifest") or {}).get("provenance", {}).get("forcing") or {}
    baseline_forcing_hashes = baseline_forcing.get("file_checksums_sha256") or {}
    coupled_forcing_hashes = coupled_forcing.get("file_checksums_sha256") or {}
    if not baseline_forcing_hashes or baseline_forcing_hashes != coupled_forcing_hashes:
        raise ValueError("Baseline and coupled forcing checksums are missing or differ")
    if any(baseline_forcing.get(key) != coupled_forcing.get(key) for key in ("start_date", "end_date", "days")):
        raise ValueError("Baseline and coupled forcing periods differ")

    baseline_row, coupled_row = source_rows[args.baseline_run_id], source_rows[args.coupled_run_id]
    if baseline_row["seed"] != coupled_row["seed"]:
        raise ValueError("Baseline and coupled source rows do not share a seed")
    if (baseline_row["start_date"], baseline_row["end_date"]) != (coupled_row["start_date"], coupled_row["end_date"]):
        raise ValueError("Baseline and coupled source rows do not share the same simulation period")
    if baseline_row["start_date"] != provenance["period"]["start"] or baseline_row["end_date"] != provenance["period"]["end"]:
        raise ValueError("Source row period differs from the verified phase 3.4 period")
    for role, row in (("baseline", baseline_row), ("coupled", coupled_row)):
        swat_config = ((row.get("requested_config") or {}).get("swat_plus") or {})
        expected_type = "SWAT_STANDARD_BASELINE" if role == "baseline" else "SWAT_MULTISCALE_COUPLED"
        if swat_config.get("run_type") != expected_type:
            raise ValueError(f"Source {role} row run_type differs from the provenance report")
        if (swat_config.get("output_frequency") != "DAILY" or swat_config.get("outlet_unit") != "153"
                or swat_config.get("warmup_period") != 0):
            raise ValueError(f"Source {role} requested output, outlet, or warmup configuration is incompatible")
        effective = row.get("effective_config") or {}
        if (effective.get("simulation_start") != "2019-01-01" or effective.get("simulation_end") != "2019-12-31"
                or effective.get("output_frequency") != "DAILY"):
            raise ValueError(f"Source {role} effective period or output frequency differs from the verified pair")
    baseline_requested = baseline_row["requested_config"]["swat_plus"]
    coupled_requested = coupled_row["requested_config"]["swat_plus"]
    for key in ("outlet_unit", "output_frequency", "warmup_period", "target_plant_name"):
        if baseline_requested.get(key) != coupled_requested.get(key):
            raise ValueError(f"Baseline and coupled requested SWAT+ configuration differs at {key}")
    for key in ("watershed_id", "scenario_id"):
        if baseline_row.get(key) != coupled_row.get(key):
            raise ValueError(f"Baseline and coupled rows do not share {key}")
    forbidden = _forbidden_values(provenance) + _forbidden_values(manifest)
    if forbidden:
        raise ValueError("Source provenance contains prohibited evidence labels: " + ", ".join(forbidden[:5]))
    return {
        "experiment_id": args.experiment_id,
        "classification": EXPERIMENT_CLASSIFICATION,
        "variant_manifest_sha256": manifest_sha,
        "baseline_run_id": args.baseline_run_id,
        "coupled_run_id": args.coupled_run_id,
        "baseline_plants_sha256": _sha256(baseline_dir / "plants.plt"),
        "coupled_plants_sha256": _sha256(coupled_dir / "plants.plt"),
        "playback_integrity": playback_integrity,
        "period": provenance["period"],
        "seed": baseline_row["seed"],
        "source_verification_database_sha256": _sha256(source_database),
        "source_rows": source_rows,
        "playback_manifests": playback_manifest_by_role,
        "watershed_code": provenance["watershed_snapshot"]["code"],
        "forcing_checksums": baseline_forcing_hashes,
    }


def _parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _paired_run_payloads(args: argparse.Namespace, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    common_swat_config = {
        "backend": "SWAT_PLUS", "watershed_code": artifacts["watershed_code"],
        "outlet_unit": "153", "output_frequency": "DAILY", "warmup_period": 0,
        "simulation_start": artifacts["period"]["start"], "simulation_end": artifacts["period"]["end"],
        "experiment_id": args.experiment_id, "variant_manifest_sha256": artifacts["variant_manifest_sha256"],
        "forcing_checksums_sha256": artifacts["forcing_checksums"],
        "scientific_classification": EXPERIMENT_CLASSIFICATION,
    }
    payloads = []
    for role, run_id in (("BASELINE", args.baseline_run_id), ("COUPLED", args.coupled_run_id)):
        source = artifacts["source_rows"][run_id]
        peer_id = args.coupled_run_id if role == "BASELINE" else args.baseline_run_id
        playback = artifacts["playback_manifests"]["baseline" if role == "BASELINE" else "coupled"]
        run_type = "SWAT_STANDARD_BASELINE" if role == "BASELINE" else "SWAT_MULTISCALE_COUPLED"
        requested = {"swat_plus": {**common_swat_config, "run_type": run_type},
                     "experiment_pair": {"experiment_id": args.experiment_id, "role": role, "peer_run_id": peer_id}}
        effective = {**common_swat_config, "run_type": run_type,
                     "target_watershed_id": args.watershed_id, "target_scenario_id": args.scenario_id}
        provenance = deepcopy(source["provenance"])
        provenance["playback"] = playback
        provenance["experiment_id"] = args.experiment_id
        provenance["experiment"] = {
            "experiment_id": args.experiment_id,
            "baseline_run_id": args.baseline_run_id,
            "coupled_run_id": args.coupled_run_id,
            "role": role,
            "peer_run_id": peer_id,
        }
        provenance["scientific_classification"] = EXPERIMENT_CLASSIFICATION
        provenance["registration"] = {
            "registration_method": "EXPLICIT_VERIFIED_EXPERIMENT_IMPORT",
            "variant_manifest_sha256": artifacts["variant_manifest_sha256"],
            "source_verification_database_sha256": artifacts["source_verification_database_sha256"],
            "plants_plt_sha256": artifacts["baseline_plants_sha256" if role == "BASELINE" else "coupled_plants_sha256"],
            "playback_sha256": artifacts["playback_integrity"][run_id]["sha256"],
            "classification": EXPERIMENT_CLASSIFICATION,
        }
        data = {field: deepcopy(source.get(field)) for field in ROW_JSON_FIELDS}
        data.update({
            "id": run_id, "user_id": args.owner_id, "watershed_id": args.watershed_id,
            "scenario_id": args.scenario_id, "name": f"{args.experiment_id} {role} verified SWAT+ 2019",
            "status": "COMPLETED", "duration_days": source["duration_days"],
            "seed": source["seed"], "requested_config": requested, "effective_config": effective,
            "provenance": provenance, "started_at": _parse_datetime(source.get("started_at")),
            "finished_at": _parse_datetime(source.get("finished_at")), "mode": "SWAT_PLUS",
            "plant_count": source.get("plant_count") or 1000, "hydrology_backend": "SWAT_PLUS",
            "external_model_id": None, "management_scenario": "BASELINE", "climate_source": "SWAT_PROJECT",
            "station_id": "05451210", "start_date": _parse_date(source["start_date"]),
            "end_date": _parse_date(source["end_date"]),
        })
        payloads.append(data)
    return payloads


def _identity_payload(row: SimulationRun) -> dict[str, Any]:
    provenance = row.provenance or {}
    return {
        "id": row.id, "user_id": row.user_id, "watershed_id": row.watershed_id,
        "scenario_id": row.scenario_id, "status": row.status, "seed": row.seed,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "experiment": provenance.get("experiment"),
        "classification": provenance.get("scientific_classification"),
        "playback_sha256": ((provenance.get("registration") or {}).get("playback_sha256")),
        "variant_manifest_sha256": ((provenance.get("registration") or {}).get("variant_manifest_sha256")),
        "plants_plt_sha256": ((provenance.get("registration") or {}).get("plants_plt_sha256")),
    }


async def _persist(args: argparse.Namespace, artifacts: dict[str, Any]) -> dict[str, Any]:
    target = make_url(settings.DATABASE_URL)
    if args.database_scope != "development":
        raise ValueError("Writes require --database-scope development")
    if settings.APP_ENV.lower() != "development":
        raise ValueError("Writes are allowed only while APP_ENV=development")
    socket_host = target.query.get("host")
    if (not target.drivername.startswith("postgresql") or
            (target.host not in {"localhost", "127.0.0.1", "::1"}
             and socket_host != "/tmp/from-plant-to-watershed-pg")):
        raise ValueError("Writes require a loopback PostgreSQL DATABASE_URL; target details were not printed")
    payloads = _paired_run_payloads(args, artifacts)
    ids = [payload["id"] for payload in payloads]
    result: dict[str, Any] = {"database_scope": "development", "database_host": target.host or "local socket", "run_ids": ids}

    async with AsyncSessionLocal() as session:
        if args.verify_existing:
            existing = list((await session.execute(select(SimulationRun).where(SimulationRun.id.in_(ids)))).scalars())
            by_id = {row.id: row for row in existing}
            if set(by_id) != set(ids):
                raise ValueError("--verify-existing requires both pair IDs to exist")
            for expected in payloads:
                if _identity_payload(by_id[expected["id"]]) != {
                    "id": expected["id"], "user_id": expected["user_id"],
                    "watershed_id": expected["watershed_id"], "scenario_id": expected["scenario_id"],
                    "status": expected["status"], "seed": expected["seed"],
                    "start_date": expected["start_date"].isoformat(), "end_date": expected["end_date"].isoformat(),
                    "experiment": expected["provenance"]["experiment"],
                    "classification": EXPERIMENT_CLASSIFICATION,
                    "playback_sha256": expected["provenance"]["playback"]["sha256"],
                    "variant_manifest_sha256": artifacts["variant_manifest_sha256"],
                    "plants_plt_sha256": expected["provenance"]["registration"]["plants_plt_sha256"],
                }:
                    raise ValueError(f"Existing run {expected['id']} differs from the verified source; no row was modified")
            result.update({"status": "EXISTING_PAIR_VERIFIED", "rows": [_identity_payload(by_id[run_id]) for run_id in ids]})
            return result

        async with session.begin():
            existing_ids = set((await session.execute(select(SimulationRun.id).where(SimulationRun.id.in_(ids)))).scalars())
            _reject_existing_ids(ids, existing_ids)
            owner = await session.get(User, args.owner_id)
            watershed = await session.get(Watershed, args.watershed_id)
            scenario = await session.get(ClimateScenario, args.scenario_id)
            if owner is None or not owner.is_active:
                raise ValueError("The explicit target owner does not exist or is inactive")
            if watershed is None or watershed.code != artifacts["watershed_code"]:
                raise ValueError("The explicit target watershed must exist and match the verified watershed code")
            if scenario is None or abs(scenario.temp_anomaly_c) > 1e-12 or abs(scenario.precip_factor - 1.0) > 1e-12:
                raise ValueError("The explicit target scenario must exist and be neutral (temperature anomaly 0, precipitation factor 1)")
            if scenario.source_type.upper() not in {"LOCAL_VERIFICATION", "SWAT_PROJECT", "NEUTRAL"}:
                raise ValueError("The explicit target scenario is not a development verification scenario")
            rows = [SimulationRun(**payload) for payload in payloads]
            for row in rows:
                session.add(row)
            try:
                await session.flush()
            except IntegrityError as exc:
                raise ValueError("Atomic registration failed a database constraint; transaction rolled back") from exc
            legacy_store = PlaybackArtifactStore(Path(args.playback_root))
            database_store = PlaybackDatabaseStore(session)
            for row, payload in zip(rows, payloads, strict=True):
                legacy = payload["provenance"]["playback"]
                stored = await database_store.write(
                    row.id, legacy_store.iter_records(row.id, legacy),
                    provenance=legacy.get("provenance", {}), limitations=legacy.get("limitations", []),
                )
                if stored["record_count"] != legacy["record_count"]:
                    raise ValueError("Playback import count differs from verified manifest")
                row.provenance = {**row.provenance, "legacy_playback_artifact": legacy, "playback": stored}
        result.update({"status": "REGISTERED", "rows": [_paired_run_identity_dict(payload) for payload in payloads]})
    return result


def _paired_run_identity_dict(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = payload["provenance"]
    return {
        "id": payload["id"], "user_id": payload["user_id"], "watershed_id": payload["watershed_id"],
        "scenario_id": payload["scenario_id"], "status": payload["status"], "seed": payload["seed"],
        "start_date": payload["start_date"].isoformat(), "end_date": payload["end_date"].isoformat(),
        "experiment": provenance["experiment"], "classification": EXPERIMENT_CLASSIFICATION,
        "playback_sha256": provenance["playback"]["sha256"],
        "variant_manifest_sha256": provenance["registration"]["variant_manifest_sha256"],
        "plants_plt_sha256": provenance["registration"]["plants_plt_sha256"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-manifest", default=str(DEFAULT_DATA / "phase34-cdl-2019" / "manifest.json"))
    parser.add_argument("--provenance-report", default=str(DEFAULT_DATA / "phase34-verification" / "phase34-real-engine-report.json"))
    parser.add_argument("--playback-manifest-report", default=str(DEFAULT_DATA / "phase34-verification" / "phase34-real-engine-report.json"),
                        help="Phase 3.4 report carrying both baseline and coupled playback manifests")
    parser.add_argument("--source-verification-db", default=str(DEFAULT_DATA / "phase34-verification" / "verification-only.sqlite"))
    parser.add_argument("--playback-root", default=str(DEFAULT_DATA / "playback" / "v1"))
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--coupled-run-id", required=True)
    parser.add_argument("--owner-id")
    parser.add_argument("--watershed-id")
    parser.add_argument("--scenario-id")
    parser.add_argument("--database-scope", choices=["development"])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-only", action="store_true", help="Verify manifests, workspaces, rows, and playback without a database connection")
    action.add_argument("--apply", action="store_true", help="Atomically register both runs in loopback development PostgreSQL")
    action.add_argument("--verify-existing", action="store_true", help="Read-only identity and checksum check for both existing PostgreSQL rows")
    return parser


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = _validate_artifacts(args)
    if args.check_only:
        return {
            "status": "ARTIFACTS_VERIFIED_NO_DATABASE_ACCESS",
            "experiment_id": artifacts["experiment_id"],
            "classification": artifacts["classification"],
            "variant_manifest_sha256": artifacts["variant_manifest_sha256"],
            "baseline_run_id": artifacts["baseline_run_id"],
            "coupled_run_id": artifacts["coupled_run_id"],
            "playback_integrity": artifacts["playback_integrity"],
            "period": artifacts["period"],
            "seed": artifacts["seed"],
            "source_verification_database_sha256": artifacts["source_verification_database_sha256"],
        }
    if not all((args.owner_id, args.watershed_id, args.scenario_id, args.database_scope)):
        raise ValueError("Database operations require --database-scope development, --owner-id, --watershed-id, and --scenario-id")
    if args.apply:
        await apply_pending_migrations(engine)
    return await _persist(args, artifacts)


def main() -> None:
    args = _parser().parse_args()
    try:
        result = asyncio.run(_main(args))
    finally:
        if not args.check_only:
            asyncio.run(engine.dispose())
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()

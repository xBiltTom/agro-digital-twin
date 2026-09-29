"""Register a completed South Fork playback artifact in existing simulation storage."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.database import AsyncSessionLocal, engine
from app.core.migrations import apply_pending_migrations
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_database import PlaybackDatabaseStore


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def register(result_dir: Path, owner_id: str, watershed_id: str, scenario_id: str) -> str:
    manifest_path = result_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETED" or manifest.get("run", {}).get("frequency") != "DAILY":
        raise ValueError("Only a completed daily South Fork coupled result can be registered")
    run_id = manifest["run_id"]
    playback = manifest["playback"]
    if playback.get("record_count") != 365 or playback.get("first_date") != "2019-01-01" or playback.get("last_date") != "2019-12-31":
        raise ValueError("Playback does not cover all 365 dates of South Fork 2019")
    for name, artifact in manifest["artifacts"].items():
        if _hash(result_dir / name) != artifact["sha256"]:
            raise ValueError(f"Result artifact checksum mismatch: {name}")
    store = PlaybackArtifactStore(BACKEND / "data/playback/v1")
    await apply_pending_migrations(engine)
    async with AsyncSessionLocal() as db:
        owner, watershed, scenario = (await db.get(User, owner_id),
                                      await db.get(Watershed, watershed_id),
                                      await db.get(ClimateScenario, scenario_id))
        if owner is None or watershed is None or scenario is None:
            raise ValueError("Owner, watershed and neutral scenario must already exist")
        if "05451210" not in watershed.code or abs(scenario.temp_anomaly_c) > 1e-12 or abs(scenario.precip_factor - 1) > 1e-12:
            raise ValueError("South Fork watershed and neutral scenario are required")
        run = await db.get(SimulationRun, run_id)
        if run is not None:
            if (run.user_id, run.watershed_id, run.scenario_id) != (owner_id, watershed_id, scenario_id):
                raise ValueError("Existing simulation has different owner, watershed or scenario")
            if run.status != "COMPLETED":
                raise ValueError("Existing simulation is not completed")
            old = (run.provenance or {}).get("playback") or {}
            if old.get("storage") == "POSTGRESQL_JSONB":
                legacy = (run.provenance or {}).get("legacy_playback_artifact") or {}
                if legacy.get("sha256") != playback.get("sha256"):
                    raise ValueError("Registered playback differs from the scientific archive")
                database_store = PlaybackDatabaseStore(db)
                total, _ = await database_store.page(run_id, "DAILY", limit=1)
                if total != 365:
                    raise ValueError("Registered PostgreSQL playback is incomplete")
                repeated = await database_store.write(
                    run_id, store.iter_records(run_id, playback),
                    provenance=playback.get("provenance", {}),
                    limitations=playback.get("limitations", []), idempotent=True,
                )
                if repeated["record_count"] != 365:
                    raise ValueError("Scientific archive is incomplete")
                if (run.provenance or {}).get("phase_result_manifest_sha256") != _hash(manifest_path):
                    # A manifest-only erratum may correct explanatory provenance;
                    # the immutable frame archive checksum must still match.
                    corrected = dict(run.provenance)
                    corrected["phase_result_manifest_sha256"] = _hash(manifest_path)
                    corrected["fspm_calendar_provenance"] = manifest["fspm_forcing_provenance"]
                    corrected["legacy_playback_artifact"] = playback
                    corrected["playback"] = {**old, "provenance": playback.get("provenance", {}),
                                              "limitations": playback.get("limitations", [])}
                    run.provenance = corrected
                    await db.commit()
                return run_id
            if old.get("sha256") != playback.get("sha256"):
                raise ValueError("Existing simulation points to a different scientific playback")
        else:
            run = SimulationRun(
            id=run_id, user_id=owner_id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="South Fork 2019 dynamic plant-soil-water twin", status="COMPLETED", duration_days=365,
            seed=manifest["run"]["seed"], plant_count=manifest["run"]["plant_count_per_calendar_group"],
            mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", climate_source="SWAT_PROJECT",
            management_scenario="BASELINE", dataset_ids=[], dataset_roles={},
            start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
            requested_config={"swat_plus": {"run_type": "SWAT_MULTISCALE_COUPLED", "output_frequency": "DAILY"}},
            effective_config={"backend": "SWAT_PLUS", "run_type": "SWAT_MULTISCALE_COUPLED",
                              "output_frequency": "DAILY", "outlet_unit": "153"},
            provenance={"evidence_type": "REAL_SWAT_PLUS_COUPLED",
                        "phase_result_manifest": str(manifest_path),
                        "phase_result_manifest_sha256": _hash(manifest_path),
                        "fspm_calendar_provenance": manifest["fspm_forcing_provenance"],
                        "executed_calendar_coupling": manifest["calendar_coupling"]},
            summary_metrics={"evidence_type": "REAL_SWAT_PLUS_COUPLED", "period_count": 365,
                             "water_balance": manifest["swat_outputs"]["water_balance"]},
            validation={"status": "NOT_AVAILABLE", "reason": "Operational twin, not observational calibration"},
            field_aggregates={"calendar": manifest["calendar"]},
            hru_aggregates={"status": "AVAILABLE_IN_POSTGRESQL_PLAYBACK"},
            plant_sample=[], monthly_outputs=[],
            )
            db.add(run)
            await db.flush()
        database_playback = await PlaybackDatabaseStore(db).write(
            run_id, store.iter_records(run_id, playback), provenance=playback.get("provenance", {}),
            limitations=playback.get("limitations", []), idempotent=True,
        )
        if database_playback["record_count"] != 365:
            raise ValueError("Indexed playback count differs from manifest")
        provenance = dict(run.provenance or {})
        provenance["legacy_playback_artifact"] = playback
        provenance["playback"] = database_playback
        provenance["soil_water_interpretation"] = (
            "PRE_CORRECTION_SWAT_SOIL_WATER" if run_id.endswith("-v1")
            else "CORRECTED_SWAT_SOIL_WATER_61.0.2.61"
        )
        run.provenance = provenance
        await db.commit()
    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", type=Path)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--watershed-id", required=True)
    parser.add_argument("--scenario-id", required=True)
    args = parser.parse_args()
    print(asyncio.run(register(args.result_dir, args.owner_id, args.watershed_id, args.scenario_id)))

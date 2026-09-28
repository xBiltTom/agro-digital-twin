from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from scripts import register_verified_experiment as registration


def _artifact_bundle():
    source_rows = {}
    manifests = {}
    for role, run_id, run_type in (
        ("baseline", "phase34-sf19-baseline", "SWAT_STANDARD_BASELINE"),
        ("coupled", "phase34-sf19-coupled", "SWAT_MULTISCALE_COUPLED"),
    ):
        source_rows[run_id] = {
            "provenance": {"evidence_type": "REAL_SWAT_PLUS" if role == "baseline" else "REAL_SWAT_PLUS_COUPLED"},
            "duration_days": 365, "seed": 42, "started_at": None, "finished_at": None,
            "plant_count": 1000, "start_date": date(2019, 1, 1), "end_date": date(2019, 12, 31),
            "parameters": {}, "summary_metrics": {}, "requested_config": {}, "effective_config": {},
            "error": None, "field_aggregates": None, "hru_aggregates": None, "plant_sample": [],
            "monthly_outputs": [], "validation": None, "dataset_ids": [], "dataset_roles": {},
        }
        manifests[role] = {"sha256": f"playback-{role}"}
    return {
        "watershed_code": "USGS-05451210", "variant_manifest_sha256": "variant-hash",
        "source_verification_database_sha256": "source-db-hash", "forcing_checksums": {"rain.pcp": "rain-hash"},
        "baseline_plants_sha256": "plants-base", "coupled_plants_sha256": "plants-coupled",
        "playback_integrity": {
            "phase34-sf19-baseline": {"sha256": "playback-baseline"},
            "phase34-sf19-coupled": {"sha256": "playback-coupled"},
        },
        "period": {"start": "2019-01-01", "end": "2019-12-31"}, "seed": 42,
        "source_rows": source_rows, "playback_manifests": manifests,
    }


def _args():
    return SimpleNamespace(
        experiment_id="phase34-south-fork-cdl-2019-verification", owner_id=7,
        watershed_id=2, scenario_id=3, baseline_run_id="phase34-sf19-baseline",
        coupled_run_id="phase34-sf19-coupled",
    )


def test_verified_pair_payloads_preserve_owner_roles_peers_and_classification():
    rows = registration._paired_run_payloads(_args(), _artifact_bundle())

    assert [row["user_id"] for row in rows] == [7, 7]
    assert [row["scenario_id"] for row in rows] == [3, 3]
    assert rows[0]["provenance"]["experiment"] == {
        "experiment_id": "phase34-south-fork-cdl-2019-verification",
        "baseline_run_id": "phase34-sf19-baseline", "coupled_run_id": "phase34-sf19-coupled",
        "role": "BASELINE", "peer_run_id": "phase34-sf19-coupled",
    }
    assert rows[1]["provenance"]["experiment"]["peer_run_id"] == "phase34-sf19-baseline"
    assert {row["provenance"]["scientific_classification"] for row in rows} == {
        registration.EXPERIMENT_CLASSIFICATION,
    }
    assert {row["provenance"]["evidence_type"] for row in rows} == {
        "REAL_SWAT_PLUS", "REAL_SWAT_PLUS_COUPLED",
    }


def test_import_checksum_mismatch_is_rejected(tmp_path):
    artifact = tmp_path / "output.txt"
    artifact.write_text("verified bytes", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum mismatch"):
        registration._require_sha256(artifact, "0" * 64, "SWAT+ output")


def test_duplicate_simulation_ids_are_rejected_without_overwrite():
    with pytest.raises(ValueError, match="refusing overwrite"):
        registration._reject_existing_ids(
            ["phase34-sf19-baseline", "phase34-sf19-coupled"],
            {"phase34-sf19-baseline"},
        )


def test_playback_id_mismatch_and_fixture_evidence_are_rejected():
    manifest = {
        "schema_version": "twin-playback-v1", "artifact_file": "another-run.sqlite",
        "sha256": "0" * 64, "record_count": 365,
        "first_date": "2019-01-01", "last_date": "2019-12-31", "resolution": "DAILY",
    }
    with pytest.raises(ValueError, match="incompatible with simulation_id"):
        registration._check_playback_manifest_match(manifest, manifest, "phase34-sf19-baseline")

    assert registration._forbidden_values({"evidence_type": "fixture"}) == [
        "root.evidence_type=fixture",
    ]


class _ScalarsResult:
    def __init__(self, values=()):
        self.values = values

    def scalars(self):
        return iter(self.values)


class _Transaction:
    def __init__(self):
        self.rolled_back = False
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.rolled_back = exc_type is not None
        self.committed = exc_type is None
        return False


class _FailingSession:
    def __init__(self):
        self.transaction = _Transaction()
        self.added = []
        self.lookups = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def begin(self):
        return self.transaction

    async def execute(self, statement):
        return _ScalarsResult()

    async def get(self, model, identity):
        self.lookups.append((model, identity))
        if model is registration.User:
            return SimpleNamespace(is_active=True)
        if model is registration.Watershed:
            return SimpleNamespace(code="USGS-05451210")
        if model is registration.ClimateScenario:
            return SimpleNamespace(temp_anomaly_c=0.0, precip_factor=1.0, source_type="NEUTRAL")
        raise AssertionError(f"Unexpected model lookup: {model}")

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        raise IntegrityError("insert", {}, RuntimeError("synthetic constraint rejection"))


@pytest.mark.asyncio
async def test_registration_uses_explicit_owner_and_rolls_back_failed_pair(monkeypatch):
    session = _FailingSession()
    monkeypatch.setattr(registration, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(registration.settings, "DATABASE_URL", "postgresql+asyncpg://dev@localhost/devdb")
    monkeypatch.setattr(registration.settings, "APP_ENV", "development")
    args = _args()
    args.database_scope = "development"
    args.verify_existing = False

    with pytest.raises(ValueError, match="transaction rolled back"):
        await registration._persist(args, _artifact_bundle())

    assert (registration.User, 7) in session.lookups
    assert [row.user_id for row in session.added] == [7, 7]
    assert session.transaction.rolled_back is True
    assert session.transaction.committed is False

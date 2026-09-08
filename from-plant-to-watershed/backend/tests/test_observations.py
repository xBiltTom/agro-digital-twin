import hashlib
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.database import Base
from app.main import app
from app.models.observation import DatasetArtifact, StreamflowObservation
from app.services.observational_registry import register_usgs_streamflow
from app.services.usgs_streamflow import CFS_TO_M3S, StreamflowRecord, UsgsStreamflowProvider
from app.services.watershed_selection import CandidateAssessment, assess_candidate, calculate_agricultural_fraction


FIXTURE = Path(__file__).parent / "fixtures" / "usgs_daily_values.json"


def test_usgs_parser_conversion_and_qc():
    records = UsgsStreamflowProvider.parse_daily_values(FIXTURE.read_bytes(), "05451210")
    assert records[0].value_m3s == pytest.approx(CFS_TO_M3S)
    assert records[1].value_m3s is None
    qc = UsgsStreamflowProvider.quality_control(records)
    assert qc.n_observations == 3
    assert qc.missing_count == 1
    assert qc.gap_count == 0
    assert qc.coverage_fraction == pytest.approx(2 / 3)
    assert qc.start_date == "2020-01-01"


def test_usgs_parser_rejects_corrupt_and_wrong_station_response():
    with pytest.raises(ValueError, match="Invalid USGS"):
        UsgsStreamflowProvider.parse_daily_values(b"not-json", "05451210")
    with pytest.raises(ValueError, match="station_id"):
        UsgsStreamflowProvider.build_daily_values_url("unsafe/path", date(2020, 1, 1), date(2020, 1, 2))


def test_usgs_qc_detects_duplicate_negative_and_gaps():
    records = [
        StreamflowRecord(date(2020, 1, 1), 1, CFS_TO_M3S, "ft3/s", None),
        StreamflowRecord(date(2020, 1, 1), 2, 2 * CFS_TO_M3S, "ft3/s", None),
        StreamflowRecord(date(2020, 1, 3), -1, -CFS_TO_M3S, "ft3/s", None),
    ]
    qc = UsgsStreamflowProvider.quality_control(records)
    assert qc.duplicate_count == 1
    assert qc.invalid_count == 1
    assert qc.gap_count == 1


def test_monthly_mean_keeps_incomplete_months_explicit():
    full = [StreamflowRecord(date(2024, 1, 1) + timedelta(days=i), 10, 10 * CFS_TO_M3S, "ft3/s", None) for i in range(31)]
    complete = UsgsStreamflowProvider.monthly_mean_discharge(full)
    assert complete[0].included is True
    assert complete[0].mean_discharge_m3s == pytest.approx(10 * CFS_TO_M3S)
    incomplete = UsgsStreamflowProvider.monthly_mean_discharge(full[:10])
    assert incomplete[0].included is False
    assert incomplete[0].mean_discharge_m3s is None


@pytest.mark.asyncio
async def test_registry_preserves_raw_checksum_and_normalized_rows(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'observations.sqlite'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    raw = FIXTURE.read_bytes()
    provider = UsgsStreamflowProvider(data_root=tmp_path, downloader=lambda _url: raw)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        url, artifact_path, checksum, records, qc = await provider.fetch_parse_and_store(
            "05451210", date(2020, 1, 1), date(2020, 1, 3)
        )
        assert checksum == hashlib.sha256(raw).hexdigest()
        async with session_factory() as session:
            dataset = await register_usgs_streamflow(session, "05451210", url, artifact_path, checksum, records, qc)
            artifact = await session.scalar(select(DatasetArtifact).where(DatasetArtifact.dataset_id == dataset.id))
            rows = (await session.execute(select(StreamflowObservation).where(StreamflowObservation.dataset_id == dataset.id))).scalars().all()
        assert artifact.artifact_kind == "RAW"
        assert artifact.checksum_sha256 == checksum
        assert len(rows) == 3
        assert dataset.evidence_type == "OBSERVED"
    finally:
        await engine.dispose()


def test_selection_requires_verified_geospatial_and_observational_criteria():
    decision = assess_candidate(CandidateAssessment(
        watershed_name="Candidate", gauge_usgs="05451210", effective_years=21,
        daily_coverage_fraction=0.95, agricultural_fraction=0.7, major_dam_present=False,
        geometry_crs="EPSG:5070", gauge_watershed_verified=True,
    ))
    assert decision["decision"] == "INCLUDE"
    incomplete = assess_candidate(CandidateAssessment(
        watershed_name="Unknown", gauge_usgs="05451210", effective_years=None,
        daily_coverage_fraction=None, agricultural_fraction=None, major_dam_present=None,
        geometry_crs=None, gauge_watershed_verified=False,
    ))
    assert incomplete["decision"] == "EXCLUDE"
    assert calculate_agricultural_fraction(100, 60, "EPSG:4326", "EPSG:5070") == 0.6
    with pytest.raises(ValueError, match="projected"):
        calculate_agricultural_fraction(100, 60, "EPSG:4326", "EPSG:4326")


@pytest.mark.asyncio
async def test_usgs_ingest_api_uses_observed_registry_without_network(tmp_path: Path, monkeypatch):
    raw = FIXTURE.read_bytes()
    artifact = tmp_path / "fixture-usgs.json"
    artifact.write_bytes(raw)
    records = UsgsStreamflowProvider.parse_daily_values(raw, "05451210")
    qc = UsgsStreamflowProvider.quality_control(records)

    async def fake_ingest(_self, _station, _start, _end):
        return "https://example.invalid/usgs-fixture", artifact, hashlib.sha256(raw).hexdigest(), records, qc

    monkeypatch.setattr(UsgsStreamflowProvider, "fetch_parse_and_store", fake_ingest)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = await client.post("/api/v1/datasets/usgs/ingest", headers=headers, json={
            "station_id": "05451210", "start_date": "2020-01-01", "end_date": "2020-01-03",
        })
        assert response.status_code == 201
        assert response.json()["evidence_type"] == "OBSERVED"
        listed = await client.get("/api/v1/datasets/streamflow/observations?station_id=05451210", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 3

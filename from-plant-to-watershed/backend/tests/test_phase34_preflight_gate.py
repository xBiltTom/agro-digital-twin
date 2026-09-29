from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.api.v1.simulations import _is_coupled_swat_request
from app.core.database import Base
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import Role, User
from app.models.watershed import Watershed
from app.schemas.simulation import SimulationRunCreate
from app.services.swat_plus_adapter import SwatPlusAdapter
from app.services.twin_coupling_engine import TwinCouplingEngine
from scripts.run_phase34_south_fork_verification import _attach_experiment_pair_metadata


def _request(*, mode, hydrology_backend, run_type):
    return SimulationRunCreate(
        name="preflight-gate fixture", watershed_id="watershed-fixture",
        scenario_id="scenario-fixture", duration_days=3, mode=mode, hydrology_backend=hydrology_backend,
        climate_source=("SWAT_PROJECT" if mode == "SWAT_PLUS" and hydrology_backend == "SWAT_PLUS" else "SYNTHETIC"),
        start_date=date(2019, 6, 1), end_date=date(2019, 6, 3),
        swat_plus={"run_type": run_type},
    )


def test_preflight_gate_matches_both_swat_execution_selectors():
    assert _is_coupled_swat_request(_request(
        mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", run_type="SWAT_MULTISCALE_COUPLED"
    ))
    with pytest.raises(ValidationError, match="require both hydrology_backend and mode"):
        _request(mode="SWAT_PLUS", hydrology_backend="SIMPLIFIED", run_type="SWAT_MULTISCALE_COUPLED")
    assert not _is_coupled_swat_request(_request(
        mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", run_type="SWAT_STANDARD_BASELINE"
    ))
    assert not _is_coupled_swat_request(_request(
        mode="RESEARCH_MULTISCALE", hydrology_backend="SIMPLIFIED", run_type="SWAT_MULTISCALE_COUPLED"
    ))


def test_verification_pair_persists_shared_experiment_id_and_peer_ids():
    baseline = SimpleNamespace(
        id="baseline-local", requested_config={"swat_plus": {"run_type": "SWAT_STANDARD_BASELINE"}},
        provenance={"exit_code": 0},
    )
    coupled = SimpleNamespace(
        id="coupled-local", requested_config={"swat_plus": {"run_type": "SWAT_MULTISCALE_COUPLED"}},
        provenance={"exit_code": 0},
    )

    _attach_experiment_pair_metadata(baseline, coupled)

    assert baseline.requested_config["swat_plus"]["experiment_id"] == coupled.requested_config["swat_plus"]["experiment_id"]
    assert baseline.requested_config["swat_plus"]["baseline_run_id"] == "baseline-local"
    assert coupled.requested_config["swat_plus"]["coupled_run_id"] == "coupled-local"
    assert baseline.provenance["experiment"]["role"] == "BASELINE"
    assert baseline.provenance["experiment"]["peer_run_id"] == "coupled-local"
    assert coupled.provenance["experiment"]["role"] == "COUPLED"
    assert coupled.provenance["experiment"]["peer_run_id"] == "baseline-local"


@pytest.mark.asyncio
async def test_blocked_coupled_post_creates_no_runs_or_artifacts(tmp_path, monkeypatch):
    artifact_root = tmp_path / "artifacts"
    monkeypatch.setattr("app.api.v1.simulations.settings.DATA_ARTIFACT_ROOT", str(artifact_root))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'preflight-gate.sqlite'}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def local_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = local_db
    preflight_calls = []
    execute = AsyncMock(side_effect=AssertionError("blocked request reached the executor"))
    monkeypatch.setattr(TwinCouplingEngine, "execute_simulation_run", execute)

    def blocked_preflight(self, config, *, target_crop):
        preflight_calls.append((config.run_type, target_crop))
        return {
            "status": "BLOCKED", "checks": {"coupled_crop_management": False},
            "blockers": [{"code": "COUPLED_CROP_CONFIGURATION_INVALID", "message": "management does not sow corn"}],
        }

    monkeypatch.setattr(SwatPlusAdapter, "preflight", blocked_preflight)
    try:
        async with session_factory() as db:
            role = Role(name="INVESTIGADOR_HIDROLOGO", description="fixture")
            owner = User(email="phase34-owner@fixture.invalid", hashed_password="fixture",
                         full_name="Fixture Owner", is_active=True, roles=[role])
            watershed = Watershed(code="USGS-05451210", name="South Fork fixture", area_km2=10,
                                  outlet_lat=0, outlet_lon=0)
            scenario = ClimateScenario(code="NEUTRAL", name="Neutral", pathway="fixture",
                                       description="fixture", temp_anomaly_c=0,
                                       precip_factor=1, co2_ppm=400)
            db.add_all([owner, watershed, scenario])
            await db.commit()
            owner_id, watershed_id, scenario_id = owner.id, watershed.id, scenario.id

        headers = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
        payload = {
            "name": "Blocked coupled fixture", "watershed_id": watershed_id,
            "scenario_id": scenario_id, "duration_days": 3, "seed": 5,
            "mode": "SWAT_PLUS", "hydrology_backend": "SWAT_PLUS",
            "climate_source": "SWAT_PROJECT", "start_date": date(2019, 6, 1).isoformat(),
            "end_date": date(2019, 6, 3).isoformat(), "parameters": {},
            "swat_plus": {
                "project_path": str(tmp_path / "source-project"),
                "executable_path": str(tmp_path / "swatplus"),
                "working_directory": str(tmp_path / "workspaces"),
                "run_type": "SWAT_MULTISCALE_COUPLED", "target_plant_name": "corn",
                "output_frequency": "DAILY",
            },
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/simulations", headers=headers, json=payload)

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["type"] == "SWAT_COUPLED_PREFLIGHT_BLOCKED"
        assert detail["blockers"][0]["code"] == "COUPLED_CROP_CONFIGURATION_INVALID"
        assert preflight_calls == [("SWAT_MULTISCALE_COUPLED", "corn")]
        execute.assert_not_awaited()
        async with session_factory() as db:
            assert await db.scalar(select(func.count(SimulationRun.id))) == 0
        assert not artifact_root.exists()
        assert not (tmp_path / "workspaces").exists()
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()

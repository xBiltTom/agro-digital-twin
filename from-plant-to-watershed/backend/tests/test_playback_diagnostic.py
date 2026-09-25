from datetime import date
import json
from types import SimpleNamespace

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User, Role
from app.models.watershed import Watershed
from app.schemas.playback import PlaybackPage
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_diagnostic import diagnose_record, diagnose_simulation
from scripts.generate_visual_fixtures import OUT, generate
from scripts.populate_swat_simulations import build_historical_payload


def _run(run_id, manifest=None, run_type="SWAT_MULTISCALE_COUPLED", historical=False):
    return SimpleNamespace(id=run_id, name="fixture", status="COMPLETED",
        requested_config={"swat_plus": {"run_type": run_type}}, effective_config={},
        provenance={**({"source_kind": "HISTORICAL_IMPORT"} if historical else {}),
                    **({"playback": manifest} if manifest else {})})


def test_fixture_contract_and_diagnostics(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "DATA_ARTIFACT_ROOT", str(tmp_path))
    assert json.loads(OUT.read_text()) == generate()
    pages = {key: PlaybackPage.model_validate(value) for key, value in generate()["pages"].items()}
    daily = pages["coupled_daily"].records
    assert [diagnose_record(row).mode for row in daily] == ["SCIENTIFIC_ACTIVE", "SCIENTIFIC_ACTIVE", "SCIENTIFIC_FALLOW"]
    assert daily[0].weather["precipitation_mm"].value == 0
    assert daily[1].weather["precipitation_mm"].value is None
    assert daily[0].field["soil_moisture_vol_percent"].unit == "volumetric percent"
    assert daily[0].hydrology["soil_water_mm"].unit == "mm"
    assert daily[0].field["biomass_g_plant"].unit == "g/plant"
    assert diagnose_record(pages["baseline"].records[0]).mode == "HYDROLOGY_ONLY"
    assert "FIELD_HEIGHT_MISSING" in diagnose_record(pages["incomplete"].records[0]).codes
    assert diagnose_record(pages["coupled_monthly"].records[0]).mode == "HYDROLOGY_ONLY"
    assert "HISTORICAL_REFERENCE" in diagnose_simulation(_run("fixture-historical", historical=True)).codes
    assert "NO_PLAYBACK_ARTIFACT" in diagnose_simulation(_run("missing")).codes

    store = PlaybackArtifactStore()
    manifest = store.write("fixture-coupled", daily, provenance={"fixture": True})
    result = diagnose_simulation(_run("fixture-coupled", manifest), on=date(2020, 11, 10))
    summary = result.resolutions[0]
    assert summary.first_record == date(2020, 5, 10)
    assert summary.first_active_crop == date(2020, 5, 10)
    assert summary.first_representable_field == date(2020, 5, 10)
    assert summary.first_plant_samples == date(2020, 5, 10)
    assert summary.selected_date.mode == "SCIENTIFIC_FALLOW"
    path = store.root / manifest["artifact_file"]
    path.write_bytes(path.read_bytes() + b"damage")
    assert result.resolutions[0].artifact_status == "AVAILABLE"
    assert diagnose_simulation(_run("fixture-coupled", manifest)).resolutions[0].artifact_status == "INVALID"
    path.unlink()
    assert diagnose_simulation(_run("fixture-coupled", manifest)).resolutions[0].artifact_status == "UNAVAILABLE"


def test_historical_import_units_and_missing_science():
    frame = pd.DataFrame({"date": ["2020-01-01"], "coupled_streamflow_m3s": [2.],
        "coupled_runoff_mm": [1.], "coupled_et_mm": [3.], "precipitation_mm": [0.],
        "observed_streamflow_m3s": [2.5], "soil_water_mm": [150.],
        "FSPM_LAI": [1.], "FSPM_root_depth": [0.5], "FSPM_biomass": [125.]})
    source_copy = frame.copy(deep=True)
    payload = build_historical_payload({"validation": {}}, frame,
        {"units": {"soil_water_mm": "mm", "FSPM_biomass": "g/plant"}})
    pd.testing.assert_frame_equal(frame, source_copy)
    assert payload["monthly_outputs"][0]["precip_mm"] == 0
    assert payload["monthly_outputs"][0]["percolation_mm"] is None
    assert payload["field_aggregates"]["mean_biomass_g_plant"] == 125
    assert "mean_biomass_kg_m2" not in payload["field_aggregates"]
    assert payload["summary_metrics"]["mean_soil_moisture_percent"] is None
    assert payload["summary_metrics"]["total_percolation_mm"] is None
    assert payload["summary_metrics"]["water_balance"]["closure_error_mm"] is None
    assert "calibrad" not in payload["validation"]["interpretation"].lower()


@pytest.mark.asyncio
async def test_availability_endpoint_owner_and_filtered_pagination(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "DATA_ARTIFACT_ROOT", str(tmp_path))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite'}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async def local_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = local_db
    try:
        async with session_factory() as db:
            owner_role = Role(name="INVESTIGADOR_HIDROLOGO", description="fixture")
            outsider_role = Role(name="OPERADOR_AGROPECUARIO", description="fixture")
            owner = User(email="owner@fixture.invalid", hashed_password="fixture", full_name="Owner",
                         is_active=True, roles=[owner_role])
            outsider = User(email="other@fixture.invalid", hashed_password="fixture", full_name="Other",
                            is_active=True, roles=[outsider_role])
            watershed = Watershed(code="TEST", name="Test basin", area_km2=1, outlet_lat=0, outlet_lon=0)
            scenario = ClimateScenario(code="TEST", name="Test", pathway="test", description="test")
            db.add_all([owner, outsider, watershed, scenario])
            await db.flush()
            run = SimulationRun(user_id=owner.id, watershed_id=watershed.id, scenario_id=scenario.id,
                                name="Availability fixture", status="COMPLETED", duration_days=1, seed=7)
            db.add(run)
            await db.commit()
            run_id, owner_id, outsider_id = run.id, owner.id, outsider.id
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            path = f"/api/v1/simulations/{run_id}/availability"
            assert (await client.get(path)).status_code == 401
            owner_headers = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
            outsider_headers = {"Authorization": f"Bearer {create_access_token(outsider_id)}"}
            assert (await client.get(path, headers=owner_headers)).json()["codes"] == ["NO_PLAYBACK_ARTIFACT"]
            assert (await client.get(path, headers=outsider_headers)).status_code == 404
            for suffix in ("", "/results", "/swat-results", "/playback", "/ai-insights"):
                assert (await client.get(f"/api/v1/simulations/{run_id}{suffix}", headers=outsider_headers)).status_code == 404
            own_list = (await client.get("/api/v1/simulations?limit=1", headers=owner_headers)).json()
            assert len(own_list) == 1 and own_list[0]["user_id"] == owner_id
            other_list = (await client.get("/api/v1/simulations?limit=50", headers=outsider_headers)).json()
            assert all(item["id"] != run_id for item in other_list)
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()

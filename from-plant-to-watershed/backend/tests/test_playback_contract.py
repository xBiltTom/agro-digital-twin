"""Small deterministic playback contract and API checks; no SWAT+ executable needed."""

from datetime import date
import hashlib
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.schemas.playback import Evidence, VariableState
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_builder import _weather, simplified_frames, swat_frames
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantMappingError
from app.services.swat_plus_parser import SwatOutputParser, _date_from_row
from scripts.backfill_playback import backfill
from scientific_core import MultiscaleSimulationOrchestrator, RunConfig


def _weather_workspace(root: Path, *, temperature_days=(59, 60, 61), duplicate=False):
    (root / "weather-sta.cli").write_text("stations\nheader\na null a.pcp a.tmp null null null null null\n")
    (root / "a.pcp").write_text("a\nb\nc\n2020 59 1\n2020 60 2\n2020 61 3\n")
    rows = "".join(f"2020 {day} 20 10\n" for day in temperature_days)
    if duplicate:
        rows += "2020 60 20 10\n"
    (root / "a.tmp").write_text("a\nb\nc\n" + rows)


def test_weather_dates_leap_day_missing_and_duplicate(tmp_path):
    _weather_workspace(tmp_path)
    rows, meta = SwatClimateForcingReader(tmp_path).for_period(date(2020, 2, 28), date(2020, 3, 1), require_fspm=False)
    assert [row["date"] for row in rows] == ["2020-02-28", "2020-02-29", "2020-03-01"]
    assert [row["precip_mm"] for row in rows] == [1, 2, 3]
    assert rows[0]["solar_rad_mj"] is None
    assert meta["station_aggregation"].startswith("equal_station_mean")
    _weather_workspace(tmp_path, temperature_days=(59, 61))
    with pytest.raises(SwatPlantMappingError, match="2020-02-29"):
        SwatClimateForcingReader(tmp_path).for_period(date(2020, 2, 28), date(2020, 3, 1), require_fspm=False)
    _weather_workspace(tmp_path, duplicate=True)
    with pytest.raises(SwatPlantMappingError, match="Duplicate weather date"):
        SwatClimateForcingReader(tmp_path).for_period(date(2020, 2, 28), date(2020, 3, 1), require_fspm=False)
    (tmp_path / "a.tmp").write_text("a\nb\nc\n2019 366 20 10\n")
    with pytest.raises(SwatPlantMappingError, match="Invalid day of year"):
        SwatClimateForcingReader(tmp_path).for_period(date(2020, 2, 28), date(2020, 3, 1), require_fspm=False)


def test_existing_normalized_forcing_defaults_are_declared_as_assumptions():
    weather = _weather({"precip_mm": 1., "solar_rad_mj": 18.5,
                        "assumed_weather_variables": ["solar_rad_mj"]},
                       resolution="DAILY", source="normalized fixture", evidence=Evidence.DERIVED)
    assert weather["solar_radiation_mj_m2"].evidence == Evidence.ASSUMED
    assert weather["solar_radiation_mj_m2"].value == 18.5
    assert weather["precipitation_mm"].evidence == Evidence.DERIVED


def _swat_records():
    return [{"period": "2020-02-28", "runoff_mm": 1.0, "evapotranspiration_mm": 2.0,
             "soil_water_mm": 150.0, "percolation_mm": 0.4, "streamflow_m3s": 3.0},
            {"period": "2020-03-01", "runoff_mm": 0.0, "evapotranspiration_mm": 1.5,
             "soil_water_mm": 148.0, "percolation_mm": 0.2, "streamflow_m3s": 2.0}]


def test_swat_baseline_missing_day_and_units_are_explicit():
    forcing = [{"date": d, "temp_c": 15.0, "precip_mm": 2.0, "solar_rad_mj": None,
                "rh_percent": None, "co2_ppm": None} for d in ("2020-02-28", "2020-02-29", "2020-03-01")]
    frames = list(swat_frames(simulation_id="run-1", watershed_id="basin", run_type="SWAT_STANDARD_BASELINE",
                              resolution="DAILY", records=_swat_records(),
                              hru_results=[{"period": "2020-02-28", "hru_unit": "17", "soil_water_mm": 70.0}],
                              forcing=forcing, forcing_source="SWAT station basin mean",
                              start_date=date(2020, 2, 28), end_date=date(2020, 3, 1)))
    assert [item.date.isoformat() for item in frames] == ["2020-02-28", "2020-02-29", "2020-03-01"]
    assert frames[1].hydrology["streamflow_m3s"].value is None
    assert frames[1].hydrology["streamflow_m3s"].evidence == Evidence.NOT_AVAILABLE
    assert all(item.crop is None and item.field == {} and item.plant_samples == [] for item in frames)
    assert frames[0].hydrology["soil_water_mm"].unit == "mm"
    assert "soil_moisture_vol_percent" not in frames[0].hydrology
    assert frames[0].hru_results[0].hru_id == "17"
    assert frames[0].hru_results[0].polygon_id is None
    assert frames[0].weather["precipitation_mm"].evidence == Evidence.DERIVED
    assert frames[0].weather["precipitation_mm"].value == 2.0
    with pytest.raises(ValueError, match="Duplicate SWAT"):
        list(swat_frames(simulation_id="run-1", watershed_id="basin", run_type="SWAT_STANDARD_BASELINE",
                         resolution="DAILY", records=_swat_records() * 2, hru_results=[], forcing=None,
                         forcing_source="missing"))
    with pytest.raises(ValueError, match="outside the requested interval"):
        list(swat_frames(simulation_id="run-1", watershed_id="basin", run_type="SWAT_STANDARD_BASELINE",
                         resolution="DAILY", records=_swat_records(), hru_results=[], forcing=forcing,
                         forcing_source="missing", start_date=date(2020, 2, 29), end_date=date(2020, 3, 1)))


@pytest.mark.parametrize("resolution,periods", [("MONTHLY", ["2020-02-01", "2020-03-01"]),
                                                 ("ANNUAL", ["2020-01-01"])])
def test_effective_monthly_and_annual_frequency(resolution, periods):
    forcing = [{"date": "2020-02-29", "temp_c": 10.0, "precip_mm": 4.0},
               {"date": "2020-03-01", "temp_c": 20.0, "precip_mm": 6.0}]
    records = [{"period": period, "runoff_mm": 1.0} for period in periods]
    frames = list(swat_frames(simulation_id="run-2", watershed_id="basin", run_type="SWAT_STANDARD_BASELINE",
                              resolution=resolution, records=records, hru_results=[], forcing=forcing,
                              forcing_source="basin mean", start_date=date(2020, 2, 29), end_date=date(2020, 3, 1)))
    assert [item.date.isoformat() for item in frames] == periods
    assert all(item.resolution == resolution for item in frames)
    assert sum(item.weather["precipitation_mm"].value for item in frames) == 10.0
    assert frames[0].weather["precipitation_mm"].unit == "mm/period"


def test_swat_parser_recognizes_year_only_as_annual_period():
    assert _date_from_row({"yr": 0}, ["2020"]) == "2020-01-01"


def test_channel_morphology_file_does_not_duplicate_channel_flow(tmp_path):
    (tmp_path / "channel_sd_day.txt").write_text("flow\n")
    (tmp_path / "channel_sdmorph_day.txt").write_text("morphology\n")
    assert [path.name for path in SwatOutputParser("DAILY")._files(tmp_path, ("channel_sd",))] == ["channel_sd_day.txt"]


def test_observed_daily_streamflow_is_aggregated_by_actual_month():
    frames = list(swat_frames(simulation_id="obs-run", watershed_id="basin", run_type="SWAT_STANDARD_BASELINE",
                              resolution="MONTHLY", records=[{"period": "2020-02-01", "streamflow_m3s": 8.}],
                              hru_results=[], forcing=None, forcing_source="unavailable",
                              observations={"2020-02-28": 2., "2020-02-29": 4.}, observation_source="USGS fixture",
                              start_date=date(2020, 2, 28), end_date=date(2020, 2, 29)))
    observed = frames[0].hydrology["observed_streamflow_m3s"]
    assert observed.value == 3.0 and observed.evidence == Evidence.OBSERVED
    assert "2 available observed days" in observed.limitation


def test_crop_window_boundaries_and_assumed_moisture():
    forcing = [{"date": f"2020-01-0{i}", "temp_c": 18., "precip_mm": 0.} for i in (1, 2, 3)]
    crop = {"active": True, "crop": "maize", "season_id": "2020-01-02", "window_status": "APPROXIMATE_PLANTING_WINDOW",
            "source": "SWAT auto-management PHU window approximation"}
    days = {"2020-01-01": {"crop": {"active": False, "source": crop["source"]}},
            "2020-01-02": {"crop": crop, "field": {"mean_LAI": 0.3, "soil_moisture_vol": 24.,
                                                        "soil_moisture_source": "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"}},
            "2020-01-03": {"crop": {"active": False, "source": crop["source"]}}}
    frames = list(swat_frames(simulation_id="run-3", watershed_id="basin", run_type="SWAT_MULTISCALE_COUPLED",
                              resolution="DAILY", records=[{"period": row["date"]} for row in forcing],
                              hru_results=[], forcing=forcing, forcing_source="basin mean", fspm_days=days,
                              start_date=date(2020, 1, 1), end_date=date(2020, 1, 3)))
    assert [item.crop.active for item in frames] == [False, True, False]
    assert [item.availability["field"] for item in frames] == ["NOT_AVAILABLE", "AVAILABLE", "NOT_AVAILABLE"]
    moisture = frames[1].field["soil_moisture_vol_percent"]
    assert moisture.value == 24.0 and moisture.unit == "volumetric percent" and moisture.evidence == Evidence.ASSUMED
    assert "SWAT+" in moisture.limitation


def test_seeded_daily_fspm_field_trajectory_and_date_alignment(tmp_path):
    config = RunConfig(run_id="test", seed=7, duration_days=3, watershed_area_km2=10,
                       start_date=date(2020, 2, 28), end_date=date(2020, 3, 1))
    core = MultiscaleSimulationOrchestrator()
    first, second = core.execute(config, plant_count=8), core.execute(config, plant_count=8)
    assert first.playback_daily == second.playback_daily
    frames = list(simplified_frames(simulation_id="run-4", watershed_id="basin", rows=first.results,
                                    daily_fields=first.playback_daily, climate_source="SYNTHETIC"))
    assert [item.date.isoformat() for item in frames] == ["2020-02-28", "2020-02-29", "2020-03-01"]
    assert frames[0].field["lai"].value == first.playback_daily[0]["field"]["mean_LAI"]
    assert frames[0].field["soil_moisture_vol_percent"].unit == "volumetric percent"
    assert frames[0].hydrology["soil_water_mm"].unit == "mm"
    assert frames[0].plant_samples[0].plant_id == frames[1].plant_samples[0].plant_id
    assert frames[0].plant_samples[0].variables["lai"].value != frames[0].field["lai"].value
    store = PlaybackArtifactStore(tmp_path / "playback")
    manifest = store.write("run-4", frames, provenance={"seed": 7})
    total, page = store.page("run-4", manifest, start=date(2020, 2, 29), end=date(2020, 3, 1), limit=1)
    assert total == 2 and [item.date.isoformat() for item in page] == ["2020-02-29"]
    assert store.page("run-4", manifest, start=date(2020, 2, 29), end=date(2020, 3, 1), offset=1, limit=1)[1][0].date.isoformat() == "2020-03-01"
    assert manifest["sha256"] == hashlib.sha256((tmp_path / "playback" / "run-4.sqlite").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="do not align"):
        list(simplified_frames(simulation_id="run-4", watershed_id="basin", rows=first.results,
                               daily_fields=tuple(reversed(first.playback_daily)), climate_source="SYNTHETIC"))
    with pytest.raises(ValueError, match="finite"):
        VariableState(value=float("nan"), unit="mm", evidence=Evidence.DERIVED, source="test", availability="AVAILABLE")


@pytest.mark.asyncio
async def test_playback_api_auth_owner_and_pagination(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "DATA_ARTIFACT_ROOT", str(tmp_path))
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "investigador@digitaltwin.org"))
        watershed = await db.scalar(select(Watershed).limit(1))
        scenario = await db.scalar(select(ClimateScenario).limit(1))
        run = SimulationRun(user_id=owner.id, watershed_id=watershed.id, scenario_id=scenario.id,
                            name="Playback fixture", status="COMPLETED", duration_days=2,
                            start_date=date(2020, 1, 1), end_date=date(2020, 1, 2), seed=7)
        db.add(run)
        await db.flush()
        manifest = PlaybackArtifactStore().write(run.id, swat_frames(
            simulation_id=run.id, watershed_id=watershed.code, run_type="SWAT_STANDARD_BASELINE",
            resolution="DAILY", records=[{"period": "2020-01-01", "runoff_mm": 1.},
                                         {"period": "2020-01-02", "runoff_mm": 2.}], hru_results=[],
            forcing=None, forcing_source="unavailable", start_date=date(2020, 1, 1), end_date=date(2020, 1, 2)),
            provenance={"fixture": True})
        run.provenance = {"playback": manifest}
        await db.commit()
        run_id = run.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        path = f"/api/v1/simulations/{run_id}/playback"
        assert (await client.get(path)).status_code == 401
        owner_login = await client.post("/api/v1/auth/login", json={"email": "investigador@digitaltwin.org", "password": "Investiga123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
        response = await client.get(path, params={"offset": 1, "limit": 1}, headers=owner_headers)
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 2
        assert response.json()["records"][0]["date"] == "2020-01-02"
        assert response.json()["records"][0]["field"] == {}
        assert response.json()["variables"]["hydrology.runoff_mm"]["unit"] == "mm/day"
        assert (await client.get(path, params={"date": "2020-01-01"}, headers=owner_headers)).json()["total"] == 1
        assert (await client.get(path, params={"start": "2020-01-02", "end": "2020-01-01"}, headers=owner_headers)).status_code == 422
        outsider = await client.post("/api/v1/auth/login", json={"email": "operador@digitaltwin.org", "password": "Operador123!"})
        outsider_headers = {"Authorization": f"Bearer {outsider.json()['access_token']}"}
        assert (await client.get(path, headers=outsider_headers)).status_code == 404
        assert (await client.get(f"/api/v1/simulations/{run_id}", headers=owner_headers)).status_code == 200
        for run_status in ("PENDING", "RUNNING", "FAILED"):
            async with AsyncSessionLocal() as db:
                run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
                run.status = run_status
                await db.commit()
            unavailable = (await client.get(path, headers=owner_headers)).json()
            assert unavailable["simulation_status"] == run_status
            assert unavailable["artifact_status"] == "NOT_AVAILABLE"
    async with AsyncSessionLocal() as db:
        run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
        await db.delete(run)
        await db.commit()


@pytest.mark.asyncio
async def test_monthly_swat_can_expose_daily_fspm_without_daily_hydrology(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "DATA_ARTIFACT_ROOT", str(tmp_path))
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "investigador@digitaltwin.org"))
        watershed = await db.scalar(select(Watershed).limit(1))
        scenario = await db.scalar(select(ClimateScenario).limit(1))
        run = SimulationRun(user_id=owner.id, watershed_id=watershed.id, scenario_id=scenario.id,
                            name="Dual frequency fixture", status="COMPLETED", duration_days=2,
                            start_date=date(2020, 2, 28), end_date=date(2020, 2, 29), seed=7)
        db.add(run)
        await db.flush()
        forcing = [{"date": day, "temp_c": 15., "precip_mm": 1.} for day in ("2020-02-28", "2020-02-29")]
        monthly = PlaybackArtifactStore().write(run.id, swat_frames(
            simulation_id=run.id, watershed_id=watershed.code, run_type="SWAT_MULTISCALE_COUPLED",
            resolution="MONTHLY", records=[{"period": "2020-02-01", "runoff_mm": 5.}], hru_results=[],
            forcing=forcing, forcing_source="fixture", start_date=run.start_date, end_date=run.end_date),
            provenance={"fixture": True})
        daily_store = PlaybackArtifactStore(tmp_path / "playback" / "v1" / "fspm-daily")
        daily = daily_store.write(run.id, swat_frames(
            simulation_id=run.id, watershed_id=watershed.code, run_type="SWAT_MULTISCALE_COUPLED",
            resolution="DAILY", records=[], hru_results=[], forcing=forcing, forcing_source="fixture",
            fspm_days={"2020-02-28": {"crop": {"active": True, "crop": "maize", "source": "fixture"},
                                           "field": {"mean_LAI": 0.4, "soil_moisture_vol": 24.,
                                                     "soil_moisture_source": "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"}},
                       "2020-02-29": {"crop": {"active": False, "source": "fixture"}}},
            start_date=run.start_date, end_date=run.end_date), provenance={"fixture": True})
        run.provenance = {"playback": monthly, "playback_daily_fspm": daily}
        await db.commit()
        run_id = run.id
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={"email": "investigador@digitaltwin.org", "password": "Investiga123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        path = f"/api/v1/simulations/{run_id}/playback"
        monthly_response = (await client.get(path, headers=headers)).json()
        assert monthly_response["resolution"] == "MONTHLY"
        assert monthly_response["available_resolutions"] == ["MONTHLY", "DAILY"]
        daily_response = (await client.get(path, params={"resolution": "DAILY"}, headers=headers)).json()
        assert daily_response["total"] == 2
        assert daily_response["records"][0]["field"]["lai"]["value"] == 0.4
        assert daily_response["records"][0]["hydrology"]["runoff_mm"]["value"] is None
        assert daily_response["records"][1]["crop"]["active"] is False
        assert (await client.get(path, params={"resolution": "ANNUAL"}, headers=headers)).status_code == 422
    async with AsyncSessionLocal() as db:
        run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
        await db.delete(run)
        await db.commit()


def test_historical_v2_report_is_not_touched_by_playback_artifacts(tmp_path):
    report = Path(__file__).parents[2] / "research_domain" / "final_report_v2.json"
    before = hashlib.sha256(report.read_bytes()).hexdigest()
    frames = swat_frames(simulation_id="history-fixture", watershed_id="fixture", run_type="SWAT_STANDARD_BASELINE",
                         resolution="DAILY", records=[{"period": "2020-01-01"}], hru_results=[],
                         forcing=None, forcing_source="unavailable")
    PlaybackArtifactStore(tmp_path).write("history-fixture", frames, provenance={"fixture": True})
    assert hashlib.sha256(report.read_bytes()).hexdigest() == before


@pytest.mark.asyncio
async def test_backfill_uses_persisted_baseline_without_fspm_or_swat_execution(tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "DATA_ARTIFACT_ROOT", str(tmp_path))
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "investigador@digitaltwin.org"))
        watershed = await db.scalar(select(Watershed).limit(1))
        scenario = await db.scalar(select(ClimateScenario).limit(1))
        run = SimulationRun(user_id=owner.id, watershed_id=watershed.id, scenario_id=scenario.id,
                            name="Backfill fixture", status="COMPLETED", duration_days=1,
                            start_date=date(2020, 1, 1), end_date=date(2020, 1, 1), seed=5,
                            provenance={"evidence_type": "REAL_SWAT_PLUS", "workspace": str(tmp_path / "absent")},
                            effective_config={"output_frequency": "DAILY"},
                            monthly_outputs=[{"period": "2020-01-01", "soil_water_mm": 100.}],
                            hru_aggregates={"results": []})
        db.add(run)
        await db.commit()
        run_id = run.id
    manifest = await backfill(run_id)
    assert manifest["record_count"] == 1
    assert manifest["provenance"]["forcing"]["status"] == "NOT_AVAILABLE"
    _, records = PlaybackArtifactStore().page(run_id, manifest)
    assert records[0].field == {} and records[0].crop is None
    assert records[0].weather["precipitation_mm"].value is None
    assert records[0].hydrology["soil_water_mm"].value == 100.
    async with AsyncSessionLocal() as db:
        run = await db.scalar(select(SimulationRun).where(SimulationRun.id == run_id))
        await db.delete(run)
        await db.commit()

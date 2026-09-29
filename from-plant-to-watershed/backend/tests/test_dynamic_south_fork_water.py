"""Profile water conversion and dated multiscale playback boundaries."""

from datetime import date
import gzip
import hashlib

import pytest

from app.schemas.playback import Evidence, PlaybackRecord
from app.services.playback_artifact import PlaybackArtifactStore
from app.services.playback_builder import swat_frames
from app.services.swat_soil_water import SoilLayer, SoilProfile, hru_water_state, read_hru_soils


def test_profile_storage_uses_soil_thickness_and_root_zone_thresholds(tmp_path):
    (tmp_path / "soils.sol").write_text(
        "soils\nname nly hyd_grp dp_tot anion_excl perc_crk texture\n"
        "s1 2 B 1000 .5 0 null\n"
        "300 1.3 .10 10 1 30 40 30 0 0 0 0 0 7\n"
        "1000 1.4 .15 10 1 25 40 35 0 0 0 0 0 7\n"
    )
    (tmp_path / "hru-data.hru").write_text("hru\nid name soil\n1 a s1\n")
    profile = read_hru_soils(tmp_path)[1]
    wilting = hru_water_state(profile, 0, .2)
    field_capacity = hru_water_state(profile, profile.field_capacity_storage_mm, .2)
    dry = hru_water_state(profile, 100, .8)
    assert profile.field_capacity_storage_mm == pytest.approx(135)
    assert wilting["estimated_soil_moisture_vol_percent"] == pytest.approx(wilting["wilting_point_vol_percent"])
    assert wilting["estimated_plant_available_fraction"] == 0
    assert field_capacity["estimated_soil_moisture_vol_percent"] == pytest.approx(field_capacity["field_capacity_vol_percent"])
    assert field_capacity["estimated_root_zone_water_mm"] == pytest.approx(51.2)
    assert field_capacity["estimated_root_zone_depth_mm"] == 200
    assert field_capacity["estimated_plant_available_fraction"] == 1
    assert dry["estimated_plant_available_fraction"] < 1
    assert field_capacity["wilting_point_vol_percent"] == pytest.approx(15.6)
    assert dry["field_capacity_vol_percent"] != field_capacity["field_capacity_vol_percent"]


def test_soil_initialization_matches_swat_porosity_fallback(tmp_path):
    (tmp_path / "soils.sol").write_text(
        "soils\nname nly hyd_grp dp_tot anion_excl perc_crk texture\n"
        "s1 1 B 1000 .5 0 null\n"
        "1000 1.7 .50 10 1 20 40 40 0 0 0 0 0 7\n"
    )
    (tmp_path / "hru-data.hru").write_text("hru\nid name soil\n1 a s1\n")
    profile = read_hru_soils(tmp_path)[1]
    porosity = 1 - 1.7 / 2.65
    assert profile.layers[0].wilting_fraction == pytest.approx(porosity * .25)
    assert profile.layers[0].available_fraction == pytest.approx(porosity * .50)
    assert hru_water_state(profile, profile.field_capacity_storage_mm, 1)["field_capacity_vol_percent"] == pytest.approx(porosity * 75)


def test_daily_playback_keeps_hru_crop_and_channel_units():
    profile = SoilProfile("s1", (SoilLayer(1000, .12, .18, .45),))
    rows = list(swat_frames(
        simulation_id="dynamic-2019", watershed_id="05451210", run_type="SWAT_MULTISCALE_COUPLED",
        resolution="DAILY", records=[{"period": "2019-05-14", "streamflow_m3s": 2},
                                     {"period": "2019-05-15", "streamflow_m3s": 3}],
        hru_results=[{"period": day, "hru_unit": 7, "soil_water_average_mm": water}
                     for day, water in (("2019-05-14", 200), ("2019-05-15", 180))],
        channel_results=[{"period": day, "channel_unit": 2, "channel_gis_id": 153,
                          "streamflow_m3s": flow, "channel_water_storage_m3": 1000}
                         for day, flow in (("2019-05-14", 2), ("2019-05-15", 3))],
        soil_profiles={7: profile}, hru_gis_ids={7: "107"},
        hru_calendar={7: {"calendar_id": "corn-1", "planting_date": "2019-05-15", "harvest_date": "2019-08-27"}},
        forcing=None, forcing_source="unavailable",
        fspm_days={"2019-05-14": {"crop": {"active": False, "source": "calendar"}},
                   "2019-05-15": {"crop": {"active": True, "crop": "maize", "source": "calendar"}}},
        start_date=date(2019, 5, 14), end_date=date(2019, 5, 15),
    ))
    assert rows[0].hru_results[0].crop.active is False
    assert rows[1].hru_results[0].crop.active is True
    assert rows[1].hru_results[0].gis_id == "107"
    assert rows[1].hru_results[0].variables["estimated_soil_moisture_vol_percent"].value == pytest.approx(30)
    assert rows[1].hru_results[0].variables["estimated_soil_moisture_vol_percent"].evidence == Evidence.DERIVED
    assert rows[1].channel_results[0].gis_id == "153"
    assert rows[1].channel_results[0].variables["streamflow_m3s"].unit == "m3/s"
    assert "river_depth_m" not in rows[1].channel_results[0].variables


def test_playback_sidecar_recovers_from_checked_archive(tmp_path):
    store = PlaybackArtifactStore(tmp_path / "data/playback/v1")
    record = PlaybackRecord(simulation_id="archive-run", date=date(2019, 1, 1),
                            resolution="DAILY", run_type="SWAT_MULTISCALE_COUPLED",
                            watershed_id="05451210", spatial_support="WATERSHED_OUTLET_AND_BASIN")
    manifest = store.write("archive-run", [record], provenance={})
    sidecar = store.root / manifest["artifact_file"]
    archive = tmp_path / "data/phase1-south-fork-2019/results/archive-run/playback.sqlite.gz"
    archive.parent.mkdir(parents=True)
    with sidecar.open("rb") as source, gzip.open(archive, "wb") as target:
        target.write(source.read())
    manifest.update(archive_file=archive.name, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    sidecar.unlink()
    count, restored = store.page("archive-run", manifest, on=date(2019, 1, 1))
    assert count == 1 and restored[0].date == date(2019, 1, 1)
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == manifest["sha256"]

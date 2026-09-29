"""Phase 1 input integrity, executed crop calendars and dated scale contracts."""

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from app.schemas.playback import Evidence
from app.services.playback_builder import swat_frames
from app.services.executed_calendar_fspm import _combine_daily_fields
from app.services.swat_executed_calendar import CropCalendarGroup, SwatExecutedCropCalendar
from app.services.swat_input_compatibility import SwatInputCompatibility, SwatInputCompatibilityError
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from scripts.run_phase1_south_fork_2019 import (
    _engine_source_fingerprint,
    _period_rows,
    _variable_catalog,
    _write_csv,
)


def test_result_csv_writer_uses_lf_line_endings(tmp_path: Path):
    output = tmp_path / "daily.csv"

    metadata = _write_csv(output, [{"date": "2019-01-01", "rain_mm": 1.25}])

    assert output.read_bytes() == b"date,rain_mm\n2019-01-01,1.25\n"
    assert metadata["row_count"] == 1
    assert len(metadata["sha256"]) == 64


def _integer_input_project(root: Path) -> Path:
    root.mkdir()
    (root / "plants.plt").write_text(
        "plants.plt\nname days_mat bm_e yrs_mat description\n"
        "corn 120.00000 35.00000 1.00000 corn\n",
        encoding="utf-8",
    )
    (root / "plant.ini").write_text(
        "plant.ini\npcom_name plt_cnt rot_yr_ini plt_name lc_status lai_init bm_init phu_init plnt_pop yrs_init rsd_init\n"
        "corn_comm 2.00000 1.00000 corn y 0 0 0 0 1 0\n"
        "corn y 0 0 0 0 1 0\nsoyb y 0 0 0 0 1 0\n",
        encoding="utf-8",
    )
    (root / "management.sch").write_text(
        "management.sch\nname numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 op_data3\n"
        "corn_rot 1.00000 1.00000\npl_hv_summer1_corn corn\nplnt 5.00000 15.00000 0 corn null 0\n",
        encoding="utf-8",
    )
    (root / "time.sim").write_text("time.sim\nheader\n1.00000 2019.00000 365.00000 2019.00000 0.00000\n", encoding="utf-8")
    (root / "print.prt").write_text("print.prt\nheader\n0.00000 1.00000 2019.00000 365.00000 2019.00000 1.00000\n", encoding="utf-8")
    return root


def test_swat_integer_format_normalizes_only_an_isolated_copy_and_logs_each_repair(tmp_path: Path):
    source = _integer_input_project(tmp_path / "source")
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    for name in ("plants.plt", "plant.ini", "management.sch", "time.sim", "print.prt"):
        (isolated / name).write_bytes((source / name).read_bytes())
    source_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                     for name in ("plants.plt", "plant.ini", "management.sch", "time.sim", "print.prt")}

    result = SwatInputCompatibility.normalize_copy(isolated)

    assert result["status"] == "VALIDATED_WITH_FORMAT_NORMALIZATION"
    assert result["scope"] == "copied_run_workspace_only"
    assert result["numeric_values_changed"] is False
    assert result["scientific_parameters_changed_by_compatibility_layer"] is False
    assert set(result["corrections_by_file"]) == {"plants.plt", "plant.ini", "management.sch", "time.sim", "print.prt"}
    assert {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in source_hashes} == source_hashes
    assert (isolated / "plants.plt").read_text().splitlines()[2].split() == ["corn", "120", "35.00000", "1", "corn"]
    assert (isolated / "management.sch").read_text().splitlines()[2].split() == ["corn_rot", "1", "1"]
    assert (isolated / "management.sch").read_text().splitlines()[4].split()[:3] == ["plnt", "5", "15"]
    log_path = isolated / "swat_input_compatibility.json"
    logged = json.loads(log_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(log_path.read_bytes()).hexdigest() == result["log_sha256"]
    assert sum(len(rows) for rows in logged["corrections_by_file"].values()) > 0
    assert SwatInputCompatibility.inspect(isolated)["correction_count"] == 0


def test_swat_integer_format_rejects_nonintegral_fields_without_changing_any_bytes(tmp_path: Path):
    project = _integer_input_project(tmp_path / "bad")
    plant_file = project / "plants.plt"
    plant_file.write_text(plant_file.read_text().replace("120.00000", "120.50000"), encoding="utf-8")
    original = plant_file.read_bytes()
    with pytest.raises(SwatInputCompatibilityError, match="non-integral"):
        SwatInputCompatibility.normalize_copy(project)
    assert plant_file.read_bytes() == original
    assert not (project / "swat_input_compatibility.json").exists()


def test_executed_calendar_retains_distinct_hru_dates_and_area_weights():
    events = [
        {"hru_id": 1, "crop": "corn", "date": "2019-05-15", "operation": "PLANT"},
        {"hru_id": 1, "crop": "corn", "date": "2019-08-27", "operation": "HARV/KILL"},
        {"hru_id": 2, "crop": "corn", "date": "2019-05-16", "operation": "PLANT"},
        {"hru_id": 2, "crop": "corn", "date": "2019-08-29", "operation": "HARV/KILL"},
        {"hru_id": 3, "crop": "corn", "date": "2019-05-15", "operation": "PLANT"},
        {"hru_id": 3, "crop": "corn", "date": "2019-08-27", "operation": "HARV/KILL"},
        {"hru_id": 4, "crop": "agrl", "date": "2019-05-15", "operation": "PLANT"},
    ]
    calendar = SwatExecutedCropCalendar.from_events(
        events, crop="corn", start_date=date(2019, 1, 1), end_date=date(2019, 12, 31),
        hru_weights={1: 100., 2: 200., 3: 300.},
    )
    assert len(calendar.groups) == 2
    assert calendar.hru_calendar == {1: calendar.groups[0].calendar_id,
                                     3: calendar.groups[0].calendar_id,
                                     2: calendar.groups[1].calendar_id}
    assert calendar.groups[0].planting_date == "2019-05-15"
    assert calendar.groups[0].harvest_date == "2019-08-27"
    assert calendar.groups[0].hru_ids == (1, 3)
    assert calendar.groups[0].spatial_weight == 400.
    assert calendar.groups[1].planting_date == "2019-05-16"
    assert calendar.groups[1].spatial_weight == 200.
    assert calendar.as_dict()["status"] == "EXECUTED_SWAT_MANAGEMENT_EVENTS"


def test_dated_fspm_field_retains_static_traits_required_by_swat_mapper():
    group = CropCalendarGroup("calendar-1", "corn", "2019-05-15", "2019-08-27", (1,), 100.0)
    field = {
        "n_plants": 1000, "mean_LAI": 2.1, "canopy_cover": .7, "plant_height_mean_m": 1.2,
        "root_depth_mean_m": .8, "mean_thermal_maturity_gdd": 1450.,
        "canopy_extinction_coefficient": .5, "biomass_energy_ratio_kg_ha_per_mj_m2": 40.,
        "units": {"mean_LAI": "m2/m2"},
    }
    combined = _combine_daily_fields((group,), {"calendar-1": {"field": field}})
    assert combined["canopy_extinction_coefficient"] == .5
    assert combined["biomass_energy_ratio_kg_ha_per_mj_m2"] == 40.
    assert combined["mean_thermal_maturity_gdd"] == 1450.


def test_exporter_uses_one_canonical_date_field_for_swat_rows():
    rows = _period_rows([
        {"period": "2019-01-01", "precip_mm": 2.0},
        {"period": "2019-01-02", "precip_mm": 0.0},
    ])
    assert rows == [
        {"date": "2019-01-01", "precip_mm": 2.0},
        {"date": "2019-01-02", "precip_mm": 0.0},
    ]


def test_variable_catalog_keeps_units_scales_sources_and_evidence_classes_explicit():
    catalog = _variable_catalog()
    assert catalog["soil_water_mm"]["unit"] == "mm"
    assert catalog["soil_water_mm"]["classification"] == "SIMULATED"
    assert catalog["channel_water_storage_m3"]["unit"] == "m3"
    assert catalog["channel_water_storage_m3"]["spatial_scale"] == "channel"
    assert catalog["channel_water_temp_c"]["date_field"] == "date"
    assert catalog["temp_c"]["classification"] == "SOURCE_UNVERIFIED"
    assert catalog["co2_ppm"]["classification"] == "ASSUMED"
    assert catalog["x_m"]["classification"] == "ASSUMED"
    assert catalog["water_stress"]["classification"] == "DERIVED"


def test_reproduction_manifest_fingerprints_the_engine_sources():
    fingerprint = _engine_source_fingerprint()
    assert fingerprint["sha256"]
    assert "backend/app/services/swat_plus_adapter.py" in fingerprint["files"]
    assert "backend/scientific_core/multiscale.py" in fingerprint["files"]
    assert all(len(value) == 64 for value in fingerprint["files"].values())


def _station_files(root: Path, station: str, precip: float, tmax: float, tmin: float, rh: float) -> None:
    for extension, value in (("pcp", f"2020 1 {precip}\n"),
                             ("tmp", f"2020 1 {tmax} {tmin}\n"),
                             ("slr", "2020 1 12\n"), ("hmd", f"2020 1 {rh}\n"),
                             ("wnd", "2020 1 2\n"), ("pet", "2020 1 3\n")):
        (root / f"{station}.{extension}").write_text(f"title\nheader\nunits\n{value}", encoding="utf-8")


def test_fspm_climate_uses_the_same_dated_hru_station_mix_and_units_as_swat(tmp_path: Path):
    (tmp_path / "weather-sta.cli").write_text(
        "weather stations\nname wgn pcp tmp slr hmd wnd pet atmo_dep\n"
        "sta null sta.pcp sta.tmp sta.slr sta.hmd sta.wnd sta.pet null\n"
        "stb null stb.pcp stb.tmp stb.slr stb.hmd stb.wnd stb.pet null\n",
        encoding="utf-8",
    )
    (tmp_path / "hru.con").write_text(
        "hru.con\nid name gis_id area lat lon elev hru wst cst ovfl rule out_tot\n"
        "1 hru01 1 100 42 0 0 1 sta 0 0 0 0\n"
        "2 hru02 2 300 42 0 0 2 stb 0 0 0 0\n",
        encoding="utf-8",
    )
    _station_files(tmp_path, "sta", 10, 30, 10, .5)
    _station_files(tmp_path, "stb", 2, 20, 0, .75)

    rows, provenance = SwatClimateForcingReader(tmp_path).for_hrus(
        date(2020, 1, 1), date(2020, 1, 1), [1, 2], crop_fraction_by_hru={1: .5, 2: 1.},
    )

    assert rows == [{
        "date": "2020-01-01", "temp_c": pytest.approx((20 * 50 + 10 * 300) / 350),
        "precip_mm": pytest.approx((10 * 50 + 2 * 300) / 350),
        "solar_rad_mj": pytest.approx(12), "rh_percent": pytest.approx((50 * 50 + 75 * 300) / 350),
        "wind_speed_ms": pytest.approx(2), "pet_mm": pytest.approx(3), "co2_ppm": 400.0,
    }]
    assert provenance["forcing_support"] == "selected_management_hrus"
    assert provenance["hru_station_source"] == "hru.con.wst"
    assert provenance["station_aggregation"] == "area_weighted_from_hru.con"
    assert provenance["hru_con_sha256"]


def test_playback_exposes_swat_hru_plant_variables_without_inventing_height_or_soil_percent():
    frame = next(iter(swat_frames(
        simulation_id="phase1", watershed_id="south-fork", run_type="SWAT_MULTISCALE_COUPLED",
        resolution="DAILY", records=[{"period": "2019-07-01", "precip_mm": 4., "runoff_mm": 1.,
                                       "soil_water_mm": 180., "streamflow_m3s": .25}],
        hru_results=[{"period": "2019-07-01", "hru_unit": "7", "precip_mm": 4., "soil_water_mm": 90.}],
        plant_results=[{"period": "2019-07-01", "hru_unit": "7", "lai_m2_m2": 5.2,
                        "biomass_kg_ha": 12000., "water_stress_factor": .1}],
        forcing=[{"date": "2019-07-01", "temp_c": 22., "precip_mm": 4., "solar_rad_mj": 18.,
                  "rh_percent": 65., "co2_ppm": 400.}], forcing_source="hru climate",
        fspm_days={"2019-07-01": {"crop": {"active": True, "crop": "maize",
                                                   "window_status": "EXECUTED_SWAT_MANAGEMENT_EVENTS",
                                                   "source": "mgt_out.txt"},
                                  "field": {"mean_LAI": 3.1, "mean_stress": .08,
                                            "plant_height_mean_m": 1.2,
                                            "root_depth_mean_m": .8,
                                            "soil_moisture_vol": 24.,
                                            "soil_moisture_source": "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"}}},
        start_date=date(2019, 7, 1), end_date=date(2019, 7, 1),
    )))
    hru = frame.hru_results[0]
    assert hru.variables["precipitation_mm"].value == 4.
    assert hru.variables["soil_water_mm"].value == 90.
    assert hru.variables["swat_lai_m2_m2"].value == 5.2
    assert hru.variables["swat_biomass_kg_ha"].unit == "kg/ha"
    assert "height" not in hru.variables
    assert "soil_moisture_vol_percent" not in hru.variables
    assert frame.field["height_m"].value == 1.2
    assert frame.field["water_stress"].value == .08
    assert frame.field["soil_moisture_vol_percent"].evidence == Evidence.ASSUMED
    assert frame.hydrology["soil_water_mm"].unit == "mm"
    assert frame.hydrology["precipitation_mm"].unit == "mm/day"

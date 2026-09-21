from datetime import date

from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader


def _workspace(path):
    (path / "hru-data.hru").write_text("hru\nheader\n1 hru01 x x soil corn_lum\n2 hru02 x x soil corn_lum\n", encoding="utf-8")
    (path / "landuse.lum").write_text("lum\nheader\ncorn_lum null corn_comm corn_rot\n", encoding="utf-8")
    (path / "plant.ini").write_text("ini\nheader\ncorn_comm 1 1\ncorn n 0\n", encoding="utf-8")
    (path / "management.sch").write_text("sch\nheader\ncorn_rot 0 1\npl_hv_summer1 corn\n", encoding="utf-8")
    (path / "lum.dtl").write_text("plant              crop\nharvest_kill              crop\n", encoding="utf-8")
    (path / "plants.plt").write_text("plt\nname lai_pot can_ht_max rt_dp_max\ncorn 6 2.5 2\n", encoding="utf-8")


def test_crop_chain_diagnostic_requires_complete_active_corn_path(tmp_path):
    _workspace(tmp_path)
    diagnostic = SwatCropChainDiagnostic.input_chain(tmp_path, [1, 2])
    assert diagnostic["status"] == "PASS"
    assert all(diagnostic["checks"].values())
    assert diagnostic["planting"]["status"] == "AUTO_MANAGEMENT_CONFIGURED"
    assert diagnostic["plant_growth"]["parameters"]["lai_pot"] == 6.0


def test_fspm_reader_uses_all_direct_swat_weather_stations(tmp_path):
    (tmp_path / "weather-sta.cli").write_text("sta\nheader\na null a.pcp a.tmp a.slr a.hmd null null null\nb null b.pcp b.tmp b.slr b.hmd null null null\n", encoding="utf-8")
    for name, rows in {
        "a.pcp": "2019 1 2\n", "b.pcp": "2019 1 4\n",
        "a.tmp": "2019 1 20 10\n", "b.tmp": "2019 1 24 14\n",
        "a.slr": "2019 1 10\n", "b.slr": "2019 1 14\n",
        "a.hmd": "2019 1 .5\n", "b.hmd": "2019 1 .7\n",
    }.items():
        (tmp_path / name).write_text(f"x\ny\nz\n{rows}", encoding="utf-8")
    rows, provenance = SwatClimateForcingReader(tmp_path).for_period(date(2019, 1, 1), date(2019, 1, 1))
    assert rows == [{"temp_c": 17.0, "precip_mm": 3.0, "solar_rad_mj": 12.0, "rh_percent": 60.0, "co2_ppm": 400.0}]
    assert provenance["station_count"] == 2


def test_auto_management_season_uses_phu_window_not_january_first(tmp_path):
    (tmp_path / "management.sch").write_text("sch\nheader\ncorn_rot 0 1\npl_hv_summer1 corn\n", encoding="utf-8")
    (tmp_path / "lum.dtl").write_text(
        "lum\nheader\n"
        "pl_hv_summer1 6 5 3\n"
        "phu_base0 hru 0 null - .15000 > - - - -\n"
        "phu_plant hru 0 phu_mat - 1.15000 - > - -\n"
        "soil_water hru 0 fc * 2.00000 < < - - -\n"
        "year_rot hru 0 null - 1.00000 - - - >\n"
        "jday hru 0 null - 350 = - - - -\n"
        "act_typ obj obj_num name option const\n"
        "name next 0\n", encoding="utf-8")
    (tmp_path / "plants.plt").write_text("plt\nname tmp_base\ncorn 8\n", encoding="utf-8")
    season = SwatCropChainDiagnostic.auto_management_season(tmp_path)
    windows = season.windows(date(2020, 1, 1), date(2020, 12, 31), [18.0] * 366, thermal_maturity_gdd=1450.0)
    assert windows[0]["start_date"] != "2020-01-01"
    assert windows[0]["status"] == "APPROXIMATE_PLANTING_WINDOW"
    provenance = season.provenance(windows)
    assert provenance["season_start_method"] == "SWAT_AUTO_MANAGEMENT_PHU_TRIGGER_APPROXIMATION"
    assert provenance["preplant_trigger_reset"] == "CALENDAR_YEAR_BOUNDARY_FOR_ANNUAL_PHU_ACCUMULATOR_ONLY_NOT_FSPM_SEASON_RESET"
    assert provenance["fspm_growth_temperature_base_c"] == 8.0
    assert provenance["fspm_growth_temperature_base_source"] == "plants.plt.tmp_base"
    assert set(provenance["dynamic_conditions_not_reproduced"]) >= {"phu_plant", "soil_water", "year_rot"}
    assert provenance["window_conditions_used"] == ["phu_base0", "jday"]
    assert provenance["confidence"] == "LIMITED"
    assert "no executed planting-event log" in provenance["limitation"]


def test_tmp_base_from_plants_plt_controls_fspm_growth_gdd(tmp_path):
    (tmp_path / "management.sch").write_text("sch\nheader\ncorn_rot 0 1\npl_hv_summer1 corn\n", encoding="utf-8")
    (tmp_path / "lum.dtl").write_text(
        "lum\nheader\npl_hv_summer1 2 1 1\n"
        "phu_base0 hru 0 null - .15000 > -\n"
        "jday hru 0 null - 350 = -\n"
        "act_typ obj obj_num name option const\nname next 0\n", encoding="utf-8")
    plants = tmp_path / "plants.plt"
    plants.write_text("plt\nname tmp_base\ncorn 8\n", encoding="utf-8")
    base_eight = SwatCropChainDiagnostic.auto_management_season(tmp_path)
    plants.write_text("plt\nname tmp_base\ncorn 10\n", encoding="utf-8")
    base_ten = SwatCropChainDiagnostic.auto_management_season(tmp_path)
    assert base_eight.fspm_growth_gdd_increment(18.0) == 10.0
    assert base_ten.fspm_growth_gdd_increment(18.0) == 8.0

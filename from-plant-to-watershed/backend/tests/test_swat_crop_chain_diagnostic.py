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

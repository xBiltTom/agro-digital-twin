import hashlib

from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from scripts.prepare_south_fork_cdl_experiment import prepare_configuration


def _source_project(path):
    path.mkdir()
    (path / "hru-data.hru").write_text(
        "hru-data.hru\nid name topo hydro soil lu_mgt init surf snow field\n"
        "1 hru01 top1 hyd1 soil agrl_lum null null null null\n"
        "2 hru02 top2 hyd2 soil agrl_lum null null null null\n", encoding="utf-8"
    )
    (path / "landuse.lum").write_text(
        "landuse.lum\nname cal_group plnt_com mgt\nagrl_lum null agrl_comm agrl_rot\n", encoding="utf-8"
    )
    (path / "plant.ini").write_text(
        "plant.ini\nheader\nagrl_comm 1 1\nagrl n 0\n", encoding="utf-8"
    )
    (path / "management.sch").write_text(
        "management.sch\nheader\nagrl_rot 0 1\npl_hv_summer1 agrl\n", encoding="utf-8"
    )
    (path / "lum.dtl").write_text(
        "lum.dtl\nheader\npl_hv_summer1 2 1 1\n"
        "phu_base0 hru 0 null - .15000 > -\njday hru 0 null - 350 = -\n"
        "act_typ obj obj_num name option const\nplant crop\nharvest_kill crop\n"
        "name generic\npl_hv_summer1_corn 2 1 1\n"
        "phu_base0 hru 0 null - .15000 > -\njday hru 0 null - 350 = -\n"
        "act_typ obj obj_num name option const\nplant plant_corn corn\nharvest_kill grain_harv corn\n", encoding="utf-8"
    )
    (path / "plants.plt").write_text(
        "plants.plt\nname tmp_base lai_pot frac_hu1 lai_max1 frac_hu2 lai_max2 hu_lai_decl can_ht_max rt_dp_max ext_co bm_e\n"
        "agrl 0 4 .15 .15 .5 .95 .8 1.5 1 .6 35\n"
        "corn 8 6 .15 .15 .5 .95 .8 2.5 2 .65 40\n", encoding="utf-8"
    )
    return path


def test_cdl_variant_is_atomic_and_changes_only_selected_hru_crop_chain(tmp_path):
    source = _source_project(tmp_path / "source-project")
    source_before = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in ("hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl", "plants.plt")
    }
    composition = [
        {"hru_id": 1, "cdl_year": 2019, "corn_fraction": .71, "soybean_fraction": .2, "coverage_quality": "VALID"},
        {"hru_id": 2, "cdl_year": 2019, "corn_fraction": .20, "soybean_fraction": .7, "coverage_quality": "VALID"},
    ]
    destination = tmp_path / "experiment-bundle"

    manifest = prepare_configuration(source, composition, destination)

    assert manifest["configuration_status"] == "PREPARED_AND_VALIDATED"
    assert manifest["selected_hru_ids"] == [1]
    assert manifest["changed_project_files"] == ["hru-data.hru", "landuse.lum", "management.sch", "plant.ini"]
    assert manifest["crop_chain_diagnostic"]["status"] == "PASS"
    assert manifest["auto_management"]["configured_crop"] == "corn"
    assert manifest["auto_management"]["decision_table"] == "pl_hv_summer1_corn"
    assert manifest["auto_management"]["season_windows"] is None
    assert manifest["auto_management"]["season_window_evaluation"] == "NOT_EVALUATED_BY_CONFIGURATION_PREPARER"
    assert manifest["active_management_operation"]["effective_decision_table"] == "pl_hv_summer1_corn"
    assert manifest["scientific_scope"]["not_claimed"][0] == "observed planting or harvest dates"
    assert SwatPlantParameterMapper._active_hrus(destination / "project", "corn") == ["hru01"]
    assert "corn_lum" in (destination / "project" / "hru-data.hru").read_text(encoding="utf-8")
    assert "agrl_lum" in (destination / "project" / "hru-data.hru").read_text(encoding="utf-8")
    assert source_before == {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in source_before
    }

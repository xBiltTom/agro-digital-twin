from pathlib import Path

import pytest

from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from scientific_core import PlantPopulation, PlantToFieldAggregator


FORCING = {"temp_c": 24.0, "solar_rad_mj": 18.0, "rh_percent": 65.0, "co2_ppm": 400.0, "gdd_c_day": 900.0}


def _field(seed=42):
    states = PlantPopulation(1000, seed).step(120, FORCING, .24)
    field = PlantToFieldAggregator.aggregate(states, .24)
    field["swat_lai_contract"] = {
        "lai_pot": field["mean_LAI"], "frac_hu1": .18, "lai_max1": .16,
        "frac_hu2": .48, "lai_max2": .86, "hu_lai_decl": .76,
    }
    return states, field


def _swat_workspace(path: Path):
    (path / "plants.plt").write_text(
        "plants.plt\nname lai_pot frac_hu1 lai_max1 frac_hu2 lai_max2 hu_lai_decl can_ht_max rt_dp_max ext_co bm_e description\ncorn 6 .15 .15 .5 .95 .8 2.5 2 .65 40 corn\n", encoding="utf-8"
    )
    (path / "hru-data.hru").write_text("hru-data.hru\nid name topo hydro soil lu_mgt init surf snow field\n2 hru0002 t h soil mntill_corn_lum init null null null\n", encoding="utf-8")
    (path / "landuse.lum").write_text("landuse.lum\nname cal_group plnt_com mgt\nmntill_corn_lum null corn_comm mgt_08\n", encoding="utf-8")
    (path / "management.sch").write_text("management.sch\nheader\n plnt 4 28 0 corn null 0\n", encoding="utf-8")


def test_maize_population_is_seed_reproducible_and_has_explicit_units():
    first, field = _field(8)
    second, _ = _field(8)
    third, _ = _field(9)
    assert len(first) == 1000
    assert first == second
    assert first != third
    assert all(plant.lai >= 0 and .05 <= plant.root_depth_m <= plant.root_depth_cm / 100 for plant in first)
    assert all(0 <= plant.stress <= 1 for plant in first)
    assert all(10 <= plant.radiation_use_efficiency_kg_ha_per_mj_m2 <= 90 for plant in first)
    assert all(.05 <= plant.canopy_extinction_coefficient <= 2 for plant in first)
    assert field["units"]["mean_LAI"] == "m2_leaf/m2_ground"
    assert field["units"]["biomass_energy_ratio_kg_ha_per_mj_m2"] == "kg/ha/(MJ/m2)"
    assert field["LAI_distribution"]["p10"] <= field["mean_LAI"] <= field["LAI_distribution"]["p90"]


def test_field_to_documented_swat_inputs_emits_a_complete_manifest(tmp_path):
    _swat_workspace(tmp_path)
    _, field = _field()
    manifest = SwatPlantParameterMapper("corn").apply(tmp_path, field)
    assert manifest["target_hrus"] == ["hru0002"]
    assert {row["swat_parameter"] for row in manifest["parameter_updates"]} == {"lai_pot", "frac_hu1", "lai_max1", "frac_hu2", "lai_max2", "hu_lai_decl", "can_ht_max", "rt_dp_max", "ext_co", "bm_e"}
    assert {row["status"] for row in manifest["parameter_updates"]} <= {"CHANGED", "UNCHANGED"}
    assert all(row["unit"] and row["justification"] for row in manifest["parameter_updates"])
    assert "corn 6 .15 .15 .5 .95 .8 2.5 2 .65 40 corn" not in (tmp_path / "plants.plt").read_text(encoding="utf-8")
    assert {entry["variable"] for entry in manifest["not_coupled"]} >= {"actual_ET_mm_day", "water_stress", "root_distribution"}


def test_seasonal_lai_contract_is_ordered_and_physically_bounded():
    states = PlantPopulation(1000, 8)
    trajectory = []
    for gdd in range(50, 1451, 50):
        trajectory.append(PlantToFieldAggregator.aggregate(states.step(gdd, {**FORCING, "gdd_c_day": float(gdd)}, .24), .24))
    contract = PlantToFieldAggregator.seasonal_lai_contract(trajectory)
    assert 0 < contract["frac_hu1"] < contract["frac_hu2"] < contract["hu_lai_decl"] <= 1
    assert 0 < contract["lai_max1"] < contract["lai_max2"] <= 1
    assert contract["lai_pot"] > 0

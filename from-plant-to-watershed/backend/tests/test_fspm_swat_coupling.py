from datetime import date, timedelta
from pathlib import Path

import pytest

from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from app.services.swat_crop_chain_diagnostic import SwatAutoManagementSeason
from scientific_core import PlantPopulation, PlantToFieldAggregator
from scientific_core.units import ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT


FORCING = {"temp_c": 24.0, "solar_rad_mj": 18.0, "rh_percent": 65.0, "co2_ppm": 400.0, "gdd_c_day": 900.0}


def _field(seed=42):
    states = PlantPopulation(1000, seed).step(120, FORCING, ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT)
    field = PlantToFieldAggregator.aggregate(states, ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT)
    field["soil_moisture_source"] = "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"
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
    for parameter in ("ext_co", "bm_e"):
        trait = field["coupling_parameter_provenance"][parameter]
        assert trait["assumption_status"] == "ASSUMED_PARAMETER_NOT_CALIBRATED"
        assert trait["calibrated"] is False
        assert trait["population_std"] > 0


def test_field_to_documented_swat_inputs_emits_a_complete_manifest(tmp_path):
    _swat_workspace(tmp_path)
    _, field = _field()
    manifest = SwatPlantParameterMapper("corn").apply(tmp_path, field)
    assert manifest["target_hrus"] == ["hru0002"]
    assert {row["swat_parameter"] for row in manifest["parameter_updates"]} == {"lai_pot", "frac_hu1", "lai_max1", "frac_hu2", "lai_max2", "hu_lai_decl", "can_ht_max", "rt_dp_max", "ext_co", "bm_e"}
    assert {row["status"] for row in manifest["parameter_updates"]} <= {"CHANGED", "UNCHANGED"}
    assert all(row["unit"] and row["justification"] for row in manifest["parameter_updates"])
    traits = {row["swat_parameter"]: row["source_parameter_provenance"] for row in manifest["parameter_updates"]}
    assert traits["ext_co"]["source_value"] == .5
    assert traits["bm_e"]["source_value"] == 40.0
    assert "corn 6 .15 .15 .5 .95 .8 2.5 2 .65 40 corn" not in (tmp_path / "plants.plt").read_text(encoding="utf-8")
    assert {entry["variable"] for entry in manifest["not_coupled"]} >= {"actual_ET_mm_day", "water_stress", "root_distribution"}
    assert manifest["soil_moisture_input"] == {
        "value": 24.0, "unit": "volumetric percent",
        "source": "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT", "swat_soil_water_feedback": "NOT_COUPLED",
    }


def test_seasonal_lai_contract_is_ordered_and_physically_bounded():
    states = PlantPopulation(1000, 8)
    trajectory = []
    for gdd in range(50, 1451, 50):
        trajectory.append(PlantToFieldAggregator.aggregate(states.step(gdd, {**FORCING, "gdd_c_day": float(gdd)}, ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT), ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT))
    contract = PlantToFieldAggregator.seasonal_lai_contract(trajectory)
    assert 0 < contract["frac_hu1"] < contract["frac_hu2"] < contract["hu_lai_decl"] <= 1
    assert 0 < contract["lai_max1"] < contract["lai_max2"] <= 1
    assert contract["lai_pot"] > 0


def test_multiyear_seasons_reset_all_computed_crop_state_without_replacing_population():
    season = SwatAutoManagementSeason(
        decision_table="pl_hv_summer1", management_schedule="mgt_corn",
        configured_crop="corn", growth_temperature_crop="corn",
        phu_base0_fraction=.55, harvest_day_of_year=300,
        crop_temperature_base_c=8.0,
    )
    start, end = date(2019, 1, 1), date(2020, 12, 31)
    temperature = 20.0
    windows = season.windows(start, end, [temperature] * ((end - start).days + 1),
                             thermal_maturity_gdd=1450.0)
    assert len(windows) == 2
    assert [window["status"] for window in windows] == ["APPROXIMATE_PLANTING_WINDOW"] * 2
    starts = [date.fromisoformat(window["start_date"]) for window in windows]
    assert starts[0].year == 2019 and starts[1].year == 2020

    active = {}
    for window in windows:
        first, last = date.fromisoformat(window["start_date"]), date.fromisoformat(window["end_date"])
        while first <= last:
            active[first] = window
            first += timedelta(days=1)

    population = PlantPopulation(120, seed=51, crop="maize")
    gdd = absorbed_par = 0.0
    snapshots = {}
    for day_index in range((end - start).days + 1):
        current = start + timedelta(days=day_index)
        window = active.get(current)
        if window is None:
            continue
        season_start = date.fromisoformat(window["start_date"])
        if current == season_start:
            gdd, absorbed_par = 0.0, 0.0
        gdd += season.fspm_growth_gdd_increment(temperature)
        forcing = {
            "temp_c": temperature, "solar_rad_mj": 18.0, "rh_percent": 65.0,
            "co2_ppm": 400.0, "gdd_c_day": gdd,
            "cumulative_absorbed_par_mj_m2": absorbed_par,
        }
        states = population.step(day_index + 1, forcing, ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT)
        field = PlantToFieldAggregator.aggregate(states, ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT)
        elapsed = (current - season_start).days
        if elapsed in {0, 45}:
            snapshots[(season_start.year, elapsed)] = (field, states)
        absorbed_par += forcing["solar_rad_mj"] * .48 * field["canopy_cover"]

    first_year, next_year = snapshots[(2019, 0)], snapshots[(2020, 0)]
    assert first_year == next_year
    first_field, first_states = first_year
    mature_field, mature_states = snapshots[(2019, 45)]
    assert first_field["mean_growing_degree_days_c_day"] == pytest.approx(12.0, rel=0.01)
    assert mature_field["mean_LAI"] > first_field["mean_LAI"]
    assert mature_field["plant_height_mean_m"] > first_field["plant_height_mean_m"]
    assert mature_field["root_depth_mean_m"] > first_field["root_depth_mean_m"]
    assert mature_field["biomass_g_plant"] > first_field["biomass_g_plant"]
    assert [(state.plant_id, state.x_m, state.y_m) for state in first_states] == [
        (state.plant_id, state.x_m, state.y_m) for state in mature_states
    ]
    # The crop calendar remains the configured PHU approximation, not a fixed planting date.
    assert season.provenance(windows)["season_start_method"] == "SWAT_AUTO_MANAGEMENT_PHU_TRIGGER_APPROXIMATION"


def test_representative_samples_are_deterministic_stable_and_spread_across_population():
    population = PlantPopulation(1000, seed=18)
    early = population.step(1, {**FORCING, "gdd_c_day": 80.0}, 24.0)
    later = population.step(2, {**FORCING, "gdd_c_day": 800.0}, 24.0)
    early_sample = population.representative_sample(early)
    later_sample = population.representative_sample(later)

    assert len(early_sample) == 10
    assert early_sample == population.representative_sample(early)
    assert [state.plant_id for state in early_sample] == [state.plant_id for state in later_sample]
    assert early_sample[0].plant_id == "maize-00001"
    assert early_sample[-1].plant_id == "maize-01000"
    assert len({state.y_m for state in early_sample}) > 5
    assert len(population.representative_sample(early, max_samples=1)) == 1
    with pytest.raises(ValueError, match="positive"):
        population.representative_sample(early, max_samples=0)

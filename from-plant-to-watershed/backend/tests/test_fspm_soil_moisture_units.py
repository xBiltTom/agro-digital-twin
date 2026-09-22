"""Small deterministic checks of the simplified crop water contract."""

import math

import pytest

from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from scientific_core import FieldToHRUCoupler, PlantPopulation, PlantToFieldAggregator
from scientific_core.plant import SimplifiedPlantModel
from scientific_core.units import (
    ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT,
    soil_moisture_fraction_to_vol_percent,
    validate_soil_moisture_vol_percent,
)


FORCING = {
    "temp_c": 25.0, "solar_rad_mj": 20.0, "rh_percent": 60.0,
    "co2_ppm": 415.0, "gdd_c_day": 900.0,
    "cumulative_absorbed_par_mj_m2": 60.0,
}


def test_fraction_conversion_is_explicit_and_bounded():
    assert ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT == 24.0
    assert soil_moisture_fraction_to_vol_percent(.24) == 24.0
    assert validate_soil_moisture_vol_percent(24) == 24.0
    for invalid in (-.01, 1.01, math.nan, math.inf):
        with pytest.raises(ValueError):
            soil_moisture_fraction_to_vol_percent(invalid)
    for invalid in (-1, 101, math.nan, -math.inf):
        with pytest.raises(ValueError):
            validate_soil_moisture_vol_percent(invalid)
    # An actual 0.24% is physically possible; only an explicit source unit
    # permits converting it. The percent API must never guess and multiply.
    assert validate_soil_moisture_vol_percent(.24) == .24


@pytest.mark.parametrize("moisture", [8.0, 15.0, 24.0, 32.0])
def test_plant_outputs_are_finite_and_bounded(moisture):
    model = SimplifiedPlantModel()
    result = model.compute_daily_plant_step(25.0, 20.0, 60.0, moisture)
    assert all(math.isfinite(value) for value in result.values())
    assert 0 <= result["actual_transpiration_mm"] <= result["potential_transpiration_mm"]
    assert result["root_water_uptake_mm"] == result["actual_transpiration_mm"]
    assert 0 <= result["feddes_alpha"] <= 1
    assert 0 <= result["cwsi_stress_index"] <= 1


def test_drought_reduces_actual_transpiration_but_not_potential():
    model = SimplifiedPlantModel()
    low = model.compute_daily_plant_step(25, 20, 60, 15)
    moderate = model.compute_daily_plant_step(25, 20, 60, 24)
    adequate = model.compute_daily_plant_step(25, 20, 60, 32)
    assert low["potential_transpiration_mm"] == moderate["potential_transpiration_mm"] == adequate["potential_transpiration_mm"]
    assert 0 < low["actual_transpiration_mm"] < moderate["actual_transpiration_mm"] <= adequate["actual_transpiration_mm"]
    assert low["cwsi_stress_index"] > moderate["cwsi_stress_index"] >= adequate["cwsi_stress_index"]
    wilted = model.compute_daily_plant_step(25, 20, 60, 8)
    assert wilted["actual_transpiration_mm"] == 0
    assert wilted["sap_flow_velocity_cmh"] == 0


def test_population_field_and_proxy_hru_share_percent_contract_and_seed():
    population = PlantPopulation(32, 77)
    first = population.step(120, FORCING, 24.0)
    second = PlantPopulation(32, 77).step(120, FORCING, 24.0)
    assert first == second
    field = PlantToFieldAggregator.aggregate(first, 24.0)
    hru = FieldToHRUCoupler(10).couple(field)
    assert field["soil_moisture_vol"] == 24.0
    assert field["units"]["soil_moisture_vol"] == "volumetric percent [0, 100]"
    assert [entry["field_inputs"]["soil_moisture_vol"] for entry in hru["hrus"]] == [24.0, 24.0, 22.75]
    assert field["transpiration_mm_day"] > 0
    assert field["soil_water_uptake_mm_day"] == field["transpiration_mm_day"]
    assert 0 <= field["water_stress"] < 1
    for plant in first:
        assert all(math.isfinite(value) for value in (
            plant.lai, plant.biomass_g_plant, plant.canopy_cover_fraction,
            plant.actual_transpiration_mm_day, plant.potential_transpiration_mm_day,
            plant.soil_water_uptake_mm_day, plant.stress,
        ))
        assert 0 <= plant.actual_transpiration_mm_day <= plant.potential_transpiration_mm_day
        assert 0 <= plant.canopy_cover_fraction <= 1
        assert 0 <= plant.lai <= 7
        assert plant.biomass_g_plant >= 0


def test_population_water_response_changes_lai_and_biomass():
    population = PlantPopulation(32, 77)
    dry = PlantToFieldAggregator.aggregate(population.step(120, FORCING, 15), 15)
    wet = PlantToFieldAggregator.aggregate(population.step(120, FORCING, 32), 32)
    assert dry["potential_ET_mm_day"] == wet["potential_ET_mm_day"]
    assert dry["actual_ET_mm_day"] < wet["actual_ET_mm_day"]
    assert dry["water_stress"] > wet["water_stress"]
    assert dry["mean_LAI"] < wet["mean_LAI"]
    assert dry["biomass_g_plant"] < wet["biomass_g_plant"]


@pytest.mark.parametrize("invalid", [-1, 101, math.nan, math.inf])
def test_component_boundaries_reject_invalid_moisture(invalid, tmp_path):
    population = PlantPopulation(2, 1)
    with pytest.raises(ValueError, match="soil_moisture_vol"):
        population.step(1, FORCING, invalid)
    states = population.step(1, FORCING, 24)
    with pytest.raises(ValueError, match="soil_moisture_vol"):
        PlantToFieldAggregator.aggregate(states, invalid)
    with pytest.raises(ValueError, match="soil_moisture_vol"):
        FieldToHRUCoupler(10).couple({"soil_moisture_vol": invalid})
    with pytest.raises(ValueError, match="soil_moisture_vol"):
        SwatPlantParameterMapper("corn").apply(tmp_path, {"soil_moisture_vol": invalid})


def test_nonfinite_forcing_cannot_create_nonfinite_crop_states():
    with pytest.raises(ValueError, match="gdd_c_day"):
        PlantPopulation(2, 1).step(1, {**FORCING, "gdd_c_day": math.nan}, 24)

from pathlib import Path

import pytest

from scientific_core import RunConfig, SimulationOrchestrator
from scientific_core.climate import SyntheticClimateProvider
from scientific_core.hydrology import SimplifiedHydrologyModel
from scientific_core.plant import SimplifiedPlantModel
from scientific_core.units import litres_per_plant_day_to_mm_day


def config(seed: int = 7, **parameters: float) -> RunConfig:
    return RunConfig(run_id="unit-test", seed=seed, duration_days=30, watershed_area_km2=10, parameters=parameters)


def test_core_has_no_framework_or_orm_imports():
    root = Path(__file__).parents[1] / "scientific_core"
    source = "\n".join(path.read_text() for path in root.glob("*.py"))
    assert "fastapi" not in source.lower()
    assert "sqlalchemy" not in source.lower()


def test_pipeline_is_deterministic_and_seeded():
    orchestrator = SimulationOrchestrator()
    first = orchestrator.execute(config(100))
    second = orchestrator.execute(config(100))
    different = orchestrator.execute(config(101))
    assert first.results == second.results
    assert first.summary_metrics == second.summary_metrics
    assert first.results != different.results


def test_unknown_and_out_of_range_parameters_are_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        config(crop=1)
    with pytest.raises(ValueError, match="curve_number"):
        config(curve_number=100)
    with pytest.raises(ValueError, match="management_scenario"):
        RunConfig(run_id="bad", seed=1, duration_days=30, watershed_area_km2=10, management_scenario="MAGIC")
    with pytest.raises(ValueError, match="climate_source"):
        RunConfig(run_id="bad", seed=1, duration_days=30, watershed_area_km2=10, climate_source="MAGIC")


def test_supported_parameters_have_an_effect():
    normal = SimulationOrchestrator().execute(config(3, base_kc=1.0, max_root_depth_cm=120))
    shallow = SimulationOrchestrator().execute(config(3, base_kc=1.0, max_root_depth_cm=30))
    assert normal.results[0]["actual_transpiration_mm"] > shallow.results[0]["actual_transpiration_mm"]


def test_every_supported_run_parameter_changes_a_relevant_output():
    baseline = SimulationOrchestrator().execute(config(17))
    higher_kc = SimulationOrchestrator().execute(config(17, base_kc=1.4))
    wetter_initial = SimulationOrchestrator().execute(config(17, initial_soil_moisture_vol=35))
    lower_cn = SimulationOrchestrator().execute(config(17, curve_number=55))
    irrigated = SimulationOrchestrator().execute(config(17, irrigation_mm_per_day=2))

    assert higher_kc.summary_metrics["total_actual_et_mm"] != baseline.summary_metrics["total_actual_et_mm"]
    assert wetter_initial.results[0]["soil_moisture_vol"] != baseline.results[0]["soil_moisture_vol"]
    assert lower_cn.summary_metrics["total_surface_runoff_mm"] != baseline.summary_metrics["total_surface_runoff_mm"]
    assert irrigated.summary_metrics["total_irrigation_mm"] == 60
    assert irrigated.results[0]["soil_water_depth_mm"] != baseline.results[0]["soil_water_depth_mm"]


def test_temperature_and_precipitation_controls_change_synthetic_forcing():
    baseline = RunConfig(run_id="controls", seed=8, duration_days=30, watershed_area_km2=10)
    warmer = RunConfig(run_id="controls", seed=8, duration_days=30, watershed_area_km2=10, temp_anomaly_c=2)
    drier = RunConfig(run_id="controls", seed=8, duration_days=30, watershed_area_km2=10, precip_factor=0)
    first = SimulationOrchestrator().execute(baseline)
    warm = SimulationOrchestrator().execute(warmer)
    dry = SimulationOrchestrator().execute(drier)
    assert sum(row["temp_c"] for row in warm.results) > sum(row["temp_c"] for row in first.results)
    assert dry.summary_metrics["total_precip_mm"] == 0


def test_scenario_co2_and_watershed_scale_change_relevant_outputs():
    baseline = SimulationOrchestrator().execute(config(23))
    elevated_co2 = SimulationOrchestrator().execute(
        RunConfig(run_id="unit-test", seed=23, duration_days=30, watershed_area_km2=10, co2_ppm=800)
    )
    larger_watershed = SimulationOrchestrator().execute(
        RunConfig(run_id="unit-test", seed=23, duration_days=30, watershed_area_km2=20)
    )
    assert elevated_co2.summary_metrics["total_actual_et_mm"] != baseline.summary_metrics["total_actual_et_mm"]
    assert larger_watershed.summary_metrics["peak_streamflow_m3s"] != baseline.summary_metrics["peak_streamflow_m3s"]


@pytest.mark.parametrize("precip,moisture", [(0, 12), (45, 25), (100, 43.9)])
def test_daily_water_balance_closes_for_boundaries(precip: float, moisture: float):
    model = SimplifiedHydrologyModel(initial_soil_moisture_vol=moisture)
    step = model.calculate_daily_step(precip, 3, 4)
    assert step["soil_water_depth_mm"] >= 0
    assert step["groundwater_storage_mm"] >= 0
    assert abs(step["water_balance_residual_mm"]) < 1e-9


def test_multiday_zero_input_does_not_create_water():
    model = SimplifiedHydrologyModel(initial_soil_moisture_vol=0, initial_groundwater_storage_mm=0)
    for _ in range(20):
        step = model.calculate_daily_step(0, 0, 4)
        assert step["streamflow_m3s"] == 0
        assert step["actual_et_mm"] == 0
        assert abs(step["water_balance_residual_mm"]) < 1e-12


def test_negative_physical_inputs_are_rejected():
    with pytest.raises(ValueError):
        SimplifiedHydrologyModel().calculate_daily_step(-1, 0, 0)
    with pytest.raises(ValueError):
        SimplifiedPlantModel().feddes_reduction_factor(-0.1)


def test_synthetic_climate_controls_and_provenance():
    base = SyntheticClimateProvider(9).generate_daily_weather(365)
    warm = SyntheticClimateProvider(9).generate_daily_weather(365, temp_anomaly_c=2)
    dry = SyntheticClimateProvider(9).generate_daily_weather(365, precip_factor=0)
    assert sum(day["temp_c"] for day in warm) / 365 > sum(day["temp_c"] for day in base) / 365 + 1.9
    assert sum(day["precip_mm"] for day in dry) == 0
    assert SyntheticClimateProvider(9).provenance.evidence_type.value == "SYNTHETIC"


def test_plant_to_field_unit_conversion():
    assert litres_per_plant_day_to_mm_day(2, 1000, 2000) == 1
    with pytest.raises(ValueError):
        litres_per_plant_day_to_mm_day(2, 1000, 0)

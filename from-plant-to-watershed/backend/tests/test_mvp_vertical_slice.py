import json
from pathlib import Path

import pytest

from app.services.external_model_bundle import ExternalModelBundleAdapter
from scientific_core import FieldToHRUCoupler, MultiscaleSimulationOrchestrator, PlantPopulation, PlantToFieldAggregator, RunConfig, ValidationEngine


def test_1000_plants_are_deterministic_and_variable():
    first, second = PlantPopulation(1000, 77), PlantPopulation(1000, 77)
    assert first.plants == second.plants
    assert len(first.plants) == 1000
    assert len({round(plant.root_depth_cm, 4) for plant in first.plants}) > 900


def test_plant_to_field_and_field_to_hru_are_explicit():
    population = PlantPopulation(1000, 2)
    forcing = {"temp_c": 25, "solar_rad_mj": 20, "rh_percent": 60, "co2_ppm": 415}
    field = PlantToFieldAggregator.aggregate(population.step(90, forcing, 28), 28)
    hru = FieldToHRUCoupler(100).couple(field)
    assert field["n_plants"] == 1000
    assert field["std_root_depth_cm"] > 0
    assert hru["count"] == 3
    assert hru["area_fraction_sum"] == pytest.approx(1)


def test_multiscale_baseline_and_twin_use_identical_forcing():
    run = MultiscaleSimulationOrchestrator().execute(
        RunConfig("mvp", 5, 35, 100, start_date=__import__("datetime").date(2020, 1, 1)), 1000
    )
    assert run.summary_metrics["plant_count"] == 1000
    assert run.provenance["forcing_identity"].startswith("baseline and twin")
    assert all("baseline_streamflow_m3s" in row for row in run.results)


def test_validation_metrics_and_undefined_states():
    metrics = ValidationEngine.evaluate([1, 2, 3], [1, 2, 4])
    assert metrics["rmse"]["value"] == pytest.approx((1 / 3) ** .5)
    assert metrics["nse"]["status"] == "DEFINED"
    undefined = ValidationEngine.evaluate([2, 2], [1, 2])
    assert undefined["nse"] == {"status": "UNDEFINED", "value": None, "reason": "zero observed variance"}


def test_external_bundle_schema_controls_order_and_missing_features(tmp_path: Path):
    schema = {"feature_names": ["rain", "lai"], "features": [
        {"name": "rain", "required": True, "min_val": 0, "max_val": 500},
        {"name": "lai", "required": True, "min_val": 0, "max_val": 8},
    ]}
    metadata = {"model_name": "Fixture RF", "target_name": "monthly_runoff_mm", "feature_order": ["rain", "lai"]}
    (tmp_path / "feature_schema.json").write_text(json.dumps(schema))
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    (tmp_path / "metrics.json").write_text("{}")
    (tmp_path / "model.joblib").write_bytes(b"fixture")
    adapter = ExternalModelBundleAdapter(tmp_path)
    assert adapter.validate_bundle()["status"] == "VALID"
    assert adapter._ordered_features({"lai": 3, "rain": 20}) == [20, 3]
    with pytest.raises(ValueError, match="missing required"):
        adapter._ordered_features({"rain": 20})

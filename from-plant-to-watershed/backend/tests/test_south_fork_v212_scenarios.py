import inspect
from types import SimpleNamespace

import scripts.run_final_south_fork as runner


def _field(*, scenario_name="HISTORICAL_COUPLED_V2", crop="maize", target="corn"):
    return {
        "scenario_name": scenario_name, "fspm_crop": crop,
        "fspm_classification": "SIMPLIFIED_SORGHUM_PROXY" if crop == "sorghum_proxy" else "SIMPLIFIED_FSPM",
        "target_plant_name": target, "plant_count": 1000, "fspm_seed": 42,
        "swat_lai_contract": {"lai_pot": 3.0}, "plant_height_mean_m": 1.2,
        "root_depth_mean_m": .7, "canopy_extinction_coefficient": .5,
        "biomass_energy_ratio_kg_ha_per_mj_m2": 40.0,
    }


def test_climate_scenario_forcing_is_perturbed_before_fspm_execution(monkeypatch):
    historical = [{"temp_c": 20.0, "precip_mm": 10.0, "solar_rad_mj": 15.0, "rh_percent": 60.0, "co2_ppm": 400.0}]
    calls = []

    def fake_fspm(**kwargs):
        calls.append(kwargs)
        return _field(scenario_name=kwargs["scenario_name"], crop=kwargs.get("crop", "maize"), target=kwargs.get("target_plant_name", "corn")), {}

    monkeypatch.setattr(runner, "_fspm_field", fake_fspm)
    historical_field = _field()
    field, _, lineage = runner._prepare_scenario_fspm(
        scenario_name="TEMPERATURE_PLUS_2C", options=runner.SCENARIO_DEFINITIONS["TEMPERATURE_PLUS_2C"],
        historical_field=historical_field, historical_forcing=historical, historical_forcing_provenance={"source": "SWAT"},
    )
    assert calls[0]["forcing"][0]["temp_c"] == 22.0
    assert calls[0]["forcing"] is not historical
    assert field is not historical_field
    assert lineage["fspm_recomputed"] is True
    assert lineage["forcing_modified"] is True
    assert lineage["comparison_baseline"] == "HISTORICAL_COUPLED_V2"


def test_dry_scenario_recomputes_fspm_with_reduced_precipitation(monkeypatch):
    historical = [{"temp_c": 20.0, "precip_mm": 10.0, "solar_rad_mj": 15.0, "rh_percent": 60.0, "co2_ppm": 400.0}]
    calls = []
    monkeypatch.setattr(runner, "_fspm_field", lambda **kwargs: (calls.append(kwargs) or _field(scenario_name=kwargs["scenario_name"]), {}))
    _, _, lineage = runner._prepare_scenario_fspm(
        scenario_name="PRECIPITATION_MINUS_15PCT", options=runner.SCENARIO_DEFINITIONS["PRECIPITATION_MINUS_15PCT"],
        historical_field=_field(), historical_forcing=historical, historical_forcing_provenance={},
    )
    assert calls[0]["forcing"][0]["precip_mm"] == 8.5
    assert lineage["fspm_recomputed"] is True
    assert lineage["forcing_modified"] is True
    assert "FSPM_WATER_RESPONSE=NOT_MODELED" in lineage["fspm_response_limitation"]


def test_no_till_reuses_historical_fspm_but_retains_coupled_contract():
    historical = _field()
    field, daily, lineage = runner._prepare_scenario_fspm(
        scenario_name="NO_TILL", options=runner.SCENARIO_DEFINITIONS["NO_TILL"], historical_field=historical,
        historical_forcing=[], historical_forcing_provenance={},
    )
    assert field is historical and daily == {}
    assert lineage["fspm_recomputed"] is False
    assert lineage["management_modified"] is True
    assert "FSPM_RESPONSE_TO_MANAGEMENT=NOT_MODELED" in lineage["fspm_response_limitation"]


def test_sorghum_proxy_is_recomputed_and_targets_grsg_not_maize(monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "_fspm_field", lambda **kwargs: (calls.append(kwargs) or _field(
        scenario_name=kwargs["scenario_name"], crop=kwargs["crop"], target=kwargs["target_plant_name"]), {}))
    field, _, lineage = runner._prepare_scenario_fspm(
        scenario_name="MAIZE_TO_SORGHUM", options=runner.SCENARIO_DEFINITIONS["MAIZE_TO_SORGHUM"],
        historical_field=_field(), historical_forcing=[], historical_forcing_provenance={},
    )
    assert calls[0]["crop"] == "sorghum_proxy"
    assert calls[0]["target_plant_name"] == "grsg"
    assert field["fspm_crop"] == "sorghum_proxy"
    assert lineage["fspm_classification"] == "SIMPLIFIED_SORGHUM_PROXY"
    assert lineage["crop_modified"] is True
    assert 'field.get("target_plant_name") != crop' in inspect.getsource(runner._run)


def test_scenario_execution_is_coupled_and_compared_with_historical_coupled(monkeypatch):
    lineage = {"scenario_name": "TEMPERATURE_PLUS_2C", "comparison_baseline": "HISTORICAL_COUPLED_V2"}
    monkeypatch.setattr(runner, "_prepare_scenario_fspm", lambda **_: (_field(), {}, lineage))
    captured = {}
    run = SimpleNamespace(run_id="scenario-run", records=[{"period": "2018-01-01", "streamflow_m3s": 2.0, "runoff_mm": 1.0, "evapotranspiration_mm": 1.0, "soil_water_mm": 1.0}], provenance={})
    historical = SimpleNamespace(run_id="historical-coupled", records=[{"period": "2018-01-01", "streamflow_m3s": 1.0, "runoff_mm": 1.0, "evapotranspiration_mm": 1.0, "soil_water_mm": 1.0}])

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return run

    monkeypatch.setattr(runner, "_run", fake_run)
    record = runner._run_coupled_scenario(
        scenario_name="TEMPERATURE_PLUS_2C", options=runner.SCENARIO_DEFINITIONS["TEMPERATURE_PLUS_2C"],
        historical_field=_field(), historical_forcing=[], historical_forcing_provenance={}, historical_coupled=historical,
    )
    assert captured["coupled"] is True
    assert record["comparison_baseline"] == "HISTORICAL_COUPLED_V2"
    assert record["reference_run_id"] == "historical-coupled"
    assert record["delta_from_historical_coupled_v2"]["streamflow_m3s_mean"]["absolute"] == 1.0


def test_wilcoxon_ui_selects_interpretation_or_reason():
    source = (runner.ROOT / "frontend/src/components/scientific/StatisticalBatteryPanel.tsx").read_text(encoding="utf-8")
    assert 'wilcoxon.status === "COMPUTED"' in source
    assert "wilcoxon.interpretation" in source
    assert "wilcoxon.reason" in source


def test_scenario_ui_uses_coupled_reference_and_current_runner_identifiers():
    source = (runner.ROOT / "frontend/src/components/scientific/ClimateScenariosPanel.tsx").read_text(encoding="utf-8")
    assert "delta_from_historical_coupled_v2" in source
    assert "HISTORICAL_COUPLED_V2" in source
    for scenario_name in runner.SCENARIO_DEFINITIONS:
        assert scenario_name in source

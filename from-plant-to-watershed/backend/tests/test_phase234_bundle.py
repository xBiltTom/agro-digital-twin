"""Regressions for the immutable South Fork phase234 demo bundle."""

from scripts.validate_phase234_bundle import validate_bundle


def test_phase234_bundle_has_complete_aligned_finite_daily_states():
    result = validate_bundle()

    assert result["status"] == "VALID"
    assert result["period"] == {"start": "2019-01-01", "end": "2019-12-31"}
    assert result["days"] == result["basin_records"] == 365
    assert result["hru_count"] == 36
    assert result["hru_records"] == 36 * 365
    assert result["corn_hrus_in_executed_calendar"] == 32
    assert result["channel_count"] == 37
    assert result["channel_records"] == 37 * 365
    assert result["coupling"]["run_type"] == "SWAT_MULTISCALE_COUPLED"
    assert result["coupling"]["iterations"] == 2
    assert result["coupling"]["final_max_soil_water_delta_mm"] <= result["coupling"]["tolerance_mm"]
    assert result["coupling"]["fspm_parameter_updates"] > 0

import pytest
from app.services.ai_insights import AICopilotService


@pytest.mark.asyncio
async def test_ai_copilot_service_heuristic_fallback():
    """Verify that AICopilotService produces valid structured insights even without an API key."""
    sim_data = {
        "id": "sim-test-123",
        "name": "Simulación South Fork +2C",
        "duration_days": 365,
        "management_scenario": "NO_TILL",
        "climate_source": "GRIDMET",
        "watershed_name": "South Fork Iowa River",
        "summary_metrics": {
            "total_precipitation_mm": 720.5,
            "total_runoff_mm": 95.2,
            "total_evapotranspiration_mm": 580.4,
            "mean_soil_moisture_percent": 27.8,
            "water_balance": {
                "mean_streamflow_m3s": 5.4,
                "peak_streamflow_m3s": 18.2,
                "closure_error_mm": 0.0,
            },
            "paired_comparison": {
                "streamflow_m3s": {"delta_percentage": -4.2}
            }
        },
        "field_aggregates": {
            "mean_lai": 3.75,
            "mean_root_depth_m": 1.30,
            "mean_transpiration_mm": 395.0,
            "mean_water_stress": 0.08,
        },
        "scenario": {
            "name": "+2C Climate Shock",
            "temp_anomaly_c": 2.0,
            "precip_factor": 1.0,
            "co2_ppm": 450.0,
        },
    }

    insights = await AICopilotService.analyze_simulation(sim_data)

    assert "executive_summary" in insights
    assert len(insights["executive_summary"]) > 50
    assert "multiscale_biophysical_diagnosis" in insights
    assert "micro_scale_plant" in insights["multiscale_biophysical_diagnosis"]
    assert "meso_scale_field" in insights["multiscale_biophysical_diagnosis"]
    assert "macro_scale_watershed" in insights["multiscale_biophysical_diagnosis"]
    assert "climate_resilience_assessment" in insights
    assert "policy_recommendations" in insights
    assert len(insights["policy_recommendations"]) >= 3
    assert "provider" in insights
    assert "generated_at" in insights

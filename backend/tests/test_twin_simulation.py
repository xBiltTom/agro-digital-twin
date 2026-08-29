import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.climate_engine import DownscaledClimateEngine
from app.services.plant_model import IndividualPlantPhysiologyModel
from app.services.swat_hydrology import SWATHydrologyEngine

def test_climate_engine_downscaling():
    engine = DownscaledClimateEngine(seed=123)
    weather = engine.generate_daily_weather(
        duration_days=365,
        temp_anomaly_c=2.5,
        precip_factor=0.85
    )
    assert len(weather) == 365
    temps = [w["temp_c"] for w in weather]
    precips = [w["precip_mm"] for w in weather]

    # Verificar que las temperaturas son físicamente realistas
    assert all(-5.0 < t < 45.0 for t in temps)
    # Media de temperatura debe reflejar la anomalía positiva
    assert sum(temps) / len(temps) > 18.0
    # La lluvia debe acumularse
    assert sum(precips) > 200.0

def test_plant_model_feddes_reduction():
    plant = IndividualPlantPhysiologyModel(
        base_kc=1.1,
        wilting_point_vol=12.0,
        field_capacity_vol=32.0,
        saturation_vol=44.0
    )

    # 1. Condición óptima (a capacidad de campo: theta = 30%)
    alpha_optimal = plant.feddes_reduction_factor(30.0)
    assert alpha_optimal == 1.0

    # 2. Estrés hídrico (cerca del punto de marchitez: theta = 15%)
    alpha_stress = plant.feddes_reduction_factor(15.0)
    assert 0.0 < alpha_stress < 1.0

    # 3. Punto de marchitez permanente (theta <= 12%)
    alpha_wilted = plant.feddes_reduction_factor(10.0)
    assert alpha_wilted == 0.0

    # 4. Cálculo de paso diario
    step = plant.compute_daily_plant_step(
        temp_c=25.0,
        solar_rad_mj=20.0,
        rh_percent=60.0,
        soil_moisture_vol=28.0
    )
    assert step["actual_transpiration_mm"] > 0.0
    assert 0.0 <= step["cwsi_stress_index"] <= 1.0
    assert step["sap_flow_velocity_cmh"] > 0.0

def test_swat_hydrology_water_balance():
    swat = SWATHydrologyEngine(
        watershed_area_km2=420.5,
        curve_number=74.0,
        initial_soil_moisture_vol=25.0
    )

    # 1. Día con lluvia fuerte (45 mm)
    step_rain = swat.calculate_daily_step(
        precip_mm=45.0,
        plant_transpiration_mm=3.5,
        potential_et_mm=4.5
    )
    assert step_rain["surface_runoff_mm"] > 0.0
    assert step_rain["streamflow_m3s"] > 1.0
    assert step_rain["soil_moisture_vol"] > 25.0

    # 2. Día seco posterior (0 mm lluvia)
    step_dry = swat.calculate_daily_step(
        precip_mm=0.0,
        plant_transpiration_mm=3.0,
        potential_et_mm=4.2
    )
    assert step_dry["surface_runoff_mm"] == 0.0
    assert step_dry["actual_et_mm"] > 0.0
    # Humedad debe descender debido a la evapotranspiración
    assert step_dry["soil_moisture_vol"] <= step_rain["soil_moisture_vol"]

@pytest.mark.asyncio
async def test_api_simulation_workflow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login como Investigador
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org",
            "password": "Investiga123!"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Obtener escenarios climáticos
        scenarios_res = await ac.get("/api/v1/simulations/scenarios/all", headers=headers)
        assert scenarios_res.status_code == 200
        scenarios = scenarios_res.json()
        assert len(scenarios) >= 4
        scenario_id = scenarios[0]["id"]

        # 3. Obtener cuencas
        watersheds_res = await ac.get("/api/v1/simulations/watersheds/all", headers=headers)
        assert watersheds_res.status_code == 200
        watersheds = watersheds_res.json()
        assert len(watersheds) >= 1
        watershed_id = watersheds[0]["id"]

        # 4. Crear y ejecutar nueva simulación acoplada de 90 días
        create_res = await ac.post("/api/v1/simulations", headers=headers, json={
            "name": "Simulación Experimental Test Pytest (90d)",
            "watershed_id": watershed_id,
            "scenario_id": scenario_id,
            "duration_days": 90,
            "irrigation_efficiency": 0.90
        })
        assert create_res.status_code == 201
        sim_data = create_res.json()
        assert sim_data["status"] == "COMPLETED"
        assert "total_precip_mm" in sim_data["summary_metrics"]
        assert sim_data["duration_days"] == 90
        sim_id = sim_data["id"]

        # 5. Consultar resultados diarios
        results_res = await ac.get(f"/api/v1/simulations/{sim_id}/results?limit=90", headers=headers)
        assert results_res.status_code == 200
        results = results_res.json()
        assert len(results) == 90
        assert results[0]["streamflow_m3s"] >= 0.0
        assert results[0]["plant_transpiration_mm"] >= 0.0

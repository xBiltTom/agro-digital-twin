import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.services.climate_engine import DownscaledClimateEngine
from app.services.plant_model import IndividualPlantPhysiologyModel
from app.services.swat_hydrology import SWATHydrologyEngine
from app.services.twin_coupling_engine import TwinCouplingEngine

def test_synthetic_climate_provider():
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

def test_simplified_hydrology_water_balance():
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
    assert abs(step_rain["water_balance_residual_mm"]) < 1e-9

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
    assert abs(step_dry["water_balance_residual_mm"]) < 1e-9

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
            "seed": 1234,
            "parameters": {}
        })
        assert create_res.status_code == 201
        sim_data = create_res.json()
        assert sim_data["status"] == "COMPLETED"
        assert "total_precip_mm" in sim_data["summary_metrics"]
        assert sim_data["duration_days"] == 90
        assert sim_data["seed"] == 1234
        assert sim_data["effective_config"]["seed"] == 1234
        assert sim_data["provenance"]["climate"]["evidence_type"] == "SYNTHETIC"
        assert sim_data["provenance"]["hydrology"]["model"] == "SimplifiedHydrologyModel"
        sim_id = sim_data["id"]

        # 5. Consultar resultados diarios
        results_res = await ac.get(f"/api/v1/simulations/{sim_id}/results?limit=90", headers=headers)
        assert results_res.status_code == 200
        results = results_res.json()
        assert len(results) == 90
        assert results[0]["streamflow_m3s"] >= 0.0
        assert results[0]["plant_transpiration_mm"] >= 0.0
        assert abs(results[0]["water_balance_residual_mm"]) < 1e-9

        rejected = await ac.post("/api/v1/simulations", headers=headers, json={
            "name": "Parámetro inerte", "watershed_id": watershed_id,
            "scenario_id": scenario_id, "duration_days": 5, "seed": 1,
            "parameters": {"crop": "Palto Hass"},
        })
        assert rejected.status_code == 422

        lai_rejected = await ac.post("/api/v1/simulations", headers=headers, json={
            "name": "LAI no implementado", "watershed_id": watershed_id,
            "scenario_id": scenario_id, "duration_days": 5, "seed": 1,
            "parameters": {"lai": 3},
        })
        assert lai_rejected.status_code == 422

        irrigation_efficiency_rejected = await ac.post("/api/v1/simulations", headers=headers, json={
            "name": "Eficiencia no implementada", "watershed_id": watershed_id,
            "scenario_id": scenario_id, "duration_days": 5, "seed": 1,
            "irrigation_efficiency": 0.85,
        })
        assert irrigation_efficiency_rejected.status_code == 422


@pytest.mark.asyncio
async def test_failed_run_is_persisted_as_failed():
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).limit(1))
        watershed_id = await db.scalar(select(Watershed.id).limit(1))
        scenario_id = await db.scalar(select(ClimateScenario.id).limit(1))
        run = SimulationRun(
            user_id=user_id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="Intentional failure", duration_days=3, seed=4,
            parameters={"unsupported": 1}, requested_config={"parameters": {"unsupported": 1}},
        )
        db.add(run)
        await db.commit()
        run_id = run.id
        with pytest.raises(ValueError, match="Unsupported"):
            await TwinCouplingEngine.execute_simulation_run(db, run_id)
        await db.refresh(run)
        assert run.status == "FAILED"
        assert run.error["type"] == "ValueError"

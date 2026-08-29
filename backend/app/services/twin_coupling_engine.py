from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.watershed import Watershed
from backend.app.models.simulation import ClimateScenario, SimulationRun, SimulationResult
from backend.app.services.climate_engine import DownscaledClimateEngine
from backend.app.services.plant_model import IndividualPlantPhysiologyModel
from backend.app.services.swat_hydrology import SWATHydrologyEngine

class TwinCouplingEngine:
    """
    Orquestador de Acoplamiento Multiescala del Gemelo Digital (AP-3):
    Integra las proyecciones climáticas downscaled con la fisiología vegetal individual (Micro)
    y el balance hidrológico de cuenca SWAT (Macro).
    """

    @staticmethod
    async def execute_simulation_run(
        db: AsyncSession,
        simulation_run_id: str
    ) -> SimulationRun:
        # 1. Obtener la simulación y sus entidades relacionadas
        stmt = select(SimulationRun).where(SimulationRun.id == simulation_run_id)
        res = await db.execute(stmt)
        sim_run = res.scalar_one_or_none()
        if not sim_run:
            raise ValueError(f"Simulación con ID {simulation_run_id} no encontrada")

        # Cargar cuenca
        watershed_stmt = select(Watershed).where(Watershed.id == sim_run.watershed_id)
        watershed_res = await db.execute(watershed_stmt)
        watershed = watershed_res.scalar_one_or_none()

        # Cargar escenario climático
        scenario_stmt = select(ClimateScenario).where(ClimateScenario.id == sim_run.scenario_id)
        scenario_res = await db.execute(scenario_stmt)
        scenario = scenario_res.scalar_one_or_none()

        # Marcar estado en ejecución
        sim_run.status = "RUNNING"
        await db.commit()

        # 2. Inicializar motores científicos
        climate_engine = DownscaledClimateEngine(seed=42 + hash(sim_run.id) % 10000)
        daily_weather = climate_engine.generate_daily_weather(
            duration_days=sim_run.duration_days,
            temp_anomaly_c=scenario.temp_anomaly_c if scenario else 0.0,
            precip_factor=scenario.precip_factor if scenario else 1.0,
            co2_ppm=scenario.co2_ppm if scenario else 415.0
        )

        plant_model = IndividualPlantPhysiologyModel(
            base_kc=1.05,
            max_root_depth_cm=120.0
        )

        swat_engine = SWATHydrologyEngine(
            watershed_area_km2=watershed.area_km2 if watershed else 420.5,
            curve_number=74.0,
            initial_soil_moisture_vol=24.5
        )

        # 3. Bucle de acoplamiento multiescala día a día
        start_date = datetime(2026, 1, 1)
        sim_results: List[SimulationResult] = []

        total_precip = 0.0
        total_runoff = 0.0
        total_actual_et = 0.0
        total_streamflow_m3 = 0.0
        peak_streamflow = 0.0
        cwsi_sum = 0.0

        current_moisture_vol = 24.5

        for w in daily_weather:
            day_idx = w["day_index"]
            curr_date = start_date + timedelta(days=day_idx - 1)
            date_str = curr_date.strftime("%Y-%m-%d")

            # Paso Micro: Fisiología de la Planta individual
            plant_step = plant_model.compute_daily_plant_step(
                temp_c=w["temp_c"],
                solar_rad_mj=w["solar_rad_mj"],
                rh_percent=w["rh_percent"],
                soil_moisture_vol=current_moisture_vol,
                co2_ppm=w["co2_ppm"]
            )

            # Paso Macro: Balance Hidrológico SWAT
            swat_step = swat_engine.calculate_daily_step(
                precip_mm=w["precip_mm"],
                plant_transpiration_mm=plant_step["actual_transpiration_mm"],
                potential_et_mm=plant_step["et0_mm"]
            )

            # Actualizar estado de acoplamiento de humedad
            current_moisture_vol = swat_step["soil_moisture_vol"]

            # Acumuladores para KPIs
            total_precip += w["precip_mm"]
            total_runoff += swat_step["surface_runoff_mm"]
            total_actual_et += swat_step["actual_et_mm"]
            total_streamflow_m3 += swat_step["streamflow_m3s"] * 86400.0
            peak_streamflow = max(peak_streamflow, swat_step["streamflow_m3s"])
            cwsi_sum += plant_step["cwsi_stress_index"]

            # Crear registro de resultado diario
            res_obj = SimulationResult(
                simulation_run_id=sim_run.id,
                day_index=day_idx,
                date_str=date_str,
                precip_mm=w["precip_mm"],
                temp_c=w["temp_c"],
                solar_rad_mj=w["solar_rad_mj"],
                potential_et_mm=plant_step["et0_mm"],
                actual_et_mm=swat_step["actual_et_mm"],
                surface_runoff_mm=swat_step["surface_runoff_mm"],
                percolation_mm=swat_step["percolation_mm"],
                streamflow_m3s=swat_step["streamflow_m3s"],
                soil_moisture_vol=current_moisture_vol,
                soil_water_depth_mm=swat_step["soil_water_depth_mm"],
                plant_transpiration_mm=plant_step["actual_transpiration_mm"],
                root_water_uptake_mm=plant_step["root_water_uptake_mm"],
                cwsi_stress_index=plant_step["cwsi_stress_index"],
                sap_flow_velocity_cmh=plant_step["sap_flow_velocity_cmh"]
            )
            sim_results.append(res_obj)

        # 4. Guardar resultados y actualizar métricas de resumen
        db.add_all(sim_results)

        total_volume_hm3 = round(total_streamflow_m3 / 1_000_000.0, 2)
        mean_cwsi = round(cwsi_sum / len(daily_weather), 3)

        sim_run.summary_metrics = {
            "total_precip_mm": round(total_precip, 1),
            "total_surface_runoff_mm": round(total_runoff, 1),
            "total_actual_et_mm": round(total_actual_et, 1),
            "total_discharge_hm3": total_volume_hm3,
            "peak_streamflow_m3s": round(peak_streamflow, 2),
            "mean_cwsi": mean_cwsi,
            "drought_stress_status": "Bajo / Óptimo" if mean_cwsi < 0.25 else ("Moderado" if mean_cwsi < 0.45 else "Crítico")
        }
        sim_run.status = "COMPLETED"

        await db.commit()
        await db.refresh(sim_run)
        return sim_run

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from .climate import SyntheticClimateProvider
from .config import RunConfig
from .hydrology import SimplifiedHydrologyModel
from .plant import SimplifiedPlantModel
from .provenance import EvidenceType


@dataclass(frozen=True)
class ScientificRun:
    results: tuple[dict[str, Any], ...]
    summary_metrics: dict[str, Any]
    effective_config: dict[str, Any]
    provenance: dict[str, Any]


class SimulationOrchestrator:
    """Pure deterministic coordinator. It has no persistence or web dependencies."""

    def execute(self, config: RunConfig) -> ScientificRun:
        effective = config.effective_dict()
        params = effective["parameters"]
        climate = SyntheticClimateProvider(config.seed)
        plant = SimplifiedPlantModel(params["base_kc"], params["max_root_depth_cm"])
        hydrology = SimplifiedHydrologyModel(config.watershed_area_km2, params["curve_number"],
                                             initial_soil_moisture_vol=params["initial_soil_moisture_vol"])
        weather = climate.generate_daily_weather(config.duration_days, config.temp_anomaly_c,
                                                  config.precip_factor, config.co2_ppm)
        results: list[dict[str, Any]] = []
        moisture = params["initial_soil_moisture_vol"]
        totals = {"precip": 0.0, "irrigation": 0.0, "runoff": 0.0, "et": 0.0, "discharge_m3": 0.0, "cwsi": 0.0}
        peak = 0.0
        for forcing in weather:
            plant_step = plant.compute_daily_plant_step(
                forcing["temp_c"], forcing["solar_rad_mj"], forcing["rh_percent"], moisture, forcing["co2_ppm"])
            irrigation = params["irrigation_mm_per_day"]
            hydro = hydrology.calculate_daily_step(forcing["precip_mm"], plant_step["actual_transpiration_mm"],
                                                    plant_step["et0_mm"], irrigation)
            moisture = hydro["soil_moisture_vol"]
            date_str = (config.start_date + timedelta(days=forcing["day_index"] - 1)).isoformat()
            row = {**forcing, **plant_step, **hydro, "date_str": date_str, "irrigation_mm": irrigation}
            results.append(row)
            totals["precip"] += forcing["precip_mm"]
            totals["irrigation"] += irrigation
            totals["runoff"] += hydro["surface_runoff_mm"]
            totals["et"] += hydro["actual_et_mm"]
            totals["discharge_m3"] += hydro["streamflow_m3s"] * 86400.0
            totals["cwsi"] += plant_step["cwsi_stress_index"]
            peak = max(peak, hydro["streamflow_m3s"])
        mean_cwsi = totals["cwsi"] / config.duration_days
        summary = {
            "total_precip_mm": round(totals["precip"], 6),
            "total_irrigation_mm": round(totals["irrigation"], 6),
            "total_surface_runoff_mm": round(totals["runoff"], 6),
            "total_actual_et_mm": round(totals["et"], 6),
            "total_discharge_hm3": round(totals["discharge_m3"] / 1_000_000.0, 6),
            "peak_streamflow_m3s": round(peak, 6), "mean_cwsi": round(mean_cwsi, 6),
            "cumulative_water_balance_residual_mm": hydrology.cumulative_balance_residual_mm,
            "interpretation_status": "NOT_VALIDATED",
        }
        provenance = {
            "run_evidence_type": EvidenceType.DEMO.value,
            "climate": climate.provenance.as_dict(), "plant": plant.provenance.as_dict(),
            "hydrology": hydrology.provenance.as_dict(),
            "datasets": [],
            "statement": "Synthetic forcing and simplified models; no observed-data validation.",
        }
        return ScientificRun(tuple(results), summary, effective, provenance)

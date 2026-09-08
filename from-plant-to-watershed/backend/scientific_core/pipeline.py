from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any

from .climate import SyntheticClimateProvider
from .config import RunConfig
from .hydrology import SimplifiedHydrologyModel
from .plant import SimplifiedPlantModel
from .provenance import EvidenceType
from .multiscale import FieldToHRUCoupler, PlantPopulation, PlantToFieldAggregator
from .validation import ValidationEngine


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


@dataclass(frozen=True)
class MultiscaleRun:
    results: tuple[dict[str, Any], ...]
    summary_metrics: dict[str, Any]
    field_aggregates: dict[str, Any]
    hru_aggregates: dict[str, Any]
    plant_sample: tuple[dict[str, Any], ...]
    monthly_outputs: tuple[dict[str, Any], ...]
    validation: dict[str, Any]
    effective_config: dict[str, Any]
    provenance: dict[str, Any]


class MultiscaleSimulationOrchestrator:
    """End-to-end demo comparison using one forcing for baseline and twin."""

    def execute(self, config: RunConfig, plant_count: int = 1000) -> MultiscaleRun:
        effective = config.effective_dict()
        management = config.management_effects()
        params = management["parameters"]
        effective["parameters"] = params
        effective["management"] = {key: value for key, value in management.items() if key != "parameters"}
        weather = SyntheticClimateProvider(config.seed).generate_daily_weather(
            config.duration_days, config.temp_anomaly_c, config.precip_factor, config.co2_ppm
        )
        population = PlantPopulation(plant_count, config.seed, base_kc=params["base_kc"],
                                     max_root_depth_cm=params["max_root_depth_cm"], crop=management["crop"])
        coupler = FieldToHRUCoupler(config.watershed_area_km2,
                                    curve_number_delta=management["curve_number_adjustment"], crop=management["crop"])
        baseline_plant = SimplifiedPlantModel(params["base_kc"], params["max_root_depth_cm"])
        baseline_hydro = SimplifiedHydrologyModel(config.watershed_area_km2, params["curve_number"],
                                                  initial_soil_moisture_vol=params["initial_soil_moisture_vol"])
        twin_hydro = SimplifiedHydrologyModel(config.watershed_area_km2, params["curve_number"],
                                              initial_soil_moisture_vol=params["initial_soil_moisture_vol"])
        baseline_moisture = twin_moisture = params["initial_soil_moisture_vol"]
        rows, monthly = [], {}
        final_field: dict[str, Any] = {}
        final_hru: dict[str, Any] = {}
        final_states = ()
        field_lai, field_stress = [], []
        for forcing in weather:
            states = population.step(forcing["day_index"], forcing, twin_moisture)
            field = PlantToFieldAggregator.aggregate(states, twin_moisture)
            hru = coupler.couple(field)
            baseline_step = baseline_plant.compute_daily_plant_step(
                forcing["temp_c"], forcing["solar_rad_mj"], forcing["rh_percent"], baseline_moisture, forcing["co2_ppm"]
            )
            baseline = baseline_hydro.calculate_daily_step(
                forcing["precip_mm"], baseline_step["actual_transpiration_mm"], baseline_step["et0_mm"],
                params["irrigation_mm_per_day"]
            )
            twin = twin_hydro.calculate_daily_step(
                forcing["precip_mm"], field["mean_transpiration_mm"], baseline_step["et0_mm"],
                params["irrigation_mm_per_day"]
            )
            baseline_moisture, twin_moisture = baseline["soil_moisture_vol"], twin["soil_moisture_vol"]
            date_value = config.start_date + timedelta(days=forcing["day_index"] - 1)
            month_key = date_value.strftime("%Y-%m")
            bucket = monthly.setdefault(month_key, {"baseline": [], "twin": []})
            bucket["baseline"].append(baseline["streamflow_m3s"])
            bucket["twin"].append(twin["streamflow_m3s"])
            rows.append({**forcing, **twin, "date_str": date_value.isoformat(),
                         "et0_mm": baseline_step["et0_mm"], "actual_transpiration_mm": field["mean_transpiration_mm"],
                         "root_water_uptake_mm": field["mean_transpiration_mm"], "cwsi_stress_index": field["mean_stress"],
                         "sap_flow_velocity_cmh": 2.5 + field["mean_transpiration_mm"] / 6 * 18,
                         "baseline_streamflow_m3s": baseline["streamflow_m3s"], "irrigation_mm": params["irrigation_mm_per_day"]})
            final_field, final_hru, final_states = field, hru, states
            field_lai.append(field["mean_lai"])
            field_stress.append(field["mean_stress"])
        monthly_rows = tuple({"month": key, "baseline_streamflow_m3s": sum(v["baseline"]) / len(v["baseline"]),
                              "twin_streamflow_m3s": sum(v["twin"]) / len(v["twin"]),
                              "observed_streamflow_m3s": None} for key, v in sorted(monthly.items()))
        validation = {"status": "NOT_AVAILABLE", "reason": "no date-compatible observations supplied",
                      "interpretation": "DEMONSTRATION_ONLY"}
        total_precip = sum(row["precip_mm"] for row in rows)
        total_runoff = sum(row["surface_runoff_mm"] for row in rows)
        mean_lai = sum(field_lai) / len(field_lai)
        mean_stress = sum(field_stress) / len(field_stress)
        potential_yield = 9.2 if management["crop"] == "sorghum_proxy" else 12.8
        yield_proxy = max(0.0, potential_yield * min(1.0, mean_lai / (4.2 if management["crop"] == "sorghum_proxy" else 5.2)) * (1.0 - 0.55 * mean_stress))
        summary = {"total_precip_mm": total_precip, "total_surface_runoff_mm": total_runoff,
                   "total_actual_et_mm": sum(row["actual_et_mm"] for row in rows),
                   "total_discharge_hm3": sum(row["streamflow_m3s"] * 86400 for row in rows) / 1_000_000,
                   "peak_streamflow_m3s": max(row["streamflow_m3s"] for row in rows),
                   "mean_cwsi": sum(row["cwsi_stress_index"] for row in rows) / len(rows),
                   "cumulative_water_balance_residual_mm": twin_hydro.cumulative_balance_residual_mm,
                   "interpretation_status": "NOT_FORMAL_HYPOTHESIS_TEST", "plant_count": plant_count,
                   "hru_count": len(coupler.hrus), "seasonal_crop_yield_proxy_t_ha": yield_proxy,
                   "yield_proxy_evidence_type": "DERIVED", "management_scenario": management["scenario"]}
        sample_step = max(1, len(final_states) // 30)
        sample = tuple(asdict(p) for p in final_states[::sample_step][:30])
        return MultiscaleRun(tuple(rows), summary, final_field, final_hru, sample, monthly_rows, validation, effective,
                             {"run_evidence_type": "DEMO", "climate": SyntheticClimateProvider(config.seed).provenance.as_dict(),
                              "plant": {"model": "SimplifiedPlantModel", "evidence_type": "SIMPLIFIED", "population": plant_count},
                              "field": {"model": "PlantToFieldAggregator", "evidence_type": "DERIVED"},
                              "hru": {"model": "FieldToHRUCoupler", "evidence_type": "COARSE_HRU_PROXY"},
                              "hydrology": twin_hydro.provenance.as_dict(), "management": management,
                              "yield_proxy": {"evidence_type": "DERIVED", "unit": "t/ha",
                                              "statement": "Seasonal stress/LAI proxy; not observed USDA NASS yield."},
                              "comparison": "DEMONSTRATION_COMPARISON",
                              "forcing_identity": "baseline and twin share the same generated weather series"})

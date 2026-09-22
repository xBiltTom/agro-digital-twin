import math
from typing import Any

from .provenance import EvidenceType, Provenance
from .units import validate_soil_moisture_vol_percent


class SimplifiedPlantModel:
    """Algebraic representative-plant water-stress model; not a full FSPM."""

    VERSION = "1.0"

    def __init__(self, base_kc: float = 1.05, max_root_depth_cm: float = 120.0,
                 wilting_point_vol: float = 12.0, field_capacity_vol: float = 32.0,
                 saturation_vol: float = 44.0):
        if not all(math.isfinite(value) for value in (base_kc, max_root_depth_cm, wilting_point_vol, field_capacity_vol, saturation_vol)) or not 0 < base_kc <= 2 or not 0 < max_root_depth_cm <= 500:
            raise ValueError("base_kc and max_root_depth_cm are outside the supported domain")
        if not 0 <= wilting_point_vol < field_capacity_vol < saturation_vol <= 100:
            raise ValueError("soil moisture thresholds must be strictly ordered")
        self.base_kc, self.max_root_depth_cm = base_kc, max_root_depth_cm
        self.theta_wp, self.theta_fc, self.theta_sat = wilting_point_vol, field_capacity_vol, saturation_vol
        self.theta_crit = wilting_point_vol + 0.55 * (field_capacity_vol - wilting_point_vol)

    @property
    def provenance(self) -> Provenance:
        return Provenance(self.__class__.__name__, self.VERSION, EvidenceType.SIMPLIFIED,
                          "representative plant expressed as field-equivalent depth", "daily",
                          {"et0_mm": "mm/day", "actual_transpiration_mm": "mm/day", "soil_moisture_vol": "volumetric percent [0, 100]", "max_root_depth_cm": "cm", "lai": "not modelled"})

    def calculate_potential_et(self, temp_c: float, solar_rad_mj: float, rh_percent: float) -> float:
        if not all(math.isfinite(value) for value in (temp_c, solar_rad_mj, rh_percent)) or solar_rad_mj < 0 or not 0 <= rh_percent <= 100:
            raise ValueError("solar radiation and relative humidity are outside their physical domain")
        if temp_c <= 0:
            return 0.2
        et0 = 0.013 * (temp_c / (temp_c + 15.0)) * (23.885 * (solar_rad_mj * 0.408) + 50.0)
        if rh_percent < 50.0:
            et0 *= 1.0 + (50.0 - rh_percent) / 70.0
        return max(0.5, et0)

    def feddes_reduction_factor(self, soil_moisture_vol: float) -> float:
        validate_soil_moisture_vol_percent(soil_moisture_vol)
        theta = min(self.theta_sat, soil_moisture_vol)
        if theta > self.theta_sat - 2.0:
            return 0.35
        if theta >= self.theta_crit:
            return 1.0
        if theta > self.theta_wp:
            return max(0.0, min(1.0, (theta - self.theta_wp) / (self.theta_crit - self.theta_wp)))
        return 0.0

    def compute_daily_plant_step(self, temp_c: float, solar_rad_mj: float, rh_percent: float,
                                 soil_moisture_vol: float, co2_ppm: float = 415.0) -> dict[str, Any]:
        if not math.isfinite(co2_ppm) or co2_ppm <= 0:
            raise ValueError("co2_ppm must be positive")
        et0 = self.calculate_potential_et(temp_c, solar_rad_mj, rh_percent)
        co2_factor = max(0.5, 1.0 - 0.05 * math.log(max(400.0, co2_ppm) / 400.0))
        potential = et0 * self.base_kc * co2_factor
        # This simplified depth response represents reduced accessible root-zone volume.
        root_access = min(1.0, self.max_root_depth_cm / 120.0)
        actual = potential * self.feddes_reduction_factor(soil_moisture_vol) * root_access
        cwsi = max(0.0, min(1.0, 1.0 - actual / max(1e-12, potential)))
        return {"et0_mm": round(et0, 6), "potential_transpiration_mm": round(potential, 6),
                "actual_transpiration_mm": round(actual, 6), "root_water_uptake_mm": round(actual, 6),
                "feddes_alpha": round(self.feddes_reduction_factor(soil_moisture_vol), 6),
                "cwsi_stress_index": round(cwsi, 6), "sap_flow_velocity_cmh": round(actual / 6.0 * 18.0, 6),
                "leaf_water_potential_mpa": round(-0.4 - cwsi * 1.8, 6),
                "stomatal_conductance_mmol": round(320.0 * (1.0 - cwsi * 0.85), 6)}

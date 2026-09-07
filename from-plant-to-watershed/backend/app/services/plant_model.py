import math
from typing import Dict, Any

class IndividualPlantPhysiologyModel:
    """
    Modelo Biofísico de Planta Individual a escala Micro:
    Calcula la transpiración real, conductancia estomática, absorción radicular
    según la función de reducción de Feddes y el índice de estrés hídrico (CWSI).
    """

    def __init__(
        self,
        base_kc: float = 1.05,
        max_root_depth_cm: float = 120.0,
        wilting_point_vol: float = 12.0,  # Punto de marchitez permanente (θ_wp en %)
        field_capacity_vol: float = 32.0, # Capacidad de campo (θ_fc en %)
        saturation_vol: float = 44.0      # Porosidad / Saturación (θ_sat en %)
    ):
        self.base_kc = base_kc
        self.max_root_depth_cm = max_root_depth_cm
        self.theta_wp = wilting_point_vol
        self.theta_fc = field_capacity_vol
        self.theta_sat = saturation_vol
        # Umbral crítico de agotamiento hídrico fácilmente aprovechable (RAW)
        self.theta_crit = wilting_point_vol + 0.55 * (field_capacity_vol - wilting_point_vol)

    def calculate_potential_et(self, temp_c: float, solar_rad_mj: float, rh_percent: float) -> float:
        """
        Calcula la Evapotranspiración de Referencia (ET0 en mm/día)
        utilizando la aproximación de Turc / Hargreaves-Samani calibrada.
        """
        # Estimación de ET0 por balance de radiación térmica
        if temp_c <= 0:
            return 0.2
        # Fórmula de Turc para climas templados/semiáridos
        et0 = 0.013 * (temp_c / (temp_c + 15.0)) * (23.885 * (solar_rad_mj * 0.408) + 50.0)
        if rh_percent < 50.0:
            et0 *= (1.0 + (50.0 - rh_percent) / 70.0)
        return max(0.5, round(et0, 2))

    def feddes_reduction_factor(self, soil_moisture_vol: float) -> float:
        """
        Función de reducción de absorción de agua radicular de Feddes (α):
        Varía entre 0.0 (estrés hídrico extremo / anoxia) y 1.0 (absorción óptima).
        """
        theta = max(0.0, min(self.theta_sat, soil_moisture_vol))

        # 1. Zona de anoxia (suelo anegado/saturado, raíces sin oxígeno)
        if theta > self.theta_sat - 2.0:
            return 0.35

        # 2. Zona óptima de transpiración (entre capacidad de campo y umbral crítico)
        if theta >= self.theta_crit:
            return 1.0

        # 3. Zona de estrés hídrico (entre umbral crítico y punto de marchitez permanente)
        if theta > self.theta_wp:
            alpha = (theta - self.theta_wp) / (self.theta_crit - self.theta_wp)
            return max(0.05, min(1.0, alpha))

        # 4. Por debajo del punto de marchitez: cesa la absorción
        return 0.0

    def compute_daily_plant_step(
        self,
        temp_c: float,
        solar_rad_mj: float,
        rh_percent: float,
        soil_moisture_vol: float,
        co2_ppm: float = 415.0
    ) -> Dict[str, Any]:
        """
        Calcula el paso diario completo de la planta individual acoplada al suelo.
        """
        et0 = self.calculate_potential_et(temp_c, solar_rad_mj, rh_percent)

        # Efecto de fertilización por CO2 en conductancia estomática
        # (Mayor CO2 incrementa ligeramente la eficiencia en uso del agua WUE)
        co2_efficiency_factor = 1.0 - 0.05 * math.log(max(400.0, co2_ppm) / 400.0)

        potential_transpiration = et0 * self.base_kc * co2_efficiency_factor

        # Factor de Feddes dependiente de la humedad radicular
        alpha = self.feddes_reduction_factor(soil_moisture_vol)

        # Transpiración real de la planta (mm/día)
        actual_transpiration = round(potential_transpiration * alpha, 2)

        # Absorción radicular en el perfil (Root Water Uptake - RWU)
        root_water_uptake = actual_transpiration

        # Índice de estrés hídrico del cultivo (CWSI)
        # 0 = sin estrés, 1 = estrés total / marchitez
        cwsi = round(1.0 - (actual_transpiration / max(0.1, potential_transpiration)), 3)
        cwsi = max(0.0, min(1.0, cwsi))

        # Velocidad de flujo de savia en el xilema (cm/h durante horas diurnas)
        # Escala típica: 2 - 25 cm/h
        sap_flow_velocity = round(2.5 + (actual_transpiration / 6.0) * 18.0, 2)

        # Potencial hídrico foliar estimado Ψ_leaf (MPa, valores negativos: -0.4 óptimo a -2.5 severo)
        leaf_water_potential_mpa = round(-0.4 - (cwsi * 1.8), 2)

        # Conductancia estomática g_s (mmol / m²·s)
        stomatal_conductance = round(320.0 * (1.0 - cwsi * 0.85), 1)

        return {
            "et0_mm": et0,
            "potential_transpiration_mm": round(potential_transpiration, 2),
            "actual_transpiration_mm": actual_transpiration,
            "root_water_uptake_mm": root_water_uptake,
            "feddes_alpha": round(alpha, 3),
            "cwsi_stress_index": cwsi,
            "sap_flow_velocity_cmh": sap_flow_velocity,
            "leaf_water_potential_mpa": leaf_water_potential_mpa,
            "stomatal_conductance_mmol": stomatal_conductance
        }

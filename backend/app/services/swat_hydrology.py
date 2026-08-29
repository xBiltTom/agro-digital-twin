from typing import Dict, Any

class SWATHydrologyEngine:
    """
    Motor Hidrológico a Escala de Cuenca basado en las ecuaciones de balance de SWAT:
    - Escorrentía superficial por el método de la Curva Número SCS (USDA-NRCS).
    - Percolación entre horizontes y recarga de acuífero poco profundo.
    - Flujo base y tránsito de caudales en la red de drenaje fluvial (m³/s).
    """

    def __init__(
        self,
        watershed_area_km2: float = 420.5,
        curve_number: float = 74.0,
        soil_profile_depth_mm: float = 1000.0,
        initial_soil_moisture_vol: float = 24.0
    ):
        self.area_km2 = watershed_area_km2
        self.curve_number = curve_number
        self.profile_depth_mm = soil_profile_depth_mm
        
        # Parámetros edáficos del perfil de suelo
        self.theta_sat = 44.0  # Saturación (%)
        self.theta_fc = 32.0   # Capacidad de campo (%)
        self.theta_wp = 12.0   # Punto de marchitez (%)

        # Agua disponible máxima a capacidad de campo (mm)
        self.fc_depth_mm = self.profile_depth_mm * (self.theta_fc / 100.0) # ~320 mm
        self.sat_depth_mm = self.profile_depth_mm * (self.theta_sat / 100.0) # ~440 mm
        
        # Almacenamiento inicial de agua en el suelo (mm)
        self.soil_water_mm = self.profile_depth_mm * (initial_soil_moisture_vol / 100.0)
        
        # Almacenamiento en acuífero somero para flujo base (mm)
        self.groundwater_storage_mm = 65.0

    def calculate_scs_runoff(self, precip_mm: float, soil_moisture_vol: float) -> float:
        """
        Calcula la escorrentía superficial Q_surf mediante la Curva Número SCS (SWAT estándar),
        ajustando el CN según la condición de humedad antecedente (AMC I, II, III).
        """
        if precip_mm <= 0.0:
            return 0.0

        # Ajuste dinámico de CN por condición de humedad antecedente
        # Si el suelo está muy húmedo (> capacidad de campo), CN sube hacia AMC III
        cn = self.curve_number
        if soil_moisture_vol > self.theta_fc:
            # Aproximación polinómica SWAT para AMC III
            cn = cn / (0.4036 + 0.0059 * cn)
        elif soil_moisture_vol < self.theta_wp * 1.3:
            # Aproximación SWAT para AMC I (suelo seco)
            cn = (4.2 * cn) / (10.0 - 0.058 * cn)

        cn = max(35.0, min(98.0, cn))

        # Máxima retención potencial del suelo S (mm)
        s_retention = (25400.0 / cn) - 254.0
        # Abstracción inicial Ia (por defecto 0.2 * S en SWAT)
        initial_abstraction = 0.2 * s_retention

        if precip_mm <= initial_abstraction:
            return 0.0

        # Ecuación de escorrentía superficial SCS
        numerator = (precip_mm - initial_abstraction) ** 2
        denominator = (precip_mm - initial_abstraction) + s_retention
        runoff_mm = round(numerator / denominator, 2)
        return min(precip_mm, runoff_mm)

    def calculate_daily_step(
        self,
        precip_mm: float,
        plant_transpiration_mm: float,
        potential_et_mm: float,
        irrigation_mm: float = 0.0
    ) -> Dict[str, Any]:
        """
        Ejecuta el balance hidrológico diario de SWAT acoplado con la planta:
        SW_t = SW_{t-1} + R_{day} + I_{irr} - Q_{surf} - E_a - w_{seep} - Q_{gw}
        """
        # Humedad volumétrica previa
        prev_vol = (self.soil_water_mm / self.profile_depth_mm) * 100.0

        # 1. Escorrentía superficial
        q_surf_mm = self.calculate_scs_runoff(precip_mm, prev_vol)

        # 2. Infiltración neta en la zona radicular
        water_infiltrated_mm = max(0.0, (precip_mm - q_surf_mm) + irrigation_mm)
        self.soil_water_mm += water_infiltrated_mm

        # 3. Evapotranspiración Real (Ea)
        # Se compone de la transpiración calculada por el modelo de planta + evaporación del suelo
        soil_evaporation_mm = round(max(0.1, (potential_et_mm - plant_transpiration_mm) * 0.35 * (prev_vol / self.theta_fc)), 2)
        actual_et_mm = round(min(self.soil_water_mm * 0.6, plant_transpiration_mm + soil_evaporation_mm), 2)
        self.soil_water_mm = max(0.0, self.soil_water_mm - actual_et_mm)

        # 4. Percolación a acuífero profundo (w_seep) cuando supera capacidad de campo
        percolation_mm = 0.0
        if self.soil_water_mm > self.fc_depth_mm:
            excess_water = self.soil_water_mm - self.fc_depth_mm
            # Tasa de conductividad hidráulica insaturada SWAT
            percolation_mm = round(excess_water * 0.45, 2)
            self.soil_water_mm -= percolation_mm
            self.groundwater_storage_mm += percolation_mm

        # Limitar suelo a saturación física máxima
        if self.soil_water_mm > self.sat_depth_mm:
            overflow = self.soil_water_mm - self.sat_depth_mm
            q_surf_mm += overflow
            self.soil_water_mm = self.sat_depth_mm

        # 5. Flujo base del acuífero (Q_gw) hacia el río
        # Coeficiente de recesión de flujo base alfa_bf ~ 0.048
        baseflow_mm = round(self.groundwater_storage_mm * 0.045, 2)
        self.groundwater_storage_mm = max(20.0, self.groundwater_storage_mm - baseflow_mm)

        # 6. Humedad volumétrica resultante (%)
        current_moisture_vol = round((self.soil_water_mm / self.profile_depth_mm) * 100.0, 2)

        # 7. Caudal en el punto de salida de la cuenca (m³/s)
        # Caudal total = (Escorrentía superficial + Flujo base) integrado sobre el área de la cuenca
        total_runoff_mm = q_surf_mm + baseflow_mm
        # Factor de conversión: 1 mm sobre 1 km² = 1,000 m³ / día = (1,000 / 86400) m³/s ≈ 0.011574 m³/s
        streamflow_m3s = round(total_runoff_mm * self.area_km2 * (1000.0 / 86400.0), 2)
        # Caudal ecológico base mínimo en estiaje
        streamflow_m3s = max(0.45, streamflow_m3s)

        return {
            "surface_runoff_mm": q_surf_mm,
            "actual_et_mm": actual_et_mm,
            "soil_evaporation_mm": soil_evaporation_mm,
            "percolation_mm": percolation_mm,
            "baseflow_mm": baseflow_mm,
            "soil_water_depth_mm": round(self.soil_water_mm, 1),
            "soil_moisture_vol": current_moisture_vol,
            "streamflow_m3s": streamflow_m3s
        }

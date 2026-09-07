import math
import random
from typing import List, Dict, Any

class DownscaledClimateEngine:
    """Motor generador de forzamiento climático a escala diaria acoplado a escenarios CMIP6."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_daily_weather(
        self,
        duration_days: int = 365,
        temp_anomaly_c: float = 0.0,
        precip_factor: float = 1.0,
        co2_ppm: float = 415.0
    ) -> List[Dict[str, Any]]:
        """
        Genera una serie temporal meteorológica diaria sintética calibrada con estacionalidad,
        modulada por las proyecciones climáticas downscaled seleccionadas.
        """
        weather_series = []

        # Parámetros base de cuenca de montaña / valle agrícola interandino
        base_temp_mean = 17.5 + temp_anomaly_c
        temp_amplitude = 4.5
        annual_base_rain_mm = 850.0 * precip_factor

        # Probabilidad de lluvia por estación (pico de lluvias en meses 1-4: Ene-Abr)
        for day in range(1, duration_days + 1):
            day_of_year = (day - 1) % 365 + 1
            # Radián para ciclo anual estacional
            rad = 2 * math.pi * (day_of_year - 80) / 365.0

            # Temperatura diaria con ruido Gaussiano
            seasonal_temp = base_temp_mean + temp_amplitude * math.sin(rad)
            daily_temp = round(seasonal_temp + self.rng.gauss(0, 1.4), 2)

            # Radiación solar extraterrestre y a nivel de superficie (MJ/m²·día)
            base_radiation = 19.5 + 4.0 * math.sin(rad + 0.3)
            solar_radiation = max(8.0, round(base_radiation + self.rng.gauss(0, 2.0), 2))

            # Probabilidad de precipitación estacional (alta en verano austral)
            rain_prob = 0.45 + 0.35 * math.cos(2 * math.pi * (day_of_year - 45) / 365.0)
            # Modulador de sequía bajo escenarios de altas emisiones
            if temp_anomaly_c > 2.0:
                rain_prob *= 0.85

            is_rain_day = self.rng.random() < rain_prob

            if is_rain_day:
                # Distribución Gamma/Exponencial para intensidad de lluvia
                mean_depth = 12.0 * precip_factor
                # Eventos extremos ocasionales (convección / El Niño)
                if self.rng.random() < 0.08:
                    precip_mm = round(self.rng.expovariate(1.0 / (mean_depth * 2.8)), 2)
                else:
                    precip_mm = round(self.rng.expovariate(1.0 / mean_depth), 2)
                precip_mm = min(120.0, max(0.5, precip_mm))
                rh_percent = min(98.0, round(75.0 + precip_mm * 0.8 + self.rng.gauss(0, 5), 1))
            else:
                precip_mm = 0.0
                rh_percent = max(28.0, round(52.0 - (daily_temp - base_temp_mean) * 1.5 + self.rng.gauss(0, 6), 1))

            weather_series.append({
                "day_index": day,
                "temp_c": daily_temp,
                "precip_mm": precip_mm,
                "solar_rad_mj": solar_radiation,
                "rh_percent": rh_percent,
                "co2_ppm": co2_ppm
            })

        return weather_series

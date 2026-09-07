import math
import random
from typing import Any

from .provenance import EvidenceType, Provenance


class SyntheticClimateProvider:
    """Seeded synthetic daily weather for tests and demos; not observed or CMIP6 data."""

    VERSION = "1.0"

    def __init__(self, seed: int = 42):
        if not 0 <= seed <= 2**32 - 1:
            raise ValueError("seed must be an unsigned 32-bit integer")
        self.seed = seed

    @property
    def provenance(self) -> Provenance:
        return Provenance(
            model=self.__class__.__name__, implementation_version=self.VERSION,
            evidence_type=EvidenceType.SYNTHETIC, spatial_support="representative watershed forcing",
            temporal_support="daily", units={"temp_c": "degC", "precip_mm": "mm/day", "solar_rad_mj": "MJ/m2/day", "rh_percent": "%"},
        )

    def generate_daily_weather(self, duration_days: int = 365, temp_anomaly_c: float = 0.0,
                               precip_factor: float = 1.0, co2_ppm: float = 415.0) -> list[dict[str, Any]]:
        if duration_days < 1 or precip_factor < 0:
            raise ValueError("duration_days must be positive and precip_factor non-negative")
        rng = random.Random(self.seed)
        series: list[dict[str, Any]] = []
        base_temp_mean = 17.5 + temp_anomaly_c
        for day in range(1, duration_days + 1):
            day_of_year = (day - 1) % 365 + 1
            rad = 2 * math.pi * (day_of_year - 80) / 365.0
            daily_temp = round(base_temp_mean + 4.5 * math.sin(rad) + rng.gauss(0, 1.4), 2)
            solar = max(8.0, round(19.5 + 4.0 * math.sin(rad + 0.3) + rng.gauss(0, 2.0), 2))
            rain_prob = 0.45 + 0.35 * math.cos(2 * math.pi * (day_of_year - 45) / 365.0)
            if temp_anomaly_c > 2.0:
                rain_prob *= 0.85
            if rng.random() < rain_prob and precip_factor > 0:
                mean_depth = 12.0 * precip_factor
                scale = mean_depth * (2.8 if rng.random() < 0.08 else 1.0)
                precip = min(120.0, max(0.5, round(rng.expovariate(1.0 / scale), 2)))
                humidity = min(98.0, round(75.0 + precip * 0.8 + rng.gauss(0, 5), 1))
            else:
                precip = 0.0
                humidity = max(28.0, round(52.0 - (daily_temp - base_temp_mean) * 1.5 + rng.gauss(0, 6), 1))
            series.append({"day_index": day, "temp_c": daily_temp, "precip_mm": precip,
                           "solar_rad_mj": solar, "rh_percent": humidity, "co2_ppm": co2_ppm})
        return series

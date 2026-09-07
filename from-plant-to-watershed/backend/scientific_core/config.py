from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Mapping


SUPPORTED_PARAMETERS = frozenset({
    "base_kc",
    "max_root_depth_cm",
    "curve_number",
    "initial_soil_moisture_vol",
    "irrigation_mm_per_day",
})


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    seed: int
    duration_days: int
    watershed_area_km2: float
    temp_anomaly_c: float = 0.0
    precip_factor: float = 1.0
    co2_ppm: float = 415.0
    start_date: date = date(2026, 1, 1)
    parameters: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.parameters) - SUPPORTED_PARAMETERS
        if unknown:
            raise ValueError(f"Unsupported scientific parameters: {', '.join(sorted(unknown))}")
        if not 1 <= self.duration_days <= 3650:
            raise ValueError("duration_days must be between 1 and 3650")
        if not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("seed must be an unsigned 32-bit integer")
        if self.watershed_area_km2 <= 0:
            raise ValueError("watershed_area_km2 must be positive")
        if self.precip_factor < 0:
            raise ValueError("precip_factor cannot be negative")
        ranges = {
            "base_kc": (0.1, 2.0),
            "max_root_depth_cm": (1.0, 500.0),
            "curve_number": (30.0, 98.0),
            "initial_soil_moisture_vol": (0.0, 44.0),
            "irrigation_mm_per_day": (0.0, 100.0),
        }
        for name, value in self.parameters.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            low, high = ranges[name]
            if not low <= float(value) <= high:
                raise ValueError(f"{name} must be between {low} and {high}")

    def effective_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["start_date"] = self.start_date.isoformat()
        values["parameters"] = {
            "base_kc": 1.05,
            "max_root_depth_cm": 120.0,
            "curve_number": 74.0,
            "initial_soil_moisture_vol": 24.5,
            "irrigation_mm_per_day": 0.0,
            **{key: float(value) for key, value in self.parameters.items()},
        }
        return values

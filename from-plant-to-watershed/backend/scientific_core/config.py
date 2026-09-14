from dataclasses import asdict, dataclass, field
from datetime import date
import re
from typing import Any, Mapping


SUPPORTED_PARAMETERS = frozenset({
    "base_kc",
    "max_root_depth_cm",
    "curve_number",
    "initial_soil_moisture_vol",
    "irrigation_mm_per_day",
})

MANAGEMENT_SCENARIOS = frozenset({"BASELINE", "NO_TILL", "MAIZE_TO_SORGHUM"})
CLIMATE_SOURCES = frozenset({"SYNTHETIC", "CMIP6_FILE", "OBSERVED", "OBSERVED_HYBRID"})
DATASET_ROLES = frozenset({"FORCING", "OBSERVATION", "SOIL_INPUT", "LAND_COVER", "YIELD_OBSERVATION", "VALIDATION", "CONTEXT_ONLY"})


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    seed: int
    duration_days: int
    watershed_area_km2: float
    start_date: date
    end_date: date
    temp_anomaly_c: float = 0.0
    precip_factor: float = 1.0
    co2_ppm: float = 415.0
    parameters: Mapping[str, float] = field(default_factory=dict)
    management_scenario: str = "BASELINE"
    climate_source: str = "SYNTHETIC"
    station_id: str | None = None
    dataset_ids: tuple[str, ...] = ()
    dataset_roles: Mapping[str, str] = field(default_factory=dict)

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
        if self.management_scenario not in MANAGEMENT_SCENARIOS:
            raise ValueError(f"Unsupported management_scenario: {self.management_scenario}")
        if self.climate_source not in CLIMATE_SOURCES:
            raise ValueError(f"Unsupported climate_source: {self.climate_source}")
        if self.station_id is not None and not re.fullmatch(r"\d{8,15}", self.station_id):
            raise ValueError("station_id must contain 8 to 15 digits")
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if (self.end_date - self.start_date).days + 1 != self.duration_days:
            raise ValueError("duration_days must equal the inclusive start_date/end_date period")
        unknown_role_ids = set(self.dataset_roles) - set(self.dataset_ids)
        if unknown_role_ids:
            raise ValueError("dataset_roles may only reference dataset_ids")
        invalid_roles = set(self.dataset_roles.values()) - DATASET_ROLES
        if invalid_roles:
            raise ValueError(f"Unsupported dataset role: {', '.join(sorted(invalid_roles))}")
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
        values["end_date"] = self.end_date.isoformat()
        values["dataset_ids"] = list(self.dataset_ids)
        values["dataset_roles"] = dict(self.dataset_roles)
        values["parameters"] = {
            "base_kc": 1.05,
            "max_root_depth_cm": 120.0,
            "curve_number": 74.0,
            "initial_soil_moisture_vol": 24.5,
            "irrigation_mm_per_day": 0.0,
            **{key: float(value) for key, value in self.parameters.items()},
        }
        return values

    def management_effects(self) -> dict[str, Any]:
        """Declared, small-scope management adjustments for the academic MVP."""
        effective = self.effective_dict()["parameters"]
        if self.management_scenario == "NO_TILL":
            effective["curve_number"] = max(30.0, effective["curve_number"] - 4.0)
            return {
                "scenario": "NO_TILL", "crop": "maize",
                "curve_number_adjustment": -4.0,
                "statement": "MVP conservation-tillage proxy; not a calibrated SWAT+ management operation.",
                "parameters": effective,
            }
        if self.management_scenario == "MAIZE_TO_SORGHUM":
            effective["base_kc"] = min(effective["base_kc"], 0.92)
            effective["max_root_depth_cm"] = max(effective["max_root_depth_cm"], 145.0)
            return {
                "scenario": "MAIZE_TO_SORGHUM", "crop": "sorghum_proxy",
                "curve_number_adjustment": 0.0,
                "statement": "MVP crop-substitution proxy; it is not a calibrated sorghum crop model.",
                "parameters": effective,
            }
        return {
            "scenario": "BASELINE", "crop": "maize", "curve_number_adjustment": 0.0,
            "statement": "Baseline maize management.", "parameters": effective,
        }

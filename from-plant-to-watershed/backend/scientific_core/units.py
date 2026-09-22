from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AggregationRecord:
    source_unit: str
    destination_unit: str
    spatial_support: str
    temporal_support: str
    method: str


def validate_soil_moisture_vol_percent(value: float) -> float:
    """Validate volumetric soil water in percent [0, 100], not fraction or mm.

    Values below 1% are possible, so this function cannot infer the caller's
    intended unit. Fractional sources must call the explicit converter below.
    """
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("soil_moisture_vol must be finite volumetric percent in [0, 100]")
    return float(value)


def soil_moisture_fraction_to_vol_percent(fraction: float) -> float:
    """Convert a documented volumetric fraction [0, 1] to percent [0, 100]."""
    if not isinstance(fraction, (int, float)) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("soil moisture fraction must be finite and in [0, 1]")
    return float(fraction) * 100.0


# Existing South Fork fixed 0.24 volumetric fraction. Its origin is not
# calibrated here; it is not inferred from SWAT+ soil-water storage.
ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT = soil_moisture_fraction_to_vol_percent(0.24)


def litres_per_plant_day_to_mm_day(litres_per_plant_day: float, plants: int, field_area_m2: float) -> float:
    """Convert plant volume to field water depth (1 L/m2 == 1 mm)."""
    if litres_per_plant_day < 0 or plants < 0 or field_area_m2 <= 0:
        raise ValueError("volume and plant count cannot be negative; area must be positive")
    return litres_per_plant_day * plants / field_area_m2

from dataclasses import dataclass


@dataclass(frozen=True)
class AggregationRecord:
    source_unit: str
    destination_unit: str
    spatial_support: str
    temporal_support: str
    method: str


def litres_per_plant_day_to_mm_day(litres_per_plant_day: float, plants: int, field_area_m2: float) -> float:
    """Convert plant volume to field water depth (1 L/m2 == 1 mm)."""
    if litres_per_plant_day < 0 or plants < 0 or field_area_m2 <= 0:
        raise ValueError("volume and plant count cannot be negative; area must be positive")
    return litres_per_plant_day * plants / field_area_m2

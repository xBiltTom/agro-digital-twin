"""Deterministic simplified plant-population, field, and coarse-HRU coupling."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
from statistics import fmean, pstdev
from typing import Any, Iterable

from .plant import SimplifiedPlantModel


@dataclass(frozen=True)
class PlantState:
    plant_id: str
    x_m: float
    y_m: float
    base_kc: float
    root_depth_cm: float
    soil_moisture_offset: float
    lai: float = 0.0
    transpiration_mm: float = 0.0
    stress: float = 0.0


class PlantPopulation:
    """Seeded maize population. Variability is bounded and used by the model."""

    VERSION = "1.0"

    def __init__(self, count: int = 1000, seed: int = 42, *, base_kc: float = 1.05,
                 max_root_depth_cm: float = 120.0, crop: str = "maize"):
        if not 1 <= count <= 10_000:
            raise ValueError("plant_count must be between 1 and 10000")
        self.count, self.seed, self.crop = count, seed, crop
        self._base_kc, self._max_root_depth_cm = base_kc, max_root_depth_cm
        rng = random.Random(seed)
        columns = max(1, math.ceil(math.sqrt(count)))
        self.plants = tuple(
            PlantState(
                plant_id=f"maize-{index + 1:05d}",
                x_m=round((index % columns) * 0.75 + rng.uniform(-0.05, 0.05), 4),
                y_m=round((index // columns) * 0.20 + rng.uniform(-0.02, 0.02), 4),
                base_kc=max(0.55, min(1.30, rng.gauss(base_kc, 0.08))),
                root_depth_cm=max(50.0, min(220.0, rng.gauss(max_root_depth_cm, 14.0))),
                soil_moisture_offset=max(-3.0, min(3.0, rng.gauss(0.0, 1.1))),
            ) for index in range(count)
        )

    def step(self, day_index: int, forcing: dict[str, float], soil_moisture_vol: float) -> tuple[PlantState, ...]:
        season = max(0.0, math.sin(math.pi * min(180, max(0, day_index - 20)) / 180.0))
        peak_lai = 4.2 if self.crop == "sorghum_proxy" else 5.2
        states = []
        for plant in self.plants:
            model = SimplifiedPlantModel(plant.base_kc, plant.root_depth_cm)
            moisture = max(0.0, soil_moisture_vol + plant.soil_moisture_offset)
            result = model.compute_daily_plant_step(
                forcing["temp_c"], forcing["solar_rad_mj"], forcing["rh_percent"], moisture, forcing["co2_ppm"]
            )
            lai = max(0.05, min(7.0, peak_lai * season * (1.0 - 0.55 * result["cwsi_stress_index"])))
            states.append(PlantState(
                **{key: getattr(plant, key) for key in ("plant_id", "x_m", "y_m", "base_kc", "root_depth_cm", "soil_moisture_offset")},
                lai=round(lai, 6), transpiration_mm=result["actual_transpiration_mm"],
                stress=result["cwsi_stress_index"],
            ))
        return tuple(states)


class PlantToFieldAggregator:
    @staticmethod
    def aggregate(plants: Iterable[PlantState], soil_moisture_vol: float) -> dict[str, Any]:
        rows = tuple(plants)
        if not rows:
            raise ValueError("at least one plant is required")
        values = {
            "lai": [p.lai for p in rows], "root_depth_cm": [p.root_depth_cm for p in rows],
            "transpiration_mm": [p.transpiration_mm for p in rows], "stress": [p.stress for p in rows],
        }
        result: dict[str, Any] = {"n_plants": len(rows), "soil_moisture_vol": soil_moisture_vol}
        for name, series in values.items():
            ordered = sorted(series)
            result[f"mean_{name}"] = fmean(series)
            result[f"std_{name}"] = pstdev(series)
            result[f"p10_{name}"] = ordered[int((len(ordered) - 1) * .10)]
            result[f"p90_{name}"] = ordered[int((len(ordered) - 1) * .90)]
        result["et_mm"] = result["mean_transpiration_mm"]
        result["evidence_type"] = "DERIVED"
        result["provenance"] = {"source": "SimplifiedPlantModel population", "aggregation": "unweighted population statistics"}
        return result


@dataclass(frozen=True)
class HRUProxy:
    hru_id: str
    area_km2: float
    area_fraction: float
    crop: str
    soil_type: str
    curve_number: float
    evidence_type: str = "COARSE_HRU_PROXY"


class FieldToHRUCoupler:
    """Explicit area-weighted mapping; these are not SWAT+ HRUs."""

    def __init__(self, watershed_area_km2: float, *, curve_number_delta: float = 0.0, crop: str = "maize"):
        self.hrus = (
            HRUProxy("proxy-crop", watershed_area_km2 * .60, .60, crop, "loam", 74.0 + curve_number_delta),
            HRUProxy("proxy-soy", watershed_area_km2 * .25, .25, "soy_proxy", "loam", 72.0 + curve_number_delta),
            HRUProxy("proxy-other", watershed_area_km2 * .15, .15, "other", "mixed", 70.0 + curve_number_delta),
        )

    def couple(self, field: dict[str, Any]) -> dict[str, Any]:
        crop_factor = {"maize": 1.0, "sorghum_proxy": .92, "soy_proxy": .83, "other": .68}
        soil_offset = {"loam": 0.0, "mixed": -1.25}
        mapped = []
        for hru in self.hrus:
            modifier = crop_factor.get(hru.crop, .75)
            mapped.append({**asdict(hru), "field_inputs": {
                "transpiration_mm_day": field["mean_transpiration_mm"] * modifier,
                "root_depth_cm": field["mean_root_depth_cm"] * (1.0 if hru.crop in {"maize", "sorghum_proxy"} else .82),
                "soil_moisture_vol": max(0.0, field["soil_moisture_vol"] + soil_offset.get(hru.soil_type, 0.0)),
                "stress": min(1.0, field["mean_stress"] + (1.0 - modifier) * .12),
            }})
        return {"count": len(mapped), "hrus": mapped, "area_fraction_sum": sum(h.area_fraction for h in self.hrus),
                "resolution": "daily", "evidence_type": "COARSE_HRU_PROXY"}

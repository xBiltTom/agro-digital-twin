"""Deterministic maize FSPM, aggregation, and the legacy proxy HRU contract.

The population is intentionally lightweight: individual parameters are sampled once
from a seeded distribution and the daily state equations are evaluated in a vector
style loop.  It is a transparent crop-state model, not an alternative hydrology
engine.  Real SWAT+ coupling is implemented by ``SwatPlantParameterMapper``.
"""

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
    phenological_stage: str = "SOWN"
    growing_degree_days_c_day: float = 0.0
    plant_height_m: float = 0.0
    leaf_count: float = 0.0
    leaf_area_m2: float = 0.0
    canopy_cover_fraction: float = 0.0
    root_depth_m: float = 0.05
    root_distribution: tuple[float, float, float] = (1.0, 0.0, 0.0)
    biomass_g_plant: float = 0.0
    potential_transpiration_mm_day: float = 0.0
    actual_transpiration_mm_day: float = 0.0
    soil_water_uptake_mm_day: float = 0.0
    estimated_yield_g_plant: float = 0.0
    leaf_area_scale: float = 1.0
    transpiration_capacity_scale: float = 1.0
    phenology_scale: float = 1.0
    biomass_response_scale: float = 1.0


class PlantPopulation:
    """Seeded maize population. Variability is bounded and used by the model."""

    VERSION = "2.0-maize-fspm"

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
                leaf_area_scale=max(.75, min(1.25, rng.gauss(1.0, .08))),
                transpiration_capacity_scale=max(.75, min(1.25, rng.gauss(1.0, .07))),
                phenology_scale=max(.88, min(1.12, rng.gauss(1.0, .04))),
                biomass_response_scale=max(.75, min(1.25, rng.gauss(1.0, .08))),
            ) for index in range(count)
        )

    def step(self, day_index: int, forcing: dict[str, float], soil_moisture_vol: float) -> tuple[PlantState, ...]:
        # A maize thermal-time state.  ``day_index`` is deliberately only the
        # calendar/management clock; every output is deterministic for seed +
        # forcing + soil + management/parameters.
        gdd = float(forcing.get("gdd_c_day", max(0.0, day_index * max(0.0, forcing["temp_c"] - 8.0))))
        peak_lai = 4.2 if self.crop == "sorghum_proxy" else 5.2
        states = []
        for plant in self.plants:
            model = SimplifiedPlantModel(plant.base_kc, plant.root_depth_cm)
            moisture = max(0.0, soil_moisture_vol + plant.soil_moisture_offset / 100.0)
            result = model.compute_daily_plant_step(
                forcing["temp_c"], forcing["solar_rad_mj"], forcing["rh_percent"], moisture, forcing["co2_ppm"]
            )
            scaled_gdd = gdd / plant.phenology_scale
            stage = "EMERGENCE" if scaled_gdd < 100 else "VEGETATIVE" if scaled_gdd < 650 else "REPRODUCTIVE" if scaled_gdd < 1200 else "MATURITY"
            # Smooth leaf expansion/senescence curve; LAI is m2 leaf / m2 soil.
            expansion = 1.0 / (1.0 + math.exp(-(scaled_gdd - 430.0) / 120.0))
            senescence = 1.0 if scaled_gdd < 1050 else max(0.05, 1.0 - (scaled_gdd - 1050.0) / 600.0)
            lai = max(0.0, min(7.0, peak_lai * plant.leaf_area_scale * expansion * senescence * (1.0 - .45 * result["cwsi_stress_index"])))
            root_depth_m = min(plant.root_depth_cm / 100.0, .08 + .00155 * scaled_gdd)
            height_m = min(2.8, 2.8 * (1.0 - math.exp(-scaled_gdd / 480.0)))
            leaf_count = min(22.0, max(0.0, 2.0 + scaled_gdd / 55.0))
            # The individual leaf area is reported explicitly; the field LAI is
            # still the canopy state used by the existing simplified contract.
            leaf_area = lai / 7.0 * .75
            potential = result["potential_transpiration_mm"] * plant.transpiration_capacity_scale
            actual = min(potential, result["actual_transpiration_mm"] * plant.transpiration_capacity_scale)
            biomass = max(0.0, (scaled_gdd / 1450.0) * 260.0 * plant.biomass_response_scale * (1.0 - .35 * result["cwsi_stress_index"]))
            distribution = (round(.60 if root_depth_m <= .3 else .45, 5), round(.30 if root_depth_m <= .3 else .35, 5), round(.10 if root_depth_m <= .3 else .20, 5))
            states.append(PlantState(
                **{key: getattr(plant, key) for key in ("plant_id", "x_m", "y_m", "base_kc", "root_depth_cm", "soil_moisture_offset", "leaf_area_scale", "transpiration_capacity_scale", "phenology_scale", "biomass_response_scale")},
                lai=round(lai, 6), transpiration_mm=actual, stress=result["cwsi_stress_index"],
                phenological_stage=stage, growing_degree_days_c_day=scaled_gdd,
                plant_height_m=height_m, leaf_count=leaf_count, leaf_area_m2=leaf_area,
                canopy_cover_fraction=1.0 - math.exp(-.5 * lai), root_depth_m=root_depth_m,
                root_distribution=distribution, biomass_g_plant=biomass,
                potential_transpiration_mm_day=potential, actual_transpiration_mm_day=actual,
                soil_water_uptake_mm_day=actual, estimated_yield_g_plant=biomass * (.5 if stage == "MATURITY" else 0.0),
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
        # Explicit field-scale contract for the real SWAT+ mapper.
        result.update({
            "mean_LAI": result["mean_lai"], "LAI_distribution": {"p10": result["p10_lai"], "p90": result["p90_lai"], "std": result["std_lai"], "unit": "m2_leaf/m2_ground"},
            "canopy_cover": fmean(p.canopy_cover_fraction for p in rows),
            "plant_height_mean_m": fmean(p.plant_height_m for p in rows),
            "root_depth_mean_m": fmean(p.root_depth_m for p in rows),
            "root_depth_distribution": {"p10_m": sorted(p.root_depth_m for p in rows)[int((len(rows)-1)*.10)], "p90_m": sorted(p.root_depth_m for p in rows)[int((len(rows)-1)*.90)]},
            "actual_ET_mm_day": fmean(p.actual_transpiration_mm_day for p in rows),
            "potential_ET_mm_day": fmean(p.potential_transpiration_mm_day for p in rows),
            "transpiration_mm_day": fmean(p.actual_transpiration_mm_day for p in rows),
            "soil_water_uptake_mm_day": fmean(p.soil_water_uptake_mm_day for p in rows),
            "water_stress": fmean(p.stress for p in rows), "biomass_g_plant": fmean(p.biomass_g_plant for p in rows),
            "yield_estimate_g_plant": fmean(p.estimated_yield_g_plant for p in rows),
            "units": {"mean_LAI": "m2_leaf/m2_ground", "canopy_cover": "fraction", "root_depth_mean_m": "m", "actual_ET_mm_day": "mm/day", "potential_ET_mm_day": "mm/day", "biomass_g_plant": "g/plant", "yield_estimate_g_plant": "g/plant"},
        })
        result["evidence_type"] = "DERIVED_FSPM"
        result["provenance"] = {"source": "SimplifiedPlantModel maize FSPM population", "version": PlantPopulation.VERSION, "aggregation": "unweighted population statistics", "units_explicit": True}
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

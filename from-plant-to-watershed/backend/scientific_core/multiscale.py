"""Deterministic simplified maize crop states and the legacy proxy HRU contract.

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
    radiation_use_efficiency_kg_ha_per_mj_m2: float = 40.0
    canopy_extinction_coefficient: float = 0.50
    thermal_maturity_gdd: float = 1450.0


class PlantPopulation:
    """Seeded, bounded-variability simplified maize crop population.

    The 1,000 members are deterministic representative plants, not a claim that
    the simulated HRU contains exactly 1,000 physical plants. The explicit
    field density is used only to make biomass units traceable.
    """

    VERSION = "3.0-simplified-fspm"

    def __init__(self, count: int = 1000, seed: int = 42, *, base_kc: float = 1.05,
                 max_root_depth_cm: float = 120.0, crop: str = "maize",
                 plant_density_plants_m2: float = 8.0,
                 biomass_energy_ratio_kg_ha_per_mj_m2: float = 40.0,
                 canopy_extinction_coefficient: float = 0.50,
                 thermal_maturity_gdd: float = 1450.0):
        if not 1 <= count <= 10_000:
            raise ValueError("plant_count must be between 1 and 10000")
        if not 1.0 <= plant_density_plants_m2 <= 20.0:
            raise ValueError("plant_density_plants_m2 must be in [1, 20]")
        if not 10.0 <= biomass_energy_ratio_kg_ha_per_mj_m2 <= 90.0:
            raise ValueError("biomass_energy_ratio_kg_ha_per_mj_m2 must be in [10, 90]")
        if not 0.05 <= canopy_extinction_coefficient <= 2.0:
            raise ValueError("canopy_extinction_coefficient must be in [0.05, 2]")
        if not 800.0 <= thermal_maturity_gdd <= 2200.0:
            raise ValueError("thermal_maturity_gdd must be in [800, 2200]")
        self.count, self.seed, self.crop = count, seed, crop
        self._base_kc, self._max_root_depth_cm = base_kc, max_root_depth_cm
        self.plant_density_plants_m2 = plant_density_plants_m2
        self.biomass_energy_ratio_kg_ha_per_mj_m2 = biomass_energy_ratio_kg_ha_per_mj_m2
        self.canopy_extinction_coefficient = canopy_extinction_coefficient
        self.thermal_maturity_gdd = thermal_maturity_gdd
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
                radiation_use_efficiency_kg_ha_per_mj_m2=max(10.0, min(90.0, rng.gauss(biomass_energy_ratio_kg_ha_per_mj_m2, 2.0))),
                canopy_extinction_coefficient=max(.05, min(2.0, rng.gauss(canopy_extinction_coefficient, .025))),
                thermal_maturity_gdd=thermal_maturity_gdd,
            ) for index in range(count)
        )

    def step(self, day_index: int, forcing: dict[str, float], soil_moisture_vol: float) -> tuple[PlantState, ...]:
        # A maize thermal-time state.  ``day_index`` is deliberately only the
        # calendar/management clock; every output is deterministic for seed +
        # forcing + soil + management/parameters.
        gdd = float(forcing.get("gdd_c_day", max(0.0, day_index * max(0.0, forcing["temp_c"] - 8.0))))
        peak_lai = 4.2 if self.crop == "sorghum_proxy" else 5.2
        cumulative_apar = max(0.0, float(forcing.get("cumulative_absorbed_par_mj_m2", 0.0)))
        states = []
        for plant in self.plants:
            model = SimplifiedPlantModel(plant.base_kc, plant.root_depth_cm)
            moisture = max(0.0, soil_moisture_vol + plant.soil_moisture_offset / 100.0)
            result = model.compute_daily_plant_step(
                forcing["temp_c"], forcing["solar_rad_mj"], forcing["rh_percent"], moisture, forcing["co2_ppm"]
            )
            scaled_gdd = gdd / plant.phenology_scale
            maturity_scale = plant.thermal_maturity_gdd / 1450.0
            stage = "EMERGENCE" if scaled_gdd < 100 * maturity_scale else "VEGETATIVE" if scaled_gdd < 650 * maturity_scale else "REPRODUCTIVE" if scaled_gdd < 1200 * maturity_scale else "MATURITY"
            # Smooth leaf expansion/senescence curve; LAI is m2 leaf / m2 soil.
            expansion = 1.0 / (1.0 + math.exp(-(scaled_gdd - 430.0 * maturity_scale) / (120.0 * maturity_scale)))
            senescence = 1.0 if scaled_gdd < 1050 * maturity_scale else max(0.05, 1.0 - (scaled_gdd - 1050.0 * maturity_scale) / (600.0 * maturity_scale))
            lai = max(0.0, min(7.0, peak_lai * plant.leaf_area_scale * expansion * senescence * (1.0 - .45 * result["cwsi_stress_index"])))
            root_depth_m = min(plant.root_depth_cm / 100.0, .08 + .00155 * scaled_gdd / maturity_scale)
            height_m = min(2.8, 2.8 * (1.0 - math.exp(-scaled_gdd / (480.0 * maturity_scale))))
            leaf_count = min(22.0, max(0.0, 2.0 + scaled_gdd / 55.0))
            # The individual leaf area is reported explicitly; the field LAI is
            # still the canopy state used by the existing simplified contract.
            leaf_area = lai / 7.0 * .75
            potential = result["potential_transpiration_mm"] * plant.transpiration_capacity_scale
            actual = min(potential, result["actual_transpiration_mm"] * plant.transpiration_capacity_scale)
            # kg/ha = RUE [kg/ha/(MJ/m2)] * absorbed PAR [MJ/m2]. Dividing
            # by 10 converts that field biomass to g/plant at plants/m2.
            biomass = max(0.0, plant.radiation_use_efficiency_kg_ha_per_mj_m2 * cumulative_apar /
                          (10.0 * self.plant_density_plants_m2) * plant.biomass_response_scale *
                          (1.0 - .35 * result["cwsi_stress_index"]))
            distribution = (round(.60 if root_depth_m <= .3 else .45, 5), round(.30 if root_depth_m <= .3 else .35, 5), round(.10 if root_depth_m <= .3 else .20, 5))
            states.append(PlantState(
                **{key: getattr(plant, key) for key in ("plant_id", "x_m", "y_m", "base_kc", "root_depth_cm", "soil_moisture_offset", "leaf_area_scale", "transpiration_capacity_scale", "phenology_scale", "biomass_response_scale", "radiation_use_efficiency_kg_ha_per_mj_m2", "canopy_extinction_coefficient", "thermal_maturity_gdd")},
                lai=round(lai, 6), transpiration_mm=actual, stress=result["cwsi_stress_index"],
                phenological_stage=stage, growing_degree_days_c_day=scaled_gdd,
                plant_height_m=height_m, leaf_count=leaf_count, leaf_area_m2=leaf_area,
                canopy_cover_fraction=1.0 - math.exp(-plant.canopy_extinction_coefficient * lai), root_depth_m=root_depth_m,
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
            "mean_growing_degree_days_c_day": fmean(p.growing_degree_days_c_day for p in rows),
            "mean_thermal_maturity_gdd": fmean(p.thermal_maturity_gdd for p in rows),
            "phenology_fraction": fmean(min(1.0, p.growing_degree_days_c_day / p.thermal_maturity_gdd) for p in rows),
            "canopy_extinction_coefficient": fmean(p.canopy_extinction_coefficient for p in rows),
            "biomass_energy_ratio_kg_ha_per_mj_m2": fmean(p.radiation_use_efficiency_kg_ha_per_mj_m2 for p in rows),
            "units": {"mean_LAI": "m2_leaf/m2_ground", "canopy_cover": "fraction", "root_depth_mean_m": "m", "actual_ET_mm_day": "mm/day", "potential_ET_mm_day": "mm/day", "biomass_g_plant": "g/plant", "yield_estimate_g_plant": "g/plant", "mean_growing_degree_days_c_day": "degC_day", "mean_thermal_maturity_gdd": "degC_day", "phenology_fraction": "fraction", "canopy_extinction_coefficient": "dimensionless", "biomass_energy_ratio_kg_ha_per_mj_m2": "kg/ha/(MJ/m2)"},
        })
        result["evidence_type"] = "DERIVED_FSPM"
        result["provenance"] = {"source": "SIMPLIFIED_FSPM maize population", "version": PlantPopulation.VERSION, "aggregation": "unweighted population statistics", "units_explicit": True, "classification": "SIMPLIFIED_FSPM"}
        return result

    @staticmethod
    def seasonal_lai_contract(daily_fields: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """Derive SWAT+'s two LAI-growth points and senescence onset.

        Each row must be from a single crop season. A caller must split annual
        crops by season before using this method; silently spanning several
        maize years would make heat-unit fractions meaningless.
        """
        rows = tuple(daily_fields)
        if len(rows) < 3:
            raise ValueError("at least three daily field aggregates are required for a seasonal LAI contract")
        peak_index, peak = max(enumerate(rows), key=lambda item: float(item[1]["mean_LAI"]))
        peak_lai = float(peak["mean_LAI"])
        if peak_lai <= 0:
            raise ValueError("seasonal LAI contract requires a positive peak LAI")

        def growth_point(threshold: float) -> tuple[float, float]:
            row = next((item for item in rows[:peak_index + 1]
                        if float(item["mean_LAI"]) >= peak_lai * threshold), peak)
            return float(row["phenology_fraction"]), min(1.0, float(row["mean_LAI"]) / peak_lai)

        frac_hu1, lai_max1 = growth_point(.15)
        frac_hu2, lai_max2 = growth_point(.85)
        # First post-peak date at which green LAI has fallen by 2%; if the
        # supplied season stops before senescence, keep the seasonal end and
        # make the limitation visible in provenance.
        decline = next((item for item in rows[peak_index + 1:]
                        if float(item["mean_LAI"]) <= peak_lai * .98), rows[-1])
        return {
            "lai_pot": peak_lai,
            "frac_hu1": frac_hu1, "lai_max1": lai_max1,
            "frac_hu2": frac_hu2, "lai_max2": lai_max2,
            "hu_lai_decl": float(decline["phenology_fraction"]),
            "seasonal_peak_lai": peak_lai,
            "senescence_observed": decline is not rows[-1] or float(rows[-1]["mean_LAI"]) <= peak_lai * .98,
            "derivation": "15% and 85% of FSPM seasonal peak LAI; first 2% post-peak LAI decline",
        }


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

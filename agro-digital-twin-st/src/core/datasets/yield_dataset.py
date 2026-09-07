"""
Seasonal Yield Dataset Builder for Maize (Zea mays) in Corn Belt.
CRITICAL METHODOLOGICAL RIGOR (P0.5):
Eliminates artificial monthly zeros by aggregating monthly dynamics into
1 sample per HRU per growing season/year.

Growing Season for Maize in the Corn Belt:
- Planting & Vegetative: May to June (months 5-6)
- Reproductive & Flowering: July to August (months 7-8)
- Maturity & Harvest: September to October (months 9-10)
- Grain yield is recorded at end of season (October).
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def calculate_gdd(temp_mean_c: float, t_base: float = 10.0, t_cutoff: float = 30.0) -> float:
    """
    Calculates Growing Degree Days (GDD) for Maize with base temperature 10°C and cutoff 30°C.
    Standard agronomic formula: GDD = max(0.0, min(T_cutoff, T_mean) - T_base).
    """
    capped_temp = min(t_cutoff, max(t_base, temp_mean_c))
    return max(0.0, capped_temp - t_base)


def build_seasonal_yield_dataset(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms a monthly multi-scale ecohydrological dataset into an annual/seasonal
    crop yield dataset where 1 sample = 1 HRU × 1 growing season/year.

    Columns produced:
    - watershed_id
    - hru_id
    - year
    - seasonal_precip_mm
    - growing_season_temp_mean_c
    - gdd
    - seasonal_et_mm
    - seasonal_transpiration_mm
    - mean_soil_moisture
    - mean_water_stress
    - peak_lai
    - max_root_depth_m
    - climate_scenario
    - management_scenario
    - maize_yield_t_ha (Target: annual/seasonal yield in t/ha)

    SCIENTIFIC DOCUMENTATION & USDA NASS NOTICE:
    Real-world USDA NASS county-level yield data typically has spatial county granularity
    (FIPS code), whereas SWAT+ operates on HRUs. When coupling real observational USDA NASS data,
    an area-weighted spatial cross-walk (disaggregation / downscaling) must be performed.
    """
    df = monthly_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # Filter to growing season (May = 5 to October = 10)
    gs_df = df[(df["month"] >= 5) & (df["month"] <= 10)].copy()

    # Calculate monthly GDD approximation (30 days per month)
    gs_df["monthly_gdd"] = gs_df["temp_mean_c"].apply(calculate_gdd) * 30.0

    seasonal_records: List[Dict[str, Any]] = []

    # Group by (watershed_id, hru_id, year)
    group_keys = ["watershed_id", "hru_id", "year"]
    grouped = gs_df.groupby(group_keys, as_index=False)

    for (ws_id, hru_id, year), group in grouped:
        # Aggregations during the active growing season
        seasonal_precip = float(group["precip_mm"].sum())
        gs_temp_mean = float(group["temp_mean_c"].mean())
        total_gdd = float(group["monthly_gdd"].sum())
        seasonal_et = float(group["et_mm"].sum())
        seasonal_transp = float(group["transpiration_mm"].sum())
        mean_soil_moist = float(group["soil_moisture"].mean())
        mean_water_stress = float(group["water_stress"].mean())
        peak_lai = float(group["lai"].max())
        max_root_depth = float(group["root_depth_m"].max())

        climate_scen = group["climate_scenario"].iloc[0]
        mgmt_scen = group["management_scenario"].iloc[0]

        # Extract harvest yield from October (month 10)
        oct_row = group[group["month"] == 10]
        if not oct_row.empty and oct_row["maize_yield_t_ha"].iloc[0] > 0.0:
            yield_val = float(oct_row["maize_yield_t_ha"].iloc[0])
        else:
            # Fallback biological estimate if harvest row is missing
            is_sorghum = (mgmt_scen == "Maize_to_Sorghum")
            pot_yield = 9.5 if is_sorghum else 12.8
            yield_val = round(max(3.0, pot_yield - (mean_water_stress * 5.0) + (seasonal_precip * 0.005)), 2)

        seasonal_records.append({
            "watershed_id": ws_id,
            "hru_id": hru_id,
            "year": int(year),
            "date": f"{year}-10-01",  # Representative harvest date for chronological splitters
            "seasonal_precip_mm": round(seasonal_precip, 1),
            "growing_season_temp_mean_c": round(gs_temp_mean, 2),
            "gdd": round(total_gdd, 1),
            "seasonal_et_mm": round(seasonal_et, 1),
            "seasonal_transpiration_mm": round(seasonal_transp, 1),
            "mean_soil_moisture": round(mean_soil_moist, 2),
            "mean_water_stress": round(mean_water_stress, 3),
            "peak_lai": round(peak_lai, 2),
            "max_root_depth_m": round(max_root_depth, 2),
            "climate_scenario": climate_scen,
            "management_scenario": mgmt_scen,
            "maize_yield_t_ha": round(yield_val, 2),
            "is_synthetic": True,
            "data_provenance": "DEMO / SYNTHETIC DATA (Seasonal Maize Yield Aggregation)"
        })

    yield_df = pd.DataFrame(seasonal_records)
    yield_df["date"] = pd.to_datetime(yield_df["date"])
    yield_df = yield_df.sort_values(by=["year", "watershed_id", "hru_id"]).reset_index(drop=True)
    return yield_df

"""
Synthetic Multi-Scale Dataset Generator for AgroTwin-AI.
Research Context:
"From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models
with SWAT Hydrology and Downscaled Climate Projections"

IMPORTANT NOTICE:
This module produces DEMO / SYNTHETIC DATA for testing, development, and architectural validation.
It simulates realistic dynamics of Maize (Zea mays) in the US Corn Belt across 4 coupled scales:
  Level 1: Plant (FSPM: LAI, root depth, transpiration, water stress)
  Level 2: Field (~1000 plants aggregated with spatial heterogeneity)
  Level 3: Watershed (SWAT+ with HRUs: runoff, streamflow, infiltration, soil balance)
  Level 4: Climate (Historical, SSP2-4.5, SSP5-8.5, and management scenarios)

THIS IS NOT REAL USGS, USDA NASS, OR CMIP6 OBSERVATIONAL DATA.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

DATASET_SOURCE_LABEL = "DEMO / SYNTHETIC DATA (Plant-to-Watershed Simulator)"
IS_SYNTHETIC_DATA = True

# Corn Belt Watersheds & HRUs specification
DEFAULT_WATERSHEDS = ["WS_Cedar_01", "WS_Raccoon_02", "WS_Iowa_03"]
DEFAULT_HRUS_PER_WS = 3  # HRU_1 (silt loam, gentle slope), HRU_2 (clay loam), HRU_3 (sandy loam)
DEFAULT_CLIMATE_SCENARIOS = ["Historical", "SSP2-4.5", "SSP5-8.5"]
DEFAULT_MANAGEMENT_SCENARIOS = ["Baseline", "No-Till", "+2C_Warming", "-15pct_Precip", "Maize_to_Sorghum"]


class SyntheticMultiScaleDatasetGenerator:
    """
    Generates synthetic multi-scale eco-hydrological and agronomic data
    for Maize (Zea mays) in the Corn Belt coupled with SWAT+ watershed dynamics.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.is_synthetic = True
        self.source_label = DATASET_SOURCE_LABEL

    def generate(
        self,
        start_year: int = 2018,
        num_years: int = 6,
        watersheds: Optional[List[str]] = None,
        hrus_per_ws: int = DEFAULT_HRUS_PER_WS,
        climate_scenario: str = "Historical",
        management_scenario: str = "Baseline"
    ) -> pd.DataFrame:
        """
        Generates a monthly aggregated time-series dataset covering multiple watersheds and HRUs.
        """
        np.random.seed(self.seed)
        ws_list = watersheds or DEFAULT_WATERSHEDS
        records: List[Dict] = []

        total_months = num_years * 12

        # Climate adjustment factors
        temp_offset = 0.0
        precip_factor = 1.0
        if climate_scenario == "SSP2-4.5":
            temp_offset += 1.2
            precip_factor *= 1.05
        elif climate_scenario == "SSP5-8.5":
            temp_offset += 2.5
            precip_factor *= 0.92

        if management_scenario == "+2C_Warming":
            temp_offset += 2.0
        elif management_scenario == "-15pct_Precip":
            precip_factor *= 0.85

        # Soil parameters by HRU index
        hru_props = [
            {"name": "SiltLoam_Flat", "fc": 34.0, "wp": 14.0, "ksat_mm_h": 12.0, "cn2": 72},
            {"name": "ClayLoam_Rolling", "fc": 38.0, "wp": 20.0, "ksat_mm_h": 6.0, "cn2": 78},
            {"name": "SandyLoam_Upland", "fc": 26.0, "wp": 9.0, "ksat_mm_h": 25.0, "cn2": 66},
        ]

        # Management adjustments
        cn2_modifier = 0.0
        if management_scenario == "No-Till":
            cn2_modifier = -4.0  # Increases infiltration, reduces runoff

        is_sorghum = (management_scenario == "Maize_to_Sorghum")

        for ws_idx, ws_id in enumerate(ws_list):
            ws_area_km2 = 450.0 + (ws_idx * 150.0)  # Watershed size
            baseflow_baseline = 4.0 + (ws_idx * 1.8)

            for hru_sub in range(hrus_per_ws):
                hru_id = f"{ws_id}_HRU{hru_sub + 1}"
                props = hru_props[hru_sub % len(hru_props)]
                fc = props["fc"]
                wp = props["wp"]
                cn2 = props["cn2"] + cn2_modifier

                soil_moist = fc * 0.85

                for m_idx in range(total_months):
                    year = start_year + (m_idx // 12)
                    month = (m_idx % 12) + 1  # 1 to 12
                    date_str = f"{year}-{month:02d}-01"

                    # Corn Belt Seasonality (Northern Hemisphere, Iowa / Illinois climate)
                    # Winter: Jan-Feb (cold, sub-zero, snow)
                    # Spring: Apr-May (planting, rains)
                    # Summer: Jun-Aug (hot, peak growth, convective storms)
                    # Autumn: Sep-Oct (harvest, drying)
                    # Phase: peak in July (month 7)
                    seasonal_phase = math.sin(2 * math.pi * (month - 4) / 12.0)

                    # Temperature (°C)
                    t_mean_base = 10.5 + 16.0 * seasonal_phase + temp_offset
                    temp_mean = round(t_mean_base + np.random.normal(0, 1.5), 2)

                    # Precipitation (mm/month)
                    # Corn Belt: peak rain May-July (~90-130mm/mo), dry winter (~25-40mm/mo)
                    p_mean = (40.0 + 75.0 * max(0.0, seasonal_phase)) * precip_factor
                    precip_mm = round(max(5.0, float(np.random.gamma(shape=4.0, scale=p_mean / 4.0))), 1)

                    # Solar Radiation (MJ/m2/day)
                    sol_rad = round(max(6.0, 15.0 + 8.5 * seasonal_phase + np.random.normal(0, 1.2)), 2)

                    # Maize Phenology / Plant Scale (FSPM aggregated)
                    # Growing season: May (month 5) to October (month 10)
                    if 5 <= month <= 10:
                        grow_progress = (month - 5) / 5.0  # 0.0 to 1.0
                        if is_sorghum:
                            # Sorghum is more drought tolerant, slightly lower max LAI
                            max_lai = 4.2
                            root_depth_max = 1.6
                        else:
                            max_lai = 5.2
                            root_depth_max = 1.4

                        # Phenological curve (bell-shaped around July/August, month 7-8)
                        lai_curve = math.sin(math.pi * grow_progress) ** 1.8
                        lai = round(max(0.1, max_lai * lai_curve + np.random.normal(0, 0.15)), 2)
                        root_depth_m = round(max(0.15, root_depth_max * (1.0 / (1.0 + math.exp(-6.0 * (grow_progress - 0.3))))), 2)
                    else:
                        lai = 0.0
                        root_depth_m = 0.1

                    # Soil Water Balance & Feddes Water Stress
                    # Potential ET (mm/month)
                    pet_mm = max(10.0, (temp_mean + 5.0) * 4.2 + (sol_rad * 2.8))
                    if temp_mean < 0.0:
                        pet_mm = 8.0

                    # Infiltration via SCS-CN approximation
                    s_pot = (25400.0 / cn2) - 254.0
                    ia = 0.2 * s_pot
                    if precip_mm > ia:
                        runoff_est = ((precip_mm - ia) ** 2) / (precip_mm - ia + s_pot)
                    else:
                        runoff_est = 0.0

                    infil_mm = round(max(0.0, precip_mm - runoff_est), 1)

                    # Dynamic soil moisture update
                    soil_recharge_pct = (infil_mm / 300.0) * 100.0
                    soil_moist = min(fc * 1.15, max(wp * 0.7, soil_moist + soil_recharge_pct))

                    # Crop Water Stress Index [0, 1]
                    theta_crit = wp + 0.6 * (fc - wp)
                    if lai > 0.5:
                        if soil_moist >= theta_crit:
                            water_stress = round(max(0.0, np.random.normal(0.05, 0.03)), 3)
                        else:
                            stress_val = (theta_crit - soil_moist) / max(0.1, theta_crit - wp)
                            water_stress = round(min(1.0, max(0.0, stress_val + np.random.normal(0, 0.05))), 3)
                    else:
                        water_stress = 0.0

                    # Transpiration (mm/month)
                    if lai > 0.0:
                        pot_transp = (pet_mm * 0.65) * (1.0 - math.exp(-0.6 * lai))
                        transpiration_mm = round(max(0.0, pot_transp * (1.0 - water_stress)), 1)
                    else:
                        transpiration_mm = 0.0

                    # Total Evapotranspiration ET (soil evaporation + transpiration)
                    soil_evap = min(35.0, pet_mm * 0.3 * (soil_moist / fc))
                    et_mm = round(min(pet_mm, transpiration_mm + soil_evap), 1)

                    # Deplete soil moisture from ET
                    soil_moist = max(wp * 0.7, soil_moist - ((et_mm / 300.0) * 100.0))

                    # Level 3: SWAT+ Baseline Simulation (Standard uncoupled parameters)
                    # SWAT standard uses a static single crop table without individual plant architecture
                    swat_baseline_runoff = round(max(1.5, (runoff_est * 0.75) + (precip_mm * 0.08) + np.random.normal(0, 1.2)), 2)
                    swat_baseline_streamflow = round(max(0.8, baseflow_baseline + (swat_baseline_runoff * (ws_area_km2 / 1000.0) * 0.38) + np.random.normal(0, 0.4)), 2)

                    # Multi-scale "Observed-like" target:
                    # Incorporates feedback from root depth, plant transpiration, and spatial infiltration
                    # Multi-scale twin signal: higher LAI & root depth enhances soil infiltration and reduces surface quickflow
                    vegetation_attenuation = 1.0 - (0.22 * min(1.0, lai / 4.5))
                    root_channeling = 0.08 * (root_depth_m / 1.4)

                    true_runoff = (swat_baseline_runoff * vegetation_attenuation) - (infil_mm * root_channeling)
                    true_runoff = round(max(0.5, true_runoff + np.random.normal(0, 0.6)), 2)

                    quickflow_m3s = (true_runoff * (ws_area_km2 / 1000.0) * 0.42)
                    true_streamflow = round(max(0.5, baseflow_baseline * 0.95 + quickflow_m3s + np.random.normal(0, 0.3)), 2)

                    # Maize Yield (t/ha) (Harvested at end of season in Oct, month 10)
                    # Corn Belt average yield: ~9.5 to 13.5 t/ha
                    if month == 10:
                        # Yield penalized by cumulative water stress
                        potential_yield = 12.8 if not is_sorghum else 9.2
                        stress_penalty = water_stress * 4.5
                        maize_yield = round(max(3.5, potential_yield - stress_penalty + np.random.normal(0, 0.6)), 2)
                    else:
                        maize_yield = 0.0

                    records.append({
                        "date": date_str,
                        "year": year,
                        "month": month,
                        "watershed_id": ws_id,
                        "hru_id": hru_id,
                        "precip_mm": precip_mm,
                        "temp_mean_c": temp_mean,
                        "solar_radiation": sol_rad,
                        "soil_moisture": round(soil_moist, 2),
                        "infiltration_mm": infil_mm,
                        "et_mm": et_mm,
                        "lai": lai,
                        "root_depth_m": root_depth_m,
                        "transpiration_mm": transpiration_mm,
                        "water_stress": water_stress,
                        "swat_baseline_runoff_mm": swat_baseline_runoff,
                        "swat_baseline_streamflow_m3s": swat_baseline_streamflow,
                        "monthly_runoff_mm": true_runoff,
                        "monthly_streamflow_m3s": true_streamflow,
                        "maize_yield_t_ha": maize_yield,
                        "climate_scenario": climate_scenario,
                        "management_scenario": management_scenario,
                        "is_synthetic": True,
                        "data_provenance": DATASET_SOURCE_LABEL
                    })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(by=["date", "watershed_id", "hru_id"]).reset_index(drop=True)
        return df


def generate_full_synthetic_benchmark_dataset(seed: int = 42) -> pd.DataFrame:
    """
    Generates a full comprehensive dataset including multiple climate and management scenarios.
    """
    generator = SyntheticMultiScaleDatasetGenerator(seed=seed)
    dfs = []

    # 1. Historical Baseline
    df_hist = generator.generate(
        start_year=2015,
        num_years=8,
        climate_scenario="Historical",
        management_scenario="Baseline"
    )
    dfs.append(df_hist)

    # 2. Historical No-Till
    df_notill = generator.generate(
        start_year=2015,
        num_years=8,
        climate_scenario="Historical",
        management_scenario="No-Till"
    )
    dfs.append(df_notill)

    # 3. Future SSP2-4.5
    df_ssp2 = generator.generate(
        start_year=2025,
        num_years=5,
        climate_scenario="SSP2-4.5",
        management_scenario="Baseline"
    )
    dfs.append(df_ssp2)

    # 4. Future SSP5-8.5
    df_ssp5 = generator.generate(
        start_year=2025,
        num_years=5,
        climate_scenario="SSP5-8.5",
        management_scenario="+2C_Warming"
    )
    dfs.append(df_ssp5)

    full_df = pd.concat(dfs, ignore_index=True)
    full_df = full_df.sort_values(by=["date", "watershed_id", "hru_id"]).reset_index(drop=True)
    return full_df

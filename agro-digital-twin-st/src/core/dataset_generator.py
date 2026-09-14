"""
Dataset Generator & Manager Module for AgroTwin-AI.
Refactored to support Plant-to-Watershed (Maize / SWAT+ / Climate) multi-scale domain.

Replaces previous single-crop Hass avocado generator.
Uses SyntheticMultiScaleDatasetGenerator clearly labeled as DEMO / SYNTHETIC DATA.
"""

import os
import pandas as pd
from typing import Optional

from src.utils.config import DATASET_RAW_PATH, DATASET_CLEANED_PATH
from src.core.datasets.synthetic_generator import (
    SyntheticMultiScaleDatasetGenerator,
    generate_full_synthetic_benchmark_dataset,
    DATASET_SOURCE_LABEL,
    IS_SYNTHETIC_DATA
)


def generate_ecohydrological_dataset(
    seed: int = 42,
    scenario: str = "Historical"
) -> pd.DataFrame:
    """
    Backwards-compatible entrypoint.
    Generates multi-scale dataset for Maize in the Corn Belt.
    """
    generator = SyntheticMultiScaleDatasetGenerator(seed=seed)
    return generator.generate(
        start_year=2016,
        num_years=8,
        climate_scenario=scenario,
        management_scenario="Baseline"
    )


def load_primary_experiment_dataset(path: str) -> pd.DataFrame:
    """Load the primary project's final export without regenerating data."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Primary experiment dataset not found: {path}")
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    required = {"date", "watershed_id", "observed_streamflow_m3s", "baseline_streamflow_m3s", "coupled_streamflow_m3s", "data_classification"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Primary experiment dataset missing columns: {', '.join(sorted(missing))}")
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    return df


def get_dataset(force_regenerate: bool = False, seed: int = 42) -> pd.DataFrame:
    """
    Loads existing dataset or generates the new Plant-to-Watershed synthetic dataset.
    Ensures data has all required multi-scale variables:
    date, watershed_id, hru_id, precip_mm, temp_mean_c, solar_radiation,
    soil_moisture, infiltration_mm, et_mm, lai, root_depth_m, transpiration_mm,
    water_stress, swat_baseline_runoff_mm, swat_baseline_streamflow_m3s,
    monthly_runoff_mm, monthly_streamflow_m3s, maize_yield_t_ha,
    climate_scenario, management_scenario.
    """
    primary_path = os.environ.get("AGRO_TWIN_PRIMARY_EXPERIMENT_DATASET")
    if primary_path:
        return load_primary_experiment_dataset(primary_path)

    os.makedirs(os.path.dirname(DATASET_RAW_PATH), exist_ok=True)

    regenerate = force_regenerate or not os.path.exists(DATASET_RAW_PATH)

    if not regenerate:
        try:
            df = pd.read_csv(DATASET_RAW_PATH)
            # Check if dataset has new schema or legacy schema
            if "monthly_runoff_mm" not in df.columns or "watershed_id" not in df.columns:
                print("🔄 Legacy dataset schema detected. Regenerating with Plant-to-Watershed multi-scale schema...")
                regenerate = True
            else:
                df["date"] = pd.to_datetime(df["date"])
                return df
        except Exception as e:
            print(f"⚠️ Error reading existing dataset ({e}). Regenerating...")
            regenerate = True

    if regenerate:
        print(f"🌱 Generating new Multi-Scale Plant-to-Watershed dataset (seed={seed})...")
        df = generate_full_synthetic_benchmark_dataset(seed=seed)
        df.to_csv(DATASET_RAW_PATH, index=False)
        df.to_csv(DATASET_CLEANED_PATH, index=False)
        print(f"✅ Generated {len(df)} records saved to {DATASET_RAW_PATH}")
        return df

    return pd.read_csv(DATASET_RAW_PATH)

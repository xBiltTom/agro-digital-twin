"""
Tests for dataset generator reproducibility and schema correctness.
"""

import pytest
import pandas as pd
from src.core.datasets.synthetic_generator import (
    SyntheticMultiScaleDatasetGenerator,
    DATASET_SOURCE_LABEL
)


def test_dataset_reproducibility():
    gen1 = SyntheticMultiScaleDatasetGenerator(seed=123)
    df1 = gen1.generate(start_year=2020, num_years=2)

    gen2 = SyntheticMultiScaleDatasetGenerator(seed=123)
    df2 = gen2.generate(start_year=2020, num_years=2)

    pd.testing.assert_frame_equal(df1, df2)


def test_dataset_required_columns():
    gen = SyntheticMultiScaleDatasetGenerator(seed=42)
    df = gen.generate(start_year=2020, num_years=1)

    required_cols = [
        "date", "watershed_id", "hru_id", "precip_mm", "temp_mean_c",
        "solar_radiation", "soil_moisture", "infiltration_mm", "et_mm",
        "lai", "root_depth_m", "transpiration_mm", "water_stress",
        "swat_baseline_runoff_mm", "swat_baseline_streamflow_m3s",
        "monthly_runoff_mm", "monthly_streamflow_m3s", "maize_yield_t_ha",
        "climate_scenario", "management_scenario", "is_synthetic", "data_provenance"
    ]

    for col in required_cols:
        assert col in df.columns, f"Required column '{col}' is missing."

    assert df["is_synthetic"].all() == True
    assert df["data_provenance"].iloc[0] == DATASET_SOURCE_LABEL

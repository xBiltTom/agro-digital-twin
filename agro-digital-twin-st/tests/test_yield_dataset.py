"""
Tests for Seasonal Yield Dataset Builder.
Verifies aggregation of growing season (May-Oct) into 1 sample per HRU per year.
"""

import pytest
import pandas as pd
import numpy as np
from src.core.datasets.yield_dataset import build_seasonal_yield_dataset, calculate_gdd


def test_calculate_gdd():
    # Base temp 10, cutoff 30
    assert calculate_gdd(5.0) == 0.0
    assert calculate_gdd(10.0) == 0.0
    assert calculate_gdd(22.0) == 12.0
    assert calculate_gdd(35.0) == 20.0  # capped at 30


def test_build_seasonal_yield_dataset():
    # Create 2 years of monthly data for 1 HRU (24 months)
    dates = pd.date_range("2020-01-01", periods=24, freq="MS")
    df = pd.DataFrame({
        "date": dates,
        "watershed_id": "WS_Cedar",
        "hru_id": 1,
        "precip_mm": 50.0,
        "temp_mean_c": 20.0,
        "solar_radiation": 18.0,
        "soil_moisture": 28.0,
        "et_mm": 40.0,
        "transpiration_mm": 25.0,
        "lai": 3.0,
        "root_depth_m": 1.2,
        "water_stress": 0.1,
        "climate_scenario": "Baseline",
        "management_scenario": "Current",
        "maize_yield_t_ha": [0.0]*9 + [10.5] + [0.0]*2 + [0.0]*9 + [11.2] + [0.0]*2
    })

    seasonal_df = build_seasonal_yield_dataset(df)

    # 1 HRU x 2 years = 2 samples!
    assert len(seasonal_df) == 2
    assert set(seasonal_df["year"]) == {2020, 2021}
    assert "seasonal_precip_mm" in seasonal_df.columns
    assert "gdd" in seasonal_df.columns
    assert "peak_lai" in seasonal_df.columns
    assert seasonal_df.loc[seasonal_df["year"] == 2020, "maize_yield_t_ha"].iloc[0] == 10.5
    assert seasonal_df.loc[seasonal_df["year"] == 2021, "maize_yield_t_ha"].iloc[0] == 11.2

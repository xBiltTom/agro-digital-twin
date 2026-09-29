"""Leakage and chronological split tests for the daily experiment."""

import pandas as pd

from src.core.experiments.next_day_flow import build_next_day_dataset, temporal_train_validation_test_split


def test_next_day_target_uses_future_day_and_features_do_not():
    frame = pd.DataFrame({
        "date": pd.date_range("2019-01-01", periods=12, freq="D"),
        "streamflow_m3s": range(12),
        "precip_mm": range(10, 22),
        "temp_mean_c": range(20, 32),
    })
    prepared, features, _ = build_next_day_dataset(frame, base_variables=("streamflow_m3s", "precip_mm", "temp_mean_c"), lags=(1, 2))
    first = prepared.iloc[0]
    assert first["issue_date"] == pd.Timestamp("2019-01-02")
    assert first["target_date"] == pd.Timestamp("2019-01-03")
    assert first["streamflow_m3s_lag_1"] == 1
    assert first["next_day_streamflow_m3s"] == 2
    assert "next_day_streamflow_m3s" not in features


def test_temporal_split_is_contiguous_and_ordered():
    frame = pd.DataFrame({
        "issue_date": pd.date_range("2019-01-01", periods=100, freq="D"),
        "target_date": pd.date_range("2019-01-02", periods=100, freq="D"),
    })
    train, validation, test, split = temporal_train_validation_test_split(frame, minimum_train_samples=10)
    assert train["issue_date"].max() < validation["issue_date"].min()
    assert validation["issue_date"].max() < test["issue_date"].min()
    assert split.train_samples + split.validation_samples + split.test_samples == 100

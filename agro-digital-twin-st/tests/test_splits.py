"""
Tests for Data Leakage Prevention and Validation Splitters.
"""

import pytest
import pandas as pd
from src.core.training.splitters import (
    TemporalHoldoutSplitter,
    WatershedHoldoutSplitter
)


def test_temporal_holdout_no_future_leakage():
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "val": range(100)})

    splitter = TemporalHoldoutSplitter(test_ratio=0.25)
    train_idx, test_idx = splitter.split(df)

    max_train_date = df.loc[train_idx, "date"].max()
    min_test_date = df.loc[test_idx, "date"].min()

    # Strict temporal separation: training end MUST be strictly before testing start
    assert max_train_date < min_test_date
    assert len(train_idx) == 75
    assert len(test_idx) == 25


def test_watershed_holdout_spatial_isolation():
    df = pd.DataFrame({
        "watershed_id": ["WS_Cedar", "WS_Cedar", "WS_Raccoon", "WS_Raccoon", "WS_Iowa", "WS_Iowa"],
        "date": pd.date_range("2020-01-01", periods=6, freq="MS"),
        "val": range(6)
    })

    splitter = WatershedHoldoutSplitter(test_watersheds=["WS_Iowa"])
    train_idx, test_idx = splitter.split(df)

    train_ws = set(df.loc[train_idx, "watershed_id"])
    test_ws = set(df.loc[test_idx, "watershed_id"])

    # Disjoint spatial sets
    assert train_ws.isdisjoint(test_ws)
    assert test_ws == {"WS_Iowa"}


def test_temporal_3way_leak_free_split():
    from src.core.training.splitters import Temporal3WaySplitter, get_three_way_split

    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({"date": dates, "val": range(100)})

    splitter = Temporal3WaySplitter(val_ratio=0.20, test_ratio=0.20)
    train_idx, val_idx, test_idx, meta = splitter.split(df)

    assert len(train_idx) == 60
    assert len(val_idx) == 20
    assert len(test_idx) == 20

    # Chronological integrity: Train < Val < Test
    max_train_date = df.loc[train_idx, "date"].max()
    min_val_date = df.loc[val_idx, "date"].min()
    max_val_date = df.loc[val_idx, "date"].max()
    min_test_date = df.loc[test_idx, "date"].min()

    assert max_train_date < min_val_date
    assert max_val_date < min_test_date
    assert meta["strategy"] == "temporal_3way"


def test_watershed_3way_spatial_isolation():
    from src.core.training.splitters import Watershed3WaySplitter

    df = pd.DataFrame({
        "watershed_id": ["WS_1"] * 20 + ["WS_2"] * 20 + ["WS_3"] * 20,
        "date": list(pd.date_range("2020-01-01", periods=20, freq="D")) * 3,
        "val": range(60)
    })

    splitter = Watershed3WaySplitter(
        train_watersheds=["WS_1"],
        val_watersheds=["WS_2"],
        test_watersheds=["WS_3"]
    )
    train_idx, val_idx, test_idx, meta = splitter.split(df)

    train_ws = set(df.loc[train_idx, "watershed_id"])
    val_ws = set(df.loc[val_idx, "watershed_id"])
    test_ws = set(df.loc[test_idx, "watershed_id"])

    assert train_ws == {"WS_1"}
    assert val_ws == {"WS_2"}
    assert test_ws == {"WS_3"}
    assert train_ws.isdisjoint(val_ws)
    assert train_ws.isdisjoint(test_ws)
    assert val_ws.isdisjoint(test_ws)

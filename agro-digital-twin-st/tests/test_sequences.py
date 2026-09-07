"""
Tests for 3D Temporal Sequence Construction & Isolation.
Verifies no future leakage and strict grouping by (watershed_id, hru_id).
"""

import pytest
import numpy as np
import pandas as pd
from src.core.features.sequences import (
    build_grouped_temporal_sequences,
    build_temporal_sequences_from_matrix
)


def test_build_grouped_temporal_sequences_isolation():
    # 2 HRUs across 2 watersheds, 15 timesteps each
    records = []
    dates = pd.date_range("2020-01-01", periods=15, freq="MS")
    for ws in ["WS_Cedar", "WS_Raccoon"]:
        for hru in [1, 2]:
            for t_idx, d in enumerate(dates):
                records.append({
                    "date": d,
                    "watershed_id": ws,
                    "hru_id": hru,
                    "f1": float(t_idx),
                    "f2": float(t_idx * 2),
                    "target": float(t_idx * 10),
                    "swat_base": float(t_idx * 8)
                })

    df = pd.DataFrame(records)
    seq_len = 5
    feature_cols = ["f1", "f2"]

    X_seq, y_seq, meta_df = build_grouped_temporal_sequences(
        df=df,
        feature_cols=feature_cols,
        target_col="target",
        sequence_length=seq_len,
        baseline_col="swat_base"
    )

    # 4 groups, each with 15 timesteps.
    # Each group produces 15 - 5 + 1 = 11 sequences. Total = 44 sequences.
    assert X_seq.shape == (44, 5, 2)
    assert len(y_seq) == 44
    assert len(meta_df) == 44

    # Target convention: Window [t-L+1, ..., t] predicts target at t
    # For first sequence: f1 is [0, 1, 2, 3, 4], target at timestep 4 is 40
    assert np.array_equal(X_seq[0, :, 0], [0.0, 1.0, 2.0, 3.0, 4.0])
    assert y_seq[0] == 40.0
    assert meta_df.iloc[0]["baseline_val"] == 32.0


def test_build_temporal_sequences_from_matrix():
    X = np.arange(20).reshape(10, 2).astype(np.float64)
    y = np.arange(10).astype(np.float64) * 5

    X_seq, y_seq = build_temporal_sequences_from_matrix(X, y, sequence_length=4)
    assert X_seq.shape == (7, 4, 2)
    assert len(y_seq) == 7
    # Last element of first window should correspond to y_seq[0]
    assert y_seq[0] == y[3]

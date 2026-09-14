"""
Temporal Sequence Construction Module for Deep Learning Eco-Hydrological Models.
CRITICAL METHODOLOGICAL REQUIREMENTS (P0.1):
1. Input shape: (samples, timesteps, features).
2. Sequences are formed STRICTLY within each (watershed_id, hru_id) group.
3. Chronological sorting by date: NO future data is ever used to predict the past.
4. Sequences NEVER cross across HRU boundaries or watershed boundaries.
5. Target convention: Window [t - L + 1, ..., t] predicts target y(t).
"""

from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import pandas as pd


def build_grouped_temporal_sequences(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    sequence_length: int = 12,
    group_cols: Optional[List[str]] = None,
    date_col: str = "date",
    baseline_col: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Constructs leak-free 3D temporal sequence windows for recurrent/convolutional models.

    Args:
        df: Input DataFrame containing features, target, date, and group identifiers.
        feature_cols: Ordered list of feature column names.
        target_col: Name of the regression target column.
        sequence_length: Number of consecutive timesteps per sample (timesteps L).
        group_cols: Grouping columns to isolate sequences (default: ['watershed_id', 'hru_id']).
        date_col: Date column name to enforce strict chronological order.
        baseline_col: Optional baseline column (e.g. SWAT baseline) for residual tracking.

    Returns:
        X_seq: 3D numpy array of shape (N_samples, sequence_length, N_features).
        y_seq: 1D numpy array of shape (N_samples,) corresponding to target at timestep t.
        meta_df: DataFrame containing metadata (date, watershed_id, hru_id, baseline) for each sample.

    Target Convention:
        Sequence X[k] = features from [t - L + 1, ..., t]
        Target y[k]   = target at timestep t
    """
    if group_cols is None:
        group_cols = ["watershed_id", "hru_id"]

    # Validate columns exist
    missing_feats = [c for c in feature_cols if c not in df.columns]
    if missing_feats:
        raise KeyError(f"Feature columns missing from DataFrame: {missing_feats}")
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in DataFrame.")
    for g in group_cols:
        if g not in df.columns:
            raise KeyError(f"Grouping column '{g}' not found in DataFrame.")

    # Work on a copy sorted strictly by date
    work_df = df.copy()
    work_df[date_col] = pd.to_datetime(work_df[date_col])

    x_list: List[np.ndarray] = []
    y_list: List[float] = []
    meta_rows: List[Dict[str, Any]] = []

    # Group by isolated spatial hydrological units
    grouped = work_df.groupby(group_cols, sort=False)

    for group_key, group_df in grouped:
        # Sort strictly chronologically within group
        sorted_group = group_df.sort_values(by=date_col).reset_index(drop=True)
        n_group_rows = len(sorted_group)

        if n_group_rows < sequence_length:
            # Group does not have enough timesteps to form even one sequence
            continue

        feat_vals = sorted_group[feature_cols].values.astype(np.float64)
        target_vals = sorted_group[target_col].values.astype(np.float64)
        dates = sorted_group[date_col].values
        baselines = (
            sorted_group[baseline_col].values.astype(np.float64)
            if (baseline_col and baseline_col in sorted_group.columns)
            else None
        )

        for i in range(sequence_length - 1, n_group_rows):
            # Window strictly from i - sequence_length + 1 up to i (inclusive)
            start_idx = i - sequence_length + 1
            end_idx = i + 1  # slice upper bound is exclusive

            window_features = feat_vals[start_idx:end_idx]
            target_value = target_vals[i]

            x_list.append(window_features)
            y_list.append(target_value)

            meta_entry = {
                "date": dates[i],
                "target_timestep": i,
                "target_val": target_value
            }
            if isinstance(group_key, tuple):
                for g_col, g_val in zip(group_cols, group_key):
                    meta_entry[g_col] = g_val
            else:
                meta_entry[group_cols[0]] = group_key

            if baselines is not None:
                meta_entry["baseline_val"] = baselines[i]

            meta_rows.append(meta_entry)

    if not x_list:
        raise ValueError(
            f"No temporal sequences could be constructed with sequence_length={sequence_length}. "
            f"Ensure groups have at least {sequence_length} timesteps."
        )

    X_seq = np.array(x_list, dtype=np.float64)
    y_seq = np.array(y_list, dtype=np.float64)
    meta_df = pd.DataFrame(meta_rows)

    return X_seq, y_seq, meta_df


def build_temporal_sequences_from_matrix(
    X: np.ndarray,
    y: np.ndarray,
    sequence_length: int = 12
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Standard rolling window for a single pre-sorted continuous series without groups.
    Shape output: (N - sequence_length + 1, sequence_length, N_features).
    """
    n_samples, n_features = X.shape
    if n_samples < sequence_length:
        raise ValueError(f"Number of samples ({n_samples}) is less than sequence_length ({sequence_length}).")

    num_seq = n_samples - sequence_length + 1
    X_seq = np.empty((num_seq, sequence_length, n_features), dtype=X.dtype)
    y_seq = np.empty((num_seq,), dtype=y.dtype)

    for i in range(num_seq):
        X_seq[i] = X[i : i + sequence_length]
        y_seq[i] = y[i + sequence_length - 1]

    return X_seq, y_seq

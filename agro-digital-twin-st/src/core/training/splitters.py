"""
Validation Splitters and Data Leakage Prevention for AgroTwin-AI.
CRITICAL METHODOLOGICAL RIGOR (P0.3):
- Formal 3-way partition: TRAIN, VALIDATION, TEST.
- TEST set remains completely held out until final evaluation.
- Preprocessing scaler is fit ONLY on TRAIN.
- Zero future temporal leakage: past -> train, later -> validation, latest -> test.
- Spatial isolation for watershed transferability: train watersheds, val watersheds, test watersheds.
"""

from typing import Tuple, List, Generator, Optional, Dict, Any
import numpy as np
import pandas as pd


class Temporal3WaySplitter:
    """
    Splits time-series data strictly into 3 chronological partitions:
    Past (Train) -> Middle (Validation) -> Future (Test).
    Zero future-to-past data leakage.
    """

    def __init__(self, val_ratio: float = 0.20, test_ratio: float = 0.20):
        if val_ratio + test_ratio >= 1.0:
            raise ValueError(f"val_ratio ({val_ratio}) + test_ratio ({test_ratio}) must be < 1.0")
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        if "date" not in df.columns:
            raise KeyError("DataFrame must contain 'date' column for Temporal3WaySplitter.")

        dates = pd.to_datetime(df["date"], errors="raise").dt.normalize()
        unique_dates = np.sort(dates.unique())
        if len(unique_dates) < 3:
            raise ValueError("Temporal3WaySplitter requires at least three unique dates.")
        n_dates = len(unique_dates)
        n_train = int(n_dates * (1.0 - self.val_ratio - self.test_ratio))
        n_val = int(n_dates * self.val_ratio)
        if n_train < 1 or n_val < 1 or n_dates - n_train - n_val < 1:
            raise ValueError("Temporal3WaySplitter ratios leave an empty date partition.")
        train_dates = unique_dates[:n_train]
        val_dates = unique_dates[n_train:n_train + n_val]
        test_dates = unique_dates[n_train + n_val:]
        # Return index labels. Every entity/scenario sharing a date stays in
        # one partition, so temporal groups cannot leak across boundaries.
        train_idx = df.index[dates.isin(train_dates)].to_numpy()
        val_idx = df.index[dates.isin(val_dates)].to_numpy()
        test_idx = df.index[dates.isin(test_dates)].to_numpy()

        meta = {
            "strategy": "temporal_3way",
            "train_range": [str(pd.Timestamp(train_dates[0]).date()), str(pd.Timestamp(train_dates[-1]).date())],
            "val_range": [str(pd.Timestamp(val_dates[0]).date()), str(pd.Timestamp(val_dates[-1]).date())],
            "test_range": [str(pd.Timestamp(test_dates[0]).date()), str(pd.Timestamp(test_dates[-1]).date())],
            "date_partition_counts": {"train": len(train_dates), "validation": len(val_dates), "test": len(test_dates)},
            "train_samples": len(train_idx),
            "val_samples": len(val_idx),
            "test_samples": len(test_idx)
        }
        return train_idx, val_idx, test_idx, meta


class Watershed3WaySplitter:
    """
    Spatial 3-way holdout:
    Isolates independent watersheds for train, validation, and test.
    Guarantees out-of-sample spatial generalizability.
    """

    def __init__(
        self,
        train_watersheds: Optional[List[str]] = None,
        val_watersheds: Optional[List[str]] = None,
        test_watersheds: Optional[List[str]] = None
    ):
        self.train_watersheds = train_watersheds
        self.val_watersheds = val_watersheds
        self.test_watersheds = test_watersheds

    def split(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        if "watershed_id" not in df.columns:
            raise KeyError("DataFrame must contain 'watershed_id' column for Watershed3WaySplitter.")

        all_ws = list(df["watershed_id"].unique())
        if len(all_ws) < 3:
            # If fewer than 3 watersheds, split chronologically within watersheds
            temp_splitter = Temporal3WaySplitter()
            return temp_splitter.split(df)

        test_ws = self.test_watersheds or [all_ws[-1]]
        remaining = [w for w in all_ws if w not in test_ws]
        val_ws = self.val_watersheds or [remaining[-1]]
        train_ws = self.train_watersheds or [w for w in remaining if w not in val_ws]

        train_mask = df["watershed_id"].isin(train_ws)
        val_mask = df["watershed_id"].isin(val_ws)
        test_mask = df["watershed_id"].isin(test_ws)

        train_idx = df[train_mask].index.to_numpy()
        val_idx = df[val_mask].index.to_numpy()
        test_idx = df[test_mask].index.to_numpy()

        meta = {
            "strategy": "watershed_spatial_3way",
            "training_watersheds": train_ws,
            "validation_watersheds": val_ws,
            "test_watersheds": test_ws,
            "train_samples": len(train_idx),
            "val_samples": len(val_idx),
            "test_samples": len(test_idx)
        }
        return train_idx, val_idx, test_idx, meta


class TemporalHoldoutSplitter:
    """Backwards compatibility 2-way splitter."""
    def __init__(self, test_ratio: float = 0.25):
        self.test_ratio = test_ratio

    def split(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        dates = pd.to_datetime(df["date"], errors="raise").dt.normalize()
        unique_dates = np.sort(dates.unique())
        n_train = int(len(unique_dates) * (1.0 - self.test_ratio))
        if n_train < 1 or n_train >= len(unique_dates):
            raise ValueError("TemporalHoldoutSplitter ratios leave an empty date partition.")
        return df.index[dates.isin(unique_dates[:n_train])].to_numpy(), df.index[dates.isin(unique_dates[n_train:])].to_numpy()


class WatershedHoldoutSplitter:
    """Backwards compatibility 2-way spatial splitter."""
    def __init__(self, test_watersheds: Optional[List[str]] = None):
        self.test_watersheds = test_watersheds

    def split(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        all_ws = df["watershed_id"].unique()
        test_ws = self.test_watersheds or [all_ws[-1]]
        test_mask = df["watershed_id"].isin(test_ws)
        return df[~test_mask].index.to_numpy(), df[test_mask].index.to_numpy()


class TimeSeriesWalkForwardSplitter:
    """Expanding-window walk-forward validation for temporal series."""
    def __init__(self, n_splits: int = 4):
        self.n_splits = n_splits

    def split(self, df: pd.DataFrame) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        sorted_indices = df.sort_values(by="date").index.to_numpy()
        n_samples = len(sorted_indices)
        fold_size = n_samples // (self.n_splits + 1)
        for i in range(self.n_splits):
            train_end = (i + 1) * fold_size
            test_end = (i + 2) * fold_size if i < self.n_splits - 1 else n_samples
            yield sorted_indices[:train_end], sorted_indices[train_end:test_end]


def get_three_way_split(
    df: pd.DataFrame,
    strategy: str = "temporal",
    val_ratio: float = 0.20,
    test_ratio: float = 0.20,
    holdout_watershed: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Standardized entrypoint for 3-way leak-free splits: (train, val, test, metadata).
    """
    if strategy == "watershed":
        splitter = Watershed3WaySplitter(test_watersheds=[holdout_watershed] if holdout_watershed else None)
        return splitter.split(df)
    else:  # default temporal
        splitter = Temporal3WaySplitter(val_ratio=val_ratio, test_ratio=test_ratio)
        return splitter.split(df)


def get_validation_split(
    df: pd.DataFrame,
    strategy: str = "temporal",
    test_ratio: float = 0.25,
    holdout_watershed: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, str]:
    """Backwards compatibility 2-way adapter."""
    train_idx, val_idx, test_idx, meta = get_three_way_split(
        df, strategy=strategy, val_ratio=0.15, test_ratio=test_ratio, holdout_watershed=holdout_watershed
    )
    desc = f"Leak-Free Split: {meta.get('strategy', strategy)} (Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)})"
    return train_idx, test_idx, desc

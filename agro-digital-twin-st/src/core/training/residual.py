"""Residual reconstruction in physical units and dated sequence alignment."""
import numpy as np
import pandas as pd


def corrected_flow(baseline, residual):
    baseline = np.asarray(baseline, dtype=float).reshape(-1)
    residual = np.asarray(residual, dtype=float).reshape(-1)
    if len(baseline) != len(residual) or not np.isfinite(baseline).all() or not np.isfinite(residual).all():
        raise ValueError("Residual and physical baseline require equal finite dated arrays")
    return np.maximum(0.0, baseline + residual)


def sequence_evaluation(meta: pd.DataFrame, learning_mode: str):
    """Targets in metadata are residuals only when residual mode was requested."""
    target = meta["target_val"].to_numpy(dtype=float)
    if learning_mode == "residual":
        baseline = meta["baseline_val"].to_numpy(dtype=float)
        return target + baseline, baseline
    return target, np.zeros(len(target))


def validation_winner(scores):
    if not scores or any(not np.isfinite(value) for value in scores.values()):
        raise ValueError("Selection requires finite VALIDATION RMSE values")
    return min(scores, key=lambda name: (scores[name], name))

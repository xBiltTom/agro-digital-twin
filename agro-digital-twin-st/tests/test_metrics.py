"""
Tests for hydrological and agronomic evaluation metrics.
"""

import pytest
import numpy as np
from src.core.metrics import (
    calculate_rmse,
    calculate_mae,
    calculate_r2,
    calculate_nse,
    calculate_pbias,
    compute_all_metrics
)


def test_perfect_prediction_metrics():
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([10.0, 20.0, 30.0, 40.0])

    assert calculate_rmse(y_true, y_pred) == 0.0
    assert calculate_mae(y_true, y_pred) == 0.0
    assert calculate_r2(y_true, y_pred) == 1.0
    assert calculate_nse(y_true, y_pred) == 1.0
    assert calculate_pbias(y_true, y_pred) == 0.0


def test_known_metrics_values():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])

    # Errors: [-2, 2, -3], squared: [4, 4, 9], sum=17, mean=17/3=5.6667, sqrt=2.3805
    rmse = calculate_rmse(y_true, y_pred)
    assert pytest.approx(rmse, 0.01) == 2.38

    # Absolute errors: [2, 2, 3], mean = 7/3 = 2.3333
    mae = calculate_mae(y_true, y_pred)
    assert pytest.approx(mae, 0.01) == 2.33

    # Mean y_true = 20. Denom = (-10)^2 + 0 + 10^2 = 200.
    # Numerator = 17. NSE = 1 - 17/200 = 1 - 0.085 = 0.915
    nse = calculate_nse(y_true, y_pred)
    assert pytest.approx(nse, 0.001) == 0.915

    # PBIAS = 100 * sum(y_true - y_pred) / sum(y_true) = 100 * (-3) / 60 = -5.0%
    pbias = calculate_pbias(y_true, y_pred)
    assert pytest.approx(pbias, 0.01) == -5.0


def test_compute_all_metrics():
    y_true = [10.0, 20.0, 30.0]
    y_pred = [12.0, 18.0, 33.0]
    res = compute_all_metrics(y_true, y_pred, target_type="runoff")

    assert "rmse" in res
    assert "mae" in res
    assert "r2" in res
    assert "nse" in res
    assert "pbias" in res


def test_rank_models_multicriteria():
    from src.core.metrics import rank_models_multicriteria

    # Model A is clearly superior in runoff (lowest RMSE/MAE, highest NSE, closest PBIAS)
    # Model B is mediocre
    # Model C has terrible NSE
    models_metrics = {
        "Model_A": {"rmse": 1.2, "mae": 0.8, "nse": 0.95, "pbias": -1.5},
        "Model_B": {"rmse": 3.0, "mae": 2.1, "nse": 0.82, "pbias": 6.0},
        "Model_C": {"rmse": 8.0, "mae": 5.5, "nse": 0.40, "pbias": -18.0},
    }

    champ_name, rankings = rank_models_multicriteria(models_metrics, target_type="runoff")
    assert champ_name == "Model_A"
    assert rankings[0]["model_name"] == "Model_A"
    assert rankings[0]["composite_rank"] < rankings[1]["composite_rank"]

    # Yield test (uses R2 instead of NSE/PBIAS)
    yield_metrics = {
        "Yield_RF": {"rmse": 0.5, "mae": 0.3, "r2": 0.92},
        "Yield_XGB": {"rmse": 1.2, "mae": 0.9, "r2": 0.65}
    }
    champ_yield, y_rankings = rank_models_multicriteria(yield_metrics, target_type="yield")
    assert champ_yield == "Yield_RF"

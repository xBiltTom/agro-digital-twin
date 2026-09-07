"""
Hydrological & Agronomic Evaluation Metrics for AgroTwin-AI.
Implements standard metrics: RMSE, MAE, R², NSE (Nash-Sutcliffe), and PBIAS (Percent Bias).
"""

import numpy as np
from typing import Dict, Any, Union, List, Tuple


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Root Mean Squared Error (RMSE)."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    return float(np.sqrt(np.mean((y_t - y_p) ** 2)))


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Mean Absolute Error (MAE)."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    return float(np.mean(np.abs(y_t - y_p)))


def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Coefficient of Determination (R²)."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return float(1.0 - (ss_res / ss_tot))


def calculate_nse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculates Nash-Sutcliffe Efficiency (NSE) coefficient.
    NSE = 1 - [ sum((y_obs - y_sim)^2) / sum((y_obs - mean(y_obs))^2) ]
    Standard in hydrological watershed modeling (SWAT/SWAT+).
    Range: (-inf, 1.0]. Perfect match = 1.0.
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    denominator = np.sum((y_t - np.mean(y_t)) ** 2)
    if denominator == 0.0:
        return 1.0 if np.sum((y_t - y_p) ** 2) == 0.0 else 0.0
    numerator = np.sum((y_t - y_p) ** 2)
    return float(1.0 - (numerator / denominator))


def calculate_pbias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculates Percent Bias (PBIAS) according to Moriasi et al. (2007) / SWAT+:
    PBIAS = 100 * [ sum(y_obs - y_sim) / sum(y_obs) ]
    Optimal value: 0.0%.
    Positive value: Model underestimation bias.
    Negative value: Model overestimation bias.
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    denom = np.sum(y_t)
    if denom == 0.0:
        return 0.0
    numerator = np.sum(y_t - y_p)
    return float(100.0 * (numerator / denom))


def compute_all_metrics(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
    target_type: str = "runoff"
) -> Dict[str, float]:
    """
    Computes all relevant metrics based on the target type.
    For runoff / streamflow: RMSE, MAE, R², NSE, PBIAS.
    For yield: RMSE, MAE, R².
    """
    y_t = np.asarray(y_true, dtype=np.float64).flatten()
    y_p = np.asarray(y_pred, dtype=np.float64).flatten()

    rmse = calculate_rmse(y_t, y_p)
    mae = calculate_mae(y_t, y_p)
    r2 = calculate_r2(y_t, y_p)

    metrics = {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4)
    }

    if "yield" not in target_type.lower():
        nse = calculate_nse(y_t, y_p)
        pbias = calculate_pbias(y_t, y_p)
        metrics["nse"] = round(nse, 4)
        metrics["pbias"] = round(pbias, 2)

    return metrics


def rank_models_multicriteria(
    models_metrics: Dict[str, Dict[str, float]],
    target_type: str = "runoff"
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Ranks models using Unit-Independent Multi-Criteria Ranking (P0.6).
    Eliminates cross-unit summation by computing ordinal ranks for each metric:
      - RMSE rank (ascending, 1 = lowest error)
      - MAE rank (ascending, 1 = lowest error)
      - NSE rank (descending, 1 = highest efficiency)
      - |PBIAS| rank (ascending, 1 = smallest bias magnitude)

    Returns:
      (champion_name, ranking_table)
    """
    if not models_metrics:
        raise ValueError("models_metrics dictionary is empty.")

    model_names = list(models_metrics.keys())
    n_models = len(model_names)

    if n_models == 1:
        single_name = model_names[0]
        return single_name, [{
            "model_name": single_name,
            "composite_rank": 1.0,
            "metrics": models_metrics[single_name]
        }]

    is_yield = "yield" in target_type.lower()

    # Helper to compute fractional/ordinal ranks (1 = best)
    def compute_ranks(values: List[float], higher_is_better: bool = False) -> List[float]:
        sorted_pairs = sorted(enumerate(values), key=lambda x: x[1], reverse=higher_is_better)
        ranks = [0.0] * len(values)
        for rank_pos, (orig_idx, _) in enumerate(sorted_pairs, start=1):
            ranks[orig_idx] = float(rank_pos)
        return ranks

    rmse_vals = [models_metrics[m].get("rmse", 9999.0) for m in model_names]
    mae_vals = [models_metrics[m].get("mae", 9999.0) for m in model_names]

    rmse_ranks = compute_ranks(rmse_vals, higher_is_better=False)
    mae_ranks = compute_ranks(mae_vals, higher_is_better=False)

    ranking_records = []

    if is_yield:
        r2_vals = [models_metrics[m].get("r2", -999.0) for m in model_names]
        r2_ranks = compute_ranks(r2_vals, higher_is_better=True)

        for i, name in enumerate(model_names):
            # Weighted rank: RMSE (0.50), MAE (0.25), R² (0.25)
            comp_rank = (0.50 * rmse_ranks[i]) + (0.25 * mae_ranks[i]) + (0.25 * r2_ranks[i])
            ranking_records.append({
                "model_name": name,
                "composite_rank": round(comp_rank, 3),
                "rmse_rank": int(rmse_ranks[i]),
                "mae_rank": int(mae_ranks[i]),
                "r2_rank": int(r2_ranks[i]),
                "metrics": models_metrics[name]
            })
    else:
        nse_vals = [models_metrics[m].get("nse", -999.0) for m in model_names]
        pbias_abs_vals = [abs(models_metrics[m].get("pbias", 999.0)) for m in model_names]

        nse_ranks = compute_ranks(nse_vals, higher_is_better=True)
        pbias_ranks = compute_ranks(pbias_abs_vals, higher_is_better=False)

        for i, name in enumerate(model_names):
            # Hydrological weighted rank: NSE (0.35), RMSE (0.35), |PBIAS| (0.15), MAE (0.15)
            comp_rank = (
                (0.35 * nse_ranks[i]) +
                (0.35 * rmse_ranks[i]) +
                (0.15 * pbias_ranks[i]) +
                (0.15 * mae_ranks[i])
            )
            ranking_records.append({
                "model_name": name,
                "composite_rank": round(comp_rank, 3),
                "nse_rank": int(nse_ranks[i]),
                "rmse_rank": int(rmse_ranks[i]),
                "pbias_rank": int(pbias_ranks[i]),
                "mae_rank": int(mae_ranks[i]),
                "metrics": models_metrics[name]
            })

    # Sort ascending by composite_rank (lowest rank is #1 champion)
    ranking_records.sort(key=lambda x: x["composite_rank"])
    champion_name = ranking_records[0]["model_name"]

    return champion_name, ranking_records


def select_champion_model(
    models_metrics: Dict[str, Dict[str, float]],
    target_type: str = "runoff"
) -> str:
    """
    Selects champion model using unit-independent multi-criteria ranking.
    """
    champ_name, _ = rank_models_multicriteria(models_metrics, target_type=target_type)
    return champ_name


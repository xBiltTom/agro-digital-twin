"""
Rigorous Statistical Validation & Hypothesis Testing for AgroTwin-AI.
Scientific Focus:
H0: Plant-to-watershed coupling does not improve runoff prediction over standard SWAT+.
H1: Multi-scale twin reduces monthly runoff RMSE by >= 15% over standard SWAT+.
Implements:
- Wilcoxon Signed-Rank Test on absolute residuals
- Non-parametric Bootstrap Confidence Intervals
- Kolmogorov-Smirnov (KS) two-sample test on error distributions
- Objective evaluation of H0 vs H1 without fabricated outcomes.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import stats
from src.core.metrics import calculate_rmse, calculate_mae, calculate_nse, calculate_pbias


def perform_wilcoxon_test(
    y_true: np.ndarray,
    y_pred_candidate: np.ndarray,
    y_pred_baseline: np.ndarray
) -> Dict[str, Any]:
    """
    Performs Wilcoxon signed-rank test on paired absolute errors:
    e_cand = |y_true - y_pred_candidate|
    e_base = |y_true - y_pred_baseline|
    H0: Median difference in absolute error is zero.
    H1: Candidate model has significantly lower error (alternative='less').
    """
    err_cand = np.abs(np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred_candidate, dtype=np.float64))
    err_base = np.abs(np.asarray(y_true, dtype=np.float64) - np.asarray(y_pred_baseline, dtype=np.float64))

    diff = err_cand - err_base
    # Filter out exact ties
    non_zero = diff != 0.0
    if np.sum(non_zero) < 10:
        return {
            "wilcoxon_stat": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "mae_candidate": float(np.mean(err_cand)),
            "mae_baseline": float(np.mean(err_base)),
            "mae_reduction_pct": 0.0
        }

    stat, p_val = stats.wilcoxon(err_cand[non_zero], err_base[non_zero], alternative="less")

    mae_c = float(np.mean(err_cand))
    mae_b = float(np.mean(err_base))
    reduction_pct = float(((mae_b - mae_c) / max(1e-6, mae_b)) * 100.0)

    return {
        "wilcoxon_stat": float(stat),
        "p_value": float(p_val),
        "is_significant": bool(p_val < 0.05),
        "mae_candidate": round(mae_c, 4),
        "mae_baseline": round(mae_b, 4),
        "mae_reduction_pct": round(reduction_pct, 2)
    }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_pred_candidate: np.ndarray,
    y_pred_baseline: np.ndarray,
    n_bootstraps: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Calculates non-parametric bootstrap confidence intervals for Delta RMSE:
    Delta RMSE = RMSE(baseline) - RMSE(candidate).
    If the 95% CI is strictly positive, candidate significantly outperforms baseline.
    """
    rng = np.random.RandomState(seed)
    y_t = np.asarray(y_true, dtype=np.float64)
    y_c = np.asarray(y_pred_candidate, dtype=np.float64)
    y_b = np.asarray(y_pred_baseline, dtype=np.float64)

    n_samples = len(y_t)
    delta_rmse_samples = np.empty(n_bootstraps)

    for i in range(n_bootstraps):
        idx = rng.choice(n_samples, size=n_samples, replace=True)
        rmse_b = calculate_rmse(y_t[idx], y_b[idx])
        rmse_c = calculate_rmse(y_t[idx], y_c[idx])
        delta_rmse_samples[i] = rmse_b - rmse_c

    alpha = 1.0 - confidence_level
    ci_lower = float(np.percentile(delta_rmse_samples, (alpha / 2.0) * 100.0))
    ci_upper = float(np.percentile(delta_rmse_samples, (1.0 - alpha / 2.0) * 100.0))
    mean_delta = float(np.mean(delta_rmse_samples))

    return {
        "confidence_level": confidence_level,
        "n_bootstraps": n_bootstraps,
        "mean_delta_rmse": round(mean_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "strictly_positive_improvement": bool(ci_lower > 0.0)
    }


def perform_ks_test(
    y_true: np.ndarray,
    y_pred_candidate: np.ndarray,
    y_pred_baseline: np.ndarray
) -> Dict[str, Any]:
    """
    Two-sample Kolmogorov-Smirnov test to evaluate whether residual distributions differ.
    """
    res_cand = np.asarray(y_true) - np.asarray(y_pred_candidate)
    res_base = np.asarray(y_true) - np.asarray(y_pred_baseline)

    stat, p_val = stats.ks_2samp(res_cand, res_base)

    return {
        "ks_stat": float(stat),
        "p_value": float(p_val),
        "distributions_differ": bool(p_val < 0.05)
    }


def evaluate_scientific_hypothesis(
    y_true: np.ndarray,
    y_pred_swat_baseline: np.ndarray,
    y_pred_twin: np.ndarray
) -> Dict[str, Any]:
    """
    Evaluates the core scientific hypothesis:
    H0: Coupling does not improve monthly runoff prediction.
    H1: Multi-scale twin reduces monthly runoff RMSE by at least 15% and has p < 0.05.
    DOES NOT assume H1 is true. Evaluates objectively.
    """
    rmse_swat = calculate_rmse(y_true, y_pred_swat_baseline)
    rmse_twin = calculate_rmse(y_true, y_pred_twin)
    nse_swat = calculate_nse(y_true, y_pred_swat_baseline)
    nse_twin = calculate_nse(y_true, y_pred_twin)

    rmse_reduction_pct = ((rmse_swat - rmse_twin) / max(1e-6, rmse_swat)) * 100.0

    w_res = perform_wilcoxon_test(y_true, y_pred_twin, y_pred_swat_baseline)
    boot_res = compute_bootstrap_ci(y_true, y_pred_twin, y_pred_swat_baseline)
    ks_res = perform_ks_test(y_true, y_pred_twin, y_pred_swat_baseline)

    # Scientific criteria: RMSE reduction >= 15% AND statistically significant improvement
    meets_15pct_target = bool(rmse_reduction_pct >= 15.0)
    statistically_significant = w_res["is_significant"] and boot_res["strictly_positive_improvement"]

    rejects_h0 = bool(meets_15pct_target and statistically_significant)

    if rejects_h0:
        verdict = "REJECT H0 in favor of H1 (Evidence supports multi-scale twin superiority)"
        verdict_color = "green"
        narrative = (
            f"El gemelo multi-escala logró una reducción del RMSE de {rmse_reduction_pct:.1f}% "
            f"(superando el umbral de 15.0%) frente a SWAT+ estándar. "
            f"La prueba de Wilcoxon (p = {w_res['p_value']:.4e}) y el intervalo de confianza Bootstrap al 95% "
            f"[{boot_res['ci_lower']:.3f}, {boot_res['ci_upper']:.3f}] confirman significancia estadística."
        )
    else:
        verdict = "FAIL TO REJECT H0 (Insufficient evidence to claim >=15% RMSE reduction)"
        verdict_color = "orange"
        narrative = (
            f"La reducción del RMSE observada fue de {rmse_reduction_pct:.1f}% "
            f"({'alcanza' if meets_15pct_target else 'no alcanza'} el umbral científico del 15.0%). "
            f"La significancia estadística arrojó p = {w_res['p_value']:.4e}. "
            "No se rechaza formalmente la hipótesis nula H0 bajo los criterios predefinidos."
        )

    return {
        "rmse_swat_baseline": round(rmse_swat, 4),
        "rmse_twin": round(rmse_twin, 4),
        "rmse_reduction_pct": round(rmse_reduction_pct, 2),
        "nse_swat_baseline": round(nse_swat, 4),
        "nse_twin": round(nse_twin, 4),
        "meets_15pct_threshold": meets_15pct_target,
        "wilcoxon": w_res,
        "bootstrap": boot_res,
        "ks_test": ks_res,
        "rejects_h0": rejects_h0,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "narrative": narrative
    }

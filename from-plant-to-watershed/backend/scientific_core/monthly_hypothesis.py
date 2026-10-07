"""Versioned paired monthly inference; no calibration or legacy 15% threshold."""
from __future__ import annotations

from datetime import date
import math
import random

from .validation import ValidationEngine

CONTRASTS = (("D", "A"), ("B", "A"), ("C", "A"), ("D", "B"), ("D", "C"))
SERIES = ("A", "B", "C", "D", "AFFINE_A", "AFFINE_B", "CLIMATOLOGY")


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_monthly(rows, uncertainty):
    """Resample the full calendar grid, retaining masks instead of closing gaps.

    Positive deltas denote a reduction: RMSE(reference) - RMSE(candidate).
    All series and contrasts share the same circular block draws.
    """
    months = sorted({row["month"] for row in rows})
    keys = {(row["month"], row["series"]): row for row in rows}
    if len(keys) != len(rows) or len(rows) != len(months) * len(SERIES):
        raise ValueError("Expected unique complete month/series keys, including unavailable rows")
    ordinals = [date.fromisoformat(month + "-01").year * 12 + date.fromisoformat(month + "-01").month for month in months]
    if any(right - left != 1 for left, right in zip(ordinals, ordinals[1:])):
        raise ValueError("Bootstrap requires the full consecutive calendar, with missing months masked")
    eligible, errors, observed = [], {name: [] for name in SERIES}, []
    for month in months:
        group = [keys[month, series] for series in SERIES]
        if len({row["observed_streamflow_m3s"] for row in group}) != 1 or len({row["paired_days"] for row in group}) != 1:
            raise ValueError("Series differ in observed support")
        obs = group[0]["observed_streamflow_m3s"]
        values = [row["predicted_streamflow_m3s"] for row in group]
        valid = all(row["eligible"] for row in group) and obs is not None and all(v is not None for v in values)
        if valid and (not math.isfinite(obs) or obs < 0 or any(not math.isfinite(v) or v < 0 for v in values)):
            raise ValueError("Nonfinite or negative eligible flow")
        eligible.append(valid)
        observed.append(obs)
        for series, value in zip(SERIES, values):
            errors[series].append((value - obs) ** 2 if valid else None)
    support = [i for i, valid in enumerate(eligible) if valid]
    metrics = {series: ValidationEngine.evaluate([observed[i] for i in support],
        [keys[months[i], series]["predicted_streamflow_m3s"] for i in support]) for series in SERIES}
    if len(support) < 2:
        return {"status": "INSUFFICIENT_EVIDENCE", "hypothesis_status": "INSUFFICIENT_EVIDENCE",
            "eligible_months": len(support), "metrics": metrics, "contrasts": {}}, []
    n = len(months)
    block = uncertainty["block_months"]
    if block > n or block < 1 or uncertainty["method"] != "paired circular moving-block bootstrap on common monthly errors":
        raise ValueError("Unsupported frozen block bootstrap")
    rng = random.Random(uncertainty["seed"])
    draws, deltas, percentages = [], {f"{c}_vs_{r}": [] for c,r in CONTRASTS}, {f"{c}_vs_{r}": [] for c,r in CONTRASTS}
    for replicate in range(uncertainty["replicates"]):
        indices = []
        for _ in range(math.ceil(n / block)):
            start = rng.randrange(n)
            indices.extend((start + offset) % n for offset in range(block))
        indices = [i for i in indices[:n] if eligible[i]]
        row = {"replicate": replicate + 1, "sampled_eligible_months": len(indices)}
        if len(indices) >= 2:
            rmse = {series: math.sqrt(sum(errors[series][i] for i in indices) / len(indices)) for series in SERIES}
            for candidate, reference in CONTRASTS:
                key = f"{candidate}_vs_{reference}"
                delta = rmse[reference] - rmse[candidate]
                percent = 100 * delta / rmse[reference] if rmse[reference] else None
                deltas[key].append(delta)
                if percent is not None:
                    percentages[key].append(percent)
                row[f"{key}_reduction_m3s"] = delta
                row[f"{key}_reduction_percent"] = percent
        draws.append(row)
    tail = (1 - uncertainty["confidence"]) / 2
    contrasts = {}
    for candidate, reference in CONTRASTS:
        key = f"{candidate}_vs_{reference}"
        reference_rmse = metrics[reference]["rmse"]["value"]
        delta = reference_rmse - metrics[candidate]["rmse"]["value"]
        ci = [percentile(deltas[key], tail), percentile(deltas[key], 1 - tail)] if deltas[key] else None
        pct_ci = [percentile(percentages[key], tail), percentile(percentages[key], 1 - tail)] if percentages[key] else None
        contrasts[key] = {"rmse_reduction_m3s": delta, "rmse_reduction_percent": 100 * delta / reference_rmse if reference_rmse else None,
            "ci95_reduction_m3s": ci, "ci95_reduction_percent": pct_ci, "valid_replicates": len(deltas[key]),
            "role": "PRIMARY" if key == "D_vs_A" else "SECONDARY_EXPLORATORY_UNADJUSTED"}
    primary = contrasts["D_vs_A"]
    ci = primary["ci95_reduction_m3s"]
    status = "H1_SUPPORTED" if ci and ci[0] > 0 and primary["valid_replicates"] == uncertainty["replicates"] else "H1_NOT_SUPPORTED"
    return {"status": "EVALUATED", "hypothesis_status": status, "eligible_months": len(support),
        "calendar_months": n, "excluded_months": [m for m, valid in zip(months, eligible) if not valid],
        "metrics": metrics, "contrasts": contrasts, "uncertainty": uncertainty,
        "decision_rule": "D_vs_A absolute RMSE reduction CI95 strictly above zero; no 15% threshold",
        "secondary_policy": "Unadjusted descriptive intervals; no separate confirmatory decisions"}, draws

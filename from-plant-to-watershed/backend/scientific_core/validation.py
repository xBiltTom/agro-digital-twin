"""Validation metrics with explicit undefined/error states."""

from __future__ import annotations

import math
from typing import Iterable


def _metric(value: float | None, reason: str | None = None) -> dict[str, object]:
    return {"status": "DEFINED" if value is not None else "UNDEFINED", "value": value, "reason": reason}


class ValidationEngine:
    @staticmethod
    def evaluate(observed: Iterable[float | None], simulated: Iterable[float | None], *, units_match: bool = True) -> dict[str, object]:
        if not units_match:
            return {name: _metric(None, "incompatible units") for name in ("rmse", "nse", "pbias", "r2")}
        pairs = [(float(o), float(s)) for o, s in zip(observed, simulated)
                 if o is not None and s is not None and math.isfinite(float(o)) and math.isfinite(float(s))]
        if len(pairs) < 2:
            return {name: _metric(None, "at least two aligned finite pairs are required") for name in ("rmse", "nse", "pbias", "r2")}
        obs, sim = zip(*pairs)
        rmse = math.sqrt(sum((s - o) ** 2 for o, s in pairs) / len(pairs))
        mean_obs, mean_sim = sum(obs) / len(obs), sum(sim) / len(sim)
        denominator = sum((o - mean_obs) ** 2 for o in obs)
        nse = None if denominator == 0 else 1.0 - sum((s - o) ** 2 for o, s in pairs) / denominator
        obs_sum = sum(obs)
        pbias = None if obs_sum == 0 else 100.0 * sum(s - o for o, s in pairs) / obs_sum
        sim_denominator = sum((s - mean_sim) ** 2 for s in sim)
        r2 = None if denominator == 0 or sim_denominator == 0 else (
            sum((o - mean_obs) * (s - mean_sim) for o, s in pairs) ** 2 / (denominator * sim_denominator)
        )
        return {
            "n_pairs": len(pairs), "rmse": _metric(rmse),
            "nse": _metric(nse, "zero observed variance" if nse is None else None),
            "pbias": _metric(pbias, "zero observed sum" if pbias is None else None),
            "r2": _metric(r2, "zero observed or simulated variance" if r2 is None else None),
        }

    @staticmethod
    def compare(observed: Iterable[float | None], baseline: Iterable[float | None], twin: Iterable[float | None]) -> dict[str, object]:
        observed_values, baseline_values, twin_values = tuple(observed), tuple(baseline), tuple(twin)
        baseline_metrics = ValidationEngine.evaluate(observed_values, baseline_values)
        twin_metrics = ValidationEngine.evaluate(observed_values, twin_values)
        baseline_rmse = baseline_metrics["rmse"]["value"]
        twin_rmse = twin_metrics["rmse"]["value"]
        improvement = None if baseline_rmse in {None, 0} or twin_rmse is None else (baseline_rmse - twin_rmse) / baseline_rmse * 100.0
        return {"baseline": baseline_metrics, "twin": twin_metrics,
                "improvement_percent": _metric(improvement, "baseline RMSE unavailable or zero" if improvement is None else None),
                "threshold_reached": improvement is not None and improvement >= 15.0,
                "interpretation": "DEMONSTRATION_ONLY", "hypothesis_test": "NOT_FORMAL_HYPOTHESIS_TEST"}

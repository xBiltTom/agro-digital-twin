"""Observed-versus-simulated metrics with explicit alignment evidence.

This module deliberately contains no calibration logic.  In particular, it
never fills missing observations, interpolates dates, or changes a simulated
series before calculating a metric.  That keeps it usable for a real SWAT+
validation run as well as for the legacy demonstration path.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Iterable, Mapping


def _metric(value: float | None, reason: str | None = None) -> dict[str, object]:
    return {"status": "DEFINED" if value is not None else "UNDEFINED", "value": value, "reason": reason}


class ValidationEngine:
    @staticmethod
    def evaluate(observed: Iterable[float | None], simulated: Iterable[float | None], *, units_match: bool = True) -> dict[str, object]:
        if not units_match:
            return {name: _metric(None, "incompatible units") for name in ("rmse", "mae", "nse", "pbias", "r2", "kge")}
        pairs = [(float(o), float(s)) for o, s in zip(observed, simulated)
                 if o is not None and s is not None and math.isfinite(float(o)) and math.isfinite(float(s))]
        if len(pairs) < 2:
            return {name: _metric(None, "at least two aligned finite pairs are required") for name in ("rmse", "mae", "nse", "pbias", "r2", "kge")}
        obs, sim = zip(*pairs)
        rmse = math.sqrt(sum((s - o) ** 2 for o, s in pairs) / len(pairs))
        mae = sum(abs(s - o) for o, s in pairs) / len(pairs)
        mean_obs, mean_sim = sum(obs) / len(obs), sum(sim) / len(sim)
        denominator = sum((o - mean_obs) ** 2 for o in obs)
        nse = None if denominator == 0 else 1.0 - sum((s - o) ** 2 for o, s in pairs) / denominator
        obs_sum = sum(obs)
        pbias = None if obs_sum == 0 else 100.0 * sum(s - o for o, s in pairs) / obs_sum
        sim_denominator = sum((s - mean_sim) ** 2 for s in sim)
        r2 = None if denominator == 0 or sim_denominator == 0 else (
            sum((o - mean_obs) * (s - mean_sim) for o, s in pairs) ** 2 / (denominator * sim_denominator)
        )
        correlation = None if denominator == 0 or sim_denominator == 0 else (
            sum((o - mean_obs) * (s - mean_sim) for o, s in pairs) / math.sqrt(denominator * sim_denominator)
        )
        # KGE is undefined when either mean is zero or either variance is zero.
        # Reporting that state is preferable to selecting an arbitrary epsilon.
        if correlation is None or mean_obs == 0 or mean_sim == 0:
            kge, kge_reason = None, "zero observed/simulated variance or mean"
        else:
            std_obs = math.sqrt(denominator / len(obs))
            std_sim = math.sqrt(sim_denominator / len(sim))
            if std_obs == 0:
                kge, kge_reason = None, "zero observed variance"
            else:
                variability_ratio = (std_sim / mean_sim) / (std_obs / mean_obs)
                bias_ratio = mean_sim / mean_obs
                kge, kge_reason = 1.0 - math.sqrt((correlation - 1.0) ** 2 + (variability_ratio - 1.0) ** 2 + (bias_ratio - 1.0) ** 2), None
        return {
            "n_pairs": len(pairs), "rmse": _metric(rmse), "mae": _metric(mae),
            "nse": _metric(nse, "zero observed variance" if nse is None else None),
            "pbias": _metric(pbias, "zero observed sum" if pbias is None else None),
            "r2": _metric(r2, "zero observed or simulated variance" if r2 is None else None),
            "kge": _metric(kge, kge_reason),
        }

    @staticmethod
    def compare(
        observed: Iterable[float | None], baseline: Iterable[float | None], twin: Iterable[float | None],
        *, temporal_resolution: str = "unspecified", observed_evidence_type: str | None = None,
        baseline_evidence_type: str | None = None, coupled_evidence_type: str | None = None,
    ) -> dict[str, object]:
        observed_values, baseline_values, twin_values = tuple(observed), tuple(baseline), tuple(twin)
        baseline_metrics = ValidationEngine.evaluate(observed_values, baseline_values)
        twin_metrics = ValidationEngine.evaluate(observed_values, twin_values)
        baseline_rmse = baseline_metrics["rmse"]["value"]
        twin_rmse = twin_metrics["rmse"]["value"]
        improvement = None if baseline_rmse in {None, 0} or twin_rmse is None else (baseline_rmse - twin_rmse) / baseline_rmse * 100.0
        is_real_comparison = {
            observed_evidence_type, baseline_evidence_type, coupled_evidence_type,
        } == {"OBSERVED", "REAL_SWAT_PLUS", "REAL_SWAT_PLUS_COUPLED"}
        if improvement is None:
            hypothesis_status, hypothesis_reason = "INSUFFICIENT_EVIDENCE", "RMSE is undefined or zero"
        elif not is_real_comparison:
            hypothesis_status, hypothesis_reason = "INSUFFICIENT_EVIDENCE", "comparison does not contain observed flow plus paired real SWAT+ evidence"
        elif temporal_resolution.lower() != "monthly":
            hypothesis_status, hypothesis_reason = "INSUFFICIENT_EVIDENCE", "the registered primary hypothesis is monthly, not daily"
        elif improvement >= 15.0:
            hypothesis_status, hypothesis_reason = "H1_SUPPORTED", "monthly paired RMSE reduction is at least 15%"
        else:
            hypothesis_status, hypothesis_reason = "H1_NOT_SUPPORTED", "monthly paired RMSE reduction is below 15%"
        return {"baseline": baseline_metrics, "twin": twin_metrics,
                "improvement_percent": _metric(improvement, "baseline RMSE unavailable or zero" if improvement is None else None),
                "threshold_reached": improvement is not None and improvement >= 15.0,
                "temporal_resolution": temporal_resolution,
                "evidence": {"observed": observed_evidence_type, "baseline": baseline_evidence_type, "coupled": coupled_evidence_type},
                "hypothesis_status": hypothesis_status, "hypothesis_reason": hypothesis_reason,
                "interpretation": "OBSERVATIONAL_COMPARISON" if is_real_comparison else "DEMONSTRATION_ONLY",
                "hypothesis_test": "NOT_FORMAL_HYPOTHESIS_TEST"}

    @staticmethod
    def compare_dated(
        observed: Mapping[str | date, float | None], baseline: Mapping[str | date, float | None],
        coupled: Mapping[str | date, float | None], *, temporal_resolution: str,
        observed_evidence_type: str, baseline_evidence_type: str, coupled_evidence_type: str,
    ) -> dict[str, object]:
        """Align three series by their exact dates, retaining non-overlap as provenance.

        A mapping is used rather than parallel lists so a caller cannot silently
        compare a shifted SWAT series to USGS.  The date keys may be ISO strings
        or ``date`` objects, but duplicate normalized dates are rejected.
        """
        def normalized(values: Mapping[str | date, float | None], name: str) -> dict[str, float | None]:
            result: dict[str, float | None] = {}
            for raw_key, value in values.items():
                key = raw_key.isoformat() if isinstance(raw_key, date) else str(raw_key)
                try:
                    date.fromisoformat(key)
                except ValueError as exc:
                    raise ValueError(f"{name} contains a non-ISO date: {key!r}") from exc
                if key in result:
                    raise ValueError(f"{name} contains duplicate date {key}")
                result[key] = value
            return result

        observed_rows = normalized(observed, "observed")
        baseline_rows = normalized(baseline, "baseline")
        coupled_rows = normalized(coupled, "coupled")
        matched_dates = sorted(set(observed_rows) & set(baseline_rows) & set(coupled_rows))
        comparison = ValidationEngine.compare(
            [observed_rows[key] for key in matched_dates], [baseline_rows[key] for key in matched_dates],
            [coupled_rows[key] for key in matched_dates], temporal_resolution=temporal_resolution,
            observed_evidence_type=observed_evidence_type, baseline_evidence_type=baseline_evidence_type,
            coupled_evidence_type=coupled_evidence_type,
        )
        comparison["alignment"] = {
            "matched_dates": matched_dates, "matched_count": len(matched_dates),
            "observed_unmatched_dates": sorted(set(observed_rows) - set(matched_dates)),
            "baseline_unmatched_dates": sorted(set(baseline_rows) - set(matched_dates)),
            "coupled_unmatched_dates": sorted(set(coupled_rows) - set(matched_dates)),
            "excluded_due_to_nonoverlap": len(set(observed_rows) | set(baseline_rows) | set(coupled_rows)) - len(matched_dates),
            "imputation": "NONE",
        }
        return comparison

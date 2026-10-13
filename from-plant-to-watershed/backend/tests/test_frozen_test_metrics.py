"""Reproduction checks for the versioned USGS-backed monthly TEST metrics."""

from datetime import datetime, timezone

from scripts.report_frozen_test_metrics import reproduce_metrics


def test_frozen_test_metrics_match_the_published_usgs_evaluation():
    stamp = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    result = reproduce_metrics(stamp)

    assert result["executed_at_utc"] == stamp.isoformat()
    assert result["experiment_id"] == "sf-test-v1"
    assert result["simulation_dataset_id"] == "sf-test-v1-monthly"
    assert result["period"] == {"start": "2021-01-01", "end": "2025-12-31"}
    assert result["daily_source_observations"] == 1826
    assert result["eligible_months"] == 60
    assert result["published_hypothesis_status"] == "H1_NOT_SUPPORTED"
    assert set(result["series"]) == {"A", "B", "C", "D"}
    for series in result["series"].values():
        assert series["monthly_observation_prediction_pairs"] == 60
        assert set(series["metrics"]) == {"nse", "kge", "rmse", "mae", "pbias", "r2"}
        assert all(metric["status"] == "DEFINED" for metric in series["metrics"].values())

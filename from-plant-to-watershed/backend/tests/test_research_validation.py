from datetime import date

import pytest

from scientific_core import ValidationEngine, assign_temporal_split, validate_spatial_split


def test_dated_real_comparison_aligns_exact_dates_without_imputation():
    result = ValidationEngine.compare_dated(
        {"2020-01-01": 10.0, "2020-01-02": 20.0, "2020-01-03": 30.0},
        {"2020-01-01": 11.0, "2020-01-02": 20.0, "2020-01-04": 42.0},
        {date(2020, 1, 1): 10.0, date(2020, 1, 2): 21.0, date(2020, 1, 5): 55.0},
        temporal_resolution="monthly", observed_evidence_type="OBSERVED",
        baseline_evidence_type="REAL_SWAT_PLUS", coupled_evidence_type="REAL_SWAT_PLUS_COUPLED",
    )
    assert result["alignment"]["matched_dates"] == ["2020-01-01", "2020-01-02"]
    assert result["alignment"]["imputation"] == "NONE"
    assert result["baseline"]["mae"]["value"] == pytest.approx(0.5)
    assert result["baseline"]["kge"]["status"] == "DEFINED"
    assert result["hypothesis_status"] == "H1_NOT_SUPPORTED"
    assert result["interpretation"] == "OBSERVATIONAL_COMPARISON"


def test_hypothesis_is_not_claimed_for_proxy_or_daily_evidence():
    proxy = ValidationEngine.compare([1, 2], [2, 3], [1, 2], temporal_resolution="monthly")
    assert proxy["hypothesis_status"] == "INSUFFICIENT_EVIDENCE"
    daily = ValidationEngine.compare(
        [1, 2], [2, 3], [1, 2], temporal_resolution="daily", observed_evidence_type="OBSERVED",
        baseline_evidence_type="REAL_SWAT_PLUS", coupled_evidence_type="REAL_SWAT_PLUS_COUPLED",
    )
    assert daily["hypothesis_status"] == "INSUFFICIENT_EVIDENCE"


def test_temporal_split_uses_unique_dates_and_strict_chronology():
    dates = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06"]
    split = assign_temporal_split(dates, train_end="2020-01-02", validation_end="2020-01-04")
    assert {key for key, value in split.items() if value == "TRAIN"} == {"2020-01-01", "2020-01-02"}
    assert {key for key, value in split.items() if value == "VALIDATION"} == {"2020-01-03", "2020-01-04"}
    assert {key for key, value in split.items() if value == "TEST"} == {"2020-01-05", "2020-01-06"}
    with pytest.raises(ValueError, match="unique date"):
        assign_temporal_split(["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-03"], train_end="2020-01-01", validation_end="2020-01-02")


def test_spatial_split_keeps_watersheds_out_of_the_test_set():
    grouped = validate_spatial_split({"USGS-1": "TRAIN", "USGS-2": "VALIDATION", "USGS-3": "TEST"})
    assert grouped["TEST"] == ("USGS-3",)
    assert not (set(grouped["TRAIN"]) & set(grouped["TEST"]))
    with pytest.raises(ValueError, match="held-out"):
        validate_spatial_split({"USGS-1": "TRAIN"})

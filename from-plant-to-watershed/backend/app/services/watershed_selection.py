"""Reproducible Phase-C eligibility decisions; no hydrology-model behavior lives here."""

from dataclasses import dataclass
from typing import Any


MIN_AGRICULTURAL_FRACTION = 0.60
MIN_EFFECTIVE_YEARS = 20.0
MIN_DAILY_COVERAGE = 0.90


@dataclass(frozen=True)
class CandidateAssessment:
    watershed_name: str
    gauge_usgs: str
    effective_years: float | None
    daily_coverage_fraction: float | None
    agricultural_fraction: float | None
    major_dam_present: bool | None
    geometry_crs: str | None
    gauge_watershed_verified: bool


def calculate_agricultural_fraction(
    total_area_m2: float, agricultural_area_m2: float, source_crs: str, area_crs: str,
) -> float:
    """Validate a projected-area overlay result from an external land-cover workflow."""
    if not source_crs or not area_crs:
        raise ValueError("Source and projected area CRS are required")
    if area_crs.upper() in {"EPSG:4326", "WGS84"}:
        raise ValueError("Area calculations require a projected CRS, not geographic coordinates")
    if total_area_m2 <= 0 or agricultural_area_m2 < 0 or agricultural_area_m2 > total_area_m2:
        raise ValueError("Agricultural and total areas must be physically consistent")
    return agricultural_area_m2 / total_area_m2


def assess_candidate(candidate: CandidateAssessment) -> dict[str, Any]:
    """Apply only documented Phase-C rules and retain every exclusion reason."""
    reasons: list[str] = []
    if not candidate.geometry_crs:
        reasons.append("NOT_VERIFIED: watershed geometry CRS is missing")
    if not candidate.gauge_watershed_verified:
        reasons.append("NOT_VERIFIED: gauge-to-watershed association has not been verified")
    if candidate.effective_years is None or candidate.effective_years < MIN_EFFECTIVE_YEARS:
        reasons.append(f"INSUFFICIENT_RECORD: effective daily coverage is below {MIN_EFFECTIVE_YEARS:g} years")
    if candidate.daily_coverage_fraction is None or candidate.daily_coverage_fraction < MIN_DAILY_COVERAGE:
        reasons.append(f"INSUFFICIENT_COVERAGE: daily completeness is below {MIN_DAILY_COVERAGE:.0%}")
    if candidate.agricultural_fraction is None:
        reasons.append("NOT_VERIFIED: agricultural fraction is unavailable")
    elif candidate.agricultural_fraction < MIN_AGRICULTURAL_FRACTION:
        reasons.append(f"INSUFFICIENT_AGRICULTURE: below {MIN_AGRICULTURAL_FRACTION:.0%}")
    if candidate.major_dam_present is None:
        reasons.append("NOT_VERIFIED: major-dam/regulation screening is unavailable")
    elif candidate.major_dam_present:
        reasons.append("EXCLUDED: documented major dam or material regulation")
    return {"decision": "INCLUDE" if not reasons else "EXCLUDE", "reasons": reasons}


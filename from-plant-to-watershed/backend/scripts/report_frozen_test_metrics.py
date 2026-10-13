#!/usr/bin/env python3
"""Recalculate six metrics from the frozen USGS TEST observations and predictions."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
DOMAIN = PROJECT / "research_domain"
ARTIFACT_DIR = DOMAIN / "test_v1"
PREDICTIONS_FILE = ARTIFACT_DIR / "monthly-predictions.csv"
OBSERVATIONS_FILE = ARTIFACT_DIR / "observed-daily.csv"
ARTIFACT_MANIFEST_FILE = ARTIFACT_DIR / "artifact-manifest.json"
REPORT_FILE = DOMAIN / "south_fork_test_delivery_4_v1.json"
sys.path.insert(0, str(BACKEND))

from scientific_core.validation import ValidationEngine


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader)


def _verify_frozen_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    artifact_manifest = json.loads(ARTIFACT_MANIFEST_FILE.read_text(encoding="utf-8"))
    report_digest = _sha256(REPORT_FILE)
    if report_digest != artifact_manifest.get("report_sha256"):
        raise ValueError("The frozen TEST report checksum does not match artifact-manifest.json")
    expected_hashes = artifact_manifest.get("sha256") or {}
    for name, expected in expected_hashes.items():
        path = ARTIFACT_DIR / name
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"Frozen TEST artifact checksum mismatch: {name}")
    if PREDICTIONS_FILE.name not in expected_hashes or OBSERVATIONS_FILE.name not in expected_hashes:
        raise ValueError("The frozen TEST manifest does not cover both observations and predictions")
    report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    checksums = {
        "monthly_predictions_sha256": expected_hashes[PREDICTIONS_FILE.name],
        "observed_daily_sha256": expected_hashes[OBSERVATIONS_FILE.name],
        "published_report_sha256": report_digest,
    }
    return artifact_manifest, report, checksums


def reproduce_metrics(executed_at: datetime | None = None) -> dict[str, Any]:
    """Verify frozen artifacts and reproduce primary TEST metrics for A/B/C/D."""
    artifact_manifest, report, checksums = _verify_frozen_sources()
    daily_rows = _read_rows(OBSERVATIONS_FILE)
    interval = report["test_interval"]
    start, end = date.fromisoformat(interval[0]), date.fromisoformat(interval[1])
    expected_days = tuple(start + timedelta(days=offset) for offset in range((end - start).days + 1))
    observed_dates = [date.fromisoformat(row["date"]) for row in daily_rows]
    if len(observed_dates) != len(set(observed_dates)) or tuple(sorted(observed_dates)) != expected_days:
        raise ValueError("Frozen USGS daily observations do not exactly cover the declared TEST interval")

    all_rows = _read_rows(PREDICTIONS_FILE)
    selected: dict[str, dict[str, dict[str, str]]] = {name: {} for name in ("A", "B", "C", "D")}
    for row in all_rows:
        if row.get("partition") != "TEST" or row.get("variant") != "PRIMARY":
            continue
        series = row.get("series", "")
        if series not in selected:
            continue
        eligible = row.get("eligible", "").strip().lower()
        if eligible not in {"true", "false"}:
            raise ValueError(f"Invalid monthly eligibility value: {eligible!r}")
        if eligible == "false":
            continue
        month = row.get("month", "")
        if len(month) != 7 or month[4] != "-":
            raise ValueError(f"Invalid monthly period: {month!r}")
        date.fromisoformat(f"{month}-01")
        if month in selected[series]:
            raise ValueError(f"Duplicate TEST prediction for {series} in {month}")
        selected[series][month] = row

    expected_months = []
    current = date(start.year, start.month, 1)
    while current <= end:
        expected_months.append(current.strftime("%Y-%m"))
        current = date(current.year + (current.month == 12), (current.month % 12) + 1, 1)
    month_axis = tuple(expected_months)
    for series, rows in selected.items():
        if tuple(sorted(rows)) != month_axis:
            raise ValueError(f"Series {series} does not share the complete eligible TEST month axis")

    observation_by_month: dict[str, float] = {}
    output_series: dict[str, Any] = {}
    lineage = json.loads((ARTIFACT_DIR / "lineage.json").read_text(encoding="utf-8"))
    publications = lineage.get("publications") or []
    run_ids = {
        arm: [str(publication[arm]) for publication in publications]
        for arm in ("A", "B")
    }
    references = {"A": "A", "B": "B", "C": "A", "D": "B"}

    for series, rows in selected.items():
        ordered = [rows[month] for month in month_axis]
        observed: list[float] = []
        simulated: list[float] = []
        for row in ordered:
            try:
                obs = float(row["observed_streamflow_m3s"])
                pred = float(row["predicted_streamflow_m3s"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Series {series} contains a missing monthly value") from exc
            if not math.isfinite(obs) or not math.isfinite(pred):
                raise ValueError(f"Series {series} contains a non-finite monthly value")
            month = row["month"]
            previous = observation_by_month.setdefault(month, obs)
            if not math.isclose(previous, obs, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"Observed monthly values are not aligned across series in {month}")
            observed.append(obs)
            simulated.append(pred)

        metrics = ValidationEngine.evaluate(observed, simulated)
        published = (report.get("primary") or {}).get("metrics", {}).get(series)
        if not isinstance(published, dict):
            raise ValueError(f"Published report is missing metrics for {series}")
        for name in ("nse", "kge", "rmse", "mae", "pbias", "r2"):
            expected = published.get(name) or {}
            actual = metrics[name]
            if expected.get("status") != actual["status"]:
                raise ValueError(f"Reproduced {name.upper()} status differs from the published TEST result for {series}")
            if actual["value"] is not None and not math.isclose(
                float(expected["value"]), float(actual["value"]), rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError(f"Reproduced {name.upper()} differs from the published TEST result for {series}")
        physical_arm = references[series]
        output_series[series] = {
            "model_id": series if series in {"C", "D"} else None,
            "physical_reference_arm": physical_arm,
            "physical_reference_simulation_ids": run_ids[physical_arm],
            "monthly_observation_prediction_pairs": metrics.pop("n_pairs"),
            "period": {"start": month_axis[0], "end": month_axis[-1]},
            "metrics": metrics,
        }

    timestamp = executed_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("executed_at must include a timezone")
    return {
        "schema_version": "frozen-south-fork-test-metrics/v1",
        "status": "REPRODUCED_FROM_FROZEN_ARTIFACTS",
        "executed_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "experiment_id": report["experiment_id"],
        "simulation_dataset_id": report["dataset_id"],
        "observation_dataset_id": report["observation_dataset_id"],
        "period": {"start": interval[0], "end": interval[1]},
        "daily_source_observations": len(daily_rows),
        "eligible_months": len(month_axis),
        "metric_units": "streamflow m3/s, PBIAS percent, NSE/KGE/R2 dimensionless",
        "pbias_convention": "100 * sum(simulated - observed) / sum(observed)",
        "kge_convention": "modified KGE using coefficient-of-variation ratio",
        "published_hypothesis_status": report["primary"]["hypothesis_status"],
        "series": output_series,
        "source_artifact_count_verified": len(artifact_manifest.get("sha256", {})) + 1,
        "source_checksums": checksums,
        "interpretation": (
            "These metrics reproduce the separate sf-test-v1 monthly TEST evaluation. "
            "They do not validate the phase234-sf-2019-v2 playback or its plant physiology."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="optional JSON output path; stdout is used by default")
    args = parser.parse_args()
    try:
        result = reproduce_metrics()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Wrote verified metrics: {args.output}")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())

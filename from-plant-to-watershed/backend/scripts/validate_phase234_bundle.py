#!/usr/bin/env python3
"""Validate the immutable South Fork 2019 phase234 playback bundle."""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = BACKEND / "data/phase1-south-fork-2019/results/phase234-sf-2019-v2"
RUN_ID = "phase234-sf-2019-v2"
EXPECTED_HRUS = 36
EXPECTED_CHANNELS = 37
EXPECTED_DAYS = 365
REQUIRED_DATES = tuple(date(2019, 1, 1) + timedelta(days=offset) for offset in range(EXPECTED_DAYS))
REQUIRED_DATE_STRINGS = tuple(day.isoformat() for day in REQUIRED_DATES)


class BundleValidationError(ValueError):
    """The bundle is incomplete, internally inconsistent, or has changed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleValidationError(f"Cannot read JSON artifact {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleValidationError(f"Expected a JSON object in {path.name}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise BundleValidationError(f"CSV header is missing in {path.name}")
            return list(reader)
    except OSError as exc:
        raise BundleValidationError(f"Cannot read CSV artifact {path.name}: {exc}") from exc


def _require_finite(rows: list[dict[str, str]], file_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        for row_number, row in enumerate(rows, start=2):
            raw = row.get(column, "")
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise BundleValidationError(
                    f"{file_name}:{row_number} has no numeric {column} value"
                ) from exc
            if not math.isfinite(value):
                raise BundleValidationError(f"{file_name}:{row_number} has non-finite {column}")


def _require_daily_axis(rows: list[dict[str, str]], file_name: str) -> None:
    observed = [row.get("date", "") for row in rows]
    if tuple(sorted(set(observed))) != REQUIRED_DATE_STRINGS:
        raise BundleValidationError(
            f"{file_name} must contain exactly the unique dates 2019-01-01 through 2019-12-31"
        )
    for raw in observed:
        try:
            date.fromisoformat(raw)
        except ValueError as exc:
            raise BundleValidationError(f"{file_name} contains invalid ISO date {raw!r}") from exc


def _validate_entity_series(
    bundle: Path,
    file_name: str,
    id_column: str,
    expected_entities: int,
    numeric_columns: tuple[str, ...],
) -> tuple[list[dict[str, str]], set[str]]:
    rows = _read_csv(bundle / file_name)
    if not rows:
        raise BundleValidationError(f"{file_name} is empty")
    _require_daily_axis(rows, file_name)
    _require_finite(rows, file_name, numeric_columns)

    entity_ids = {row.get(id_column, "").strip() for row in rows}
    if "" in entity_ids or len(entity_ids) != expected_entities:
        raise BundleValidationError(
            f"{file_name} must contain {expected_entities} non-empty {id_column} values"
        )
    try:
        if any(int(identifier) <= 0 for identifier in entity_ids):
            raise ValueError
    except ValueError as exc:
        raise BundleValidationError(f"{file_name} contains an invalid {id_column}") from exc

    pairs = [(row["date"], row[id_column].strip()) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise BundleValidationError(f"{file_name} contains duplicate date/entity rows")
    expected_count = expected_entities * EXPECTED_DAYS
    if len(rows) != expected_count:
        raise BundleValidationError(
            f"{file_name} has {len(rows)} rows; expected {expected_count} aligned daily states"
        )
    expected_pairs = {(day, identifier) for day in REQUIRED_DATE_STRINGS for identifier in entity_ids}
    if set(pairs) != expected_pairs:
        raise BundleValidationError(f"{file_name} has missing or out-of-range entity dates")
    return rows, entity_ids


def validate_bundle(bundle_dir: Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    """Check checksums, dated coverage, finite required values, and coupling evidence."""
    bundle = bundle_dir.resolve()
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("run_id") != RUN_ID or manifest.get("status") != "COMPLETED":
        raise BundleValidationError(f"Expected completed run {RUN_ID}")
    run = manifest.get("run") or {}
    playback = manifest.get("playback") or {}
    if run.get("frequency") != "DAILY" or run.get("run_type") != "SWAT_MULTISCALE_COUPLED":
        raise BundleValidationError("The target bundle must be a daily SWAT_MULTISCALE_COUPLED run")
    if (run.get("start_date"), run.get("end_date")) != ("2019-01-01", "2019-12-31"):
        raise BundleValidationError("The run metadata does not cover South Fork 2019")
    if (playback.get("record_count"), playback.get("first_date"), playback.get("last_date")) != (
        EXPECTED_DAYS, "2019-01-01", "2019-12-31"
    ):
        raise BundleValidationError("Playback metadata does not describe all 365 unique dates")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise BundleValidationError("The scientific artifact checksum catalog is missing")
    verified = []
    for name, metadata in artifacts.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise BundleValidationError(f"Unsafe artifact path in manifest: {name}")
        path = bundle / relative
        if not path.is_file():
            raise BundleValidationError(f"Missing artifact: {name}")
        expected_hash = (metadata or {}).get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise BundleValidationError(f"Missing SHA-256 for artifact: {name}")
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise BundleValidationError(f"SHA-256 mismatch for artifact: {name}")
        if name.endswith(".csv") and (metadata or {}).get("row_count") is not None:
            csv_rows = _read_csv(path)
            if len(csv_rows) != metadata["row_count"]:
                raise BundleValidationError(f"Manifest row count differs for artifact: {name}")
        verified.append(name)

    archive = playback.get("archive_file")
    if not isinstance(archive, str) or archive not in artifacts:
        raise BundleValidationError("The playback archive is not included in the artifact catalog")
    if playback.get("archive_sha256") != artifacts[archive].get("sha256"):
        raise BundleValidationError("Playback archive checksums disagree")

    basin = _read_csv(bundle / "basin_daily.csv")
    _require_daily_axis(basin, "basin_daily.csv")
    _require_finite(
        basin,
        "basin_daily.csv",
        ("precip_mm", "runoff_mm", "evapotranspiration_mm", "soil_water_mm", "streamflow_m3s"),
    )
    if len(basin) != EXPECTED_DAYS:
        raise BundleValidationError("basin_daily.csv must contain exactly one basin record per date")

    hru_rows, hru_ids = _validate_entity_series(
        bundle, "hru_daily.csv", "hru_unit", EXPECTED_HRUS,
        ("precip_mm", "runoff_mm", "evapotranspiration_mm", "soil_water_mm"),
    )
    plant_rows, plant_hru_ids = _validate_entity_series(
        bundle, "plant_hru_daily.csv", "hru_unit", EXPECTED_HRUS,
        ("water_stress_factor", "lai_m2_m2", "biomass_kg_ha"),
    )
    if hru_ids != plant_hru_ids:
        raise BundleValidationError("Plant and hydrology outputs use different HRU IDs")
    if {(row["date"], row["hru_unit"].strip()) for row in hru_rows} != {
        (row["date"], row["hru_unit"].strip()) for row in plant_rows
    }:
        raise BundleValidationError("Plant and hydrology outputs are not aligned by date and HRU")

    channel_rows, channel_ids = _validate_entity_series(
        bundle, "channel_daily.csv", "channel_unit", EXPECTED_CHANNELS, ("streamflow_m3s",),
    )
    field_rows = _read_csv(bundle / "fspm_field_daily.csv")
    _require_daily_axis(field_rows, "fspm_field_daily.csv")
    if len(field_rows) != EXPECTED_DAYS:
        raise BundleValidationError("fspm_field_daily.csv must contain one field state per date")
    field_dates = [row["date"] for row in field_rows]
    if len(field_dates) != len(set(field_dates)):
        raise BundleValidationError("fspm_field_daily.csv contains duplicate dates")

    samples = _read_csv(bundle / "fspm_plant_samples_daily.csv")
    if not samples:
        raise BundleValidationError("FSPM representative plant states are missing")
    sample_keys = [
        (row.get("date", ""), row.get("calendar_id", "").strip(), row.get("plant.plant_id", "").strip())
        for row in samples
    ]
    if any(not calendar_id or not plant_id for _, calendar_id, plant_id in sample_keys) or len(sample_keys) != len(set(sample_keys)):
        raise BundleValidationError("FSPM plant sample IDs must be present and unique per calendar/date")
    if not {day for day, _, _ in sample_keys} <= set(REQUIRED_DATE_STRINGS):
        raise BundleValidationError("FSPM plant samples include a date outside 2019")
    _require_finite(samples, "fspm_plant_samples_daily.csv", (
        "plant.lai", "plant.transpiration_mm", "plant.stress", "plant.root_depth_m", "plant.biomass_g_plant",
    ))

    completeness = (manifest.get("validation") or {}).get("required_hydrology_complete") or {}
    if not completeness or not all(completeness.values()):
        raise BundleValidationError("The manifest does not mark all required basin variables complete")
    iterations = run.get("calendar_convergence_iterations") or []
    if len(iterations) < 2 or manifest["validation"].get("calendar_converged") is not True:
        raise BundleValidationError("The SWAT+/FSPM coupling did not record successful convergence")
    final = iterations[-1]
    delta = final.get("max_hru_daily_average_soil_water_delta_mm")
    tolerance = final.get("soil_water_convergence_tolerance_mm")
    if not isinstance(delta, (int, float)) or not isinstance(tolerance, (int, float)):
        raise BundleValidationError("The final soil-water convergence values are missing")
    if not math.isfinite(delta) or not math.isfinite(tolerance) or delta > tolerance:
        raise BundleValidationError("The final soil-water change exceeds the recorded tolerance")
    if final.get("per_hru_calendar_match") is not True:
        raise BundleValidationError("The final executed HRU calendar does not match the input calendar")
    if (final.get("effective_climate_match") or {}).get("date_count") != EXPECTED_DAYS:
        raise BundleValidationError("The final coupled run does not cover 365 forcing dates")
    if not isinstance(final.get("parameter_update_count"), int) or final["parameter_update_count"] <= 0:
        raise BundleValidationError("The final coupled run records no FSPM-to-SWAT+ parameter updates")

    corn_hru_count = (
        (manifest.get("calendar_coupling") or {}).get("cdl_weights") or {}
    ).get("valid_hru_count")
    return {
        "status": "VALID",
        "simulation_id": RUN_ID,
        "period": {"start": REQUIRED_DATE_STRINGS[0], "end": REQUIRED_DATE_STRINGS[-1]},
        "days": EXPECTED_DAYS,
        "basin_records": len(basin),
        "hru_count": len(hru_ids),
        "hru_records": len(hru_rows),
        "corn_hrus_in_executed_calendar": corn_hru_count,
        "channel_count": len(channel_ids),
        "channel_records": len(channel_rows),
        "plant_sample_records": len(samples),
        "plant_sample_days": len({day for day, _, _ in sample_keys}),
        "artifact_files_verified": len(verified),
        "playback_archive": archive,
        "coupling": {
            "run_type": run["run_type"],
            "iterations": len(iterations),
            "final_max_soil_water_delta_mm": delta,
            "tolerance_mm": tolerance,
            "fspm_parameter_updates": final["parameter_update_count"],
            "calendar_match": final["per_hru_calendar_match"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE,
                        help="result bundle directory (defaults to the versioned 2019 demo)")
    args = parser.parse_args()
    try:
        summary = validate_bundle(args.bundle_dir)
    except (BundleValidationError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

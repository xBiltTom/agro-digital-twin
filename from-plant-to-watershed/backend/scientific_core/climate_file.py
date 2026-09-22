"""Local normalized daily-climate artifacts; NetCDF is intentionally not required."""

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any


class NormalizedClimateFileProvider:
    """Reads a local, versioned forcing artifact into the scientific-core contract."""

    REQUIRED_METADATA = {"scenario", "gcm", "member", "period", "variables", "units", "calendar", "source", "bias_correction"}

    def __init__(self, csv_path: str | Path, metadata_path: str | Path | None = None, *, metadata: dict[str, Any] | None = None):
        if metadata_path is None and metadata is None:
            raise ValueError("metadata_path or metadata is required")
        self.csv_path, self.metadata_path, self.metadata = Path(csv_path), Path(metadata_path) if metadata_path else None, metadata

    def load(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        metadata = self.metadata or json.loads(self.metadata_path.read_text())
        missing = self.REQUIRED_METADATA - metadata.keys()
        if missing:
            raise ValueError(f"CMIP6 metadata missing: {', '.join(sorted(missing))}")
        with self.csv_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        required_columns = {"date", "precip_mm", "temp_c"}
        if not rows or not required_columns <= rows[0].keys():
            raise ValueError("normalized CMIP6 CSV requires date, precip_mm, temp_c")
        normalized: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            try:
                assumed = [name for name in ("solar_rad_mj", "rh_percent", "co2_ppm") if not row.get(name)]
                normalized.append({
                    "day_index": index, "date": row["date"], "precip_mm": float(row["precip_mm"]),
                    "temp_c": float(row["temp_c"]), "solar_rad_mj": float(row.get("solar_rad_mj") or metadata.get("default_solar_rad_mj", 18.5)),
                    "rh_percent": float(row.get("rh_percent") or metadata.get("default_rh_percent", 60.0)),
                    "co2_ppm": float(row.get("co2_ppm") or metadata.get("co2_ppm", 415.0)),
                    "assumed_weather_variables": assumed,
                })
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid normalized climate row {index}") from exc
        return normalized, metadata

    def forcing_for_period(self, start_date: str, end_date: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        rows, metadata = self.load()
        selected = [row for row in rows if start_date <= row["date"] <= end_date]
        expected = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
        if len(selected) != expected:
            raise ValueError(f"climate artifact has {len(selected)} daily rows for requested period; expected {expected}")
        if len({row["date"] for row in selected}) != expected:
            raise ValueError("climate artifact contains duplicate daily dates")
        expected_dates = [(date.fromisoformat(start_date) + timedelta(days=index)).isoformat() for index in range(expected)]
        if [row["date"] for row in selected] != expected_dates:
            raise ValueError("climate artifact dates are missing, out of order, or outside the requested daily sequence")
        return [{**row, "day_index": idx} for idx, row in enumerate(selected, start=1)], metadata


class Cmip6FileProvider(NormalizedClimateFileProvider):
    """Backward-compatible CMIP6-named provider for normalized local artifacts."""

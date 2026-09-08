"""USGS daily-streamflow retrieval, normalization, QC, and monthly derivation.

The provider deliberately preserves the exact response bytes before parsing. It is
infrastructure for observed data, not input to the simplified hydrology model.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


CFS_TO_M3S = 0.028316846592
USGS_DAILY_VALUES_URL = "https://waterservices.usgs.gov/nwis/dv/"
USGS_DAILY_VALUES_REFERENCE = "https://waterservices.usgs.gov/docs/dv-service/daily-values-service-details/"
STATION_ID_PATTERN = re.compile(r"^\d{8,15}$")
PARSER_VERSION = "1.0"


@dataclass(frozen=True)
class StreamflowRecord:
    observed_on: date
    original_value: float | None
    value_m3s: float | None
    original_unit: str
    quality_status: str | None


@dataclass(frozen=True)
class QualityReport:
    n_observations: int
    missing_count: int
    missing_fraction: float
    duplicate_count: int
    invalid_count: int
    gap_count: int
    coverage_fraction: float
    effective_years: float
    start_date: str | None
    end_date: str | None
    chronological: bool
    expected_frequency: str = "daily"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MonthlyStreamflow:
    month: str
    mean_discharge_m3s: float | None
    observed_days: int
    expected_days: int
    coverage_fraction: float
    included: bool


class UsgsStreamflowProvider:
    """Provider for USGS daily mean discharge (parameter 00060, statistic 00003)."""

    def __init__(self, data_root: Path | None = None, downloader: Callable[[str], bytes] | None = None):
        self.data_root = data_root or Path(__file__).resolve().parents[3] / "data"
        self._downloader = downloader or self._download

    @staticmethod
    def cfs_to_m3s(value_cfs: float) -> float:
        if value_cfs < 0:
            raise ValueError("Streamflow cannot be converted from a negative cfs value")
        return value_cfs * CFS_TO_M3S

    @staticmethod
    def build_daily_values_url(station_id: str, start: date, end: date) -> str:
        if not STATION_ID_PATTERN.fullmatch(station_id):
            raise ValueError("USGS station_id must contain 8 to 15 digits")
        if end < start:
            raise ValueError("end date must not precede start date")
        query = urlencode({
            "format": "json", "sites": station_id, "parameterCd": "00060", "statCd": "00003",
            "startDT": start.isoformat(), "endDT": end.isoformat(), "siteStatus": "all",
        })
        return f"{USGS_DAILY_VALUES_URL}?{query}"

    @staticmethod
    def _download(url: str) -> bytes:
        try:
            with urlopen(url, timeout=60) as response:  # nosec B310 - URL is built from the official constant above
                if response.status != 200:
                    raise RuntimeError(f"USGS returned HTTP {response.status}")
                return response.read()
        except HTTPError as exc:
            raise RuntimeError(f"USGS returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"USGS request failed: {exc.reason}") from exc

    def fetch_raw(self, station_id: str, start: date, end: date) -> tuple[str, bytes]:
        url = self.build_daily_values_url(station_id, start, end)
        raw = self._downloader(url)
        if not raw:
            raise ValueError("USGS returned an empty response")
        return url, raw

    def persist_raw_artifact(self, station_id: str, start: date, end: date, raw: bytes) -> tuple[Path, str]:
        if not STATION_ID_PATTERN.fullmatch(station_id):
            raise ValueError("Unsafe station identifier")
        target = self.data_root / "raw" / "usgs" / f"{station_id}_{start.isoformat()}_{end.isoformat()}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return target, hashlib.sha256(raw).hexdigest()

    @staticmethod
    def parse_daily_values(raw: bytes, station_id: str) -> list[StreamflowRecord]:
        try:
            payload = json.loads(raw.decode("utf-8"))
            series = payload["value"]["timeSeries"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError("Invalid USGS daily-values JSON response") from exc
        if not series:
            raise ValueError("USGS response contains no daily streamflow series")

        matching_series = [item for item in series if item.get("sourceInfo", {}).get("siteCode", [{}])[0].get("value") == station_id]
        source = matching_series[0] if matching_series else series[0]
        variable = source.get("variable", {})
        parameter = variable.get("variableCode", [{}])[0].get("value")
        unit = variable.get("unit", {}).get("unitCode")
        if parameter != "00060" or unit not in {"ft3/s", "cfs"}:
            raise ValueError("USGS response is not daily discharge in ft3/s")
        values = source.get("values", [{}])[0].get("value", [])
        records: list[StreamflowRecord] = []
        for item in values:
            try:
                observed_on = date.fromisoformat(item["dateTime"][:10])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("USGS record has an invalid date") from exc
            value_text = item.get("value")
            value = None if value_text in {None, "", "NaN"} else float(value_text)
            normalized = None if value is None else value * CFS_TO_M3S
            qualifiers = item.get("qualifiers") or []
            records.append(StreamflowRecord(observed_on, value, normalized, unit, ";".join(qualifiers) or None))
        if not records:
            raise ValueError("USGS response contains no observations")
        return records

    @staticmethod
    def quality_control(records: Iterable[StreamflowRecord]) -> QualityReport:
        rows = list(records)
        if not rows:
            return QualityReport(0, 0, 0.0, 0, 0, 0, 0.0, 0.0, None, None, True)
        dates = [row.observed_on for row in rows]
        unique_dates = set(dates)
        valid_dates = {
            row.observed_on for row in rows
            if row.value_m3s is not None and row.value_m3s >= 0
        }
        start, end = min(dates), max(dates)
        expected_days = (end - start).days + 1
        missing_count = sum(row.value_m3s is None for row in rows)
        invalid_count = sum(row.value_m3s is not None and row.value_m3s < 0 for row in rows)
        duplicate_count = len(dates) - len(unique_dates)
        observed_unique = len(unique_dates)
        gap_count = max(0, expected_days - observed_unique)
        coverage = len(valid_dates) / expected_days
        return QualityReport(
            n_observations=len(rows), missing_count=missing_count, missing_fraction=missing_count / len(rows),
            duplicate_count=duplicate_count, invalid_count=invalid_count, gap_count=gap_count,
            coverage_fraction=coverage, effective_years=len(valid_dates) / 365.2425,
            start_date=start.isoformat(), end_date=end.isoformat(), chronological=dates == sorted(dates),
        )

    @staticmethod
    def monthly_mean_discharge(records: Iterable[StreamflowRecord], minimum_coverage: float = 0.9) -> list[MonthlyStreamflow]:
        if not 0 < minimum_coverage <= 1:
            raise ValueError("minimum_coverage must be in (0, 1]")
        by_month: dict[tuple[int, int], list[StreamflowRecord]] = defaultdict(list)
        for record in records:
            by_month[(record.observed_on.year, record.observed_on.month)].append(record)
        output: list[MonthlyStreamflow] = []
        for (year, month), rows in sorted(by_month.items()):
            expected = (date(year + (month == 12), month % 12 + 1, 1) - date(year, month, 1)).days
            valid = [row.value_m3s for row in rows if row.value_m3s is not None and row.value_m3s >= 0]
            coverage = len(valid) / expected
            output.append(MonthlyStreamflow(
                month=f"{year:04d}-{month:02d}", mean_discharge_m3s=(sum(valid) / len(valid) if coverage >= minimum_coverage else None),
                observed_days=len(valid), expected_days=expected, coverage_fraction=coverage,
                included=coverage >= minimum_coverage,
            ))
        return output

    async def fetch_parse_and_store(self, station_id: str, start: date, end: date) -> tuple[str, Path, str, list[StreamflowRecord], QualityReport]:
        url, raw = await asyncio.to_thread(self.fetch_raw, station_id, start, end)
        path, checksum = await asyncio.to_thread(self.persist_raw_artifact, station_id, start, end, raw)
        records = self.parse_daily_values(raw, station_id)
        return url, path, checksum, records, self.quality_control(records)

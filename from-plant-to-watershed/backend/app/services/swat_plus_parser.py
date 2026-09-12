"""Parser and integrity checks for tabular SWAT+ output files.

Missing variables remain ``None``/``NOT_AVAILABLE``; this module never derives a
scientific value as a substitute for a missing SWAT+ output column.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from pathlib import Path
import re
from typing import Any


_TOKEN = re.compile(r"[^a-z0-9]+")
_DATE_KEYS = {"date", "day", "jday", "mon", "month", "yr", "year"}
_VARIABLES = {
    "runoff_mm": {"surq", "surqgen", "surqcont", "runoff", "suro", "qsurf"},
    "evapotranspiration_mm": {"et", "etday", "etplant", "etsoil", "etact", "aet"},
    "soil_water_mm": {"sw", "soilwater", "swfinal", "swinit", "swave"},
    "percolation_mm": {"perc", "perco", "percolation", "sepbtm"},
    "streamflow_m3s": {"floout", "flowout", "streamflow", "discharge", "flow"},
}


def _normalise(value: str) -> str:
    return _TOKEN.sub("", value.lower().replace("³", "3"))


def _parse_number(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _column_map(headers: list[str]) -> dict[str, int]:
    return {_normalise(header): index for index, header in enumerate(headers)}


def _find_column(columns: dict[str, int], aliases: set[str]) -> int | None:
    return next((index for name, index in columns.items() if name in aliases), None)


def _unit_factor(variable: str, unit: str) -> float | None:
    token = _normalise(unit)
    # SWAT+ core water-balance and channel default units are mm and m3/s.
    if not token:
        return 1.0
    if variable == "streamflow_m3s":
        if token in {"m3s", "cms", "cumec"}:
            return 1.0
        if token in {"m3d", "m3day"}:
            return 1 / 86400
        return None
    if token in {"mm", "mmd", "mmday"}:
        return 1.0
    if token in {"m", "meter", "metre"}:
        return 1000.0
    return None


def _date_from_row(columns: dict[str, int], values: list[str]) -> str | None:
    def value(name: str) -> int | None:
        idx = columns.get(name)
        if idx is None or idx >= len(values):
            return None
        try:
            return int(float(values[idx]))
        except ValueError:
            return None
    date_index = columns.get("date")
    if date_index is not None and date_index < len(values):
        try:
            return date.fromisoformat(values[date_index].strip()).isoformat()
        except ValueError:
            pass
    year = value("yr") or value("year")
    month = value("mon") or value("month")
    day = value("day")
    jday = value("jday")
    try:
        if year and month and day:
            return date(year, month, day).isoformat()
        if year and jday:
            return (date(year, 1, 1) + timedelta(days=jday - 1)).isoformat()
        if year and month:
            return date(year, month, 1).isoformat()
    except ValueError:
        return None
    return None


@dataclass(frozen=True)
class SwatParsedOutput:
    records: list[dict[str, Any]]
    hru_results: list[dict[str, Any]]
    water_balance: dict[str, Any]
    output_files: list[str]
    source_files: list[Path]


class SwatOutputParser:
    def __init__(self, output_frequency: str = "DAILY", outlet_unit: str | None = None):
        self.output_frequency = output_frequency
        self.outlet_unit = outlet_unit
        self._parse_warnings: list[dict[str, str]] = []

    def _files(self, run_directory: Path, stems: tuple[str, ...]) -> list[Path]:
        files = sorted({path for stem in stems for path in run_directory.glob(f"{stem}*") if path.is_file()})
        suffixes = {"DAILY": ("day", "daily"), "MONTHLY": ("mon", "month"), "ANNUAL": ("yr", "year", "annual")}[self.output_frequency]
        preferred = [path for path in files if any(f"_{suffix}" in path.stem.lower() for suffix in suffixes)]
        return preferred or files

    @staticmethod
    def _table(path: Path) -> tuple[list[str], list[str], list[list[str]]]:
        lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        header_index = next((index for index, line in enumerate(lines)
                             if len(line.split()) >= 2 and any(_normalise(token) in _DATE_KEYS for token in line.split())), None)
        if header_index is None:
            raise ValueError(f"{path.name} does not contain a recognizable table header")
        header_matches = list(re.finditer(r"\S+", lines[header_index]))
        headers = [match.group() for match in header_matches]
        # SWAT+ aligns unit cells below the fixed-width header. Splitting the
        # units line would drop empty cells and shift later units (notably
        # ``flo_out``) onto sediment columns.
        units_line = lines[header_index + 1] if header_index + 1 < len(lines) else ""
        split_units = units_line.split()
        units = split_units if len(split_units) == len(headers) else [
            units_line[match.start():header_matches[index + 1].start() if index + 1 < len(header_matches) else None].strip()
            for index, match in enumerate(header_matches)
        ]
        # Some legitimate SWAT+ tables omit trailing empty text fields (for
        # example ``mgt_ops``). Numeric columns are addressed defensively by
        # index below, so requiring the complete display-width would discard
        # otherwise valid daily records.
        rows = [line.split() for line in lines[header_index + 2:] if len(line.split()) >= 4]
        if not rows:
            raise ValueError(f"{path.name} has no output rows")
        return headers, units, rows

    def _read(self, path: Path, wanted: set[str]) -> list[dict[str, Any]]:
        headers, units, rows = self._table(path)
        columns = _column_map(headers)
        unit_index = next((columns[key] for key in ("unit", "unitid", "gisid") if key in columns), None)
        fields: dict[str, tuple[int, float | None]] = {}
        for variable in wanted:
            index = _find_column(columns, _VARIABLES[variable])
            if index is not None:
                unit = units[index] if index < len(units) else ""
                factor = _unit_factor(variable, unit)
                if factor is None:
                    self._parse_warnings.append({"code": "UNEXPECTED_UNIT", "message": f"{variable} uses unsupported unit {unit!r}"})
                fields[variable] = (index, factor)
        parsed = []
        for values in rows:
            period = _date_from_row(columns, values)
            if period is None:
                continue
            record: dict[str, Any] = {"period": period}
            if unit_index is not None and unit_index < len(values):
                record["_unit"] = values[unit_index]
            for variable, (index, factor) in fields.items():
                raw = _parse_number(values[index]) if index < len(values) else None
                if raw is None and index < len(values) and values[index].strip().lower() in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                    self._parse_warnings.append({"code": "NON_FINITE_VALUE", "message": f"{variable} contains a non-finite value"})
                record[variable] = raw * factor if raw is not None and factor is not None else None
            parsed.append(record)
        return parsed

    def _select_outlet(self, rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        units = {str(row["_unit"]) for row in rows if row.get("_unit") not in {None, ""}}
        if self.outlet_unit is not None:
            selected = [row for row in rows if str(row.get("_unit")) == self.outlet_unit]
            if not selected:
                raise ValueError(f"Configured outlet_unit {self.outlet_unit!r} was not found in {kind} output")
            return selected
        if len(units) > 1:
            raise ValueError(f"{kind} output contains multiple units; configure swat_plus.outlet_unit")
        return rows

    @staticmethod
    def _validate(records: list[dict[str, Any]], start_date: date | None, end_date: date | None, frequency: str) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        periods = [row.get("period") for row in records if row.get("period")]
        if len(periods) != len(set(periods)):
            warnings.append({"code": "DUPLICATE_TIMESTAMPS", "message": "SWAT+ output has duplicate periods"})
        if any(row.get("runoff_mm") is not None and row["runoff_mm"] < 0 for row in records):
            warnings.append({"code": "NEGATIVE_RUNOFF", "message": "SWAT+ output has negative runoff"})
        if any(row.get("streamflow_m3s") is not None and row["streamflow_m3s"] < 0 for row in records):
            warnings.append({"code": "NEGATIVE_STREAMFLOW", "message": "SWAT+ output has negative streamflow"})
        if any(not math.isfinite(value) for row in records for value in row.values() if isinstance(value, float)):
            warnings.append({"code": "NON_FINITE_VALUE", "message": "SWAT+ output has non-finite values"})
        if not periods:
            warnings.append({"code": "MISSING_PERIODS", "message": "No dated SWAT+ records were parsed"})
        if start_date and end_date and frequency == "DAILY":
            actual = {date.fromisoformat(period) for period in periods}
            expected = {start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)}
            if expected - actual:
                warnings.append({"code": "MISSING_PERIODS", "message": f"SWAT+ output is missing {len(expected - actual)} requested daily periods"})
        return warnings

    @staticmethod
    def _merge(water_balance: list[dict[str, Any]], channels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_period: dict[str, dict[str, Any]] = {}
        for row in water_balance + channels:
            period = row.get("period")
            if period is not None:
                by_period.setdefault(period, {"period": period}).update({key: value for key, value in row.items() if key != "period" and value is not None})
        return [by_period[period] for period in sorted(by_period)]

    def parse(self, run_directory: Path, start_date: date | None = None, end_date: date | None = None) -> SwatParsedOutput:
        self._parse_warnings = []
        wb_files = self._files(run_directory, ("output_wb", "basin_wb"))
        channel_files = self._files(run_directory, ("output_channel", "channel_sd"))
        hru_files = self._files(run_directory, ("output_hru", "hru_wb"))
        if not wb_files and not channel_files:
            raise FileNotFoundError("No output_wb* or output_channel* file exists")
        water_balance_rows = self._select_outlet(
            [row for path in wb_files for row in self._read(path, {"runoff_mm", "evapotranspiration_mm", "soil_water_mm", "percolation_mm"})], "basin water-balance",
        )
        channel_rows = self._select_outlet(
            [row for path in channel_files for row in self._read(path, {"streamflow_m3s"})], "channel",
        )
        records = self._merge(water_balance_rows, channel_rows)
        if start_date and end_date:
            records = [row for row in records if start_date.isoformat() <= row["period"] <= end_date.isoformat()]
        if not records:
            raise ValueError("Recognized SWAT+ files had no dated output records")
        hru_results = [row for path in hru_files for row in self._read(path, {"runoff_mm", "evapotranspiration_mm", "soil_water_mm", "percolation_mm"})]
        if start_date and end_date:
            hru_results = [row for row in hru_results if start_date.isoformat() <= row["period"] <= end_date.isoformat()]
        warnings = self._validate(records, start_date, end_date, self.output_frequency)
        warnings.extend({"code": warning["code"], "message": warning["message"]} for warning in self._parse_warnings if warning not in warnings)
        availability = {variable: "AVAILABLE" if any(row.get(variable) is not None for row in records) else "NOT_AVAILABLE" for variable in _VARIABLES}
        complete = all(availability[name] == "AVAILABLE" for name in ("runoff_mm", "evapotranspiration_mm", "percolation_mm"))
        water_balance = {
            "status": "CHECKED" if complete else "NOT_AVAILABLE", "variable_availability": availability,
            "warnings": warnings,
            "totals_mm": {name: sum(row.get(name, 0.0) for row in records if row.get(name) is not None) for name in ("runoff_mm", "evapotranspiration_mm", "percolation_mm")},
            "mean_streamflow_m3s": (sum(row["streamflow_m3s"] for row in records if row.get("streamflow_m3s") is not None) / sum(1 for row in records if row.get("streamflow_m3s") is not None)) if any(row.get("streamflow_m3s") is not None for row in records) else None,
            "reason": None if complete else "One or more required balance terms are absent from SWAT+ outputs",
        }
        records = [{key: value for key, value in row.items() if key != "_unit"} for row in records]
        hru_results = [{("hru_unit" if key == "_unit" else key): value for key, value in row.items()} for row in hru_results]
        source_files = wb_files + channel_files + hru_files
        return SwatParsedOutput(records=records, hru_results=hru_results, water_balance=water_balance,
                                output_files=[str(path.relative_to(run_directory)) for path in source_files], source_files=source_files)

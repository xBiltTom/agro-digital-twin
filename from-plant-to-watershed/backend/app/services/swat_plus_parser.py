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
from typing import Any, Sequence


_TOKEN = re.compile(r"[^a-z0-9]+")
_DATE_KEYS = {"date", "day", "jday", "mon", "month", "yr", "year"}
_VARIABLES = {
    "precip_mm": ("precip", "precipitation", "rain"),
    # Prefer the generated runoff term, not the routed/contributed amount.
    "runoff_mm": ("surqgen", "surq", "runoff", "suro", "qsurf"),
    "runoff_contribution_mm": ("surqcont",),
    "evapotranspiration_mm": ("et", "etday", "etact", "aet"),
    "plant_evapotranspiration_mm": ("eplant", "etplant"),
    "soil_evaporation_mm": ("esoil", "etsoil"),
    "canopy_evaporation_mm": ("ecanopy",),
    "potential_evapotranspiration_mm": ("pet",),
    # Current end-of-day storage is the state used by playback. Keep initial
    # and average storage available separately instead of letting header order
    # accidentally choose sw_init.
    "soil_water_mm": ("swfinal", "sw", "soilwater"),
    "soil_water_initial_mm": ("swinit",),
    "soil_water_average_mm": ("swave",),
    "percolation_mm": ("perc", "perco", "percolation", "sepbtm"),
    "tile_drainage_mm": ("qtile",),
    "lateral_flow_mm": ("latq",),
    "water_yield_mm": ("wateryld",),
    "streamflow_m3s": ("floout", "flowout", "streamflow", "discharge", "flow"),
    "channel_area_ha": ("area",),
    "channel_precip_volume_m3": ("precip",),
    "channel_evap_volume_m3": ("evap",),
    "channel_seep_volume_m3": ("seep",),
    "channel_water_storage_m3": ("flostor",),
    "channel_inflow_m3s": ("floin",),
    "channel_water_temp_c": ("watertemp",),
    "lai_m2_m2": ("lai",),
    "biomass_kg_ha": ("bioms", "biomass"),
    "yield_kg_ha": ("yield",),
    "water_stress_factor": ("strsw",),
    "aeration_stress_factor": ("strsa",),
    "temperature_stress_factor": ("strstmp",),
    "nitrogen_stress_factor": ("strsn",),
    "phosphorus_stress_factor": ("strsp",),
    "salinity_stress_factor": ("strss",),
    "plant_heat_unit_fraction": ("phubas0",),
    "biomass_growth_kg_ha": ("bm_grow",),
}
_WATER_BALANCE_VARIABLES = (
    "precip_mm", "runoff_mm", "runoff_contribution_mm", "evapotranspiration_mm",
    "plant_evapotranspiration_mm", "soil_evaporation_mm", "canopy_evaporation_mm",
    "potential_evapotranspiration_mm", "soil_water_mm", "soil_water_initial_mm",
    "soil_water_average_mm", "percolation_mm", "streamflow_m3s",
    "tile_drainage_mm", "lateral_flow_mm", "water_yield_mm",
)


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


def _find_column(columns: dict[str, int], aliases: Sequence[str]) -> int | None:
    return next((columns[name] for name in aliases if name in columns), None)


def _unit_factor(variable: str, unit: str) -> float | None:
    token = _normalise(unit)
    # SWAT+ core water-balance and channel default units are mm and m3/s.
    if not token:
        return 1.0
    if variable.endswith("_factor") or variable in {"lai_m2_m2", "plant_heat_unit_fraction"}:
        return 1.0 if token in {"m2m2", "fraction", "frac", "", "----", "degc"} else None
    if variable in {"biomass_kg_ha", "yield_kg_ha", "biomass_growth_kg_ha"}:
        return 1.0 if token in {"kgha", "kg/ha"} else None
    if variable == "streamflow_m3s":
        if token in {"m3s", "cms", "cumec"}:
            return 1.0
        if token in {"m3d", "m3day"}:
            return 1 / 86400
        return None
    if variable == "channel_inflow_m3s":
        return 1.0 if token in {"m3s", "cms", "cumec"} else None
    if variable == "channel_area_ha":
        return 1.0 if token in {"ha", "hectare", "hectares"} else None
    if variable in {"channel_precip_volume_m3", "channel_evap_volume_m3",
                    "channel_seep_volume_m3", "channel_water_storage_m3"}:
        return 1.0 if token in {"m3", "m^3", "cubicmeter", "cubicmetre"} else None
    if variable == "channel_water_temp_c":
        return 1.0 if token in {"degc", "c", "celsius"} else None
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
            candidate = date(year, 1, 1) + timedelta(days=jday - 1)
            return candidate.isoformat() if jday >= 1 and candidate.year == year else None
        if year and month:
            return date(year, month, 1).isoformat()
        if year:
            return date(year, 1, 1).isoformat()
    except ValueError:
        return None
    return None


@dataclass(frozen=True)
class SwatParsedOutput:
    records: list[dict[str, Any]]
    hru_results: list[dict[str, Any]]
    plant_results: list[dict[str, Any]]
    channel_results: list[dict[str, Any]]
    management_events: list[dict[str, Any]]
    water_balance: dict[str, Any]
    output_files: list[str]
    source_files: list[Path]


class SwatOutputParser:
    def __init__(self, output_frequency: str = "DAILY", outlet_unit: str | None = None):
        self.output_frequency = output_frequency
        self.outlet_unit = outlet_unit
        self._parse_warnings: list[dict[str, str]] = []

    def _files(self, run_directory: Path, stems: tuple[str, ...]) -> list[Path]:
        files = sorted({path for stem in stems for path in run_directory.glob(f"{stem}*")
                        if path.is_file() and (path.stem == stem or path.stem.startswith(f"{stem}_"))})
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
        if len(split_units) == len(headers):
            units = split_units
        else:
            # Unit strings can be wider than short headers (``m**2/m**2``
            # below ``lai``). Assign each unit token by its printed center
            # instead of slicing from the header's left edge and truncating it.
            unit_matches = list(re.finditer(r"\S+", units_line))
            centers = [(match.start() + match.end()) / 2 for match in header_matches]
            units = [""] * len(headers)
            for unit_match in unit_matches:
                center = (unit_match.start() + unit_match.end()) / 2
                nearest = min(range(len(centers)), key=lambda index: abs(centers[index] - center))
                if not units[nearest]:
                    units[nearest] = unit_match.group()
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
        gis_id_index = columns.get("gisid")
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
            parsed_date = date.fromisoformat(period)
            if self.output_frequency == "MONTHLY":
                period = parsed_date.replace(day=1).isoformat()
            elif self.output_frequency == "ANNUAL":
                period = parsed_date.replace(month=1, day=1).isoformat()
            record: dict[str, Any] = {"period": period}
            if unit_index is not None and unit_index < len(values):
                record["_unit"] = values[unit_index]
            if gis_id_index is not None and gis_id_index < len(values):
                record["_gis_id"] = values[gis_id_index]
            name_index = columns.get("name")
            if name_index is not None and name_index < len(values):
                record["_name"] = values[name_index]
            for variable, (index, factor) in fields.items():
                raw = _parse_number(values[index]) if index < len(values) else None
                if raw is None and index < len(values) and values[index].strip().lower() in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                    self._parse_warnings.append({"code": "NON_FINITE_VALUE", "message": f"{variable} contains a non-finite value"})
                record[variable] = raw * factor if raw is not None and factor is not None else None
            parsed.append(record)
        return parsed

    def _select_outlet(self, rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        selector = "_gis_id" if kind == "channel" and any(row.get("_gis_id") not in {None, ""} for row in rows) else "_unit"
        units = {str(row[selector]) for row in rows if row.get(selector) not in {None, ""}}
        if self.outlet_unit is not None:
            selected = [row for row in rows if str(row.get(selector)) == self.outlet_unit]
            if not selected:
                # SWAT+ basin-level tables conventionally use their own
                # singleton basin unit (often ``1``), whereas channel tables
                # use the selected outlet channel GIS ID.  Keep that one
                # physical basin series instead of treating the valid,
                # different identifier as a missing outlet.
                if kind == "basin water-balance" and len(units) <= 1:
                    return rows
                raise ValueError(f"Configured outlet_unit {self.outlet_unit!r} was not found in {kind} output")
            return selected
        if len(units) > 1:
            raise ValueError(f"{kind} output contains multiple units; configure swat_plus.outlet_unit")
        return rows

    @staticmethod
    def _event_rows(path: Path) -> list[dict[str, Any]]:
        lines = [line for line in path.read_text(encoding="utf-8", errors="strict").splitlines() if line.strip()]
        if len(lines) < 4:
            raise ValueError(f"{path.name} does not contain a management-event table")
        header_index = next((i for i, line in enumerate(lines)
                             if "hru" in [token.lower() for token in line.split()]
                             and "operation" in [token.lower() for token in line.split()]), None)
        if header_index is None:
            raise ValueError(f"{path.name} has no recognizable management-event header")
        headers = [token.lower() for token in lines[header_index].split()]
        positions = {name: headers.index(name) for name in ("hru", "year", "mon", "day", "crop/fert/pest", "operation")}
        events = []
        for line_number, line in enumerate(lines[header_index + 2:], header_index + 3):
            values = line.split()
            if len(values) <= max(positions.values()):
                continue
            try:
                hru_id = int(values[positions["hru"]])
                year = int(values[positions["year"]])
                month = int(values[positions["mon"]])
                day = int(values[positions["day"]])
                event_date = date(year, month, day)
            except (ValueError, IndexError):
                raise ValueError(f"Invalid management event in {path.name}:{line_number}") from None
            events.append({
                "date": event_date.isoformat(),
                "hru_id": hru_id,
                "crop": values[positions["crop/fert/pest"]],
                "operation": values[positions["operation"]],
            })
        if len({(event["hru_id"], event["date"], event["operation"], event["crop"])
                for event in events}) != len(events):
            raise ValueError(f"{path.name} contains duplicate management events")
        return events

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
        if start_date and end_date:
            expected = _expected_periods(start_date, end_date, frequency)
            actual = {date.fromisoformat(period) for period in periods}
            missing = expected - actual
            if missing:
                warnings.append({"code": "MISSING_PERIODS", "message": f"SWAT+ output is missing {len(missing)} requested {frequency.lower()} periods"})
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
        water_balance_fields = {"precip_mm", "runoff_mm", "runoff_contribution_mm", "evapotranspiration_mm",
                                "plant_evapotranspiration_mm", "soil_evaporation_mm", "canopy_evaporation_mm",
                                "potential_evapotranspiration_mm", "soil_water_mm", "soil_water_initial_mm",
                                "soil_water_average_mm", "percolation_mm",
                                "tile_drainage_mm", "lateral_flow_mm", "water_yield_mm"}
        water_balance_rows = self._select_outlet(
            [row for path in wb_files for row in self._read(path, water_balance_fields)], "basin water-balance",
        )
        channel_fields = {
            "streamflow_m3s", "channel_area_ha", "channel_precip_volume_m3",
            "channel_evap_volume_m3", "channel_seep_volume_m3", "channel_water_storage_m3",
            "channel_inflow_m3s", "channel_water_temp_c",
        }
        all_channel_rows = [row for path in channel_files for row in self._read(path, channel_fields)]
        from app.services.swat_water_path import normalize_bypass_channels
        all_channel_rows, flow_normalization = normalize_bypass_channels(run_directory, all_channel_rows, self.output_frequency)
        if flow_normalization.get("normalized_channel_rows", 0):
            self._parse_warnings.append({"code": "BYPASS_CHANNEL_FLOW_NORMALIZED",
                "message": "Audited SWAT+ 61.0.2.61 bypass-channel print bug: flow normalized from native incoming hydrograph volumes; reported values retained."})
        elif flow_normalization.get("status") == "AFFECTED_UNAVAILABLE":
            self._parse_warnings.append({"code": "BYPASS_CHANNEL_FLOW_UNAVAILABLE",
                "message": flow_normalization["reason"]})
        channel_rows = self._select_outlet(all_channel_rows, "channel")
        for kind, rows in (("basin water-balance", water_balance_rows), ("outlet channel", channel_rows)):
            periods = [row["period"] for row in rows]
            if len(periods) != len(set(periods)):
                raise ValueError(f"Duplicate {kind} output period")
        records = self._merge(water_balance_rows, channel_rows)
        period_start = start_date.replace(day=1) if start_date and self.output_frequency == "MONTHLY" else start_date.replace(month=1, day=1) if start_date and self.output_frequency == "ANNUAL" else start_date
        period_end = end_date.replace(day=1) if end_date and self.output_frequency == "MONTHLY" else end_date.replace(month=1, day=1) if end_date and self.output_frequency == "ANNUAL" else end_date
        if period_start and period_end:
            records = [row for row in records if period_start.isoformat() <= row["period"] <= period_end.isoformat()]
        if not records:
            raise ValueError("Recognized SWAT+ files had no dated output records")
        hru_results = [row for path in hru_files for row in self._read(path, water_balance_fields)]
        hru_keys = [(row["period"], row.get("_unit"), row.get("_gis_id")) for row in hru_results]
        if len(hru_keys) != len(set(hru_keys)):
            raise ValueError("Duplicate HRU output period and identifier")
        if period_start and period_end:
            hru_results = [row for row in hru_results if period_start.isoformat() <= row["period"] <= period_end.isoformat()]
        plant_files = self._files(run_directory, ("output_hru", "hru_pw"))
        plant_results = [row for path in plant_files for row in self._read(path, {
            "lai_m2_m2", "biomass_kg_ha", "yield_kg_ha", "water_stress_factor",
            "aeration_stress_factor", "temperature_stress_factor", "nitrogen_stress_factor",
            "phosphorus_stress_factor", "salinity_stress_factor", "plant_heat_unit_fraction",
            "biomass_growth_kg_ha",
        })]
        plant_keys = [(row["period"], row.get("_unit"), row.get("_gis_id")) for row in plant_results]
        if len(plant_keys) != len(set(plant_keys)):
            raise ValueError("Duplicate daily plant output period and HRU identifier")
        if period_start and period_end:
            plant_results = [row for row in plant_results if period_start.isoformat() <= row["period"] <= period_end.isoformat()]
        channel_keys = [(row["period"], row.get("_unit"), row.get("_gis_id")) for row in all_channel_rows]
        if len(channel_keys) != len(set(channel_keys)):
            raise ValueError("Duplicate channel output period and identifier")
        if period_start and period_end:
            all_channel_rows = [row for row in all_channel_rows if period_start.isoformat() <= row["period"] <= period_end.isoformat()]
        event_path = run_directory / "mgt_out.txt"
        management_events = self._event_rows(event_path) if event_path.is_file() else []
        if start_date and end_date:
            management_events = [row for row in management_events if start_date.isoformat() <= row["date"] <= end_date.isoformat()]
        warnings = self._validate(records, start_date, end_date, self.output_frequency)
        warnings.extend({"code": warning["code"], "message": warning["message"]} for warning in self._parse_warnings if warning not in warnings)
        requested_periods = (
            _expected_periods(start_date, end_date, self.output_frequency)
            if start_date and end_date else None
        )
        expected_period_count = len(requested_periods) if requested_periods is not None else len(records)
        period_coverage = {
            variable: {
                "available_periods": sum(row.get(variable) is not None for row in records),
                "expected_periods": expected_period_count,
                "complete": expected_period_count > 0
                and len(records) == expected_period_count
                and all(row.get(variable) is not None for row in records),
            }
            for variable in _WATER_BALANCE_VARIABLES
        }
        availability = {
            variable: "AVAILABLE" if coverage["complete"] else
            "PARTIAL" if coverage["available_periods"] else "NOT_AVAILABLE"
            for variable, coverage in period_coverage.items()
        }
        balance_terms = ("precip_mm", "runoff_mm", "evapotranspiration_mm", "percolation_mm")
        complete = all(period_coverage[name]["complete"] for name in balance_terms)
        water_balance = {
            "channel_flow_normalization": flow_normalization,
            # This is a coverage check for reported terms, not a physical
            # closure calculation. No residual or balance error is inferred.
            "status": "TERMS_COMPLETE" if complete else "INCOMPLETE",
            "variable_availability": availability,
            "period_coverage": period_coverage,
            "expected_output_period_count": expected_period_count,
            "warnings": warnings,
            "totals_mm": {
                name: sum(row[name] for row in records) if period_coverage[name]["complete"] else None
                for name in balance_terms
            },
            "mean_streamflow_m3s": (
                sum(row["streamflow_m3s"] for row in records) / expected_period_count
                if period_coverage["streamflow_m3s"]["complete"] else None
            ),
            "reason": None if complete else "One or more required terms are missing for at least one output period; incomplete totals are null",
        }
        # ``_unit``/``_gis_id`` are parser selectors, not public scientific
        # variables.  Keep them long enough to select the configured outlet,
        # then remove them from the normalized API records.
        records = [{key: value for key, value in row.items() if key not in {"_unit", "_gis_id"}} for row in records]
        identifier_fields = {"_unit": "hru_unit", "_gis_id": "hru_gis_id", "_name": "hru_name"}
        hru_results = [{identifier_fields.get(key, key): value for key, value in row.items() if key != "_gis_id"} for row in hru_results]
        plant_results = [{identifier_fields.get(key, key): value for key, value in row.items() if key != "_gis_id"} for row in plant_results]
        channel_results = [{"channel_unit" if key == "_unit" else "channel_gis_id" if key == "_gis_id" else "channel_name" if key == "_name" else key: value
                            for key, value in row.items()} for row in all_channel_rows]
        source_files = wb_files + channel_files + hru_files + plant_files + ([event_path] if event_path.is_file() else [])
        source_files += [run_directory / name for name in ("hydin_day.txt", "hydout_day.txt", "ru_day.txt", "aquifer_day.txt")
                         if (run_directory / name).is_file()]
        return SwatParsedOutput(records=records, hru_results=hru_results, water_balance=water_balance,
                                plant_results=plant_results, channel_results=channel_results,
                                management_events=management_events,
                                output_files=[str(path.relative_to(run_directory)) for path in source_files], source_files=source_files)


def _expected_periods(start: date, end: date, frequency: str) -> set[date]:
    """Return requested output timestamps without changing their native frequency."""
    if end < start:
        return set()
    if frequency == "DAILY":
        return {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
    if frequency == "MONTHLY":
        cursor = start.replace(day=1)
        last = end.replace(day=1)
        periods: set[date] = set()
        while cursor <= last:
            periods.add(cursor)
            cursor = cursor.replace(year=cursor.year + (cursor.month == 12), month=1 if cursor.month == 12 else cursor.month + 1)
        return periods
    if frequency == "ANNUAL":
        return {date(year, 1, 1) for year in range(start.year, end.year + 1)}
    raise ValueError(f"Unsupported SWAT+ output frequency: {frequency}")

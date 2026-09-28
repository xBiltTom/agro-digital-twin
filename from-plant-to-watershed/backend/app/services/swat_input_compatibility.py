"""SWAT+ 61.0.2.61 list-directed integer input compatibility.

SWAT+ reads several text tables directly into Fortran derived types.  The
61.0.2.61 plant table declares ``days_mat`` and ``mat_yrs`` as INTEGER even
though some editor-generated projects serialize integral values as decimals.
This module repairs only that textual representation, and only inside a
copied run workspace.  Numeric values are never rounded or otherwise changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SWAT_SOURCE_VERSION = "61.0.2.61"
SWAT_SOURCE_URLS = {
    "plant_types": "https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_data_module.f90",
    "plant_reader": "https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_parm_read.f90",
    "plant_community_reader": "https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/readpcom.f90",
    "management_reader": "https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/mgt_read_mgtops.f90",
    "management_operation_reader": "https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/read_mgtops.f90",
    "plant_ini_types": "https://docs.swat.tamu.edu/input-reference/ini/",
    "plant_table_reference": "https://docs.swat.tamu.edu/input-reference/plt/",
}

_INTEGER_COLUMN_FIELDS = {
    "plants.plt": ("days_mat", "yrs_mat"),
}
_INTEGER_CONTROL_FIELDS = {
    "time.sim": (2, 5),
    "print.prt": (2, 6),
}
_INTEGER_TOKEN = re.compile(r"^[+-]?\d+$")


class SwatInputCompatibilityError(ValueError):
    """A relevant SWAT+ input cannot be safely repaired without changing data."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


@dataclass(frozen=True)
class _FieldLocation:
    file_name: str
    line_index: int
    token_index: int
    field_name: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tokens(raw: str) -> list[re.Match[str]]:
    return list(re.finditer(r"\S+", raw))


class SwatInputCompatibility:
    """Inspect, normalize and log exact-integer textual representations."""

    @classmethod
    def inspect(cls, input_directory: Path) -> dict[str, Any]:
        return cls._build_plan(input_directory)

    @classmethod
    def normalize_copy(cls, input_directory: Path) -> dict[str, Any]:
        """Normalize a run copy, failing on non-integral or malformed values."""
        plan = cls._build_plan(input_directory)
        changes_by_file: dict[str, list[dict[str, Any]]] = {}
        file_hashes_before: dict[str, str] = {}
        lines_by_file: dict[str, list[str]] = {}
        for location, before, after in plan["corrections"]:
            path = input_directory / location.file_name
            if location.file_name not in lines_by_file:
                lines_by_file[location.file_name] = path.read_text(encoding="utf-8", errors="strict").splitlines()
                file_hashes_before[location.file_name] = _sha256(path)
            raw = lines_by_file[location.file_name][location.line_index]
            spans = _tokens(raw)
            token = spans[location.token_index]
            lines_by_file[location.file_name][location.line_index] = (
                raw[:token.start()] + after + raw[token.end():]
            )
            changes_by_file.setdefault(location.file_name, []).append({
                "line": location.line_index + 1,
                "field": location.field_name,
                "before": before,
                "after": after,
                "numeric_value_preserved": True,
                "scientific_parameter_change": False,
            })
        file_hashes_after: dict[str, str] = {}
        for file_name, lines in lines_by_file.items():
            path = input_directory / file_name
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            file_hashes_after[file_name] = _sha256(path)
        # Re-parse the effective copied inputs. This also catches a write that
        # failed to leave all integer fields in a form accepted by list input.
        verified = cls._build_plan(input_directory)
        if verified["corrections"]:
            raise SwatInputCompatibilityError(
                "SWAT+ integer input normalization left incompatible values",
                details={"remaining_fields": [
                    {"file": loc.file_name, "line": loc.line_index + 1, "field": loc.field_name, "value": before}
                    for loc, before, _ in verified["corrections"]
                ]},
            )
        log = {
            "status": "VALIDATED_WITH_FORMAT_NORMALIZATION" if changes_by_file else "VALIDATED_NO_CHANGES",
            "swat_source_version": SWAT_SOURCE_VERSION,
            "source_references": SWAT_SOURCE_URLS,
            "scope": "copied_run_workspace_only",
            "numeric_values_changed": False,
            "scientific_parameters_changed_by_compatibility_layer": False,
            "corrections_by_file": changes_by_file,
            "sha256_before": file_hashes_before,
            "sha256_after": file_hashes_after,
            "integer_fields_validated": plan["validated_fields"],
            "files_validated": plan["files_validated"],
        }
        log_path = input_directory / "swat_input_compatibility.json"
        log_path.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log["log_file"] = str(log_path)
        log["log_sha256"] = _sha256(log_path)
        return log

    @classmethod
    def _build_plan(cls, input_directory: Path) -> dict[str, Any]:
        locations: list[_FieldLocation] = []
        validated_fields: dict[str, list[str]] = {}
        files_validated: list[str] = []
        for file_name, fields in _INTEGER_COLUMN_FIELDS.items():
            path = input_directory / file_name
            if not path.is_file():
                continue
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
            if len(lines) < 3:
                raise SwatInputCompatibilityError(f"{file_name} is missing its title, header or data")
            header = [match.group().lower() for match in _tokens(lines[1])]
            wanted_positions = {field: header.index(field) for field in fields if field in header}
            if file_name == "plants.plt" and not {"days_mat", "yrs_mat"}.issubset(wanted_positions):
                raise SwatInputCompatibilityError(
                    "plants.plt does not expose the SWAT+ 61.0.2.61 integer plant fields",
                    details={"header_fields": header, "required_fields": ["days_mat", "yrs_mat"]},
                )
            validated_fields[file_name] = []
            data_count = 0
            for line_index, raw in enumerate(lines[2:], 2):
                spans = _tokens(raw)
                if not spans:
                    continue
                values = [match.group() for match in spans]
                # Plant records have one trailing editor description column;
                # all scientific/type fields before it retain header order.
                if file_name == "plants.plt" and len(values) != len(header):
                    raise SwatInputCompatibilityError(
                        "plants.plt record length differs from its header",
                        details={"line": line_index + 1, "expected_columns": len(header), "actual_columns": len(values)},
                    )
                if file_name == "management.sch" and len(values) != 3:
                    # Operation payload rows do not carry the two schedule
                    # counts and can have a different documented shape.
                    continue
                if file_name == "plant.ini" and len(values) != 3:
                    # Nested plant initial-state rows contain real values; the
                    # community count fields occur on the three-column rows.
                    continue
                data_count += 1
                for field, token_index in wanted_positions.items():
                    if token_index >= len(values):
                        raise SwatInputCompatibilityError(
                            f"{file_name} is missing integer field {field}",
                            details={"line": line_index + 1, "field": field},
                        )
                    validated_fields[file_name].append(field)
                    locations.append(_FieldLocation(file_name, line_index, token_index, field))
            if not data_count:
                raise SwatInputCompatibilityError(f"{file_name} contains no records")
            files_validated.append(file_name)

        plant_ini = input_directory / "plant.ini"
        if plant_ini.is_file():
            lines = plant_ini.read_text(encoding="utf-8", errors="strict").splitlines()
            if len(lines) < 3:
                raise SwatInputCompatibilityError("plant.ini is missing its title, header or community rows")
            header = [match.group().lower() for match in _tokens(lines[1])]
            # The editor writes plt_cnt; SWAT+ 61.0.2.61 reads this column into
            # plant_community_db%plants_com (INTEGER) in readpcom.f90.
            if not {"plt_cnt", "rot_yr_ini"}.issubset(header):
                raise SwatInputCompatibilityError(
                    "plant.ini does not expose its plant count and rotation-year fields",
                    details={"header_fields": header, "required_fields": ["plt_cnt", "rot_yr_ini"]},
                )
            count_index, rotation_index = header.index("plt_cnt"), header.index("rot_yr_ini")
            validated_fields["plant.ini"] = ["plt_cnt", "rot_yr_ini"]
            cursor = 2
            communities = 0
            while cursor < len(lines):
                values = [match.group() for match in _tokens(lines[cursor])]
                if not values:
                    cursor += 1
                    continue
                if max(count_index, rotation_index) >= len(values):
                    raise SwatInputCompatibilityError(
                        "plant.ini community row does not contain its integer fields",
                        details={"line": cursor + 1},
                    )
                locations.extend((
                    _FieldLocation("plant.ini", cursor, count_index, "plt_cnt"),
                    _FieldLocation("plant.ini", cursor, rotation_index, "rot_yr_ini"),
                ))
                raw_count = values[count_index]
                try:
                    plant_count = Decimal(raw_count)
                except InvalidOperation:
                    plant_count = Decimal("NaN")
                if not plant_count.is_finite() or plant_count != plant_count.to_integral_value() or plant_count < 0:
                    raise SwatInputCompatibilityError(
                        "plant.ini plant count is malformed, negative or non-integral",
                        details={"line": cursor + 1, "field": "plt_cnt", "value": raw_count},
                    )
                communities += 1
                cursor += 1
                cursor += int(plant_count)
            if not communities:
                raise SwatInputCompatibilityError("plant.ini contains no plant communities")
            files_validated.append("plant.ini")

        management = input_directory / "management.sch"
        if management.is_file():
            lines = management.read_text(encoding="utf-8", errors="strict").splitlines()
            if len(lines) < 3:
                raise SwatInputCompatibilityError("management.sch is missing its title, header or schedules")
            header = [match.group().lower() for match in _tokens(lines[1])]
            aliases = {"numb_ops": ("numb_ops", "num_ops"), "numb_auto": ("numb_auto", "num_autos")}
            count_indices = {}
            for field, candidates in aliases.items():
                position = next((header.index(candidate) for candidate in candidates if candidate in header), None)
                if position is None:
                    raise SwatInputCompatibilityError(
                        "management.sch does not expose schedule count fields",
                        details={"header_fields": header, "required_fields": list(aliases)},
                    )
                count_indices[field] = position
            if not {"mon", "day"}.issubset(header):
                raise SwatInputCompatibilityError(
                    "management.sch does not expose integer operation month/day fields",
                    details={"header_fields": header},
                )
            validated_fields["management.sch"] = ["numb_ops", "numb_auto", "mon", "day"]
            cursor = 2
            schedules = 0
            while cursor < len(lines):
                values = [match.group() for match in _tokens(lines[cursor])]
                if not values:
                    cursor += 1
                    continue
                max_index = max(count_indices.values())
                if max_index >= len(values):
                    raise SwatInputCompatibilityError(
                        "management.sch schedule row is missing integer count fields",
                        details={"line": cursor + 1},
                    )
                for field, position in count_indices.items():
                    locations.append(_FieldLocation("management.sch", cursor, position, field))
                try:
                    op_count = Decimal(values[count_indices["numb_ops"]])
                    auto_count = Decimal(values[count_indices["numb_auto"]])
                except InvalidOperation:
                    op_count, auto_count = Decimal("NaN"), Decimal("NaN")
                counts = (op_count, auto_count)
                if any(not count.is_finite() or count != count.to_integral_value() or count < 0 for count in counts):
                    raise SwatInputCompatibilityError(
                        "management.sch operation counts are malformed, negative or non-integral",
                        details={"line": cursor + 1, "numb_ops": values[count_indices["numb_ops"]],
                                 "numb_auto": values[count_indices["numb_auto"]]},
                    )
                op_rows, auto_rows = int(op_count), int(auto_count)
                schedules += 1
                cursor += 1
                cursor += auto_rows
                # Operation records omit the blank name/count cells from the
                # header, so ``op_typ mon day ...`` are tokens 0, 1 and 2.
                mon_index, day_index = 1, 2
                for _ in range(op_rows):
                    if cursor >= len(lines):
                        raise SwatInputCompatibilityError(
                            "management.sch declares more scheduled operations than it contains",
                            details={"schedule_line": cursor - auto_rows - 1},
                        )
                    op_values = [match.group() for match in _tokens(lines[cursor])]
                    if max(mon_index, day_index) >= len(op_values):
                        raise SwatInputCompatibilityError(
                            "management.sch operation row is missing month/day fields",
                            details={"line": cursor + 1},
                        )
                    locations.extend((
                        _FieldLocation("management.sch", cursor, mon_index, "mon"),
                        _FieldLocation("management.sch", cursor, day_index, "day"),
                    ))
                    cursor += 1
            if not schedules:
                raise SwatInputCompatibilityError("management.sch contains no schedules")
            files_validated.append("management.sch")

        for file_name, (line_index, expected_count) in _INTEGER_CONTROL_FIELDS.items():
            path = input_directory / file_name
            if not path.is_file():
                continue
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
            if len(lines) <= line_index:
                raise SwatInputCompatibilityError(f"{file_name} is missing its integer control record")
            spans = _tokens(lines[line_index])
            if len(spans) != expected_count:
                raise SwatInputCompatibilityError(
                    f"{file_name} integer control record has an unexpected field count",
                    details={"line": line_index + 1, "expected_fields": expected_count, "actual_fields": len(spans)},
                )
            for token_index in range(expected_count):
                locations.append(_FieldLocation(file_name, line_index, token_index, f"control_{token_index + 1}"))
            validated_fields[file_name] = [f"control_{index + 1}" for index in range(expected_count)]
            files_validated.append(file_name)

        corrections: list[tuple[_FieldLocation, str, str]] = []
        for location in locations:
            path = input_directory / location.file_name
            raw = path.read_text(encoding="utf-8", errors="strict").splitlines()[location.line_index]
            spans = _tokens(raw)
            before = spans[location.token_index].group()
            if _INTEGER_TOKEN.fullmatch(before):
                continue
            try:
                value = Decimal(before)
            except InvalidOperation:
                value = Decimal("NaN")
            if not value.is_finite() or value != value.to_integral_value():
                raise SwatInputCompatibilityError(
                    "A SWAT+ integer field is malformed or non-integral; no scientific value was changed",
                    details={"file": location.file_name, "line": location.line_index + 1,
                             "field": location.field_name, "value": before},
                )
            corrections.append((location, before, str(int(value))))
        return {
            "files_validated": sorted(set(files_validated)),
            "validated_fields": {name: sorted(set(fields)) for name, fields in validated_fields.items()},
            "corrections": corrections,
            "correction_count": len(corrections),
            "source_version": SWAT_SOURCE_VERSION,
        }

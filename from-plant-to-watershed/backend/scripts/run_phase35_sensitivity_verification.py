"""Run isolated SWAT+ plant sensitivity diagnostics for the phase 3.4 pair.

All new runs are local diagnostic probes tagged ``SENSITIVITY_DIAGNOSTIC_ONLY``.
The script reads the phase 3.4 bundle and report, creates fresh workspaces, and
never connects to PostgreSQL or edits the verified phase 3.4 artifacts.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from app.services.swat_plus_adapter import SwatPlusAdapter, swat_run_config_from_request


DEFAULT_BUNDLE = BACKEND_ROOT / "data" / "phase34-cdl-2019"
DEFAULT_REPORT = BACKEND_ROOT / "data" / "phase34-verification" / "phase34-real-engine-report.json"
DEFAULT_OUTPUT = BACKEND_ROOT / "data" / "phase35-sensitivity-verification-v3"
DIAGNOSTIC_TAG = "SENSITIVITY_DIAGNOSTIC_ONLY"
EXPERIMENT_CLASSIFICATION = "EXPERIMENTAL_CDL_CORN_MAJORITY_MANAGEMENT_NOT_HISTORICAL_RECONSTRUCTION"
REQUIRED_PROJECT_INPUTS = (
    "hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl",
    "plants.plt", "file.cio", "time.sim", "print.prt", "weather-sta.cli",
)
INSTRUMENTED_CONTROL_FILES = {"time.sim", "print.prt", "file.cio"}
OUTPUT_FILES_TO_COMPARE = (
    "hru_pw_day.txt", "basin_wb_day.txt", "hru_wb_day.txt", "channel_sd_day.txt",
    "crop_yld_aa.txt", "crop_yld_yr.txt", "basin_crop_yld_aa.txt", "basin_crop_yld_yr.txt",
)
DIAGNOSTIC_VALUES = {
    "lai_pot": 10.0,
    "frac_hu1": 0.05,
    "lai_max1": 0.90,
    "frac_hu2": 0.75,
    "lai_max2": 0.20,
    "hu_lai_decl": 0.98,
    "can_ht_max": 20.0,
    "rt_dp_max": 0.10,
    "ext_co": 1.80,
    "bm_e": 90.0,
}
PARAMETER_OUTPUTS = {
    "lai_pot": ["hru_pw_day.lai", "hru_pw_day.bioms"],
    "frac_hu1": ["hru_pw_day.lai", "hru_pw_day.lai_max", "hru_pw_day.phubas0"],
    "lai_max1": ["hru_pw_day.lai", "hru_pw_day.lai_max"],
    "frac_hu2": ["hru_pw_day.lai", "hru_pw_day.lai_max", "hru_pw_day.phubas0"],
    "lai_max2": ["hru_pw_day.lai", "hru_pw_day.lai_max"],
    "hu_lai_decl": ["hru_pw_day.lai", "hru_pw_day.lai_max", "hru_pw_day.bm_grow"],
    # SWAT+ hru_pw reports LAI, biomass, stress and PHU, but not direct height
    # or root depth. ET/percolation are indirect probes, not those states.
    "can_ht_max": ["hru_wb_day.eplant"],
    "rt_dp_max": ["hru_wb_day.eplant", "hru_wb_day.perc"],
    "ext_co": ["hru_pw_day.lai", "hru_pw_day.bioms", "hru_wb_day.eplant"],
    "bm_e": ["hru_pw_day.bioms", "hru_pw_day.bm_grow", "crop_yld_aa.MASS"],
}

SWAT_PARAMETER_PATHS = {
    "lai_pot": {"internal_field": "blai", "source_path": ["plant_init.f90", "pl_leaf_gro.f90"]},
    "frac_hu1": {"internal_field": "frgrw1", "source_path": ["plantparm_init.f90"]},
    "lai_max1": {"internal_field": "laimx1", "source_path": ["plantparm_init.f90"]},
    "frac_hu2": {"internal_field": "frgrw2", "source_path": ["plantparm_init.f90"]},
    "lai_max2": {"internal_field": "laimx2", "source_path": ["plantparm_init.f90"]},
    "hu_lai_decl": {"internal_field": "dlai", "source_path": ["pl_leaf_gro.f90"]},
    "can_ht_max": {"internal_field": "chtmx", "source_path": ["plant_init.f90", "pl_leaf_gro.f90", "pl_community.f90"]},
    "rt_dp_max": {"internal_field": "rdmx", "source_path": ["mgt_plantop.f90", "pl_root_gro.f90"]},
    "ext_co": {"internal_field": "ext_coef", "source_path": ["pl_community.f90"]},
    "bm_e": {"internal_field": "bio_e", "source_path": ["plantparm_init.f90", "pl_biomass_gro.f90"]},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _read_corn_record(path: Path) -> tuple[list[str], list[str], int]:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) < 3:
        raise ValueError("plants.plt does not contain a header and crop record")
    header = lines[1].split()
    for index, line in enumerate(lines[2:], 2):
        values = line.split()
        if values and values[0] == "corn":
            if len(values) != len(header):
                raise ValueError("corn record in plants.plt does not match the table header")
            return lines, values, index
    raise ValueError("plants.plt has no corn record")


def _plant_values(path: Path) -> dict[str, float]:
    _, values, _ = _read_corn_record(path)
    header = path.read_text(encoding="utf-8", errors="strict").splitlines()[1].split()
    return {name: float(values[header.index(name)]) for name in SwatPlantParameterMapper.PARAMETER_SPECS}


def _changed_plant_columns(left: Path, right: Path) -> list[str]:
    left_lines, left_values, _ = _read_corn_record(left)
    right_lines, right_values, _ = _read_corn_record(right)
    header = left_lines[1].split()
    if right_lines[1].split() != header:
        raise ValueError("plants.plt header changed between diagnostic arms")
    return [name for name, before, after in zip(header, left_values, right_values, strict=True) if before != after]


def _set_plant_values(path: Path, updates: dict[str, float]) -> str:
    lines, values, index = _read_corn_record(path)
    header = lines[1].split()
    for name, value in updates.items():
        if name not in SwatPlantParameterMapper.PARAMETER_SPECS:
            raise ValueError(f"Unsupported diagnostic parameter {name!r}")
        _, _, low, high, _ = SwatPlantParameterMapper.PARAMETER_SPECS[name]
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{name}={value} is outside the mapper's documented [{low}, {high}] range")
        values[header.index(name)] = f"{value:.6f}"
    current = {name: float(values[header.index(name)]) for name in SwatPlantParameterMapper.PARAMETER_SPECS}
    if not current["frac_hu1"] < current["frac_hu2"] < current["hu_lai_decl"]:
        raise ValueError("Diagnostic LAI fractions must satisfy frac_hu1 < frac_hu2 < hu_lai_decl")
    if not current["lai_max1"] < current["lai_max2"]:
        raise ValueError("Diagnostic LAI curve must satisfy lai_max1 < lai_max2")
    lines[index] = "  ".join(values)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _sha256(path)


def _replace_print_row(lines: list[str], label: str, flags: list[str]) -> None:
    for index, line in enumerate(lines):
        tokens = line.split()
        if len(tokens) >= 5 and tokens[0] == label:
            lines[index] = f"{label:<24}{flags[0]:>8}{flags[1]:>14}{flags[2]:>14}{flags[3]:>14}"
            return
    lines.append(f"{label:<24}{flags[0]:>8}{flags[1]:>14}{flags[2]:>14}{flags[3]:>14}")


def _instrument_outputs(workspace: Path) -> dict[str, Any]:
    print_path = workspace / "print.prt"
    lines = print_path.read_text(encoding="utf-8", errors="strict").splitlines()
    mgt_header = next((i for i, line in enumerate(lines) if line.split() == ["crop_yld", "mgtout", "hydcon", "fdcout"]), None)
    if mgt_header is None or mgt_header + 1 >= len(lines):
        raise ValueError("print.prt does not expose the crop_yld/mgtout controls")
    flags = lines[mgt_header + 1].split()
    if len(flags) != 4:
        raise ValueError("print.prt management output flags are malformed")
    flags[1] = "y"
    lines[mgt_header + 1] = " ".join(flags)
    _replace_print_row(lines, "hru_pw", ["y", "n", "n", "n"])
    print_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "diagnostic_tag": DIAGNOSTIC_TAG,
        "print_prt_sha256": _sha256(print_path),
        "daily_outputs_enabled": ["hru_pw", "basin_wb", "hru_wb", "channel_sd"],
        "management_output_enabled": True,
        "plant_height_and_root_depth_direct_outputs": "NOT_AVAILABLE_IN_SWAT_PLUS_HRU_PLANT_WEATHER_OUTPUT",
    }


def _normalized_token(token: str) -> float | str:
    try:
        value = float(token.replace("D", "E").replace("d", "e"))
        return 0.0 if value == 0.0 else value
    except ValueError:
        return token


def _normalized_output(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 3:
        return {"status": "TOO_SHORT", "normalized_rows": []}
    if path.name.startswith("crop_yld_"):
        if len(lines) < 4:
            return {"status": "TOO_SHORT", "normalized_rows": []}
        header, units, row_start = lines[2].split(), lines[3].split(), 4
    else:
        header, units, row_start = lines[1].split(), lines[2].split(), 3
    rows = [[_normalized_token(token) for token in line.split()] for line in lines[row_start:] if line.split()]
    return {
        "status": "AVAILABLE", "sha256": _sha256(path), "header": header,
        "units": units, "normalized_rows": rows, "data_line_start": row_start,
    }


def _disambiguate_headers(headers: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    output = []
    for name in headers:
        counts[name] = counts.get(name, 0) + 1
        output.append(name if counts[name] == 1 else f"{name}#{counts[name]}")
    return output


def _numeric_table(path: Path) -> dict[str, Any]:
    normalized = _normalized_output(path)
    headers = normalized.get("header", [])
    rows = normalized.get("normalized_rows", [])
    if normalized.get("status") != "AVAILABLE":
        return {"status": normalized.get("status"), "columns": {}, "row_count": 0}
    widths = {len(row) for row in rows}
    if len(widths) > 1:
        return {"status": "ROW_WIDTH_MISMATCH", "columns": {}, "row_count": len(rows), "headers": headers}
    if widths and next(iter(widths)) < len(headers):
        width = next(iter(widths))
        # Basin water-balance rows omit the two HRU-only trailing labels.
        if headers[width:] != ["plant_cov", "mgt_ops"]:
            return {"status": "ROW_WIDTH_MISMATCH", "columns": {}, "row_count": len(rows), "headers": headers}
        headers = headers[:width]
    elif widths and next(iter(widths)) > len(headers):
        return {"status": "ROW_WIDTH_MISMATCH", "columns": {}, "row_count": len(rows), "headers": headers}
    keyed_headers = _disambiguate_headers(headers)
    key_names = {"jday", "mon", "day", "yr", "unit", "gis_id", "name", "PLANTNM"}
    key_columns = [name for name in keyed_headers if name in key_names]
    columns: dict[str, dict[tuple[str, ...], float]] = {}
    for row in rows:
        raw = dict(zip(keyed_headers, row, strict=True))
        key = tuple(str(raw[name]) for name in key_columns)
        for name, value in raw.items():
            if name in key_columns or isinstance(value, str):
                continue
            columns.setdefault(name, {})[key] = float(value)
    return {
        "status": "AVAILABLE", "columns": columns, "row_count": len(rows),
        "headers": headers, "key_columns": key_columns,
    }


def _key_date(key: tuple[str, ...], key_columns: list[str]) -> str | None:
    parts = dict(zip(key_columns, key, strict=True))
    try:
        year, jday = int(float(parts["yr"])), int(float(parts["jday"]))
        return (date(year, 1, 1) + timedelta(days=jday - 1)).isoformat()
    except (KeyError, ValueError, OverflowError):
        return None


def _selected_hru_columns(table: dict[str, Any], selected_hru_ids: list[int] | None) -> dict[str, dict[tuple[str, ...], float]]:
    columns = table.get("columns", {})
    key_columns = table.get("key_columns", [])
    if not selected_hru_ids or "unit" not in key_columns:
        return columns
    unit_index = key_columns.index("unit")
    selected = {str(float(value)) for value in selected_hru_ids}
    return {
        name: {key: value for key, value in values.items() if key[unit_index] in selected}
        for name, values in columns.items()
    }


def _compare_output_tables(
    baseline: Path,
    candidate: Path,
    selected_hru_ids: list[int] | None = None,
) -> dict[str, Any]:
    if not baseline.is_file() or not candidate.is_file():
        return {"status": "OUTPUT_NOT_OBSERVABLE", "baseline_exists": baseline.is_file(), "candidate_exists": candidate.is_file()}
    left_raw, right_raw = _normalized_output(baseline), _normalized_output(candidate)
    left, right = _numeric_table(baseline), _numeric_table(candidate)
    normalized_equal = (
        left_raw.get("header") == right_raw.get("header")
        and left_raw.get("units") == right_raw.get("units")
        and left_raw.get("normalized_rows") == right_raw.get("normalized_rows")
    )
    if left.get("status") != "AVAILABLE" or right.get("status") != "AVAILABLE":
        return {
            "status": "AVAILABLE_UNPARSED", "sha256_baseline": _sha256(baseline),
            "sha256_candidate": _sha256(candidate), "normalized_content_equal": normalized_equal,
            "baseline_parse_status": left.get("status"), "candidate_parse_status": right.get("status"),
            "baseline_row_count": left.get("row_count"), "candidate_row_count": right.get("row_count"),
        }
    left_columns = _selected_hru_columns(left, selected_hru_ids)
    right_columns = _selected_hru_columns(right, selected_hru_ids)
    variable_differences: dict[str, Any] = {}
    for name in sorted(set(left_columns) & set(right_columns)):
        lvalues, rvalues = left_columns[name], right_columns[name]
        common_keys = sorted(set(lvalues) & set(rvalues))
        if not common_keys:
            continue
        changes = sorted(
            ((key, lvalues[key], rvalues[key]) for key in common_keys if lvalues[key] != rvalues[key]),
            key=lambda item: (_key_date(item[0], left["key_columns"]) or "", item[0]),
        )
        absolute = [abs(new - old) for _, old, new in changes]
        relative = [abs(new - old) / abs(old) for _, old, new in changes if old != 0]
        baseline_sum = sum(abs(lvalues[key]) for key in common_keys)
        first_key, first_old, first_new = changes[0] if changes else (None, None, None)
        variable_differences[name] = {
            "changed_records": len(changes),
            "compared_records": len(common_keys),
            "max_absolute_difference": max(absolute, default=0.0),
            "mean_absolute_difference": sum(absolute) / len(absolute) if absolute else 0.0,
            "max_relative_difference": max(relative, default=0.0),
            "relative_l1_difference": sum(absolute) / baseline_sum if baseline_sum else 0.0,
            "first_divergence_date": _key_date(first_key, left["key_columns"]) if first_key else None,
            "first_divergence_values": {"baseline": first_old, "candidate": first_new} if changes else None,
        }
    return {
        "status": "AVAILABLE", "sha256_baseline": _sha256(baseline),
        "sha256_candidate": _sha256(candidate), "normalized_content_equal": normalized_equal,
        "print_precision": _printed_precision(candidate),
        "baseline_row_count": left["row_count"], "candidate_row_count": right["row_count"],
        "numeric_columns_compared": sorted(set(left["columns"]) & set(right["columns"])),
        "comparison_hru_ids": selected_hru_ids if "unit" in left["key_columns"] else None,
        "compared_numeric_records_by_column": {
            name: len(set(left_columns[name]) & set(right_columns.get(name, {})))
            for name in sorted(left_columns)
        },
        "variable_differences": variable_differences,
    }


def _printed_precision(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 4:
        return {}
    if path.name.startswith("crop_yld_"):
        headers, row_start = lines[2].split(), 4
    else:
        headers, row_start = lines[1].split(), 3
    precision = {name: 0 for name in headers}
    for line in lines[row_start:]:
        for name, token in zip(headers, line.split(), strict=False):
            value = token.lower().replace("d", "e")
            if any(char.isdigit() for char in value):
                numeric = value.split("e", maxsplit=1)[0]
                precision[name] = max(precision[name], len(numeric.partition(".")[2]))
    return precision


def _compare_run_outputs(baseline: Path, candidate: Path, selected_hru_ids: list[int] | None = None) -> dict[str, Any]:
    outputs = {
        name: _compare_output_tables(baseline / name, candidate / name, selected_hru_ids)
        for name in OUTPUT_FILES_TO_COMPARE
    }
    plant = {name: row for name, row in outputs.items() if name.startswith("hru_pw") or name.startswith("crop_yld")}
    hydrology = {name: row for name, row in outputs.items() if name.startswith(("basin_wb", "hru_wb", "channel_sd"))}
    changed_plant_variables = sorted({
        f"{filename}.{column}"
        for filename, result in plant.items()
        for column, difference in (result.get("variable_differences") or {}).items()
        if difference.get("changed_records", 0) > 0
    })
    changed_hydrology_variables = sorted({
        f"{filename}.{column}"
        for filename, result in hydrology.items()
        for column, difference in (result.get("variable_differences") or {}).items()
        if difference.get("changed_records", 0) > 0
    })
    return {
        "files": outputs,
        "selected_corn_hru_ids": selected_hru_ids,
        "plant_output_variables_changed": changed_plant_variables,
        "hydrology_output_variables_changed": changed_hydrology_variables,
        "any_normalized_plant_output_change": bool(changed_plant_variables),
        "any_normalized_hydrology_output_change": bool(changed_hydrology_variables),
    }


def _output_inventory(workspace: Path) -> dict[str, Any]:
    path = workspace / "files_out.out"
    if not path.is_file():
        return {"status": "NOT_AVAILABLE", "listed_files": []}
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.split()
        if len(tokens) >= 2 and tokens[0] not in {"files_out.out"}:
            entries.append({"scope": tokens[0], "file": tokens[-1]})
    return {"status": "AVAILABLE", "listed_files": entries}


def _management_evidence(workspace: Path) -> dict[str, Any]:
    candidates = {entry["file"] for entry in _output_inventory(workspace)["listed_files"]}
    candidates.update(path.name for path in workspace.glob("*mgt*out*"))
    candidates.update(path.name for path in workspace.glob("mgt.out"))
    files = []
    for name in sorted(candidates):
        path = workspace / name
        if not path.is_file() or not ("mgt" in name.lower()):
            continue
        matches = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                   if "corn" in line.lower() or "plant" in line.lower() or "harv" in line.lower()]
        events: dict[tuple[str, str], set[str]] = {}
        if name == "mgt_out.txt":
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
                tokens = line.split()
                if len(tokens) < 6 or tokens[4].lower() != "corn":
                    continue
                try:
                    event_date = date(int(tokens[1]), int(tokens[2]), int(tokens[3])).isoformat()
                except ValueError:
                    continue
                events.setdefault((tokens[5].upper(), event_date), set()).add(tokens[0])
        files.append({
            "file": name, "sha256": _sha256(path), "matching_event_line_count": len(matches),
            "event_lines": matches[:40],
            "corn_management_events": [
                {"operation": operation, "date": event_date, "hru_ids": sorted(hrus, key=int), "hru_count": len(hrus)}
                for (operation, event_date), hrus in sorted(events.items(), key=lambda item: (item[0][1], item[0][0]))
            ],
        })
    return {"status": "AVAILABLE" if files else "NOT_AVAILABLE", "files": files}


def _verify_bundle(bundle: Path, report_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = bundle / "manifest.json"
    project = bundle / "project"
    if not manifest_path.is_file() or not project.is_dir() or not report_path.is_file():
        raise FileNotFoundError("Phase 3.4 bundle, project/, manifest.json, and report are required")
    manifest, report = _json(manifest_path), _json(report_path)
    expected_manifest_hash = report.get("variant_manifest_sha256")
    if expected_manifest_hash and _sha256(manifest_path) != expected_manifest_hash:
        raise ValueError("Phase 3.4 variant manifest checksum does not match the recorded report")
    if manifest.get("configuration_status") != "PREPARED_AND_VALIDATED" or manifest.get("cdl_year") != 2019:
        raise ValueError("Only the verified 2019 CDL experimental variant is accepted")
    if manifest.get("classification") != EXPERIMENT_CLASSIFICATION or report.get("classification") != EXPERIMENT_CLASSIFICATION:
        raise ValueError("Phase 3.4 classification is incompatible with this diagnostic harness")
    if report.get("source_project_unchanged") is not True or report.get("variant_input_hashes_unchanged") is not True:
        raise ValueError("Phase 3.4 source or variant immutability was not confirmed")
    checksums = manifest.get("experiment_project_input_checksums_after_sha256") or {}
    if not checksums:
        raise ValueError("Phase 3.4 manifest has no experiment-project input checksums")
    for name, expected in checksums.items():
        path = project / name
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"Phase 3.4 variant input checksum mismatch: {name}")
    for name in REQUIRED_PROJECT_INPUTS:
        if not (project / name).is_file():
            raise FileNotFoundError(f"Phase 3.4 variant is missing required input {name}")

    if report.get("experiment_id") != "phase34-south-fork-cdl-2019-verification":
        raise ValueError("Phase 3.4 report experiment_id is incompatible")
    for role in ("baseline", "coupled"):
        item = report.get(role) or {}
        run_id = item.get("simulation_id")
        if not run_id or item.get("exit_code") != 0 or item.get("run_type") not in {
            "SWAT_STANDARD_BASELINE", "SWAT_MULTISCALE_COUPLED",
        }:
            raise ValueError(f"Phase 3.4 {role} execution record is incomplete")
        workspace = report_path.parent / "swat-runs" / run_id
        if not workspace.is_dir() or not (workspace / "success.fin").is_file():
            raise FileNotFoundError(f"Phase 3.4 {role} workspace is unavailable or incomplete")
        if "Execution successfully completed" not in (workspace / "simulation.out").read_text(encoding="utf-8", errors="replace"):
            raise ValueError(f"Phase 3.4 {role} SWAT+ log does not confirm successful completion")
        for output_name, expected in (item.get("output_checksums") or {}).items():
            output_path = workspace / output_name
            if not output_path.is_file() or _sha256(output_path) != expected:
                raise ValueError(f"Phase 3.4 {role} output checksum mismatch: {output_name}")
    return manifest, report


def _phase34_pair_diagnostics(report_path: Path, manifest: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    start = date.fromisoformat(report["period"]["start"])
    end = date.fromisoformat(report["period"]["end"])
    root = report_path.parent / "swat-runs"
    baseline_id = report["baseline"]["simulation_id"]
    coupled_id = report["coupled"]["simulation_id"]
    baseline, coupled = root / baseline_id, root / coupled_id
    crop_chain = SwatCropChainDiagnostic.input_chain(coupled, manifest["selected_hru_ids"], crop="corn")
    if crop_chain.get("status") != "PASS":
        raise ValueError("Phase 3.4 coupled workspace no longer confirms the corn input chain")
    outputs = _compare_run_outputs(baseline, coupled)
    corn_yield_rows = []
    for line in (coupled / "crop_yld_aa.txt").read_text(encoding="utf-8", errors="replace").splitlines()[3:]:
        tokens = line.split()
        if any(token.lower() == "corn" for token in tokens):
            corn_yield_rows.append(line.strip())
    hru_pw_enabled = any(
        entry["file"] == "hru_pw_day.txt"
        for entry in _output_inventory(coupled)["listed_files"]
    )
    climate, climate_provenance = SwatClimateForcingReader(coupled).for_period(start, end, require_fspm=True)
    return {
        "baseline_run_id": baseline_id,
        "coupled_run_id": coupled_id,
        "baseline_vs_coupled_outputs": outputs,
        "recorded_phase34_hydrology_hashes_equal": report.get("pairing", {}).get("hydrologic_output_checksums_equal"),
        "normalized_numeric_and_text_content_equal_for_available_outputs": all(
            result.get("normalized_content_equal") is True
            for result in outputs["files"].values() if result.get("status") in {"AVAILABLE", "AVAILABLE_UNPARSED"}
        ),
        "corn_yield_aa_record_count": len(corn_yield_rows),
        "corn_yield_aa_sample_rows": corn_yield_rows[:3],
        "corn_hru_ids_in_manifest": manifest["selected_hru_ids"],
        "hru_pw_daily_output_enabled": hru_pw_enabled,
        "hru_pw_daily_output_name_discovered_in_files_out": hru_pw_enabled,
        "baseline_and_coupled_crop_chain": crop_chain,
        "forcing_days": len(climate),
        "forcing_checksums": climate_provenance["file_checksums_sha256"],
    }


def _project_input_hashes(workspace: Path, source_project: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in source_project.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source_project)
        if relative.name.endswith(("_day.txt", "_mon.txt", "_yr.txt", "_aa.txt", ".out", ".fin")) or relative.name.startswith("fort."):
            continue
        candidate = workspace / relative
        if candidate.is_file():
            hashes[relative.as_posix()] = _sha256(candidate)
    for name in ("time.sim", "print.prt", "file.cio"):
        candidate = workspace / name
        if candidate.is_file():
            hashes[name] = _sha256(candidate)
    return hashes


def _normalize_days_mat_integer_tokens(plants: Path) -> dict[str, Any]:
    """Preserve SWAT's integer days_mat values in Fortran list-directed syntax.

    SWAT+ 61.0.2.61 declares ``plant_db%days_mat`` as INTEGER. The phase 3.4
    Editor table serializes it as ``120.00000``. Its reader uses list-directed
    input and ignores positive IOSTAT conversion errors, so every later plant
    parameter can remain at the Fortran default. In copied workspaces only,
    render integral values as integer tokens (120.00000 -> 120); no numeric
    value or scientific setting changes.
    """
    lines = plants.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) < 3:
        raise ValueError("plants.plt is too short for SWAT's parameter reader")
    headers = lines[1].split()
    if "days_mat" not in headers:
        raise ValueError("plants.plt has no days_mat column")
    position = headers.index("days_mat")
    before = _sha256(plants)
    count = 0
    for line_number, line in enumerate(lines[2:], start=3):
        values = line.split()
        if not values:
            continue
        if len(values) != len(headers):
            raise ValueError(f"plants.plt row width mismatch before SWAT parsing at line {line_number}")
        try:
            value = float(values[position])
        except ValueError:
            raise ValueError(f"Invalid days_mat token at plants.plt:{line_number}") from None
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"days_mat={values[position]} is not an integral value at plants.plt:{line_number}")
        integer_token = str(int(value))
        if values[position] != integer_token:
            values[position] = integer_token
            lines[line_number - 1] = "  ".join(values)
            count += 1
    if count:
        plants.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "adapter": "SWAT_PLUS_INTEGER_DAYS_MAT_TOKEN_COMPATIBILITY",
        "internal_type": "plant_db.days_mat: INTEGER (SWAT+ 61.0.2.61)",
        "source_file_type": "decimal text tokens with integral numeric values",
        "rows_normalized": count,
        "numerical_values_changed": False,
        "sha256_before": before,
        "sha256_after": _sha256(plants),
        "applied_to_isolated_workspace_copy_only": True,
    }


def _workspace_mutator(kind: str, baseline_values: dict[str, float], coupled_values: dict[str, float],
                       diagnostic_parameter: str | None = None) -> Any:
    def mutate(workspace: Path) -> dict[str, Any]:
        input_before = {name: _sha256(workspace / name) for name in REQUIRED_PROJECT_INPUTS}
        original_values = _plant_values(workspace / "plants.plt")
        compatibility = _normalize_days_mat_integer_tokens(workspace / "plants.plt")
        instrumentation = _instrument_outputs(workspace)
        updates: dict[str, float] = {}
        if kind == "FSPM_COUPLED":
            updates = coupled_values
        elif diagnostic_parameter:
            updates = {diagnostic_parameter: DIAGNOSTIC_VALUES[diagnostic_parameter]}
        if updates:
            _set_plant_values(workspace / "plants.plt", updates)
        input_after = {name: _sha256(workspace / name) for name in REQUIRED_PROJECT_INPUTS}
        changed = sorted(name for name in input_before if input_before[name] != input_after[name])
        unexpected = [name for name in changed if name not in {"file.cio", "print.prt", "plants.plt"}]
        if unexpected:
            raise RuntimeError(f"Diagnostic preparation changed unexpected inputs: {unexpected}")
        after_values = _plant_values(workspace / "plants.plt")
        changed_parameters = sorted(name for name in original_values if original_values[name] != after_values[name])
        if changed_parameters != sorted(updates):
            raise RuntimeError(f"Scientific plants.plt parameters changed unexpectedly: {changed_parameters}")
        return {
            "diagnostic_tag": DIAGNOSTIC_TAG,
            "run_role": kind,
            "parameter_updates": updates,
            "scientific_inputs_changed": ["plants.plt"] if changed_parameters else [],
            "scientific_parameters_changed": changed_parameters,
            "compatibility_normalization": compatibility,
            "diagnostic_control_inputs_changed": [name for name in changed if name in {"file.cio", "print.prt"}],
            "instrumentation": instrumentation,
            "input_checksums_before_mutator": input_before,
            "input_checksums_after_mutator": input_after,
        }
    return mutate


def _run_one(adapter: SwatPlusAdapter, *, run_id: str, run_type: str, project: Path,
             executable: Path, working_directory: Path, start: date, end: date,
             watershed_code: str, timeout_seconds: int, role: str,
             baseline_values: dict[str, float], coupled_values: dict[str, float],
             diagnostic_parameter: str | None = None) -> dict[str, Any]:
    request = {
        "project_path": str(project), "executable_path": str(executable),
        "working_directory": str(working_directory), "warmup_period": 0,
        "output_frequency": "DAILY", "outlet_unit": "153",
        "timeout_seconds": timeout_seconds, "run_type": run_type,
    }
    config = swat_run_config_from_request(
        request, simulation_start=start, simulation_end=end,
        watershed_id=watershed_code, run_id=run_id,
    )
    result = adapter.run(
        config,
        workspace_mutator=_workspace_mutator(role, baseline_values, coupled_values, diagnostic_parameter),
    )
    workspace = Path(result.workspace)
    if result.exit_code != 0 or not (workspace / "success.fin").is_file():
        raise RuntimeError(f"SWAT+ diagnostic run {run_id} did not complete successfully")
    if "Execution successfully completed" not in (workspace / "simulation.out").read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError(f"SWAT+ diagnostic run {run_id} log has no successful completion marker")
    return {
        "run_id": run_id, "role": role, "diagnostic_tag": DIAGNOSTIC_TAG,
        "workspace": str(workspace), "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "output_checksums": {name: _sha256(workspace / name) for name in OUTPUT_FILES_TO_COMPARE if (workspace / name).is_file()},
        "output_inventory": _output_inventory(workspace),
        "management_event_evidence": _management_evidence(workspace),
        "plant_status_file": {
            "status": "AVAILABLE" if (workspace / "hru_pw_day.txt").is_file() else "NOT_AVAILABLE",
            "file": "hru_pw_day.txt",
            "sha256": _sha256(workspace / "hru_pw_day.txt") if (workspace / "hru_pw_day.txt").is_file() else None,
            "headers": _normalized_output(workspace / "hru_pw_day.txt").get("header", [])
            if (workspace / "hru_pw_day.txt").is_file() else [],
        },
        "input_mutation": result.provenance.get("workspace_modifications"),
        "input_hashes": _project_input_hashes(workspace, project),
        "plants_plt_sha256": _sha256(workspace / "plants.plt"),
    }


def _parameter_classification(parameter: str, comparison: dict[str, Any], run: dict[str, Any],
                              corn_yield_count: int) -> str:
    if comparison["any_normalized_plant_output_change"] or comparison["any_normalized_hydrology_output_change"]:
        return "ACTIVE_AND_SENSITIVE"
    table = _numeric_table(Path(run["workspace"]) / "hru_pw_day.txt")
    if table.get("status") != "AVAILABLE" or not run["plant_status_file"]["status"] == "AVAILABLE":
        return "OUTPUT_NOT_OBSERVABLE"
    if corn_yield_count == 0:
        events = _corn_events(run)
        if run.get("management_event_evidence", {}).get("status") == "AVAILABLE" and not events:
            return "LIKELY_NOT_ACTIVE"
        return "INCONCLUSIVE"
    if parameter in {"can_ht_max", "rt_dp_max"}:
        # This executable's documented hru_pw output has no direct height or
        # root-depth column. The hydrologic proxies were compared above; when
        # unchanged, the internal plant state remains unobservable here.
        return "OUTPUT_NOT_OBSERVABLE"
    output_headers = {
        name: set(_normalized_output(Path(run["workspace"]) / name).get("header", []))
        if (Path(run["workspace"]) / name).is_file() else set()
        for name in OUTPUT_FILES_TO_COMPARE
    }
    observable_columns = []
    for item in PARAMETER_OUTPUTS[parameter]:
        if "." not in item:
            continue
        filename, column = item.rsplit(".", maxsplit=1)
        filename = filename if filename.endswith(".txt") else f"{filename}.txt"
        headers = output_headers.get(filename, set())
        if column in headers or column.lower() in {header.lower() for header in headers}:
            observable_columns.append(item)
    if not observable_columns:
        return "OUTPUT_NOT_OBSERVABLE"
    return "ACTIVE_BUT_NO_DETECTABLE_RESPONSE"


def _expected_output_differences(comparison: dict[str, Any], observables: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for observable in observables:
        if "." not in observable:
            output[observable] = {"status": "NO_COLUMN_SPECIFIED"}
            continue
        filename, column = observable.rsplit(".", maxsplit=1)
        filename = filename if filename.endswith(".txt") else f"{filename}.txt"
        file_result = comparison["files"].get(filename)
        if file_result is None:
            output[observable] = {"status": "OUTPUT_NOT_AVAILABLE"}
            continue
        differences = file_result.get("variable_differences") or {}
        actual_name = next((name for name in differences if name.lower() == column.lower()), None)
        if actual_name is None:
            output[observable] = {
                "status": file_result.get("status", "OUTPUT_COLUMN_NOT_AVAILABLE"),
                "sha256_baseline": file_result.get("sha256_baseline"),
                "sha256_candidate": file_result.get("sha256_candidate"),
                "normalized_content_equal": file_result.get("normalized_content_equal"),
                "print_precision": file_result.get("print_precision", {}).get(column),
                "compared_records": 0,
                "changed_records": 0,
                "max_absolute_difference": None,
                "max_relative_difference": None,
                "first_divergence_date": None,
            }
            continue
        summary = differences[actual_name]
        output[observable] = {
            "status": file_result["status"],
            "sha256_baseline": file_result["sha256_baseline"],
            "sha256_candidate": file_result["sha256_candidate"],
            "normalized_content_equal": file_result["normalized_content_equal"],
            "print_precision": file_result.get("print_precision", {}).get(actual_name),
            **summary,
        }
    return output


def _corn_events(run: dict[str, Any]) -> list[dict[str, Any]]:
    for output in run.get("management_event_evidence", {}).get("files", []):
        if output.get("file") == "mgt_out.txt":
            return output.get("corn_management_events", [])
    return []


def _compare_management_events(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    def event_key(event: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
        return event["operation"], event["date"], tuple(str(value) for value in event["hru_ids"])

    left = {event_key(event) for event in _corn_events(baseline)}
    right = {event_key(event) for event in _corn_events(candidate)}
    return {
        "baseline_event_count": len(left), "candidate_event_count": len(right),
        "unchanged_events": len(left & right),
        "events_added_in_candidate": [list(value) for value in sorted(right - left)],
        "events_missing_from_candidate": [list(value) for value in sorted(left - right)],
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    bundle = Path(args.experiment_bundle).resolve()
    report_path = Path(args.phase34_report).resolve()
    output_root = Path(args.output_root).resolve()
    expected_data_root = (BACKEND_ROOT / "data").resolve()
    if expected_data_root not in output_root.parents:
        raise ValueError("Phase 3.5 outputs must be stored under backend/data/")
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite phase 3.5 outputs at {output_root}")
    manifest, phase34_report = _verify_bundle(bundle, report_path)
    start, end = date.fromisoformat(phase34_report["period"]["start"]), date.fromisoformat(phase34_report["period"]["end"])
    project = bundle / "project"
    executable = Path(args.executable or settings.SWAT_PLUS_EXECUTABLE).resolve()
    if not executable.is_file() or not executable.stat().st_mode & 0o111:
        raise FileNotFoundError(f"SWAT+ executable is not runnable: {executable}")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    phase34_pair = _phase34_pair_diagnostics(report_path, manifest, phase34_report)
    baseline_workspace = report_path.parent / "swat-runs" / phase34_pair["baseline_run_id"]
    coupled_workspace = report_path.parent / "swat-runs" / phase34_pair["coupled_run_id"]
    baseline_values = _plant_values(project / "plants.plt")
    coupled_values = _plant_values(coupled_workspace / "plants.plt")
    mapped_names = set(SwatPlantParameterMapper.PARAMETER_SPECS)
    if set(_changed_plant_columns(project / "plants.plt", coupled_workspace / "plants.plt")) != mapped_names:
        raise ValueError("The phase 3.4 FSPM workspace changes plants.plt columns beyond the ten mapper parameters")
    update_rows = phase34_report["coupled"]["parameter_mapping"].get("parameter_updates", [])
    changed_parameters = [row for row in update_rows if row.get("status") == "CHANGED"]
    expected_names = set(SwatPlantParameterMapper.PARAMETER_SPECS)
    if {row.get("swat_parameter") for row in changed_parameters} != expected_names:
        raise ValueError("The phase 3.4 report does not contain the expected ten changed plants.plt parameters")
    for row in changed_parameters:
        name = row["swat_parameter"]
        if not math.isclose(float(row["original_value"]), baseline_values[name], abs_tol=1e-6):
            raise ValueError(f"Phase 3.4 original value mismatch for {name}")
        if not math.isclose(float(row["coupled_value"]), coupled_values[name], abs_tol=1e-6):
            raise ValueError(f"Phase 3.4 FSPM value mismatch for {name}")
    # Validate the complete ten-parameter FSPM record and each OAT probe before
    # any new workspace is created, without touching the phase 3.4 project.
    for name, value in DIAGNOSTIC_VALUES.items():
        _, _, low, high, _ = SwatPlantParameterMapper.PARAMETER_SPECS[name]
        if not low <= value <= high:
            raise ValueError(f"Diagnostic value for {name} is outside its allowed range [{low}, {high}]")
        candidate = dict(baseline_values)
        candidate[name] = value
        if not candidate["frac_hu1"] < candidate["frac_hu2"] < candidate["hu_lai_decl"]:
            raise ValueError(f"Diagnostic value for {name} violates the LAI heat-unit order")
        if not candidate["lai_max1"] < candidate["lai_max2"]:
            raise ValueError(f"Diagnostic value for {name} violates the LAI curve order")

    run_count = len(changed_parameters) + 2
    bytes_per_workspace = sum(path.stat().st_size for path in project.rglob("*") if path.is_file())
    required_bytes = bytes_per_workspace * run_count + 512 * 1024 * 1024
    free_bytes = shutil.disk_usage(output_root.parent).free
    if free_bytes < required_bytes:
        raise RuntimeError(f"Insufficient disk space for {run_count} independent SWAT+ workspaces: need {required_bytes}, have {free_bytes}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    working_directory = output_root / "workspaces"
    working_directory.mkdir(parents=True)
    adapter = SwatPlusAdapter(executable, project, working_directory)

    runs: dict[str, dict[str, Any]] = {}
    watershed_code = phase34_report["watershed_snapshot"]["code"]
    runs["baseline"] = _run_one(
        adapter, run_id="phase35-instrumented-baseline", run_type="SWAT_STANDARD_BASELINE",
        project=project, executable=executable, working_directory=working_directory,
        start=start, end=end, watershed_code=watershed_code, timeout_seconds=args.timeout_seconds,
        role="BASELINE", baseline_values=baseline_values, coupled_values=coupled_values,
    )
    runs["fspm_coupled"] = _run_one(
        adapter, run_id="phase35-instrumented-fspm-coupled", run_type="SWAT_STANDARD_BASELINE",
        project=project, executable=executable, working_directory=working_directory,
        start=start, end=end, watershed_code=watershed_code, timeout_seconds=args.timeout_seconds,
        role="FSPM_COUPLED", baseline_values=baseline_values, coupled_values=coupled_values,
    )
    probes: dict[str, dict[str, Any]] = {}
    for name in sorted(expected_names):
        run_id = f"phase35-probe-{name}"
        probes[name] = _run_one(
            adapter, run_id=run_id, run_type="SWAT_STANDARD_BASELINE",
            project=project, executable=executable, working_directory=working_directory,
            start=start, end=end, watershed_code=watershed_code, timeout_seconds=args.timeout_seconds,
            role=DIAGNOSTIC_TAG, baseline_values=baseline_values, coupled_values=coupled_values,
            diagnostic_parameter=name,
        )

    invariant_file_differences: dict[str, list[str]] = {}
    baseline_hashes = runs["baseline"]["input_hashes"]
    for label, run in [*runs.items(), *[(f"probe:{name}", data) for name, data in probes.items()]]:
        changed = sorted(
            name for name in set(baseline_hashes) | set(run["input_hashes"])
            if name not in INSTRUMENTED_CONTROL_FILES | {"plants.plt"}
            and baseline_hashes.get(name) != run["input_hashes"].get(name)
        )
        invariant_file_differences[label] = changed
        if changed:
            raise RuntimeError(f"Forcing/management/project inputs differ in {label}: {changed}")
    fspm_changed_columns = _changed_plant_columns(
        Path(runs["baseline"]["workspace"]) / "plants.plt",
        Path(runs["fspm_coupled"]["workspace"]) / "plants.plt",
    )
    if set(fspm_changed_columns) != mapped_names:
        raise RuntimeError(f"Instrumented FSPM arm changed unexpected plants.plt columns: {fspm_changed_columns}")
    for name, run in probes.items():
        changed_columns = _changed_plant_columns(
            Path(runs["baseline"]["workspace"]) / "plants.plt",
            Path(run["workspace"]) / "plants.plt",
        )
        if changed_columns != [name]:
            raise RuntimeError(f"OAT probe for {name} changed plants.plt columns {changed_columns}")
    instrumentation_hashes = {
        name: sorted({run["input_hashes"].get(name) for run in [*runs.values(), *probes.values()]})
        for name in INSTRUMENTED_CONTROL_FILES
    }
    if any(len(values) != 1 for values in instrumentation_hashes.values()):
        raise RuntimeError("Diagnostic output instrumentation or run period differs across workspaces")

    selected_hru_ids = [int(value) for value in manifest["selected_hru_ids"]]
    coupled_comparison = _compare_run_outputs(
        Path(runs["baseline"]["workspace"]), Path(runs["fspm_coupled"]["workspace"]), selected_hru_ids
    )
    management_event_comparisons = {
        "fspm_coupled_vs_baseline": _compare_management_events(runs["baseline"], runs["fspm_coupled"]),
        **{
            f"probe:{name}_vs_baseline": _compare_management_events(runs["baseline"], run)
            for name, run in probes.items()
        },
    }
    parameter_results: dict[str, Any] = {}
    corn_yield_count = phase34_pair["corn_yield_aa_record_count"]
    for row in changed_parameters:
        name = row["swat_parameter"]
        probe = probes[name]
        comparison = _compare_run_outputs(
            Path(runs["baseline"]["workspace"]), Path(probe["workspace"]), selected_hru_ids
        )
        probe_values = _plant_values(Path(probe["workspace"]) / "plants.plt")
        if not math.isclose(probe_values[name], DIAGNOSTIC_VALUES[name], abs_tol=1e-6):
            raise RuntimeError(f"Diagnostic value for {name} was not preserved in the effective probe record")
        probe_workspace_hash = probe["input_hashes"]["plants.plt"]
        expected_observables = PARAMETER_OUTPUTS[name]
        parameter_results[name] = {
            "classification": _parameter_classification(name, comparison, probe, corn_yield_count),
            "diagnostic_tag": DIAGNOSTIC_TAG,
            "swat_parameter_path": SWAT_PARAMETER_PATHS[name],
            "input": {
                "file": "plants.plt", "crop": "corn", "original_value": baseline_values[name],
                "fspm_coupled_value": coupled_values[name], "diagnostic_value": probe_values[name],
                "allowed_range": {
                    "minimum": SwatPlantParameterMapper.PARAMETER_SPECS[name][2],
                    "maximum": SwatPlantParameterMapper.PARAMETER_SPECS[name][3],
                },
                "baseline_plants_sha256": runs["baseline"]["plants_plt_sha256"],
                "fspm_plants_sha256": runs["fspm_coupled"]["plants_plt_sha256"],
                "diagnostic_plants_sha256": probe_workspace_hash,
                "diagnostic_changes_only_corn_parameter": probe["input_mutation"]["scientific_inputs_changed"] == ["plants.plt"],
                "diagnostic_record_matches_expected_value": math.isclose(probe_values[name], DIAGNOSTIC_VALUES[name], abs_tol=1e-6),
                "diagnostic_compatibility_normalization_rows": probe["input_mutation"]["compatibility_normalization"]["rows_normalized"],
            },
            "expected_observables": expected_observables,
            "expected_output_differences": _expected_output_differences(comparison, expected_observables),
            "combined_fspm_output_differences": {
                "attribution": "TEN_PARAMETER_FSPM_CHANGE_COMBINED; NOT INDIVIDUALLY ATTRIBUTABLE",
                "outputs": _expected_output_differences(coupled_comparison, expected_observables),
            },
            "one_at_a_time_probe_vs_baseline": comparison,
            "combined_fspm_pair_vs_baseline": {
                "attribution": "TEN_PARAMETER_FSPM_CHANGE_COMBINED; NOT INDIVIDUALLY ATTRIBUTABLE",
                "plant_output_variables_changed": coupled_comparison["plant_output_variables_changed"],
                "hydrology_output_variables_changed": coupled_comparison["hydrology_output_variables_changed"],
                "any_normalized_plant_output_change": coupled_comparison["any_normalized_plant_output_change"],
                "any_normalized_hydrology_output_change": coupled_comparison["any_normalized_hydrology_output_change"],
            },
        }

    source_hash_after = {name: _sha256(project / name) for name in REQUIRED_PROJECT_INPUTS}
    for name, expected in manifest["experiment_project_input_checksums_after_sha256"].items():
        if _sha256(project / name) != expected:
            raise RuntimeError(f"Phase 3.4 source variant changed during diagnostics: {name}")

    report_out = {
        "schema_version": "phase35-sensitivity-verification-v2",
        "diagnostic_tag": DIAGNOSTIC_TAG,
        "experiment_id": phase34_report["experiment_id"],
        "classification": EXPERIMENT_CLASSIFICATION,
        "scientific_status": "DIAGNOSTIC_ONLY_NOT_A_SCIENTIFIC_CONFIGURATION",
        "period": phase34_report["period"],
        "phase34_bundle_manifest": str((bundle / "manifest.json").resolve()),
        "phase34_bundle_manifest_sha256": _sha256(bundle / "manifest.json"),
        "phase34_report": str(report_path),
        "source_variant_input_hashes_unchanged": source_hash_after == {
            name: manifest["experiment_project_input_checksums_after_sha256"][name]
            for name in source_hash_after
        },
        "phase34_pair_diagnostics": phase34_pair,
        "diagnostic_configuration": {
            "swat_executable": str(executable),
            "swat_executable_sha256": _sha256(executable),
            "swat_version": next((line.strip() for line in
                (Path(runs["baseline"]["workspace"]) / "simulation.out").read_text(encoding="utf-8", errors="replace").splitlines()
                if "revision" in line.lower()), None),
            "output_instrumentation_identical_across_runs": instrumentation_hashes,
            "forcing_and_management_invariance_differences": invariant_file_differences,
            "forcing_invariance_verified": all(not rows for rows in invariant_file_differences.values()),
            "management_invariance_verified": all(not rows for rows in invariant_file_differences.values()),
            "independent_workspace_count": len(runs) + len(probes),
            "source_project_changed": False,
            "postgresql_used": False,
            "plant_table_reader_compatibility": {
                "phase34_file_days_mat_example": "120.00000",
                "swat_61_internal_days_mat_type": "INTEGER",
                "source_reader_iostat_behavior": "READ error is only tested for eof < 0; positive conversion errors are not raised by this routine",
                "phase35_copy_only_normalization": "integral days_mat tokens rendered as integer literals in every independent workspace; numeric values preserved",
                "normalized_rows_per_workspace": runs["baseline"]["input_mutation"]["compatibility_normalization"]["rows_normalized"],
                "source_phase34_artifacts_modified": False,
                "normalized_baseline_fspm_plant_outputs_changed": coupled_comparison["any_normalized_plant_output_change"],
                "normalized_baseline_fspm_hydrology_outputs_changed": coupled_comparison["any_normalized_hydrology_output_change"],
            },
        },
        "instrumented_runs": runs,
        "diagnostic_runs": probes,
        "sensitivity_by_parameter": parameter_results,
        "combined_fspm_comparison": coupled_comparison,
        "corn_management_event_comparisons": management_event_comparisons,
        "limitations": [
            "SENSITIVITY_DIAGNOSTIC_ONLY outputs are computational probes and are not scientific parameter settings.",
            "The SWAT+ plant-weather and water-balance text outputs use the engine's configured print precision; equality is checked on parsed values and normalized records as well as hashes.",
            "This SWAT+ build does not expose direct plant height or root depth in hru_pw_day.txt. The failed object.prt plant-state request was removed because object.prt hydrograph selectors do not define plant-state output; indirect hydrologic proxies do not substitute for the missing plant state.",
            "A change in an instrumented output demonstrates computational sensitivity only; it does not establish observational validity, calibration, or historical planting dates.",
        ],
    }
    report_file = output_root / "phase35-sensitivity-report.json"
    report_file.write_text(json.dumps(report_out, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return report_out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-bundle", default=str(DEFAULT_BUNDLE))
    parser.add_argument("--phase34-report", default=str(DEFAULT_REPORT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--executable", default=settings.SWAT_PLUS_EXECUTABLE)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    report = _run(args)
    print(json.dumps({
        "report": str(Path(args.output_root).resolve() / "phase35-sensitivity-report.json"),
        "diagnostic_tag": report["diagnostic_tag"],
        "classifications": {name: item["classification"] for name, item in report["sensitivity_by_parameter"].items()},
        "baseline_vs_fspm_plant_outputs_changed": report["combined_fspm_comparison"]["plant_output_variables_changed"],
        "baseline_vs_fspm_hydrology_outputs_changed": report["combined_fspm_comparison"]["hydrology_output_variables_changed"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

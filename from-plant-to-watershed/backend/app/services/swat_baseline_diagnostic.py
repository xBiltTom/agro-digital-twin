"""Dated observational diagnostics; never calibrate or decide the research H1."""

from __future__ import annotations

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date
import hashlib
import math
from pathlib import Path
from statistics import fmean
from typing import Any

from scientific_core.validation import ValidationEngine


SCHEMA_VERSION = "swat-baseline-diagnostic/v1"


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Missing table header: {path.name}")
    header = lines[1].lower().split()
    rows = []
    for line in lines[2:]:
        if not line.strip():
            continue
        values = line.split()
        if len(values) != len(header):
            raise ValueError(f"Unexpected row layout: {path.name}")
        rows.append(dict(zip(header, values, strict=True)))
    return header, rows


def inspect_project(project: Path) -> dict:
    """Trace HRU -> landuse -> tile; a named file alone is not activation."""
    if (project / "TxtInOut").is_dir():
        project = project / "TxtInOut"
    if not (project / "landuse.lum").is_file() or not (project / "hru-data.hru").is_file():
        return {"status": "NOT_AVAILABLE", "reason": "HRU/landuse tables unavailable"}
    _, landuses = read_table(project / "landuse.lum")
    _, hrus = read_table(project / "hru-data.hru")
    definitions = {row["name"]: row for row in landuses}
    _, tiles = read_table(project / "tiledrain.str") if (project / "tiledrain.str").is_file() else ([], [])
    tile_names = {row["name"] for row in tiles}
    links = []
    for hru in hrus:
        landuse = definitions.get(hru["lu_mgt"])
        if landuse is None:
            raise ValueError(f"Unresolved landuse for HRU {hru['id']}")
        tile = landuse.get("tile", landuse.get("tiledrain", "null"))
        if tile != "null" and tile not in tile_names:
            raise ValueError(f"Unresolved tile pointer for HRU {hru['id']}: {tile}")
        links.append({"hru_id": int(hru["id"]), "landuse": hru["lu_mgt"], "tile": tile})
    routing = routing_rows(project / "rout_unit.con") if (project / "rout_unit.con").is_file() else []
    checksums = {name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                 for name in ("landuse.lum", "hru-data.hru", "tiledrain.str", "hydrology.hyd", "soils.sol", "rout_unit.con")
                 if (project / name).is_file()}
    return {"status": "INSPECTED", "hru_count": len(links),
            "tile_linked_hru_count": sum(row["tile"] != "null" for row in links),
            "landuse_tile_links": links, "tile_definitions": tiles, "input_checksums": checksums,
            "routing_unit_count": len(routing),
            "routing_units_with_tile_connection": sum(any(edge[2] in {"til", "tot"} for edge in edges) for _, edges in routing),
            "interpretation": "Input linkage only; inspect qtile to establish simulated drainage."}


def routing_rows(path: Path) -> list[tuple[list[str], list[list[str]]]]:
    """SWAT+ .con: 13 leading fields followed by out_tot groups of four."""
    rows = []
    for line in path.read_text().splitlines()[2:]:
        if not line.strip():
            continue
        values = line.split()
        if len(values) < 13 or len(values) != 13 + 4 * int(values[12]):
            raise ValueError(f"Unexpected connectivity layout: {path.name}")
        rows.append((values[:13], [values[i:i + 4] for i in range(13, len(values), 4)]))
    return rows


def route_drainage_probe(project: Path) -> dict:
    """Route tile flow to each RU's existing surface-flow channel, in a copy."""
    path = project / "rout_unit.con"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = routing_rows(path)
    for leading, edges in rows:
        if any(edge[2] in {"til", "tot"} for edge in edges):
            raise ValueError("Probe requires routing units without existing tile/total routes")
        targets = [edge for edge in edges if edge[0] == "sdc" and edge[2] == "sur"]
        if len(targets) != 1 or float(targets[0][3]) != 1:
            raise ValueError("Probe requires one full-fraction surface channel per routing unit")
        edges.append([targets[0][0], targets[0][1], "til", "1.00000"])
        leading[12] = str(len(edges))
    if not rows:
        raise ValueError("No routing units available")
    lines = path.read_text().splitlines()[:2]
    lines.extend(" ".join(leading + [value for edge in edges for value in edge]) for leading, edges in rows)
    path.write_text("\n".join(lines) + "\n")
    return {"file": "rout_unit.con", "routing_units_changed": len(rows),
            "connection": "til -> existing surface-flow sdc; fraction 1",
            "before_sha256": before, "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def link_drainage_probe(project: Path, *, landuse_name: str, tile_name: str) -> dict:
    """Explicit intervention in an isolated project, with no observed-mask claim."""
    path = project / "landuse.lum"
    header, rows = read_table(path)
    _, tiles = read_table(project / "tiledrain.str")
    if tile_name not in {row["name"] for row in tiles}:
        raise ValueError("Probe tile definition does not exist")
    tile_column = "tile" if "tile" in header else "tiledrain"
    targets = [row for row in rows if row["name"] == landuse_name]
    if len(targets) != 1:
        raise ValueError("Probe requires exactly one named landuse")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    old = targets[0][tile_column]
    targets[0][tile_column] = tile_name
    original = path.read_text().splitlines()
    path.write_text("\n".join(original[:2] + [" ".join(row[key] for key in header) for row in rows]) + "\n")
    return {"classification": "CONTROLLED_DRAINAGE_PROBE", "file": "landuse.lum",
            "landuse": landuse_name, "before": old, "after": tile_name,
            "before_sha256": before, "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "limitation": "Drainage mask is a diagnostic intervention, not observed historical management."}


def diagnose_baseline(records: list[dict], observations: dict[str, float], *,
                      quality: dict[str, str] | None = None, station_id: str | None = None,
                      frequency: str = "DAILY", minimum_monthly_coverage: float = 0.9,
                      project: dict | None = None) -> dict:
    quality = quality or {}
    project = project or {}
    if not 0 < minimum_monthly_coverage <= 1:
        raise ValueError("Monthly coverage must be in (0, 1]")
    if frequency != "DAILY":
        return {"status": "NOT_AVAILABLE", "reason": "Diagnostic requires daily outputs"}
    simulated = {}
    for row in records:
        day = str(row["period"])
        date.fromisoformat(day)
        if day in simulated:
            raise ValueError(f"Duplicate simulation date: {day}")
        simulated[day] = row.get("streamflow_m3s")
    dates = sorted(day for day in simulated if _finite(simulated[day]) and _finite(observations.get(day)))
    estimated = {day for day in dates if "e" in quality.get(day, "").replace(",", ";").split(";")}
    groups = defaultdict(list)
    for day in simulated:
        groups[day[:7]]
    for day in dates:
        groups[day[:7]].append(day)
    months = []
    for month, days in sorted(groups.items()):
        year, number = map(int, month.split("-"))
        expected = monthrange(year, number)[1]
        included = len(days) / expected >= minimum_monthly_coverage
        months.append({"month": month, "paired_days": len(days), "expected_days": expected,
                       "coverage_fraction": len(days) / expected, "included": included,
                       "estimated_days": sum(day in estimated for day in days),
                       "observed_streamflow_m3s": fmean(observations[day] for day in days) if included else None,
                       "baseline_streamflow_m3s": fmean(simulated[day] for day in days) if included else None})
    used = [row for row in months if row["included"]]
    daily = ValidationEngine.evaluate([observations[day] for day in dates], [simulated[day] for day in dates])
    monthly = ValidationEngine.evaluate([row["observed_streamflow_m3s"] for row in used],
                                        [row["baseline_streamflow_m3s"] for row in used])
    non_estimated = [day for day in dates if day not in estimated]
    sensitivity = ValidationEngine.evaluate([observations[day] for day in non_estimated], [simulated[day] for day in non_estimated])
    fluxes = {}
    for variable in ("precip_mm", "evapotranspiration_mm", "potential_evapotranspiration_mm",
                     "runoff_mm", "percolation_mm", "tile_drainage_mm", "lateral_flow_mm", "water_yield_mm"):
        values = [row.get(variable) for row in records]
        fluxes[variable] = sum(values) if values and all(_finite(value) for value in values) else None
    precipitation, et = fluxes["precip_mm"], fluxes["evapotranspiration_mm"]
    et_ratio = et / precipitation if precipitation and et is not None else None
    flags = []
    if project.get("status") == "INSPECTED" and project.get("tile_linked_hru_count") == 0:
        flags.append({"code": "DRAINAGE_NOT_LINKED", "message": "El drenaje artificial no está enlazado a las HRU."})
    if project.get("tile_linked_hru_count", 0) > 0 and project.get("routing_unit_count", 0) > 0 and project.get("routing_units_with_tile_connection") == 0:
        flags.append({"code": "TILE_ROUTING_MISSING", "message": "Hay drenaje activo, pero las unidades de ruteo no tienen salida til/tot."})
    if et_ratio is not None and et_ratio > 0.7:
        flags.append({"code": "HIGH_ET_FRACTION", "message": "ET supera el 70 % de la lluvia: revisar procesos y forcing; indicador diagnóstico."})
    nse, bias = monthly["nse"]["value"], monthly["pbias"]["value"]
    if nse is not None and nse < 0:
        flags.append({"code": "NEGATIVE_MONTHLY_NSE", "message": "El NSE mensual es negativo; la referencia necesita diagnóstico."})
    if bias is not None and abs(bias) > 30:
        flags.append({"code": "LARGE_VOLUME_BIAS", "message": "El sesgo mensual supera ±30 %; revisar el volumen simulado."})
    if not used:
        flags.append({"code": "NO_OBSERVED_MONTHS", "message": "No hay meses con cobertura suficiente para la comparación USGS."})
    return {"schema_version": SCHEMA_VERSION,
            "status": "OBSERVATIONAL_DIAGNOSTIC" if len(dates) >= 2 else "NOT_AVAILABLE",
            "interpretation": "DEVELOPMENT_DIAGNOSTIC_NOT_HYPOTHESIS_TEST",
            "station_id": station_id, "unit": "m3/s", "daily": daily, "monthly": monthly,
            "aligned_months": len(used), "monthly_outputs": months,
            "daily_comparison": [{"date": day, "observed_streamflow_m3s": observations[day],
                                  "baseline_streamflow_m3s": simulated[day],
                                  "qualifiers": quality.get(day, "UNKNOWN")} for day in dates],
            "coverage": {"simulation_days": len(simulated), "paired_days": len(dates),
                         "unmatched_dates": sorted(set(simulated) - set(dates)), "estimated_days": len(estimated),
                         "qualifiers": dict(Counter(quality.get(day, "UNKNOWN") for day in dates)),
                         "minimum_monthly_coverage": minimum_monthly_coverage,
                         "aggregation": "Both monthly means use identical valid days; observations are never imputed."},
            "daily_excluding_estimated": sensitivity, "physical": {"totals_mm": fluxes,
            "et_precipitation_ratio": et_ratio, "project": project,
            "balance_closure": "NOT_COMPUTED: these reported terms are not a complete mass balance"},
            "flags": flags, "hypothesis_status": "NOT_EVALUATED",
            "metric_conventions": {"pbias": "100 * sum(simulated - observed) / sum(observed)",
                                   "kge": "Modified KGE using coefficient-of-variation ratio"}}

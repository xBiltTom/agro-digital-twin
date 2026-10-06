"""Read-only forcing reconstruction and external model comparisons for 2019.

External gridded products are comparisons, not observed basin ET. Every series
must have complete dated coverage; missing cells/days are never interpolated.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date, timedelta
import hashlib
import io
import json
from pathlib import Path
import platform
import tarfile

import numpy as np
from scipy.io import netcdf_file
from scipy import __version__ as scipy_version

from app.services.swat_baseline_diagnostic import read_table
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from app.services.swat_water_path import period, table

SCHEMA_VERSION = "swat-meteorology-diagnostic/v2"
GRID_VARIABLES = ("pr", "tmmx", "tmmn", "srad", "rmin", "rmax", "vs")
FIELDS = ("pcp", "tmp_max", "tmp_min", "slr", "hmd", "wnd")
ROUNDING_BOUNDS = np.array([.005, .005, .005, .005, .0005, .005]) + 1e-8
EXPECTED_UNITS = {"pr": "mm", "tmmx": "K", "tmmn": "K", "srad": "W m-2",
                  "rmin": "%", "rmax": "%", "vs": "m s-1"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def string(value) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def grid(path: Path) -> dict:
    """Decode packed classic NetCDF, validating actual time/lat/lon array shape.

    These NCSS files expose a stale `dimensions='lon lat time'` attribute. The
    array actually has time/lat/lon order, so never use that text as axis order.
    """
    with netcdf_file(path, mmap=False) as dataset:
        names = [name for name, var in dataset.variables.items() if var.data.ndim == 3]
        if len(names) != 1:
            raise ValueError(f"Expected one gridded variable: {path.name}")
        variable = dataset.variables[names[0]]
        clock = dataset.variables.get("day", dataset.variables.get("time"))
        if clock is None or string(clock.units) != "days since 1900-01-01 00:00:00" or string(getattr(clock, "calendar", b"gregorian")) != "gregorian":
            raise ValueError(f"Unsupported calendar/epoch: {path.name}")
        times = np.array(clock[:], dtype=float)
        if not np.isfinite(times).all() or not np.equal(times, np.floor(times)).all():
            raise ValueError(f"Non-daily date coordinates: {path.name}")
        dates = [date(1900, 1, 1) + timedelta(days=int(day)) for day in times]
        lat, lon = np.array(dataset.variables["lat"][:]), np.array(dataset.variables["lon"][:])
        raw = np.array(variable[:])
        if raw.shape != (len(dates), len(lat), len(lon)) or len(dates) != len(set(dates)):
            raise ValueError(f"Ambiguous grid shape/dates: {path.name}")
        if not np.isfinite(lat).all() or not np.isfinite(lon).all() or len(set(lat)) != len(lat) or len(set(lon)) != len(lon):
            raise ValueError(f"Invalid spatial coordinates: {path.name}")
        missing = np.zeros(raw.shape, dtype=bool)
        for key in ("_FillValue", "missing_value"):
            if hasattr(variable, key):
                missing |= raw == getattr(variable, key)
        if string(getattr(variable, "_Unsigned", b"false")).lower() == "true":
            raw = raw.astype(f"u{raw.dtype.itemsize}")
        values = raw.astype(float) * float(getattr(variable, "scale_factor", 1)) + float(getattr(variable, "add_offset", 0))
        values[missing] = np.nan
        return {"name": names[0], "dates": dates, "lat": lat, "lon": lon, "values": values,
                "units": string(variable.units), "scale_factor": float(getattr(variable, "scale_factor", 1)),
                "add_offset": float(getattr(variable, "add_offset", 0)),
                "metadata": {key: string(value) for key, value in dataset._attributes.items()}}


def nearest(data: dict, station: dict) -> tuple[np.ndarray, dict]:
    lat_index = int(np.argmin(abs(data["lat"] - station["lat"])))
    lon_index = int(np.argmin(abs(data["lon"] - station["lon"])))
    point = {"lat": float(data["lat"][lat_index]), "lon": float(data["lon"][lon_index])}
    # All grids used here have nominal 1/24-degree resolution.
    if abs(point["lat"] - station["lat"]) > 1 / 48 + 1e-6 or abs(point["lon"] - station["lon"]) > 1 / 48 + 1e-6:
        raise ValueError(f"Nearest grid cell not covered for {station['name']}")
    values = data["values"][:, lat_index, lon_index]
    if not np.isfinite(values).all():
        raise ValueError(f"Missing grid cell values for {station['name']}")
    return values, point


def same_point(first: dict, second: dict) -> bool:
    return all(abs(first[key] - second[key]) < 1e-9 for key in ("lat", "lon"))


def station_inputs(project: Path):
    reader = SwatClimateForcingReader(project)
    stations, all_data, checksums = [], {}, {}
    for files in reader._station_files():
        header = files["pcp"].read_text().splitlines()[2].split()
        station = {"name": files["name"].name, "lat": float(header[2]), "lon": float(header[3]), "elevation_m": float(header[4])}
        records = {kind: reader._numeric_rows(files[kind], 4 if kind == "tmp" else 3)
                   for kind in ("pcp", "tmp", "slr", "hmd", "wnd")}
        keys = sorted(records["pcp"])
        dates = [date(year, 1, 1) + timedelta(days=day - 1) for year, day in keys]
        expected = [dates[0] + timedelta(days=i) for i in range((dates[-1] - dates[0]).days + 1)]
        if dates != expected or any(sorted(records[kind]) != keys for kind in records):
            raise ValueError(f"Weather coverage differs by variable or contains gaps: {station['name']}")
        values = np.array([[records["pcp"][k][0], *records["tmp"][k], records["slr"][k][0],
                            records["hmd"][k][0], records["wnd"][k][0]] for k in keys])
        if not np.isfinite(values).all() or (values[:, [0, 3, 5]] < 0).any() or (values[:, 1:3] <= -90).any() or (values[:, 1] < values[:, 2]).any() or ((values[:, 4] < 0) | (values[:, 4] > 1)).any():
            raise ValueError(f"Invalid/missing weather values: {station['name']}")
        if stations and dates != all_data[stations[0]["name"]]["dates"]:
            raise ValueError("Stations must cover identical dates")
        for kind in records:
            other = files[kind].read_text().splitlines()[2].split()
            if list(map(float, other[2:5])) != list(map(float, header[2:5])):
                raise ValueError(f"Weather coordinates disagree: {station['name']}/{kind}")
            checksums[files[kind].name] = sha256(files[kind])
        stations.append(station)
        all_data[station["name"]] = {"dates": dates, "values": values}
    checksums["weather-sta.cli"] = sha256(project / "weather-sta.cli")
    return stations, all_data, checksums


def reconstruct_gridmet(project: Path, builder_root: Path, stations: list, weather: dict, calendar_edges: Path) -> dict:
    metadata = json.loads((builder_root / "metadata.json").read_text())
    if metadata.get("weather_source") != "gridmet":
        raise ValueError("Builder metadata does not identify gridMET")
    builder_project = builder_root / "project/Scenarios/Default/TxtInOut"
    for station in stations:
        for kind in ("pcp", "tmp", "slr", "hmd", "wnd"):
            name = f"{station['name']}.{kind}"
            if sha256(project / name) != sha256(builder_project / name):
                raise ValueError(f"Weather differs from archived builder files: {name}")
    dates = weather[stations[0]["name"]]["dates"]
    edge_manifest = json.loads((calendar_edges / "manifest.json").read_text())
    if edge_manifest["classification"] != "GRIDMET_CALENDAR_EDGE_PROVENANCE_CHECK" or edge_manifest["weather_sta_sha256"] != sha256(project / "weather-sta.cli"):
        raise ValueError("Calendar supplement is not tied to the executed station file")
    for artifact in edge_manifest["artifacts"]:
        if sha256(calendar_edges / artifact["file"]) != artifact["sha256"]:
            raise ValueError("Calendar supplement changed")
    years = sorted({day.year for day in dates})
    by_year = defaultdict(list)
    for path in sorted((builder_root / "gridmet_cache").glob("grid_grid_*.nc")):
        kind = path.name.split("_")[2]
        if kind not in GRID_VARIABLES:
            continue
        with netcdf_file(path, mmap=False) as dataset:
            year = (date(1900, 1, 1) + timedelta(days=int(dataset.variables["day"][0]))).year
        if year in years:
            by_year[(kind, year)].append(path)
    errors = {field: {"compared_values": 0, "mismatches": 0, "max_absolute_error": 0.0} for field in FIELDS}
    original_errors = {field: {"compared_values": 0, "mismatches": 0, "max_absolute_error": 0.0} for field in FIELDS}
    inventory, points, annual, recovered, conflicts = {}, {}, [], [], []
    for year in years:
        indices = [i for i, day in enumerate(dates) if day.year == year]
        expected_dates = [dates[i] for i in indices]
        raw, interpolated_raw = {}, {}
        for kind in GRID_VARIABLES:
            candidates = [grid(path) for path in by_year[(kind, year)]]
            source_dates = candidates[0]["dates"] if candidates else []
            if not candidates or any(data["dates"] != source_dates for data in candidates) or not set(source_dates) <= set(expected_dates):
                raise ValueError(f"Incomplete archived gridMET coverage: {kind}/{year}")
            missing_dates = sorted(set(expected_dates) - set(source_dates))
            supplement = None
            next_candidates = []
            if missing_dates:
                if missing_dates != [date(year, 12, 31)] or len(expected_dates) != 366:
                    raise ValueError(f"Unexpected source archive date gap: {kind}/{year}")
                supplement = grid(calendar_edges / f"calendar-{kind}-{year}.nc")
                if supplement["dates"] != missing_dates or supplement["units"] != candidates[0]["units"]:
                    raise ValueError("Calendar supplement dates/units do not match")
                recovered.append({"variable": kind, "date": missing_dates[0].isoformat(), "station_values": len(stations)})
                next_candidates = [grid(path) for path in by_year[(kind, year + 1)]]
                if not next_candidates or any(data["dates"][0] != date(year + 1, 1, 1) for data in next_candidates):
                    raise ValueError("Adjacent source dates required to audit leap-day interpolation")
            for data in candidates:
                # Accept conventional ASCII spelling differences in provider units.
                unit = data["units"].replace("^", "").replace("/", " ")
                expected_unit = EXPECTED_UNITS[kind]
                if unit not in {expected_unit, "m s" if kind == "vs" else expected_unit}:
                    raise ValueError(f"Unexpected gridMET units for {kind}: {data['units']}")
            raw[kind] = []
            interpolated_raw[kind] = []
            for station in stations:
                distances = [float(np.min(abs(data["lat"] - station["lat"])) + np.min(abs(data["lon"] - station["lon"]))) for data in candidates]
                best = [i for i, distance in enumerate(distances) if abs(distance - min(distances)) < 1e-9]
                groups = defaultdict(list)
                point = None
                for index in best:
                    series, cell = nearest(candidates[index], station)
                    if point is not None and not same_point(point, cell):
                        raise ValueError("Equidistant but distinct source cells are ambiguous")
                    point = cell
                    groups[hashlib.sha256(series.astype("<f8").tobytes()).hexdigest()].append(index)
                ranked = sorted(groups.values(), key=lambda group: (-len(group), group[0]))
                if len(ranked) > 1 and len(ranked[0]) == len(ranked[1]):
                    raise ValueError(f"No unique cache consensus for {kind}/{year}/{station['name']}")
                selected_index = ranked[0][0]
                values, point = nearest(candidates[selected_index], station)
                if len(ranked) > 1:
                    variants = []
                    for group in ranked:
                        series, _ = nearest(candidates[group[0]], station)
                        files = {by_year[(kind, year)][index].name: sha256(by_year[(kind, year)][index]) for index in group}
                        inventory.update(files)
                        variants.append({"files_sha256": files, "count": len(group),
                                         "daily_values_sha256": hashlib.sha256(series.astype("<f8").tobytes()).hexdigest(),
                                         "max_difference_from_consensus": float(np.max(abs(series - values)))})
                    conflicts.append({"variable": kind, "year": year, "station": station["name"], "cell": point, "variants": variants})
                path = by_year[(kind, year)][selected_index]
                inventory[path.name] = sha256(path)
                previous = points.setdefault(station["name"], point)
                if not same_point(previous, point):
                    raise ValueError("Source cell changes across variable/year")
                if supplement is not None:
                    additional, additional_point = nearest(supplement, station)
                    if not same_point(point, additional_point):
                        raise ValueError("Supplement and archived grid cells differ")
                    distances_next = [float(np.min(abs(data["lat"] - station["lat"])) + np.min(abs(data["lon"] - station["lon"]))) for data in next_candidates]
                    next_index = int(np.argmin(distances_next))
                    next_values, next_point = nearest(next_candidates[next_index], station)
                    if not same_point(next_point, point):
                        raise ValueError("Adjacent year uses a different grid cell")
                    inventory[by_year[(kind, year + 1)][next_index].name] = sha256(by_year[(kind, year + 1)][next_index])
                    interpolated_raw[kind].append((values[-1] + next_values[0]) / 2)
                    values = np.concatenate((values, additional))
                raw[kind].append(values)
            raw[kind] = np.array(raw[kind])
            interpolated_raw[kind] = np.array(interpolated_raw[kind])
        # Conversion rules recovered from the archived daily inputs.
        converted = np.stack((raw["pr"], raw["tmmx"] - 273.15, raw["tmmn"] - 273.15,
                              raw["srad"] * .0864, (raw["rmin"] + raw["rmax"]) / 200, raw["vs"]), axis=2)
        observed = np.array([weather[s["name"]]["values"][indices] for s in stations])
        difference = np.abs(converted - observed)
        for index, field in enumerate(FIELDS):
            values = difference[:, :, index]
            errors[field]["compared_values"] += int(values.size)
            errors[field]["mismatches"] += int((values > ROUNDING_BOUNDS[index]).sum())
            errors[field]["max_absolute_error"] = max(errors[field]["max_absolute_error"], float(values.max()))
            original = values[:, :len(source_dates)]
            original_errors[field]["compared_values"] += int(original.size)
            original_errors[field]["mismatches"] += int((original > ROUNDING_BOUNDS[index]).sum())
            original_errors[field]["max_absolute_error"] = max(original_errors[field]["max_absolute_error"], float(original.max()))
        interpolation_error = None
        gap_delta = None
        if len(expected_dates) == 366:
            interpolated = np.stack((interpolated_raw["pr"], interpolated_raw["tmmx"] - 273.15,
                                     interpolated_raw["tmmn"] - 273.15, interpolated_raw["srad"] * .0864,
                                     (interpolated_raw["rmin"] + interpolated_raw["rmax"]) / 200, interpolated_raw["vs"]), axis=1)
            interpolation_error = np.abs(interpolated - observed[:, -1, :])
            gap_delta = {field: {"max_absolute_difference_from_retrieved_gridmet": float(difference[:, -1, index].max()),
                               "max_absolute_error_vs_adjacent_day_interpolation": float(interpolation_error[:, index].max())}
                         for index, field in enumerate(FIELDS)}
        annual.append({"year": year, "days": len(indices), "station_days": len(stations) * len(indices),
                       "mismatches": int((difference > ROUNDING_BOUNDS).sum()),
                       "original_cache_mismatches": int((difference[:, :len(source_dates), :] > ROUNDING_BOUNDS).sum()),
                       "interpolated_calendar_date": date(year, 12, 31).isoformat() if interpolation_error is not None else None,
                       "interpolation_mismatches": int((interpolation_error > ROUNDING_BOUNDS).sum()) if interpolation_error is not None else 0,
                       "calendar_edge_differences": gap_delta})
    matches = not any(row["mismatches"] for row in original_errors.values()) and not any(row["interpolation_mismatches"] for row in annual)
    status = ("GRIDMET_ARCHIVE_WITH_CACHE_CONFLICTS" if conflicts else
              "VERIFIED_GRIDMET_WITH_INTERPOLATED_YEAR_END_DAYS" if matches and recovered else
              "VERIFIED_ARCHIVED_GRIDMET_CONVERSIONS" if matches else "CONVERSION_MISMATCH")
    return {"status": status,
            "provider": "gridMET", "provider_type": "GRIDDED_ESTIMATES_NOT_STATION_OBSERVATIONS",
            "builder_git_sha": metadata.get("builder_git_sha"), "builder_metadata_sha256": sha256(builder_root / "metadata.json"),
            "builder_archive_manifest_sha256": sha256(builder_root / "archive-manifest.json") if (builder_root / "archive-manifest.json").exists() else None,
            "archive_root": str(builder_root), "source_cache_files_used": len(inventory),
            "source_cache_inventory_sha256": canonical_hash(inventory), "source_cells": points,
            "source_cache_consistency": {"status": "CONFLICTS_FOUND" if conflicts else "CONSISTENT",
                                         "selection_policy": "Unique largest group of identical daily arrays at each common cell; never select by similarity to SWAT forcing.",
                                         "conflicts": conflicts, "conflicting_station_variable_years": len(conflicts)},
            "calendar_recovery": {"original_cache_gaps": recovered, "supplement_manifest": edge_manifest,
                                  "supplement_manifest_sha256": sha256(calendar_edges / "manifest.json"),
                                  "interpolated_station_days": sum(len(stations) for row in annual if row["interpolated_calendar_date"]),
                                  "interpretation": "Dec 31 in leap years matches linear interpolation of adjacent archived gridMET dates. Newly retrieved gridMET values quantify the difference; existing forcing is preserved."},
            "coverage": {"start": dates[0].isoformat(), "end": dates[-1].isoformat(), "days_per_station": len(dates),
                         "stations": len(stations), "daily_missing_values": 0, "per_year": annual},
            "conversion_checks_vs_original_cache": original_errors, "conversion_checks_vs_gridmet_including_calendar_edges": errors,
            "absolute_match_tolerance_by_field": dict(zip(FIELDS, ROUNDING_BOUNDS.tolist(), strict=True)),
            "match_policy": "Unrounded decoded/conversion values versus written forcing; half of builder rounding step plus 1e-8 numeric tolerance.",
            "conversions": {"pcp": "mm -> mm, rounded 0.01", "tmp": "K - 273.15 -> degC, rounded 0.01",
                            "slr": "daily-mean W/m2 * 86400/1e6 -> MJ/m2/day, rounded 0.01",
                            "hmd": "(RHmin_percent + RHmax_percent)/200 -> fraction, rounded 0.001",
                            "wnd": "10 m wind in m/s -> m/s, rounded 0.01; height adjustment occurs inside SWAT+"},
            "limitations": ["Daily forcing has no missing-value trigger for weather generation; WGN can still influence subdaily storm characteristics.",
                            "RH is the arithmetic mean of daily extrema, not a measured daily mean.",
                            "Matching an archived grid verifies provenance/conversions, not local weather accuracy."]}


def monthly_sum(dates: list[date], values: np.ndarray) -> dict[str, float]:
    output = defaultdict(float)
    for day, value in zip(dates, values, strict=True):
        if not np.isfinite(value):
            raise ValueError("Missing/nonfinite monthly contribution")
        output[day.isoformat()[:7]] += float(value)
    return dict(output)


def weighted_grid(path: Path, stations: list, weights: dict, *, monthly: bool = False):
    data = grid(path)
    expected = [date(2019, month, 1) for month in range(1, 13)] if monthly else [date(2019, 1, 1) + timedelta(days=i) for i in range(365)]
    if data["dates"] != expected or data["units"] != "mm":
        raise ValueError(f"Unexpected coverage/units: {path.name}")
    values = np.zeros(len(expected))
    points = {}
    for station in stations:
        series, point = nearest(data, station)
        if (series < 0).any():
            raise ValueError(f"Negative ET/precipitation: {path.name}")
        values += series * weights.get(station["name"], 0) / sum(weights.values())
        points[station["name"]] = point
    return monthly_sum(expected, values), {"variable": data["name"], "units": data["units"],
        "version": data["metadata"].get("version"), "source": data["metadata"].get("source"),
        "method": data["metadata"].get("method"), "history": data["metadata"].get("History"),
        "actual_dates": [day.isoformat() for day in expected], "source_cells": points,
        "calendar_policy": "Actual time coordinates validated; aggregated global coverage attributes can be stale."}


def pet_inputs(project: Path) -> dict:
    _, codes = read_table(project / "codes.bsn")
    _, basin = read_table(project / "parameters.bsn")
    _, hydrology = read_table(project / "hydrology.hyd")
    _, hrus = read_table(project / "hru-data.hru")
    by_name = {row["name"]: row for row in hydrology}
    if len(codes) != 1 or len(basin) != 1 or int(codes[0]["pet"]) != 1:
        raise ValueError("This diagnostic is restricted to the Penman-Monteith reference")
    manifest = json.loads((project / "swat_engine_manifest.json").read_text())
    archive = Path(manifest["source"]["archive"])
    if sha256(archive) != manifest["source"]["archive_sha256"]:
        raise ValueError("Pinned engine source archive changed")
    source = {}
    with tarfile.open(archive) as tar:
        for name in ("et_pot.f90", "climate_control.f90", "basin_prm_default.f90"):
            member = next(m for m in tar.getmembers() if m.name.endswith("/src/" + name))
            body = tar.extractfile(member).read()
            source[name] = {"sha256": hashlib.sha256(body).hexdigest()}
            if name == "et_pot.f90" and (b"(170./1000.)**0.2" not in body or b"hru(j)%hyd%pet_co * pet_day" not in body):
                raise ValueError("Unexpected pinned PET implementation")
    return {"method_code": 1, "method": "SWAT+ Penman-Monteith; reference alfalfa 0.4 m",
            "external_pet_file": False, "wind_height": "gridMET wind 10 m; et_pot.f90 applies (1.7/10)^0.2 internally",
            "source_commit": manifest["source"]["commit"], "source_archive_sha256": manifest["source"]["archive_sha256"],
            "source_files": source, "co2_input_ppm": float(basin[0]["co2"]),
            "lapse_code": int(codes[0]["lapse"]), "plaps": float(basin[0]["plaps"]), "tlaps": float(basin[0]["tlaps"]),
            "hru_hydrology_inputs": [{"hru_id": int(hru["id"]), "hydro": hru["hydro"],
                **{name: float(by_name[hru["hydro"]][name]) for name in ("pet_co", "esco", "epco", "perco", "latq_co")}} for hru in hrus],
            "comparison_limits": ["gridMET ETr uses ASCE alfalfa reference, shared meteorology; it is a same-provider PET check.",
                                  "Reference crop, snow albedo, vapor-pressure averaging and CO2 treatment differ between products."]}


def diagnose_meteorology(project: Path, builder_root: Path, benchmarks: Path, calendar_edges: Path, cache_references: list[Path]) -> dict:
    stations, weather, input_checksums = station_inputs(project)
    forcing, provenance = SwatClimateForcingReader(project).for_hrus(date(2019, 1, 1), date(2019, 12, 31), require_fspm=False)
    equal, _ = SwatClimateForcingReader(project).for_period(date(2019, 1, 1), date(2019, 12, 31), require_fspm=False)
    weights = provenance["station_weights"]
    dates = [date.fromisoformat(row["date"]) for row in forcing]
    source = reconstruct_gridmet(project, builder_root, stations, weather, calendar_edges)
    references = {}
    external = {}
    stations_by_name = {station["name"]: station for station in stations}
    for directory in cache_references:
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest["classification"] != "GRIDMET_CACHE_CONFLICT_REFERENCE_CHECK" or manifest["weather_sta_sha256"] != sha256(project / "weather-sta.cli"):
            raise ValueError("Cache reference must match the executed station file")
        for artifact in manifest["artifacts"]:
            if sha256(directory / artifact["file"]) != artifact["sha256"]:
                raise ValueError("Cache conflict reference changed")
        files = [artifact["file"] for artifact in manifest["artifacts"] if artifact["file"].endswith(".nc")]
        if len(files) != 1:
            raise ValueError("One gridded variable is required in each cache reference")
        reference = grid(directory / files[0])
        kind, field = {"precipitation_amount": ("pr", 0), "daily_mean_wind_speed": ("vs", 5)}[reference["name"]]
        year = int(manifest["year"])
        expected = [date(year, 1, 1) + timedelta(days=i) for i in range((date(year + 1, 1, 1) - date(year, 1, 1)).days)]
        if reference["dates"] != expected or reference["units"] not in ({"mm"} if kind == "pr" else {"m/s", "m s-1"}):
            raise ValueError("Cache reference has unexpected dates/units")
        if (kind, year) in references:
            raise ValueError("Duplicate variable/year cache reference")
        references[(kind, year)] = reference
        delta = np.zeros(len(expected))
        mismatches = []
        for station in stations:
            current, _ = nearest(reference, station)
            original = weather[station["name"]]
            indices = [i for i, day in enumerate(original["dates"]) if day.year == year]
            difference = original["values"][indices, field] - current
            delta += difference * weights.get(station["name"], 0) / sum(weights.values())
            if np.any(abs(difference) > ROUNDING_BOUNDS[field]):
                mismatches.append({"station": station["name"], "days_differing": int(np.sum(abs(difference) > ROUNDING_BOUNDS[field])),
                    "annual_total_difference_mm" if kind == "pr" else "mean_bias_ms": float(difference.sum()) if kind == "pr" else float(difference.mean()),
                    "max_daily_absolute_difference": float(np.max(abs(difference))), "units": reference["units"]})
        external[f"{kind}/{year}"] = {"manifest": manifest, "manifest_sha256": sha256(directory / "manifest.json"),
            "conflict_checks": [], "forcing_mismatches": mismatches,
            "area_weighted_annual_forcing_minus_reference_mm" if kind == "pr" else "area_weighted_mean_forcing_minus_reference_ms": float(delta.sum()) if kind == "pr" else float(delta.mean()),
            "scope": "New retrieval from the same provider resolves archive disagreements; it is not validation against weather observations."}
    for conflict in source["source_cache_consistency"]["conflicts"]:
        key = (conflict["variable"], conflict["year"])
        if key not in references:
            raise ValueError(f"Archive conflict requires an external retrieval: {key}")
        series, point = nearest(references[key], stations_by_name[conflict["station"]])
        digest = hashlib.sha256(series.astype("<f8").tobytes()).hexdigest()
        matches = [index for index, variant in enumerate(conflict["variants"]) if variant["daily_values_sha256"] == digest]
        external[f"{key[0]}/{key[1]}"]["conflict_checks"].append({"station": conflict["station"], "cell": point,
            "matching_variant_indices": matches, "matches_cache_consensus": matches == [0]})
    source["source_cache_consistency"]["external_references"] = external
    _, runtime = read_table(project / "time.sim")
    if len(runtime) != 1:
        raise ValueError("One runtime period is required")
    runtime_start = date(int(runtime[0]["yrc_start"]), 1, 1) + timedelta(days=int(runtime[0]["day_start"]) - 1)
    runtime_end = date(int(runtime[0]["yrc_end"]), 1, 1) + timedelta(days=int(runtime[0]["day_end"]) - 1)
    interpolated_dates = [row["interpolated_calendar_date"] for row in source["coverage"]["per_year"]
                          if row["interpolated_calendar_date"] and runtime_start <= date.fromisoformat(row["interpolated_calendar_date"]) <= runtime_end]
    source["runtime_coverage"] = {"start": runtime_start.isoformat(), "end": runtime_end.isoformat(),
                                  "interpolated_dates": interpolated_dates, "interpolated_station_days": len(interpolated_dates) * len(stations),
                                  "evaluation_2019_original_cache_mismatches": next(row["original_cache_mismatches"] for row in source["coverage"]["per_year"] if row["year"] == 2019)}
    benchmark_manifest = json.loads((benchmarks / "manifest.json").read_text())
    if benchmark_manifest["weather_sta_sha256"] != sha256(project / "weather-sta.cli") or benchmark_manifest["stations"] != [{k: s[k] for k in ("name", "lat", "lon")} for s in stations]:
        raise ValueError("Benchmark coordinates or station file differ from the executed project")
    for artifact in benchmark_manifest["artifacts"]:
        if sha256(benchmarks / artifact["file"]) != artifact["sha256"]:
            raise ValueError(f"Benchmark archive changed: {artifact['file']}")
    raw_basin = table(project / "basin_wb_day.txt")
    basin = {period(row): row for row in raw_basin}
    if len(raw_basin) != len(basin) or set(basin) != {d.isoformat() for d in dates}:
        raise ValueError("Basin outputs must cover every day of 2019 exactly once")
    native = {field: monthly_sum(dates, np.array([float(basin[d.isoformat()][field]) for d in dates]))
              for field in ("precip", "et", "pet", "ecanopy", "eplant", "esoil")}
    precipitation = monthly_sum(dates, np.array([row["precip_mm"] for row in forcing]))
    equal_precipitation = monthly_sum(dates, np.array([row["precip_mm"] for row in equal]))
    maximum_precip_error = max(abs(row["precip_mm"] - float(basin[row["date"]]["precip"])) for row in forcing)
    if maximum_precip_error > .0006:
        raise ValueError("Area-weighted precipitation differs from native SWAT+ basin output; audit runtime adjustments")
    benchmark_series, benchmark_metadata = {}, {}
    for name in ("gridmet-etr", "terraclimate-aet", "terraclimate-pet", "terraclimate-ppt"):
        benchmark_series[name], benchmark_metadata[name] = weighted_grid(benchmarks / f"{name}.nc", stations, weights, monthly=name.startswith("terraclimate"))
    daymet = np.zeros((365, 3))
    for station in stations:
        lines = (benchmarks / f"daymet-{station['name']}.csv").read_text().splitlines()
        header = next(i for i, line in enumerate(lines) if line.startswith("year,yday,"))
        records = list(csv.DictReader(io.StringIO("\n".join(lines[header:]))))
        actual_dates = [date(int(row["year"]), 1, 1) + timedelta(days=int(row["yday"]) - 1) for row in records]
        if actual_dates != dates:
            raise ValueError("Daymet dates differ; leap-year policy must be explicit for other years")
        values = np.array([[float(row["prcp (mm/day)"]), (float(row["tmax (deg c)"]) + float(row["tmin (deg c)"])) / 2,
                            float(row["srad (W/m^2)"]) * float(row["dayl (s)"]) / 1e6] for row in records])
        if not np.isfinite(values).all() or (values[:, [0, 2]] < 0).any() or (values[:, 1] < -90).any():
            raise ValueError("Daymet contains missing/invalid values")
        daymet += values * weights.get(station["name"], 0) / sum(weights.values())
    benchmark_series["daymet-pcp"] = monthly_sum(dates, daymet[:, 0])
    weather_diff = {"precip_difference_mm": float(sum(row["precip_mm"] for row in forcing) - daymet[:, 0].sum()),
                    "temperature_mean_bias_c": float(np.mean([row["temp_c"] for row in forcing] - daymet[:, 1])),
                    "solar_energy_difference_mj_m2": float(sum(row["solar_rad_mj"] for row in forcing) - daymet[:, 2].sum()),
                    "gridmet_solar_energy_mj_m2": sum(row["solar_rad_mj"] for row in forcing),
                    "daymet_solar_energy_mj_m2": float(daymet[:, 2].sum()),
                    "daymet_radiation_conversion": "daylight-mean W/m2 * dayl_seconds / 1e6; not *0.0864",
                    "scope": "25 matching forcing points, same HRU area weights; not polygon integration or weather station validation"}
    months = [{"month": month, "swat_precip_mm": native["precip"][month], "swat_et_mm": native["et"][month],
               "swat_pet_mm": native["pet"][month], "swat_soil_evap_mm": native["esoil"][month],
               "swat_plant_et_mm": native["eplant"][month], "swat_canopy_evap_mm": native["ecanopy"][month],
               "area_weighted_precip_mm": precipitation[month], "equal_station_precip_mm": equal_precipitation[month],
               "daymet_precip_mm": benchmark_series["daymet-pcp"][month],
               "gridmet_etr_mm": benchmark_series["gridmet-etr"][month],
               "terraclimate_aet_mm": benchmark_series["terraclimate-aet"][month],
               "terraclimate_pet_mm": benchmark_series["terraclimate-pet"][month],
               "terraclimate_precip_mm": benchmark_series["terraclimate-ppt"][month]} for month in sorted(precipitation)]
    total_keys = [key for key in months[0] if key != "month"]
    annual = {key: sum(row[key] for row in months) for key in total_keys}
    comparisons = []
    for model, reference, classification in (("swat_pet_mm", "gridmet_etr_mm", "SAME_PROVIDER_REFERENCE_ET_CHECK"),
                                            ("swat_pet_mm", "terraclimate_pet_mm", "EXTERNAL_REFERENCE_ET_MODEL_COMPARISON"),
                                            ("swat_et_mm", "terraclimate_aet_mm", "EXTERNAL_ACTUAL_ET_MODEL_COMPARISON")):
        comparisons.append({"model": model, "reference": reference, "classification": classification,
                            "annual_difference_mm": annual[model] - annual[reference],
                            "annual_difference_percent": 100 * (annual[model] / annual[reference] - 1),
                            "monthly_difference_mm": [{"month": row["month"], "difference": row[model] - row[reference]} for row in months]})
    return {"schema_version": SCHEMA_VERSION, "status": "AUDITED", "classification": "DEVELOPMENT_DIAGNOSTIC",
            "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy_version},
            "hypothesis_status": "NOT_EVALUATED", "period": ["2019-01-01", "2019-12-31"], "weather_source": source,
            "input_checksums": {**input_checksums, **{name: sha256(project / name) for name in ("hru.con", "hru-data.hru", "hydrology.hyd", "codes.bsn", "parameters.bsn", "time.sim", "swat_engine_manifest.json")}},
            "output_checksums": {"basin_wb_day.txt": sha256(project / "basin_wb_day.txt")},
            "forcing_aggregation": {"method": "AREA_WEIGHTED_ASSIGNED_HRU_STATIONS", "station_weights_ha": weights,
                "area_km2": sum(weights.values()) / 100, "stations": stations, "hru_count": len(provenance["hru_ids"]),
                "max_daily_precip_error_vs_native_mm": maximum_precip_error,
                "equal_station_annual_precip_mm": annual["equal_station_precip_mm"], "area_weighted_annual_precip_mm": annual["area_weighted_precip_mm"],
                "equal_minus_area_weighted_precip_mm": annual["equal_station_precip_mm"] - annual["area_weighted_precip_mm"],
                "legacy_policy": "Existing playback and summary values preserve their original equal-station metadata; future baseline summaries use HRU areas."},
            "pet": pet_inputs(project), "annual_mm": annual, "monthly": months, "comparisons": comparisons,
            "daymet_weather_comparison": weather_diff,
            "benchmarks": {"manifest": benchmark_manifest, "manifest_sha256": sha256(benchmarks / "manifest.json"), "grid_metadata": benchmark_metadata},
            "limitations": ["External products sampled at assigned forcing points and weighted by HRU areas; these are not polygon-integrated basin estimates.",
                            "TerraClimate V1.1 uses ERA5/WorldClim and a monthly water-balance model with static land cover; AET is not measured ET.",
                            "Daymet uses a different gridded interpolation but can share station inputs with gridMET; statistical independence is not guaranteed.",
                            "No observed ET, flux-tower comparison, satellite ET validation, calibration or H1 test was performed.",
                            "2019 was explored during development and cannot be treated as a held-out test year."],
            "next_action": "Resolve cache conflicts and replace interpolated warmup year-end dates in an isolated forcing variant; compare with preserved reference before PET/ET sensitivity and multi-year calibration/holdout."}

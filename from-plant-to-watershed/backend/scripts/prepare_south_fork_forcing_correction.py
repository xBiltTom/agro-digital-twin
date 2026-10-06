#!/usr/bin/env python3
"""Copy the physical reference and repair only audited 2000--2018 weather.

Uses archived gridMET receipts from the meteorology audit. No downloads,
parameter fitting, new database, or changes to the evaluated 2019 weather.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import numpy as np
from app.services.swat_meteorology_diagnostic import (
    EXPECTED_UNITS, grid, nearest, sha256, station_inputs,
)
from scripts.run_south_fork_baseline_diagnostic import fingerprint


def prepare(project: Path, archive: Path, destination: Path) -> dict:
    project, archive, destination = project.resolve(), archive.resolve(), destination.resolve()
    if destination.exists() or project == destination or project in destination.parents:
        raise ValueError("Choose a new destination outside the preserved source project")
    before = fingerprint(project)
    stations, original, _ = station_inputs(project)
    if len(stations) != 25:
        raise ValueError("This correction requires the audited 25 South Fork stations")
    sources, replacements = {}, {}

    def load(directory, filename, kind, dates):
        root = archive / directory
        manifest = json.loads((root / "manifest.json").read_text())
        if manifest["weather_sta_sha256"] != sha256(project / "weather-sta.cli"):
            raise ValueError("Archive station definitions differ from this project")
        receipt = next(item for item in manifest["artifacts"] if item["file"] == filename)
        path = root / filename
        if sha256(path) != receipt["sha256"]:
            raise ValueError(f"Archive changed: {path}")
        data = grid(path)
        if data["dates"] != dates or data["units"] not in {EXPECTED_UNITS[kind], "m/s" if kind == "vs" else EXPECTED_UNITS[kind]}:
            raise ValueError(f"Unexpected grid dates/units: {path}")
        sources[f"{directory}/{filename}"] = {**receipt, "manifest_sha256": sha256(root / "manifest.json")}
        return data

    def schedule(station, day, extension, values, reason):
        key = (station["name"], day, extension)
        if key in replacements:
            raise ValueError("Duplicate weather intervention")
        replacements[key] = (values, reason)

    for year in (2000, 2004, 2008, 2012, 2016):
        day = date(year, 12, 31)
        data = {kind: load("calendar-edges", f"calendar-{kind}-{year}.nc", kind, [day])
                for kind in EXPECTED_UNITS}
        for station in stations:
            v = {kind: float(nearest(dataset, station)[0][0]) for kind, dataset in data.items()}
            converted = {"pcp": [round(v["pr"], 2)],
                         "tmp": [round(v["tmmx"] - 273.15, 2), round(v["tmmn"] - 273.15, 2)],
                         "slr": [round(v["srad"] * .0864, 2)],
                         "hmd": [round((v["rmin"] + v["rmax"]) / 200, 3)],
                         "wnd": [round(v["vs"], 2)]}
            for extension, values in converted.items():
                schedule(station, day, extension, values, "GRIDMET_ACTUAL_LEAP_YEAR_END")
    for directory, filename, kind, year, name, extension in (
        ("cache-reference-2011", "gridmet-pr-2011.nc", "pr", 2011, "s42522n93585w", "pcp"),
        ("cache-reference-2015-wind", "gridmet-vs-2015.nc", "vs", 2015, "s42480n93450w", "wnd"),
    ):
        dates = [date.fromordinal(date(year, 1, 1).toordinal() + i) for i in range(365)]
        data = load(directory, filename, kind, dates)
        station = next(s for s in stations if s["name"] == name)
        values, _ = nearest(data, station)
        for day, value in zip(dates, values):
            schedule(station, day, extension, [round(float(value), 2)], "GRIDMET_CACHE_CONFLICT_REPLACEMENT")

    shutil.copytree(project, destination)
    changes, changed_files = [], {}
    for station in stations:
        for extension in ("pcp", "tmp", "slr", "hmd", "wnd"):
            path = destination / f"{station['name']}.{extension}"
            lines = path.read_text().splitlines(keepends=True)
            for index in range(3, len(lines)):
                tokens = lines[index].split()
                if not tokens:
                    continue
                year, jday = map(int, tokens[:2])
                day = date.fromordinal(date(year, 1, 1).toordinal() + jday - 1)
                replacement = replacements.pop((station["name"], day, extension), None)
                if replacement is None:
                    continue
                values, reason = replacement
                old = list(map(float, tokens[2:]))
                if old == values:
                    continue
                lines[index] = f"{year:4d} {jday:4d} " + " ".join(f"{v:10.5f}" for v in values) + "  \n"
                changes.append({"file": path.name, "date": day.isoformat(), "before": old, "after": values, "reason": reason})
            content = "".join(lines)
            if content != path.read_text():
                path.write_text(content)
                changed_files[path.name] = {"before": sha256(project / path.name), "after": sha256(path)}
    if replacements:
        raise ValueError("Scheduled dates were absent from the weather files")
    _, corrected, _ = station_inputs(destination)
    for name, weather in original.items():
        indices = [i for i, day in enumerate(weather["dates"]) if day.year >= 2019]
        if not np.array_equal(weather["values"][indices], corrected[name]["values"][indices]):
            raise ValueError("Correction changed weather outside the warm-up")
    files_before = {p.relative_to(project).as_posix(): sha256(p) for p in project.rglob("*") if p.is_file()}
    files_after = {p.relative_to(destination).as_posix(): sha256(p) for p in destination.rglob("*") if p.is_file()}
    differing = {name for name in files_before.keys() | files_after.keys() if files_before.get(name) != files_after.get(name)}
    if differing != set(changed_files) or fingerprint(project) != before:
        raise ValueError("Unexpected input change or modification of the source")
    report = {"schema_version": "south-fork-forcing-correction/v1",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "classification": "CONTROLLED_WARMUP_FORCING_CORRECTION", "hypothesis_status": "NOT_EVALUATED",
              "source_project": str(project), "corrected_project": str(destination),
              "source_project_sha256": before, "corrected_project_sha256": fingerprint(destination),
              "source_unchanged": True, "weather_2019_and_later_identical": True,
              "warmup_years": 19, "changed_files": changed_files, "changed_records": changes,
              "archive_sources": sources, "script_sha256": sha256(Path(__file__)),
              "conversions": {"pcp": "mm, 0.01", "tmp": "K - 273.15, degC, 0.01",
                              "slr": "W/m2 * 0.0864, MJ/m2/day, 0.01",
                              "hmd": "(rmin+rmax)/200, fraction, 0.001", "wnd": "m/s at 10 m, 0.01; engine handles height"},
              "limits": ["Uses the archived retrievals, not a new meteorological validation.",
                         "Unused leap-year ends 2020 and 2024 remain as originally archived."]}
    output = destination.parent / f"{destination.name}-manifest.json"
    if output.exists():
        raise ValueError("Preserve existing correction manifests")
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"manifest": str(output), "changed_files": len(changed_files), "changed_records": len(changes)}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.project, args.archive, args.destination)

#!/usr/bin/env python3
"""Archive public 2019 weather/ET comparisons; no simulation or database writes."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen


def fetch(args):
    if args.output.exists() and (not args.resume_incomplete or (args.output / "manifest.json").exists()):
        raise ValueError("Preserve previous benchmark archives; choose a new directory")
    stations = []
    for line in (args.project / "weather-sta.cli").read_text().splitlines()[2:]:
        tokens = line.split()
        if not tokens:
            continue
        header = (args.project / tokens[2]).read_text().splitlines()[2].split()
        stations.append({"name": tokens[0], "lat": float(header[2]), "lon": float(header[3])})
    if not stations:
        raise ValueError("Direct weather stations are required")
    # Padding ensures the nearest 1/24-degree cell is included at every point.
    box = {"north": max(s["lat"] for s in stations) + .06,
           "south": min(s["lat"] for s in stations) - .06,
           "east": max(s["lon"] for s in stations) + .06,
           "west": min(s["lon"] for s in stations) - .06}
    queries = []
    for station in stations:
        query = {"lat": station["lat"], "lon": station["lon"],
                 "vars": "dayl,prcp,srad,tmax,tmin,vp", "start": "2019-01-01", "end": "2019-12-31"}
        queries.append((f"daymet-{station['name']}.csv",
                        "https://daymet.ornl.gov/single-pixel/api/data?" + urlencode(query)))
    for name, dataset, variable in (
        ("gridmet-etr", "agg_met_etr_1979_CurrentYear_CONUS", "daily_mean_reference_evapotranspiration_alfalfa"),
        ("terraclimate-aet", "agg_terraclimate_aet_1950_CurrentYear_GLOBE", "aet"),
        ("terraclimate-pet", "agg_terraclimate_pet_1950_CurrentYear_GLOBE", "pet"),
        ("terraclimate-ppt", "agg_terraclimate_ppt_1950_CurrentYear_GLOBE", "ppt"),
    ):
        base = f"https://thredds.northwestknowledge.net/thredds/ncss/grid/{dataset}.nc"
        query = {**box, "var": variable, "time_start": "2019-01-01T00:00:00Z",
                 "time_end": "2019-12-31T23:59:59Z", "accept": "netcdf", "addLatLon": "true"}
        queries.extend(((name + ".nc", base + "?" + urlencode(query)),
                        (name + "-dataset.xml", base + "/dataset.xml")))
    if args.calendar_edges:
        queries = []
        for kind, variable in (("pr", "precipitation_amount"), ("tmmx", "daily_maximum_temperature"),
                               ("tmmn", "daily_minimum_temperature"), ("srad", "daily_mean_shortwave_radiation_at_surface"),
                               ("rmin", "daily_minimum_relative_humidity"), ("rmax", "daily_maximum_relative_humidity"),
                               ("vs", "daily_mean_wind_speed")):
            base = f"https://thredds.northwestknowledge.net/thredds/ncss/grid/agg_met_{kind}_1979_CurrentYear_CONUS.nc"
            for year in range(2000, 2026, 4):
                query = {**box, "var": variable, "time_start": f"{year}-12-31T00:00:00Z",
                         "time_end": f"{year}-12-31T23:59:59Z", "accept": "netcdf", "addLatLon": "true"}
                queries.append((f"calendar-{kind}-{year}.nc", base + "?" + urlencode(query)))
    if args.gridmet_precip_year is not None:
        year = args.gridmet_precip_year
        base = "https://thredds.northwestknowledge.net/thredds/ncss/grid/agg_met_pr_1979_CurrentYear_CONUS.nc"
        query = {**box, "var": "precipitation_amount", "time_start": f"{year}-01-01T00:00:00Z",
                 "time_end": f"{year}-12-31T23:59:59Z", "accept": "netcdf", "addLatLon": "true"}
        queries = [(f"gridmet-pr-{year}.nc", base + "?" + urlencode(query)), ("gridmet-pr-dataset.xml", base + "/dataset.xml")]
    if args.gridmet_wind_year is not None:
        year = args.gridmet_wind_year
        base = "https://thredds.northwestknowledge.net/thredds/ncss/grid/agg_met_vs_1979_CurrentYear_CONUS.nc"
        query = {**box, "var": "daily_mean_wind_speed", "time_start": f"{year}-01-01T00:00:00Z",
                 "time_end": f"{year}-12-31T23:59:59Z", "accept": "netcdf", "addLatLon": "true"}
        queries = [(f"gridmet-vs-{year}.nc", base + "?" + urlencode(query)), ("gridmet-vs-dataset.xml", base + "/dataset.xml")]
    args.output.mkdir(parents=True, exist_ok=args.resume_incomplete)

    def download(item):
        name, url = item
        path = args.output / name
        receipt = args.output / (name + ".receipt.json")
        if path.exists():
            body = path.read_bytes()
            if receipt.exists():
                stored = json.loads(receipt.read_text())
                if stored["requested_url"] != url or stored["sha256"] != hashlib.sha256(body).hexdigest():
                    raise ValueError(f"Partial download receipt changed: {name}")
                return stored
            # Earlier interrupted transfers may predate receipt support. Keep
            # their bytes, explicitly mark the missing HTTP receipt and bind
            # only the reconstructed request and local file timestamp.
            metadata = {"content_type": None, "last_modified": None, "etag": None, "resolved_url": None,
                        "retrieved_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                        "retrieved_at_basis": "LOCAL_PARTIAL_DOWNLOAD_FILE_MTIME", "http_receipt_available": False}
        else:
            for attempt in range(3):
                try:
                    with urlopen(Request(url, headers={"User-Agent": "SouthForkResearchWeatherAudit/1.0"}), timeout=30) as response:
                        body = response.read()
                        metadata = {"content_type": response.headers.get("Content-Type"),
                                    "last_modified": response.headers.get("Last-Modified"),
                                    "etag": response.headers.get("ETag"), "resolved_url": response.url,
                                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                    "retrieved_at_basis": "HTTP_TRANSFER_COMPLETED", "http_receipt_available": True}
                    break
                except (URLError, TimeoutError):
                    if attempt == 2:
                        raise
        if name.endswith(".nc") and not body.startswith(b"CDF"):
            raise ValueError(f"Expected classic NetCDF: {name}")
        if not path.exists():
            path.write_bytes(body)
        result = {"file": name, "requested_url": url, **metadata, "bytes": len(body),
                  "sha256": hashlib.sha256(body).hexdigest()}
        receipt.write_text(json.dumps(result, indent=2) + "\n")
        return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        artifacts = list(pool.map(download, queries))
    reference_year = args.gridmet_precip_year if args.gridmet_precip_year is not None else args.gridmet_wind_year
    manifest = {"schema_version": "south-fork-weather-benchmarks/v1", "year": reference_year if reference_year is not None else None if args.calendar_edges else 2019,
                "classification": "GRIDMET_CACHE_CONFLICT_REFERENCE_CHECK" if reference_year is not None else "GRIDMET_CALENDAR_EDGE_PROVENANCE_CHECK" if args.calendar_edges else "EXTERNAL_MODEL_COMPARISON_NOT_OBSERVATIONAL_ET_VALIDATION",
                "stations": stations, "bounding_box": box, "artifacts": artifacts,
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "weather_sta_sha256": hashlib.sha256((args.project / "weather-sta.cli").read_bytes()).hexdigest()}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"archive": str(args.output), "artifacts": len(artifacts)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calendar-edges", action="store_true", help="Fetch Dec 31 in leap years omitted from the builder's original cache")
    parser.add_argument("--gridmet-precip-year", type=int, choices=range(2000, 2026), help="Archive a new full-year precipitation subset to check source cache conflicts")
    parser.add_argument("--gridmet-wind-year", type=int, choices=range(2000, 2026), help="Archive a new full-year wind subset to check source cache conflicts")
    parser.add_argument("--resume-incomplete", action="store_true", help="Preserve partial downloads and resume only an archive without a completed manifest")
    args = parser.parse_args()
    if sum((args.calendar_edges, args.gridmet_precip_year is not None, args.gridmet_wind_year is not None)) > 1:
        parser.error("Choose calendar edges or one full-year variable reference")
    fetch(args)

#!/usr/bin/env python3
"""Export the soil, crop, drainage and aquifer evidence of the corrected run."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.swat_baseline_diagnostic import inspect_project, read_table, routing_rows
from app.services.swat_meteorology_diagnostic import sha256
from app.services.swat_water_path import period, table
from app.services.swat_research_engine import SOURCE_COMMIT


def review(comparison: Path, run_id: str, source: Path) -> dict:
    report = json.loads(comparison.read_text())
    run = report["runs"][run_id]
    project = Path(run["workspace"])
    if run["source_build"]["source"]["commit"] != SOURCE_COMMIT:
        raise ValueError("Review requires the pinned research engine")
    for name, expected in run["input_checksums"].items():
        if sha256(project / name) != expected:
            raise ValueError(f"Physical input differs from the persisted run: {name}")
    for name, expected in run["water_path"]["output_checksums"].items():
        if sha256(project / name) != expected:
            raise ValueError(f"Physical output differs from the water-path audit: {name}")
    area = {lead[0]: float(lead[3]) for lead, _ in routing_rows(project / "hru.con")}
    total = sum(area.values())
    _, hrus = read_table(project / "hru-data.hru")
    _, hydrology = read_table(project / "hydrology.hyd")
    hyd = {row["name"]: row for row in hydrology}
    drainage = inspect_project(project)
    _, landuses = read_table(project / "landuse.lum")
    tiles = {row["name"]: row["tile"] for row in landuses}
    lines = (project / "soils.sol").read_text().splitlines()
    soils, index = {}, 2
    while index < len(lines):
        values = lines[index].split()
        if not values:
            index += 1
            continue
        name, layers, group, depth = values[:4]
        profile = []
        previous = 0.
        for line in lines[index + 1:index + 1 + int(layers)]:
            tokens = list(map(float, line.split()))
            bottom, bd, awc, conductivity, carbon, clay, silt, sand = tokens[:8]
            if bottom <= previous or not (0 < awc < .8) or conductivity <= 0 or abs(clay + silt + sand - 100) > .1:
                raise ValueError(f"Invalid soil layer: {name}")
            profile.append({"bottom_mm": bottom, "thickness_mm": bottom - previous,
                            "bd_g_cm3": bd, "awc_mm_mm": awc, "ksat_mm_h": conductivity,
                            "clay_percent": clay, "silt_percent": silt, "sand_percent": sand})
            previous = bottom
        if len(profile) != int(layers) or previous != float(depth) or name in soils:
            raise ValueError(f"Invalid soil profile: {name}")
        soils[name] = {"name": name, "group": group, "depth_mm": float(depth), "layers": profile,
                       "profile_awc_mm": sum(layer["awc_mm_mm"] * layer["thickness_mm"] for layer in profile)}
        index += 1 + int(layers)
    soil_area, used_hyd, tiled_area = defaultdict(float), [], 0.
    for hru in hrus:
        soil_area[hru["soil"]] += area[hru["id"]]
        tiled = tiles[hru["lu_mgt"]] != "null"
        if tiled:
            tiled_area += area[hru["id"]]
        row = hyd[hru["hydro"]]
        # topohyd_init sets perco=0.1 for tiled HRUs before computing perco_lim.
        perco = .1 if tiled else float(row["perco"])
        limit = min(1., math.exp(-(1.0052 * math.log(-math.log(perco - 1e-6)) + 5.6862)))
        used_hyd.append({"hru": hru["id"], "area_ha": area[hru["id"]], "tile_active": tiled,
                         "input_perco": float(row["perco"]), "initialized_perco": perco,
                         "initialized_perco_lim": limit,
                         **{key: float(row[key]) for key in ("esco", "epco", "pet_co", "latq_co")}})
    basin = table(project / "basin_wb_day.txt")
    fields = ("precip", "et", "pet", "esoil", "eplant", "ecanopy", "perc", "qtile", "surq_cont", "latq")
    months = [{"month": month, **{key: sum(float(row[key]) for row in basin if int(row["mon"]) == month) for key in fields}}
              for month in range(1, 13)]
    wb = {(period(row), row["unit"]): row for row in table(project / "hru_wb_day.txt")}
    pw = {(period(row), row["unit"]): row for row in table(project / "hru_pw_day.txt")}
    expected = {(date.fromordinal(date(2019, 1, 1).toordinal() + day).isoformat(), unit) for day in range(365) for unit in area}
    if set(wb) != expected or set(pw) != expected:
        raise ValueError("Require 365 paired HRU water and plant states")
    low_lai_esoil, snow_esoil, residue_low_lai = 0., 0., 0.
    low_lai_area_days = 0.
    hru_terms = defaultdict(lambda: defaultdict(float))
    for key, row in wb.items():
        weight = area[key[1]] / total
        esoil = float(row["esoil"])
        if float(pw[key]["lai"]) <= .1:
            low_lai_esoil += esoil * weight
            low_lai_area_days += weight
            residue_low_lai += float(pw[key]["residue"]) * weight
        if float(row["sno_init"]) > 0:
            snow_esoil += esoil * weight
        for field in fields:
            hru_terms[key[1]][field] += float(row[field])
    events = []
    for line in (project / "mgt_out.txt").read_text().splitlines()[3:]:
        tokens = line.split()
        if len(tokens) >= 6 and tokens[1] == "2019" and tokens[5] in {"PLANT", "HARV/KILL"}:
            events.append({"hru": tokens[0], "date": date(2019, int(tokens[2]), int(tokens[3])).isoformat(),
                           "crop": tokens[4], "operation": tokens[5]})
    aqu_area = {lead[0]: float(lead[3]) for lead, _ in routing_rows(project / "aquifer.con")}
    aqu_names = {lead[0]: lead[1] for lead, _ in routing_rows(project / "aquifer.con")}
    aqu_rows = table(project / "aquifer_day.txt")
    aquifers = {}
    for label, deep in (("shallow", False), ("deep", True)):
        units = {unit for unit, name in aqu_names.items() if ("deep" in name) == deep}
        subset = [row for row in aqu_rows if row["unit"] in units]
        if len(subset) != len(units) * 365 or abs(sum(aqu_area[u] for u in units) - total) > .01:
            raise ValueError("Aquifer count or area does not match HRU coverage")
        aquifers[label] = {"units": len(units), "area_ha": sum(aqu_area[u] for u in units),
            "annual_terms_basin_mm": {key: sum(float(row[key]) * aqu_area[row["unit"]] / total for row in subset)
                                      for key in ("flo", "rchrg", "seep", "revap")},
            "jan2_dec31_storage_change_basin_mm": sum((float(row["stor"]) * (1 if period(row) == "2019-12-31" else -1)) * aqu_area[row["unit"]] / total
                for row in subset if period(row) in {"2019-01-01", "2019-12-31"}),
            "zero_flow_unit_days": sum(float(row["flo"]) == 0 for row in subset)}
    source_files = ("topohyd_init.f90", "swr_percmicro.f90", "swr_percmain.f90", "et_act.f90", "et_pot.f90", "hru_control.f90", "aqu_1d_control.f90", "cal_parm_select.f90")
    input_files = ("hru.con", "hru-data.hru", "soils.sol", "hydrology.hyd", "landuse.lum", "tiledrain.str", "rout_unit.con", "aquifer.con", "aquifer.aqu", "hyd-sed-lte.cha", "codes.bsn")
    output_files = ("basin_wb_day.txt", "hru_wb_day.txt", "hru_pw_day.txt", "aquifer_day.txt", "mgt_out.txt")
    return {"schema_version": "south-fork-physical-process-review/v1", "simulation_id": run_id,
        "comparison_sha256": sha256(comparison), "classification": "DEVELOPMENT_DIAGNOSTIC", "hypothesis_status": "NOT_EVALUATED",
        "area_ha": total, "monthly_native_terms_mm": months,
        "soils": {"profiles": [{**soils[name], "used_area_ha": value} for name, value in sorted(soil_area.items())],
                  "area_weighted_profile_awc_mm": sum(soils[name]["profile_awc_mm"] * value / total for name, value in soil_area.items()),
                  "note": "Input gNATSGO profiles pass layer checks; field hydraulic properties are not validated."},
        "hydrology": used_hyd, "drainage": {"inspection": drainage, "active_area_ha": tiled_area,
                  "active_area_percent": 100 * tiled_area / total, "hru_annual_terms_mm": dict(hru_terms),
                  "scope": "Fixed corn-landuse experiment, not reconstructed historical tile coverage."},
        "et_context": {"esoil_on_lai_le_0_1_days_basin_mm": low_lai_esoil,
                       "esoil_on_snow_present_days_basin_mm": snow_esoil,
                       "low_lai_area_weighted_days": low_lai_area_days,
                       "mean_residue_on_low_lai_days_kg_ha": residue_low_lai / low_lai_area_days,
                       "note": "esoil includes snow and ponded-water evaporation. Snow-present day totals do not isolate sublimation; categories overlap."},
        "management_events_2019": events, "aquifers": aquifers,
        "input_sha256": {name: sha256(project / name) for name in input_files},
        "output_sha256": {name: sha256(project / name) for name in output_files},
        "source_commit": SOURCE_COMMIT, "source_sha256": {name: sha256(source / name) for name in source_files},
        "script_sha256": sha256(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--simulation-id", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve previous process reviews")
    report = review(args.comparison, args.simulation_id, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("simulation_id", "area_ha", "et_context", "aquifers")}))

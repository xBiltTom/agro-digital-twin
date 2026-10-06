"""Trace native SWAT+ volumes and physical/bypass channel accounting.

hydin/hydout/ru write hyd_output.flo (m3), despite their m3/s header in this
release. command.f90 preserves total bypass flow internally but prints ht1,
the last incoming connection. Only verified bypass channels are normalized.
Physical channels use reported m3/s, with partial storage/loss accounting.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
import hashlib
import math
from pathlib import Path

from app.services.swat_baseline_diagnostic import read_table, routing_rows

ENGINE_VERSION = "61.0.2.61"
CON_TYPES = {"hru.con": "hru", "rout_unit.con": "ru", "aquifer.con": "aqu",
             "chandeg.con": "chandeg", "reservoir.con": "res", "recall.con": "rec",
             "exco.con": "exco", "delratio.con": "dr", "outlet.con": "outlet"}
TYPE_ALIASES = {"sdc": "chandeg", "cha": "chan", "exc": "exco", "out": "outlet"}


def table(path: Path) -> list[dict[str, str]]:
    from app.services.swat_plus_parser import SwatOutputParser
    headers, _, rows = SwatOutputParser._table(path)
    return [dict(zip(headers, row)) for row in rows]


def period(row: dict[str, str]) -> str:
    return date(int(row["yr"]), int(row["mon"]), int(row["day"])).isoformat()


def printed_half_step(token: str) -> float:
    """Half of the final printed digit, preserving scientific-notation precision."""
    return float(Decimal(10) ** Decimal(token).as_tuple().exponent) / 2


def channel_geometry(project: Path) -> dict[str, dict]:
    required = ("chandeg.con", "channel-lte.cha", "hyd-sed-lte.cha")
    if not all((project / name).is_file() for name in required):
        return {}
    _, parameters = read_table(project / "channel-lte.cha")
    params = {row["id"]: row for row in parameters}
    lines = (project / "hyd-sed-lte.cha").read_text().splitlines()
    header = lines[1].split()
    hyd = {}
    for line in lines[2:]:
        if not line.strip():
            continue
        values = line.split()
        # Editor may omit only the optional trailing description.
        if len(values) < len(header) - int(header[-1] == "description"):
            raise ValueError("Incomplete hyd-sed-lte.cha parameter row")
        row = dict(zip(header, values))
        hyd[row["name"]] = row
    channels = {}
    for leading, edges in routing_rows(project / "chandeg.con"):
        length = float(hyd[params[leading[7]]["cha_hyd"]]["len"])
        if not math.isfinite(length) or length < 0:
            raise ValueError("Invalid channel length")
        channels[leading[0]] = {"name": leading[1], "gis_id": leading[2],
                                "length_km": length, "terminal": not edges}
    return channels


def bypass_channels(project: Path) -> dict[str, dict]:
    return {unit: value for unit, value in channel_geometry(project).items() if value["length_km"] <= 0.001}


def incoming_edges(project: Path) -> dict[str, set[tuple]]:
    incoming = defaultdict(set)
    for name, kind in CON_TYPES.items():
        if not (project / name).is_file():
            continue
        for leading, edges in routing_rows(project / name):
            for target, identifier, hyd_type, fraction in edges:
                if target != "sdc":
                    continue
                key = (kind, leading[0], hyd_type, float(fraction))
                if key in incoming[identifier]:
                    raise ValueError("Duplicate channel input connection")
                incoming[identifier].add(key)
    return dict(incoming)


def bypass_flow_series(project: Path) -> tuple[dict[tuple[str, str], float], dict]:
    channels = bypass_channels(project)
    path = project / "hydin_day.txt"
    if not channels or not path.is_file():
        return {}, {"status": "NOT_AVAILABLE", "reason": "Daily incoming hydrographs or bypass topology unavailable"}
    with path.open() as handle:
        title = handle.readline()
    if f"Rev 2026.{ENGINE_VERSION}" not in title:
        return {}, {"status": "NOT_APPLICABLE", "reason": "Unit/report override is restricted to the audited SWAT+ release"}
    expected = incoming_edges(project)
    by_name = {value["name"]: identifier for identifier, value in channels.items()}
    grouped = defaultdict(list)
    days = set()
    for row in table(path):
        days.add(period(row))
        if row["type"] == "chandeg" and row["name"] in by_name:
            grouped[(period(row), by_name[row["name"]])].append(row)
    flows = {}
    for key, rows in grouped.items():
        actual = [(TYPE_ALIASES.get(row["objtyp"], row["objtyp"]), row["typ_no"],
                   row["hyd_typ"], float(row["fraction"])) for row in rows]
        if len(actual) != len(set(actual)) or set(actual) != expected.get(key[1], set()):
            raise ValueError(f"Incomplete/ambiguous incoming hydrographs for {key}")
        values = [float(row["flo"]) for row in rows]
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("Invalid incoming water volume")
        # Each connection's fraction is already applied by the engine.
        flows[key] = sum(values) / 86400
    for day in days:
        for unit in channels:
            if not expected.get(unit):
                # Verified empty topology means hin=hz in command.f90; this
                # is distinct from missing output for an expected connection.
                flows[(day, unit)] = 0.0
    return flows, {"status": "AVAILABLE", "engine_version": ENGINE_VERSION,
                   "channels": channels, "native_unit": "m3 per daily connection",
                   "printed_unit": "m^3/s (incorrect in this release)",
                   "normalization": "sum(fraction-applied incoming volumes) / 86400 for verified bypass channels",
                   "source": path.name, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "reference": f"https://github.com/swat-model/swatplus/blob/{ENGINE_VERSION}/src/command.f90"}


def normalize_bypass_channels(project: Path, rows: list[dict], frequency: str) -> tuple[list[dict], dict]:
    channels = bypass_channels(project)
    suffix = {"DAILY": "day", "MONTHLY": "mon", "ANNUAL": "yr"}[frequency]
    channel_path = project / f"channel_sd_{suffix}.txt"
    if not channels or not channel_path.is_file():
        return rows, {"status": "NOT_APPLICABLE", "reason": "Audited bypass output not present"}
    with channel_path.open() as handle:
        title = handle.readline()
    if f"Rev 2026.{ENGINE_VERSION}" not in title:
        return rows, {"status": "NOT_APPLICABLE", "reason": "Channel release is outside the audited version"}
    def unavailable(reason: str):
        for row in rows:
            if str(row.get("_unit")) in channels:
                row["streamflow_reported_m3s"] = row.get("streamflow_m3s")
                row["channel_inflow_reported_m3s"] = row.get("channel_inflow_m3s")
                row["streamflow_m3s"] = None
                row["channel_inflow_m3s"] = None
        return rows, {"status": "AFFECTED_UNAVAILABLE", "reason": reason}
    if frequency != "DAILY":
        return unavailable("Known bypass report bug; normalize through a daily run with incoming hydrographs")
    flows, audit = bypass_flow_series(project)
    if audit["status"] != "AVAILABLE":
        return unavailable(audit["reason"])
    count = 0
    for row in rows:
        unit = str(row.get("_unit"))
        if unit not in audit["channels"]:
            continue
        key = (row["period"], unit)
        if key not in flows:
            raise ValueError(f"Missing bypass channel flow: {key}")
        row["streamflow_reported_m3s"] = row.get("streamflow_m3s")
        row["channel_inflow_reported_m3s"] = row.get("channel_inflow_m3s")
        row["streamflow_m3s"] = flows[key]
        row["channel_inflow_m3s"] = flows[key]
        row["streamflow_source"] = "SWAT+ hydin_day.txt; audited artificial-channel bypass; native m3 / 86400"
        count += 1
    return rows, {**audit, "normalized_channel_rows": count}


def diagnose_water_path(project: Path, *, outlet_gis_id: str, start: date, end: date,
                        reference_area_km2: float | None = None) -> dict:
    names = ("basin_wb_day.txt", "hru_wb_day.txt", "aquifer_day.txt", "hydin_day.txt", "hydout_day.txt", "channel_sd_day.txt")
    if not all((project / name).is_file() for name in names):
        return {"status": "NOT_AVAILABLE", "reason": "Daily soil, aquifer and connection outputs are required"}
    channels = channel_geometry(project)
    if not channels:
        return {"status": "NOT_AVAILABLE", "reason": "Channel geometry unavailable"}
    bypass = bypass_channels(project)
    physical = not bypass
    if bypass and len(bypass) != len(channels):
        return {"status": "NOT_AVAILABLE", "reason": "Mixed physical/bypass network accounting is not yet audited"}
    for name in names:
        with (project / name).open() as handle:
            if f"Rev 2026.{ENGINE_VERSION}" not in handle.readline():
                return {"status": "NOT_APPLICABLE", "reason": "Volume accounting is restricted to the audited release"}
    if physical:
        _, codes = read_table(project / "codes.bsn")
        if len(codes) != 1 or codes[0].get("gwflow") != "0" or codes[0].get("i_fpwet") != "0":
            return {"status": "NOT_AVAILABLE", "reason": "Physical trace does not account for gwflow or floodplain wetlands"}
        audit = {"status": "NOT_APPLICABLE", "engine_version": ENGINE_VERSION,
            "reason": "Physical channel outputs use the engine's m3/s conversion; bypass correction is unnecessary",
            "source": "channel_sd_day.txt"}
        flows = {}
    else:
        flows, audit = bypass_flow_series(project)
        if audit["status"] != "AVAILABLE":
            return audit
    outlets = [unit for unit, value in channels.items() if value["gis_id"] == outlet_gis_id]
    if len(outlets) != 1 or not channels[outlets[0]]["terminal"] or len([v for v in channels.values() if v["terminal"]]) != 1:
        return {"status": "NOT_AVAILABLE", "reason": "Trace currently requires one verified terminal outlet"}
    for _, edges in routing_rows(project / "chandeg.con"):
        if edges and (len(edges) != 1 or edges[0][0] != "sdc" or edges[0][1] not in channels or edges[0][2] != "tot" or float(edges[0][3]) != 1):
            return {"status": "NOT_AVAILABLE", "reason": "Trace requires one full-fraction total outflow per nonterminal channel"}
    if end <= start:
        return {"status": "NOT_AVAILABLE", "reason": "Storage accounting requires at least two days"}
    lo, hi = start.isoformat(), end.isoformat()
    tables = {name: [row for row in table(project / name) if lo <= period(row) <= hi] for name in names}
    days = {period(row) for row in tables["basin_wb_day.txt"]}
    if len(tables["basin_wb_day.txt"]) != len(days):
        raise ValueError("Duplicate daily basin states")
    channel_rows = {}
    for row in tables["channel_sd_day.txt"]:
        key = (period(row), row["unit"])
        if key in channel_rows or row["unit"] not in channels or row["gis_id"] != channels[row["unit"]]["gis_id"]:
            raise ValueError("Duplicate or mismatched channel output")
        channel_rows[key] = row
        if physical:
            if any(not math.isfinite(float(row[field])) or float(row[field]) < 0 for field in
                   ("evap", "seep", "precip", "flo_stor", "flo_in")):
                raise ValueError("Invalid physical channel flux/storage")
            value = float(row["flo_out"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("Invalid physical channel flow")
            flows[key] = value
    if set(channel_rows) != {(day, unit) for day in days for unit in channels}:
        raise ValueError("Incomplete daily channel output coverage")
    if len(days) != (end - start).days + 1 or any((day, unit) not in flows for day in days for unit in channels):
        raise ValueError("Water trace has incomplete daily/channel coverage")
    hru_areas = {lead[0]: float(lead[3]) for lead, _ in routing_rows(project / "hru.con")}
    aqu_areas = {lead[0]: float(lead[3]) for lead, _ in routing_rows(project / "aquifer.con")}
    area_ha = sum(hru_areas.values())
    incoming = tables["hydin_day.txt"]
    expected = incoming_edges(project)
    by_name = {value["name"]: unit for unit, value in channels.items()}
    grouped_in = defaultdict(list)
    for row in incoming:
        if row["type"] == "chandeg":
            if row["name"] not in by_name:
                raise ValueError("Unknown incoming channel name")
            grouped_in[(period(row), by_name[row["name"]])].append(row)
    input_errors, input_excess = [], []
    for day in days:
        for unit in channels:
            rows = grouped_in[(day, unit)]
            actual = [(TYPE_ALIASES.get(row["objtyp"], row["objtyp"]), row["typ_no"],
                       row["hyd_typ"], float(row["fraction"])) for row in rows]
            if len(actual) != len(set(actual)) or set(actual) != expected.get(unit, set()):
                raise ValueError(f"Incomplete/ambiguous incoming hydrographs for {(day, unit)}")
            volumes = [float(row["flo"]) for row in rows]
            if any(not math.isfinite(value) or value < 0 for value in volumes):
                raise ValueError("Invalid incoming volume")
            if physical:
                error = abs(sum(volumes) - float(channel_rows[(day, unit)]["flo_in"]) * 86400)
                bound = sum(printed_half_step(row["flo"]) for row in rows) + printed_half_step(channel_rows[(day, unit)]["flo_in"]) * 86400
                input_errors.append(error)
                input_excess.append(max(0, error - bound))
    channel_inputs = [row for row in incoming if row["type"] == "chandeg" and row["objtyp"] not in {"chandeg", "sdc"}]
    direct = sum(float(row["flo"]) for row in channel_inputs)
    outlet = sum(flows[(day, outlets[0])] * 86400 for day in days)
    reported = sum(float(row["flo_out"]) * 86400 for row in tables["channel_sd_day.txt"] if row["gis_id"] == outlet_gis_id)
    # Check every nonterminal channel against its actual outgoing connection,
    # not against the affected morphology/organic-matter print tables.
    output, output_precision = {}, {}
    for row in tables["hydout_day.txt"]:
        if row["type"] != "chandeg":
            continue
        key = (period(row), row["name"])
        if key in output or row["hyd_typ"] != "tot" or float(row["fraction"]) != 1:
            raise ValueError("Unexpected outgoing channel hydrograph")
        value = float(row["flo"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("Invalid outgoing channel volume")
        output[key] = value
        output_precision[key] = printed_half_step(row["flo"])
    if set(output) != {(day, info["name"]) for day in days for info in channels.values() if not info["terminal"]}:
        raise ValueError("Incomplete outgoing channel connection coverage")
    errors = [abs(flows[(day, unit)] * 86400 - output[(day, info["name"])])
              for day in days for unit, info in channels.items() if not info["terminal"]]
    output_excess = [max(0, abs(flows[(day, unit)] * 86400 - output[(day, info["name"])]) -
                        printed_half_step(channel_rows[(day, unit)]["flo_out"]) * 86400 - output_precision[(day, info["name"])])
                     for day in days for unit, info in channels.items() if physical and not info["terminal"]]
    grouped_aqu = defaultdict(list)
    for row in tables["aquifer_day.txt"]:
        grouped_aqu[row["unit"]].append(row)
    if set(grouped_aqu) != set(aqu_areas) or any(len(rows) != len(days) or {period(row) for row in rows} != days for rows in grouped_aqu.values()):
        raise ValueError("Incomplete aquifer coverage")
    for rows in grouped_aqu.values():
        rows.sort(key=period)
    # Storage is the reported end-of-day state: use Jan 2--Dec 31 for this
    # catchment accounting; no unreported Jan 1 initial aquifer state is invented.
    basin = sorted(tables["basin_wb_day.txt"], key=period)
    first, last = basin[0], basin[-1]
    accounting = basin[1:]
    window_days = {period(row) for row in accounting}
    channel_window = [row for row in tables["channel_sd_day.txt"] if period(row) in window_days]
    channel_evap = sum(float(row["evap"]) for row in channel_window) if physical else 0.0
    channel_seep = sum(float(row["seep"]) for row in channel_window) if physical else 0.0
    channel_precip = sum(float(row["precip"]) for row in channel_window) if physical else 0.0
    channel_delta = sum(float(channel_rows[(hi, unit)]["flo_stor"]) -
        float(channel_rows[(lo, unit)]["flo_stor"]) for unit in channels) if physical else 0.0
    scale = area_ha * 10
    aq_delta = sum((float(rows[-1]["stor"]) - float(rows[0]["stor"])) * aqu_areas[unit] * 10 for unit, rows in grouped_aqu.items())
    revap = sum(float(row["revap"]) * aqu_areas[unit] * 10 for unit, rows in grouped_aqu.items() for row in rows[1:])
    q_window = sum(flows[(period(row), outlets[0])] * 86400 for row in accounting)
    soil_delta = (float(last["sw_final"]) - float(first["sw_final"])) * scale
    snow_delta = (float(last["sno_final"]) - float(first["sno_final"])) * scale
    lag_delta = sum(float(last[k]) - float(first[k]) for k in ("lagsurf", "laglatq", "lagsatex")) * scale
    p_volume = sum(float(row["precip"]) for row in accounting) * scale
    et_volume = sum(float(row["et"]) for row in accounting) * scale
    residual = p_volume + channel_precip - et_volume - revap - q_window - soil_delta - snow_delta - aq_delta - lag_delta - channel_evap - channel_seep - channel_delta
    totals = {k: sum(float(row[k]) for row in basin) for k in ("precip", "et", "eplant", "esoil", "ecanopy", "pet", "perc", "qtile")}
    by_component = {kind: sum(float(row["flo"]) for row in channel_inputs if row["objtyp"] == "ru" and row["hyd_typ"] == kind)
                    for kind in ("sur", "lat", "til")}
    aqu_flow = sum(float(row["flo"]) for row in channel_inputs if row["objtyp"] == "aqu")
    direct_window = sum(float(row["flo"]) for row in channel_inputs if period(row) in window_days)
    network_residual = direct_window + channel_precip - q_window - channel_evap - channel_seep - channel_delta if physical else direct-outlet
    limitation = ("Floodplain storage is absent from channel_sd (flo_stor writes only ch_stor); canopy storage and independent unrounded states unavailable. "
                  "The physical network and catchment accounting remain partial." if physical else
                  "Canopy storage and independent unrounded state diagnostics unavailable; residual is not a full physical validation.")
    return {"schema_version": "swat-water-path/v2" if physical else "swat-water-path/v1", "status": "DIAGNOSTIC_AVAILABLE",
            "routing_mode": "PHYSICAL_CHANNEL_ROUTING" if physical else "ARTIFICIAL_BYPASS",
            "geometry": {"channel_count": len(channels), "bypass_channel_count": len(bypass),
                "total_length_km": sum(info["length_km"] for info in channels.values()),
                "min_length_km": min(info["length_km"] for info in channels.values()),
                "max_length_km": max(info["length_km"] for info in channels.values())},
            "evaluation": [lo, hi], "outlet_gis_id": outlet_gis_id, "area_km2": area_ha / 100,
            "reference_area_km2": reference_area_km2,
            "area_difference_percent": 100 * (area_ha / 100 / reference_area_km2 - 1) if reference_area_km2 else None,
            "network": {"status": "PARTIAL_ACCOUNTING" if physical else "CLOSED" if abs(direct-outlet)/max(direct,1) < 1e-5 else "RESIDUAL",
                "direct_inputs_m3": direct, "hru_components_m3": by_component, "aquifer_to_channel_m3": aqu_flow,
                "outlet_volume_m3": outlet, "reported_outlet_volume_m3": reported,
                "reporting_difference_m3": outlet-reported, "residual_m3": network_residual,
                "relative_residual": network_residual/max(direct_window if physical else direct,1),
                "max_channel_edge_difference_m3": max(errors, default=0),
                **({"evaluation": [period(accounting[0]), hi], "direct_inputs_window_m3": direct_window,
                    "outlet_window_m3": q_window, "channel_evaporation_m3": channel_evap,
                    "channel_seepage_m3": channel_seep, "channel_precipitation_m3": channel_precip,
                    "channel_storage_change_m3": channel_delta, "floodplain_storage_change_m3": None,
                    "annual_input_outlet_difference_m3": direct-outlet,
                    "max_channel_inflow_report_difference_m3": max(input_errors, default=0),
                    "max_inflow_difference_beyond_print_rounding_m3": max(input_excess, default=0),
                    "max_outflow_difference_beyond_print_rounding_m3": max(output_excess, default=0),
                    "rounding_interpretation": "Half-step intervals of printed incoming volumes and daily m3/s reports; not a model accuracy tolerance.",
                    "limitation": limitation} if physical else {})},
            "catchment_accounting": {"status": "PARTIAL_ACCOUNTING", "evaluation": [period(accounting[0]), hi],
                "precip_m3": p_volume, "hru_et_m3": et_volume, "aquifer_revap_m3": revap,
                "outlet_m3": q_window, "soil_storage_change_m3": soil_delta, "snow_storage_change_m3": snow_delta,
                "aquifer_storage_change_m3": aq_delta, "routing_lag_storage_change_m3": lag_delta,
                **({"channel_evaporation_m3": channel_evap, "channel_seepage_m3": channel_seep,
                    "channel_precipitation_m3": channel_precip, "channel_storage_change_m3": channel_delta,
                    "floodplain_storage_change_m3": None} if physical else {}),
                "residual_m3": residual, "residual_mm": residual/scale,
                "limitation": limitation},
            "annual_land_terms_mm": totals, "normalization": audit,
            "input_checksums": {name: hashlib.sha256((project/name).read_bytes()).hexdigest()
                for name in (*CON_TYPES, "hyd-sed-lte.cha", "channel-lte.cha", "nutrients.cha", "codes.bsn", "parameters.bsn", "object.cnt") if (project/name).is_file()},
            "output_checksums": {name: hashlib.sha256((project/name).read_bytes()).hexdigest() for name in names},
            "limitations": [limitation if physical else "All channels are artificial bypass objects; this does not validate physical channel routing.",
                "Calibration and research H1 are not evaluated by a closed connection-flow balance."]}

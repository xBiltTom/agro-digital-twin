"""Recover delineated channel lengths in a copied SWAT+ project.

The existing GeoPackage is opened read-only as a geospatial source. Simulation
records are persisted by the normal runner in PostgreSQL, never in this file.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sqlite3
import struct
import xml.etree.ElementTree as ET

from app.services.swat_baseline_diagnostic import read_table, routing_rows


def zero_channel_kinetics(project: Path) -> dict:
    """Reproduce the failed zero-input kinetic probe; no neutral-rate claim.

61.0.2.61 calls QUAL2E unconditionally for physical channels. Its semi-analytic
reader replaces many zero inputs with nonzero defaults. This records input
changes only and does not switch off reactions or resolve runtime underflow.
    """
    path = project / "nutrients.cha"
    original = path.read_text().splitlines()
    header = original[1].split()
    fields = ("alg_stl", "ben_disp", "ben_nh3n", "ptln_stl", "ptlp_stl", "cst_stl", "ben_cst",
        "cbn_bod_co", "air_rt", "cbn_bod_stl", "ben_bod", "bact_die", "cst_decay",
        "nh3n_no2n", "no2n_no3n", "ptln_nh3n", "ptlp_solp", "alg_grow", "alg_resp")
    columns = {field: header.index(field) for field in fields}
    changes = []
    for index, line in enumerate(original[2:], start=2):
        if not line.strip():
            continue
        tokens = line.split()
        if len(tokens) < len(header) - int(header[-1] == "description"):
            raise ValueError("Incomplete channel nutrient row")
        before = {field: float(tokens[column]) for field, column in columns.items()}
        for column in columns.values():
            tokens[column] = "0.00000"
        original[index] = " ".join(tokens)
        changes.append({"name": tokens[0], "before": before, "after": {field: 0 for field in fields}})
    if not changes:
        raise ValueError("Channel nutrient parameters are required")
    before_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text("\n".join(original) + "\n")
    return {"classification": "ZERO_CHANNEL_KINETICS_DIAGNOSTIC", "file": path.name,
        "before_sha256": before_sha, "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "changed_fields": list(fields), "rows": changes,
        "reason": "Original physical-channel run fails in the QUAL2E semi-analytic solver (SIGFPE).",
        "limitation": "Zero inputs are replaced by nonzero defaults in ch_read_nut; this does not disable channel reactions. Nutrient and water-quality outputs are not evaluated.",
        "reference": "https://github.com/swat-model/swatplus/blob/61.0.2.61/src/ch_read_nut.f90"}


def _geometry_length(blob: bytes) -> float:
    """Length of the source's standard 2D GeoPackage LINESTRING, in metres."""
    if blob[:3] != b"GP\x00" or blob[3] & 0x30:
        raise ValueError("Expected a nonempty standard GeoPackage geometry")
    envelope = (blob[3] >> 1) & 7
    sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    if envelope not in sizes:
        raise ValueError("Invalid GeoPackage envelope")
    offset = 8 + sizes[envelope]
    endian = {0: ">", 1: "<"}.get(blob[offset])
    if endian is None:
        raise ValueError("Invalid WKB byte order")
    kind, count = struct.unpack_from(endian + "II", blob, offset + 1)
    if kind != 2 or count < 2 or len(blob) != offset + 9 + count * 16:
        raise ValueError("Expected a standard 2D LINESTRING")
    points = list(struct.iter_unpack(endian + "dd", blob[offset + 9:]))
    if any(not math.isfinite(value) for point in points for value in point):
        raise ValueError("Nonfinite geometry coordinate")
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def restore_channel_lengths(project: Path, *, channels: Path, routing_graph: Path) -> dict:
    """Join GIS IDs, verify topology/units, and change only the length column."""
    channels, routing_graph = channels.resolve(), routing_graph.resolve()
    if not channels.is_file() or not routing_graph.is_file():
        raise ValueError("Existing delineation channels and routing graph are required")
    source_sha = hashlib.sha256(channels.read_bytes()).hexdigest()
    graph_sha = hashlib.sha256(routing_graph.read_bytes()).hexdigest()
    with sqlite3.connect(channels.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        layers = db.execute("SELECT table_name, srs_id FROM gpkg_contents WHERE data_type='features'").fetchall()
        if len(layers) != 1 or layers[0]["table_name"] != "channels" or layers[0]["srs_id"] != 5070:
            raise ValueError("Expected the delineation channels layer in EPSG:5070")
        crs = db.execute("SELECT definition FROM gpkg_spatial_ref_sys WHERE srs_id=5070").fetchone()
        if crs is None or 'UNIT["metre",1' not in crs[0]:
            raise ValueError("Delineation lengths require a projected metre CRS")
        features = db.execute("SELECT link_id,length_m,slope_m_m,width_m,depth_m,geom FROM channels").fetchall()
    catalogue = {}
    for feature in features:
        identifier = str(feature["link_id"])
        if identifier in catalogue:
            raise ValueError("Duplicate delineation channel GIS ID")
        values = {key: float(feature[key]) for key in ("length_m", "slope_m_m", "width_m", "depth_m")}
        if any(not math.isfinite(value) or value <= 0 for value in values.values()):
            raise ValueError(f"Invalid delineated channel geometry: {identifier}")
        geometry_length = _geometry_length(feature["geom"])
        if abs(geometry_length - values["length_m"]) > 0.01:
            raise ValueError(f"Length attribute differs from polyline geometry: {identifier}")
        catalogue[identifier] = {**values, "geometry_length_m": geometry_length}
    connections = routing_rows(project / "chandeg.con")
    by_unit = {lead[0]: lead for lead, _ in connections}
    identifiers = {lead[2] for lead, _ in connections}
    if len(by_unit) != len(connections) or len(identifiers) != len(connections) or identifiers != set(catalogue):
        raise ValueError("Delineation and SWAT+ channel IDs must match one to one")
    actual_edges = set()
    terminals = []
    for lead, edges in connections:
        if not edges:
            terminals.append(lead[2])
        for kind, target, hyd_type, fraction in edges:
            if kind != "sdc" or target not in by_unit or hyd_type != "tot" or float(fraction) != 1:
                raise ValueError("Expected full-fraction channel-to-channel total-flow routing")
            actual_edges.add((lead[2], by_unit[target][2]))
    namespace = {"g": "http://graphml.graphdrawing.org/xmlns"}
    graph = ET.parse(routing_graph).getroot().find("g:graph", namespace)
    if graph is None or graph.attrib.get("edgedefault") != "directed":
        raise ValueError("Expected directed delineation routing graph")
    nodes = {node.attrib["id"] for node in graph.findall("g:node", namespace)}
    expected_edges = {(edge.attrib["source"], edge.attrib["target"]) for edge in graph.findall("g:edge", namespace)}
    if nodes != identifiers or actual_edges != expected_edges or len(terminals) != 1:
        raise ValueError("Delineation and SWAT+ routing topology do not match")
    downstream = {source: target for source, target in actual_edges}
    if len(downstream) != len(actual_edges):
        raise ValueError("Channel graph contains multiple downstream targets")
    for identifier in identifiers:
        visited = set()
        cursor = identifier
        while cursor in downstream:
            if cursor in visited:
                raise ValueError("Channel graph contains a cycle")
            visited.add(cursor)
            cursor = downstream[cursor]
        if cursor != terminals[0]:
            raise ValueError("Channel does not reach the sole terminal")
    _, parameter_rows = read_table(project / "channel-lte.cha")
    parameters = {row["id"]: row for row in parameter_rows}
    path = project / "hyd-sed-lte.cha"
    original = path.read_text().splitlines()
    header = original[1].split()
    length_column = header.index("len")
    indexed = {}
    for index, line in enumerate(original[2:], start=2):
        if not line.strip():
            continue
        tokens = line.split()
        if len(tokens) < len(header) - int(header[-1] == "description") or tokens[0] in indexed:
            raise ValueError("Incomplete or duplicate channel hydraulic parameter row")
        indexed[tokens[0]] = (index, tokens)
    changes, used = [], set()
    # Validate every mapping before mutating the copied parameter file.
    for lead, _ in connections:
        parameter = parameters[lead[7]]["cha_hyd"]
        if parameter in used:
            raise ValueError("Channel length restoration requires distinct hydraulic rows")
        used.add(parameter)
        index, tokens = indexed[parameter]
        source = catalogue[lead[2]]
        for model_key, source_key in (("wd", "width_m"), ("dp", "depth_m"), ("slp", "slope_m_m")):
            if abs(float(tokens[header.index(model_key)]) - source[source_key]) > 0.0000051:
                raise ValueError(f"Existing {model_key} does not match delineation: {lead[2]}")
        restored = source["length_m"] / 1000
        old = float(tokens[length_column])
        if old > 0.001 or restored <= 0.001:
            raise ValueError("Probe requires bypass lengths replaced by physical reach lengths")
        changes.append({"unit": lead[0], "gis_id": lead[2], "parameter": parameter,
            "before_length_km": old, "after_length_km": restored, **source})
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    for change in changes:
        index, tokens = indexed[change["parameter"]]
        tokens[length_column] = f"{change['after_length_km']:.5f}"
        original[index] = " ".join(tokens)
    path.write_text("\n".join(original) + "\n")
    if hashlib.sha256(channels.read_bytes()).hexdigest() != source_sha or hashlib.sha256(routing_graph.read_bytes()).hexdigest() != graph_sha:
        raise ValueError("Delineation source changed during restoration")
    return {"classification": "CONTROLLED_CHANNEL_LENGTH_PROBE", "file": path.name,
        "changed_fields": ["len"], "before_sha256": before,
        "after_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": {"channels": str(channels), "channels_sha256": source_sha,
            "routing_graph": str(routing_graph), "routing_graph_sha256": graph_sha,
            "crs": "EPSG:5070", "attribute": "length_m", "conversion": "metres / 1000 -> kilometres",
            "geometry_check": "2D polyline length agrees within 0.01 m"},
        "channel_count": len(changes), "edge_count": len(actual_edges), "terminal_gis_id": terminals[0],
        "total_length_km": sum(change["after_length_km"] for change in changes),
        "min_length_km": min(change["after_length_km"] for change in changes),
        "max_length_km": max(change["after_length_km"] for change in changes), "channels": changes,
        "limitations": ["Lengths come from DEM delineation, not a field survey.",
            "Existing derived width/depth/slope and uncalibrated hydraulic parameters remain model assumptions.",
            "This intervention is development evidence, not a test of H1."]}

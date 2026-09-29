"""Traceable HRU soil-water estimates from SWAT+ profile storage and soils.sol."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path


@dataclass(frozen=True)
class SoilLayer:
    bottom_mm: float
    wilting_fraction: float
    available_fraction: float
    saturation_fraction: float


@dataclass(frozen=True)
class SoilProfile:
    name: str
    layers: tuple[SoilLayer, ...]

    @property
    def depth_mm(self) -> float:
        return self.layers[-1].bottom_mm

    def root_thresholds(self, root_depth_m: float) -> tuple[float, float, float, float]:
        depth = min(self.depth_mm, max(1.0, root_depth_m * 1000.0))
        previous = wp = fc = saturation = 0.0
        for layer in self.layers:
            thickness = max(0.0, min(layer.bottom_mm, depth) - previous)
            wp += thickness * layer.wilting_fraction
            fc += thickness * (layer.wilting_fraction + layer.available_fraction)
            saturation += thickness * layer.saturation_fraction
            previous = layer.bottom_mm
            if previous >= depth:
                break
        return depth, wp / depth * 100, fc / depth * 100, saturation / depth * 100


def read_hru_soils(project: str | Path) -> dict[int, SoilProfile]:
    root = Path(project)
    if (root / "TxtInOut" / "soils.sol").is_file():
        root /= "TxtInOut"
    lines = (root / "soils.sol").read_text(encoding="utf-8").splitlines()
    profiles: dict[str, SoilProfile] = {}
    cursor = 2
    while cursor < len(lines):
        header = lines[cursor].split()
        cursor += 1
        if not header:
            continue
        name, count, total_depth = header[0], int(header[1]), float(header[3])
        layers = []
        for _ in range(count):
            cells = lines[cursor].split()
            cursor += 1
            bottom, density, awc, clay = map(float, (cells[0], cells[1], cells[2], cells[5]))
            wp = .40 * clay * density / 100.0  # SWAT+ soil_phys_init convention
            saturation = 1.0 - density / 2.65
            if not (0 < bottom <= total_depth and 0 <= wp < wp + awc < saturation <= 1):
                raise ValueError(f"Invalid soils.sol water thresholds for {name}")
            if layers and bottom <= layers[-1].bottom_mm:
                raise ValueError(f"Non-increasing soils.sol depth for {name}")
            layers.append(SoilLayer(bottom, wp, awc, saturation))
        if not math.isclose(layers[-1].bottom_mm, total_depth, abs_tol=1.0):
            raise ValueError(f"soils.sol depth mismatch for {name}")
        if name in profiles:
            raise ValueError(f"Duplicate soils.sol profile {name}")
        profiles[name] = SoilProfile(name, tuple(layers))
    hru_lines = (root / "hru-data.hru").read_text(encoding="utf-8").splitlines()
    columns = hru_lines[1].split()
    id_col, soil_col = columns.index("id"), columns.index("soil")
    result = {}
    for line in hru_lines[2:]:
        cells = line.split()
        if not cells:
            continue
        identifier, soil = int(cells[id_col]), cells[soil_col]
        if identifier in result or soil not in profiles:
            raise ValueError(f"Duplicate HRU or missing soil profile for HRU {identifier}: {soil}")
        result[identifier] = profiles[soil]
    return result


def read_hru_gis_ids(project: str | Path) -> dict[int, str]:
    root = Path(project)
    if (root / "TxtInOut" / "hru.con").is_file():
        root /= "TxtInOut"
    lines = (root / "hru.con").read_text(encoding="utf-8").splitlines()
    columns = lines[1].split()
    id_col, gis_col = columns.index("id"), columns.index("gis_id")
    result = {}
    for line in lines[2:]:
        cells = line.split()
        if not cells:
            continue
        identifier = int(cells[id_col])
        if identifier in result:
            raise ValueError(f"Duplicate hru.con id {identifier}")
        result[identifier] = cells[gis_col]
    return result


def hru_water_state(profile: SoilProfile, storage_mm: float, root_depth_m: float) -> dict[str, float | str]:
    """Project whole-profile storage uniformly; root-zone resolution is unavailable."""
    if not math.isfinite(storage_mm) or storage_mm < 0:
        raise ValueError("SWAT+ soil-water storage must be finite and nonnegative")
    depth, wp, fc, saturation = profile.root_thresholds(root_depth_m)
    theta = storage_mm / profile.depth_mm * 100.0
    if theta > 100:
        raise ValueError("SWAT+ storage exceeds physical profile volume")
    return {
        "soil_profile": profile.name,
        "profile_depth_mm": profile.depth_mm,
        "estimated_root_zone_depth_mm": depth,
        "estimated_soil_moisture_vol_percent": theta,
        "estimated_root_zone_water_mm": theta / 100.0 * depth,
        "wilting_point_vol_percent": wp,
        "field_capacity_vol_percent": fc,
        "saturation_vol_percent": saturation,
        "estimated_plant_available_fraction": max(0.0, min(1.0, (theta - wp) / (fc - wp))),
    }

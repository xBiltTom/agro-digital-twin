"""Traceable FSPM-to-SWAT+ plant parameter mapping.

Only documented ``plants.plt`` morphology parameters are touched.  This module
never reads or changes SWAT+ outputs and refuses a target crop not referenced by
the workspace HRU land-use/management inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
from statistics import fmean
from typing import Any


class SwatPlantMappingError(ValueError):
    pass


@dataclass(frozen=True)
class SwatClimateForcingReader:
    """Read the distributed SWAT+ weather forcing used by the FSPM.

    SWAT+ ``weather-sta.cli`` points to station files.  The documented daily
    records used by the official reference projects are ``year day value`` for
    precipitation and ``year day tmax tmin`` for temperature.
    """
    project: Path

    def _station_files(self) -> list[dict[str, Path]]:
        station = self.project / "weather-sta.cli"
        if not station.is_file():
            raise SwatPlantMappingError("weather-sta.cli is required to derive FSPM forcing from the SWAT+ project")
        rows = [line.split() for line in station.read_text(encoding="utf-8", errors="strict").splitlines()[2:] if line.split()]
        if not rows or any(len(row) < 6 for row in rows):
            raise SwatPlantMappingError("weather-sta.cli does not contain a usable weather station")
        stations: list[dict[str, Path]] = []
        for row in rows:
            files = {"name": Path(row[0]), "pcp": self.project / row[2], "tmp": self.project / row[3],
                     "slr": self.project / row[4], "hmd": self.project / row[5]}
            # Existing SWAT+ examples sometimes declare *.tem while retaining *.tmp.
            if not files["tmp"].is_file() and files["tmp"].suffix == ".tem" and files["tmp"].with_suffix(".tmp").is_file():
                files["tmp"] = files["tmp"].with_suffix(".tmp")
            missing = [kind for kind, path in files.items() if kind != "name" and not path.is_file()]
            if missing:
                raise SwatPlantMappingError(f"SWAT+ station {row[0]!r} is missing direct weather files: {', '.join(missing)}")
            stations.append(files)
        return stations

    @staticmethod
    def _numeric_rows(path: Path, minimum: int) -> dict[tuple[int, int], list[float]]:
        output: dict[tuple[int, int], list[float]] = {}
        for raw in path.read_text(encoding="utf-8", errors="strict").splitlines()[3:]:
            pieces = raw.split()
            if len(pieces) < minimum:
                continue
            try:
                year, day = int(pieces[0]), int(pieces[1])
                values = [float(value) for value in pieces[2:minimum]]
            except ValueError:
                continue
            output[(year, day)] = values
        return output

    def for_period(self, start: date, end: date) -> tuple[list[dict[str, float]], dict[str, Any]]:
        stations = self._station_files()
        station_data = [
            {
                "name": files["name"].name,
                "pcp": self._numeric_rows(files["pcp"], 3),
                "tmp": self._numeric_rows(files["tmp"], 4),
                "slr": self._numeric_rows(files["slr"], 3),
                "hmd": self._numeric_rows(files["hmd"], 3),
            }
            for files in stations
        ]
        daily: list[dict[str, float]] = []
        cursor = start
        from datetime import timedelta
        while cursor <= end:
            key = (cursor.year, cursor.timetuple().tm_yday)
            available = [row for row in station_data if key in row["tmp"] and row["tmp"][key][0] > -90 and row["tmp"][key][1] > -90]
            if available:
                # The source project does not expose an HRU-to-station weight.
                # An equal-station mean is therefore a documented basin forcing
                # summary, rather than silently selecting the first grid cell.
                daily.append({
                    "temp_c": fmean((row["tmp"][key][0] + row["tmp"][key][1]) / 2.0 for row in available),
                    "precip_mm": fmean(max(0.0, row["pcp"].get(key, [0.0])[0]) for row in available),
                    "solar_rad_mj": fmean(max(0.0, row["slr"].get(key, [0.0])[0]) for row in available),
                    "rh_percent": fmean(max(0.0, row["hmd"].get(key, [0.0])[0]) * 100.0 for row in available),
                    "co2_ppm": 400.0,
                })
            cursor += timedelta(days=1)
        if not daily:
            raise SwatPlantMappingError("SWAT+ weather inputs contain no usable temperature records in the requested period")
        return daily, {
            "source": "SWAT+ weather-sta.cli direct station files",
            "station_count": len(station_data),
            "station_aggregation": "equal_station_mean; HRU-to-station weights are not available in this TxtInOut",
            "variables": ["pcp", "tmp", "slr", "hmd"], "days": len(daily),
            "limitations": "The FSPM receives a basin forcing summary rather than an HRU-specific plant forcing.",
        }


class SwatPlantParameterMapper:
    """Map a FieldAggregate to documented fields of one active SWAT+ crop record."""
    PARAMETER_SPECS = {
        "lai_pot": ("mean_LAI", "m2_leaf/m2_ground", "maximum potential LAI; SWAT+ plant growth canopy limit"),
        "can_ht_max": ("plant_height_mean_m", "m", "maximum canopy height; SWAT+ canopy morphology"),
        "rt_dp_max": ("root_depth_mean_m", "m", "maximum root depth; SWAT+ plant water uptake rooting limit"),
    }

    def __init__(self, target_plant_name: str = "corn"):
        self.target_plant_name = target_plant_name

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _active_hrus(workspace: Path, target: str) -> list[str]:
        hru_file, landuse, management = workspace / "hru-data.hru", workspace / "landuse.lum", workspace / "management.sch"
        if not all(path.is_file() for path in (hru_file, landuse, management)):
            raise SwatPlantMappingError("hru-data.hru, landuse.lum and management.sch are required for a traceable plant mapping")
        management_text = management.read_text(encoding="utf-8", errors="strict")
        # SWAT+ editor revisions differ in how much whitespace they retain on
        # the operation row.  In compact tables (including the South Fork
        # project) the planted crop is the final token; in expanded tables it
        # is column five.  Accept both representations, but only from rows
        # that actually carry an operation payload.
        management_rows = [line.split() for line in management_text.splitlines() if line.split()]
        planted_crops = {
            tokens[4] if len(tokens) >= 5 else tokens[-1]
            for tokens in management_rows
            if len(tokens) >= 2 and (
                tokens[0].startswith("pl_")
                or tokens[0].startswith("auto_")
                or tokens[0] in {"plnt", "plant"}
            )
        }
        if target not in planted_crops:
            raise SwatPlantMappingError(f"management.sch does not plant target crop '{target}'")
        # A plant community is the documented land-use bridge from an HRU to a
        # crop. This intentionally does not claim every rotation HRU is corn.
        crop_landuses = {tokens[0] for tokens in (line.split() for line in landuse.read_text(encoding="utf-8").splitlines()[2:]) if len(tokens) >= 3 and tokens[2] in {target, f"{target}_comm"}}
        hru_rows = [line.split() for line in hru_file.read_text(encoding="utf-8").splitlines()[2:] if line.split()]
        hrus = [tokens[1] for tokens in hru_rows if len(tokens) >= 6 and tokens[5] in crop_landuses]
        if not hrus:
            raise SwatPlantMappingError(f"target plant '{target}' is not used by any workspace HRU management")
        return hrus

    @staticmethod
    def _header_and_record(path: Path, target: str) -> tuple[list[str], list[str], list[str], int]:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        if len(lines) < 3:
            raise SwatPlantMappingError("plants.plt is not a valid SWAT+ plant table")
        header = lines[1].split()
        for line_index, raw in enumerate(lines[2:], 2):
            values = raw.split()
            if values and values[0] == target:
                if len(values) != len(header):
                    raise SwatPlantMappingError("plants.plt target record does not match its header")
                return lines, header, values, line_index
        raise SwatPlantMappingError(f"plants.plt does not define requested target plant '{target}'")

    @staticmethod
    def _soil_root_limit_m(workspace: Path, target_hrus: list[str]) -> float | None:
        """Return the shallowest referenced SWAT+ soil ZMX cap (mm -> m)."""
        hru_path, soils_path = workspace / "hru-data.hru", workspace / "soils.sol"
        if not soils_path.is_file():
            return None
        hru_soils = {tokens[4] for tokens in (line.split() for line in hru_path.read_text(encoding="utf-8").splitlines()[2:]) if len(tokens) >= 6 and tokens[1] in target_hrus}
        lines = soils_path.read_text(encoding="utf-8", errors="strict").splitlines()
        if len(lines) < 3:
            return None
        columns = [column.lower() for column in lines[1].split()]
        if "zmx" not in columns:
            return None
        zmx_index = columns.index("zmx")
        caps = []
        for tokens in (line.split() for line in lines[2:]):
            if len(tokens) > zmx_index and tokens[0] in hru_soils:
                try:
                    caps.append(float(tokens[zmx_index]) / 1000.0)
                except ValueError:
                    pass
        return min(caps) if caps else None

    def apply(self, workspace: Path, field: dict[str, Any]) -> dict[str, Any]:
        plants = workspace / "plants.plt"
        if not plants.is_file():
            raise SwatPlantMappingError("plants.plt is required for real FSPM coupling")
        source_sha256 = self._sha256(plants)
        target_hrus = self._active_hrus(workspace, self.target_plant_name)
        lines, header, values, index = self._header_and_record(plants, self.target_plant_name)
        aliases = {"lai_pot": "lai_pot", "can_ht_max": "can_ht_max", "rt_dp_max": "rt_dp_max"}
        height = field.get("plant_height_mean_m")
        if height is None:
            raise SwatPlantMappingError("FieldAggregate is missing plant_height_mean_m")
        root_limit_m = self._soil_root_limit_m(workspace, target_hrus)
        source_values = {"mean_LAI": float(field["mean_LAI"]), "plant_height_mean_m": float(height), "root_depth_mean_m": min(float(field["root_depth_mean_m"]), root_limit_m) if root_limit_m is not None else float(field["root_depth_mean_m"])}
        updates = []
        for swat_parameter, (source_variable, unit, justification) in self.PARAMETER_SPECS.items():
            column = aliases[swat_parameter]
            if column not in header:
                raise SwatPlantMappingError(f"plants.plt does not support documented parameter {column}")
            pos = header.index(column)
            old = float(values[pos])
            new = source_values[source_variable]
            # Coupling has to change an input.  A round-trip-equal value is valid
            # physically but cannot demonstrate this phase's experiment, so it is
            # explicitly rejected instead of silently fabricating a difference.
            if abs(new - old) < 1e-9:
                raise SwatPlantMappingError(f"FSPM value for {column} equals the baseline; choose a different deterministic seed/parameters")
            values[pos] = f"{new:.6f}"
            transformation = "direct FieldAggregate morphology value"
            if swat_parameter == "rt_dp_max" and root_limit_m is not None:
                transformation += f"; capped by soils.sol ZMX={root_limit_m:.6f} m"
            updates.append({"hru_id": target_hrus, "source_variable": source_variable, "swat_parameter": column, "input_file": "plants.plt", "original_value": old, "coupled_value": new, "unit": unit, "transformation": transformation, "justification": justification})
        lines[index] = "  ".join(values)
        plants.write_text("\n".join(lines) + "\n", encoding="utf-8")
        coupled_sha256 = self._sha256(plants)
        return {"status": "APPLIED", "target_plant_name": self.target_plant_name, "target_hrus": target_hrus, "parameter_updates": updates, "not_coupled": [{"variable": "actual_ET_mm_day", "reason": "SWAT+ recomputes transpiration internally; no output or ET input is edited"}, {"variable": "soil_water_uptake_mm_day", "reason": "SWAT+ recomputes uptake internally from soil/plant state"}, {"variable": "estimated_yield_g_plant", "reason": "yield remains a diagnostic; no harvest/output adjustment is applied"}], "workspace_input_files_modified": ["plants.plt"], "input_checksums": {"plants.plt": {"before_sha256": source_sha256, "after_sha256": coupled_sha256}}, "source_sha256": source_sha256, "coupled_sha256": coupled_sha256}

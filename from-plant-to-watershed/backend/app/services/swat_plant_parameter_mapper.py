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
    """Map a simplified-FSPM field contract to active documented SWAT+ inputs.

    This is deliberately a crop-parameter mapper, not a hydrology engine: it
    never supplies ET, infiltration, soil water, runoff, or streamflow to SWAT+.
    Parameter definitions and ranges are those published for ``plants.plt``.
    """
    PARAMETER_SPECS = {
        "lai_pot": ("swat_lai_contract.lai_pot", "m2_leaf/m2_ground", .50, 10.0,
                    "FSPM seasonal maximum green LAI -> SWAT+ maximum potential LAI"),
        "frac_hu1": ("swat_lai_contract.frac_hu1", "fraction", .001, .999,
                     "FSPM heat-unit fraction at 15% peak LAI -> first SWAT+ optimal LAI curve point"),
        "lai_max1": ("swat_lai_contract.lai_max1", "fraction", .001, .999,
                     "FSPM relative LAI at first curve point -> first SWAT+ optimal LAI curve point"),
        "frac_hu2": ("swat_lai_contract.frac_hu2", "fraction", .001, .999,
                     "FSPM heat-unit fraction at 85% peak LAI -> second SWAT+ optimal LAI curve point"),
        "lai_max2": ("swat_lai_contract.lai_max2", "fraction", .001, .999,
                     "FSPM relative LAI at second curve point -> second SWAT+ optimal LAI curve point"),
        "hu_lai_decl": ("swat_lai_contract.hu_lai_decl", "fraction", .20, 1.0,
                        "FSPM first post-peak green-LAI decline -> SWAT+ fraction of heat units initiating LAI decline"),
        "can_ht_max": ("plant_height_mean_m", "m", .10, 20.0,
                       "FSPM maximum canopy height -> SWAT+ maximum canopy height"),
        "rt_dp_max": ("root_depth_mean_m", "m", .0, 3.0,
                      "FSPM maximum live-root depth -> SWAT+ maximum rooting depth, constrained by referenced soil depth"),
        "ext_co": ("canopy_extinction_coefficient", "dimensionless", .0, 2.0,
                   "FSPM Beer-Lambert canopy-cover extinction coefficient -> SWAT+ light extinction coefficient"),
        "bm_e": ("biomass_energy_ratio_kg_ha_per_mj_m2", "kg/ha/(MJ/m2)", 10.0, 90.0,
                 "FSPM population mean radiation-use efficiency -> SWAT+ biomass-energy ratio"),
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
    def _soil_root_limit_m(workspace: Path, target_hrus: list[str]) -> tuple[float | None, str | None]:
        """Return the shallowest documented referenced soil profile cap (mm -> m)."""
        hru_path, soils_path = workspace / "hru-data.hru", workspace / "soils.sol"
        if not soils_path.is_file():
            return None, None
        hru_soils = {tokens[4] for tokens in (line.split() for line in hru_path.read_text(encoding="utf-8").splitlines()[2:]) if len(tokens) >= 6 and tokens[1] in target_hrus}
        lines = soils_path.read_text(encoding="utf-8", errors="strict").splitlines()
        if len(lines) < 3:
            return None, None
        columns = [column.lower() for column in lines[1].split()]
        # Current editor projects use dp_tot. Older compatible projects can
        # expose zmx. Do not infer a cap when neither field exists.
        cap_name = "zmx" if "zmx" in columns else "dp_tot" if "dp_tot" in columns else None
        if cap_name is None:
            return None, None
        cap_index = columns.index(cap_name)
        caps = []
        for tokens in (line.split() for line in lines[2:]):
            if len(tokens) > cap_index and tokens[0] in hru_soils:
                try:
                    caps.append(float(tokens[cap_index]) / 1000.0)
                except ValueError:
                    pass
        return (min(caps), cap_name) if caps else (None, None)

    @staticmethod
    def _field_value(field: dict[str, Any], dotted_name: str) -> float:
        value: Any = field
        for part in dotted_name.split("."):
            if not isinstance(value, dict) or part not in value:
                raise SwatPlantMappingError(f"FieldAggregate is missing {dotted_name}")
            value = value[part]
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise SwatPlantMappingError(f"FieldAggregate value {dotted_name} is not numeric") from exc

    def apply(self, workspace: Path, field: dict[str, Any]) -> dict[str, Any]:
        plants = workspace / "plants.plt"
        if not plants.is_file():
            raise SwatPlantMappingError("plants.plt is required for real FSPM coupling")
        source_sha256 = self._sha256(plants)
        target_hrus = self._active_hrus(workspace, self.target_plant_name)
        lines, header, values, index = self._header_and_record(plants, self.target_plant_name)
        root_limit_m, root_limit_source = self._soil_root_limit_m(workspace, target_hrus)
        updates = []
        changed = False
        for swat_parameter, (source_variable, unit, lower, upper, justification) in self.PARAMETER_SPECS.items():
            column = swat_parameter
            if column not in header:
                raise SwatPlantMappingError(f"plants.plt does not support documented parameter {column}")
            pos = header.index(column)
            old = float(values[pos])
            raw = self._field_value(field, source_variable)
            if swat_parameter == "rt_dp_max" and root_limit_m is not None:
                raw = min(raw, root_limit_m)
            new = min(upper, max(lower, raw))
            if swat_parameter in {"frac_hu2", "hu_lai_decl"}:
                new = max(new, float(values[header.index("frac_hu1")]) + .001)
            if swat_parameter == "hu_lai_decl":
                new = max(new, float(values[header.index("frac_hu2")]) + .001)
            was_changed = abs(new - old) >= 1e-9
            if was_changed:
                values[pos] = f"{new:.6f}"
                changed = True
            transformation = f"direct FieldAggregate value clamped to documented [{lower}, {upper}]"
            if swat_parameter == "rt_dp_max" and root_limit_m is not None:
                transformation += f"; capped by soils.sol {root_limit_source}={root_limit_m:.6f} m"
            updates.append({"hru_id": target_hrus, "crop": self.target_plant_name, "source_variable": source_variable, "fspm_value": raw, "swat_parameter": column, "input_file": "plants.plt", "original_value": old, "coupled_value": new, "delta_absolute": new - old, "delta_percent": None if old == 0 else (new - old) / old * 100.0, "unit": unit, "clamp": {"minimum": lower, "maximum": upper, "applied": new != raw}, "source_parameter_provenance": (field.get("coupling_parameter_provenance") or {}).get(column), "transformation": transformation, "justification": justification, "status": "CHANGED" if was_changed else "UNCHANGED"})
        if changed:
            lines[index] = "  ".join(values)
            plants.write_text("\n".join(lines) + "\n", encoding="utf-8")
        coupled_sha256 = self._sha256(plants)
        return {"status": "APPLIED" if changed else "NO_PARAMETER_CHANGE", "target_plant_name": self.target_plant_name, "target_hrus": target_hrus, "parameter_updates": updates, "lineage": "PlantPopulation(1000 SIMPLIFIED_FSPM plants) -> PlantToFieldAggregator -> documented plants.plt crop record -> SWAT+ internal hydrology", "not_coupled": [{"variable": "actual_ET_mm_day", "reason": "NOT_COUPLED: SWAT+ recomputes transpiration internally; no ET input or output is edited"}, {"variable": "potential_ET_mm_day", "reason": "NOT_COUPLED: SWAT+ owns potential ET calculation"}, {"variable": "soil_water_uptake_mm_day", "reason": "NOT_COUPLED: SWAT+ computes root uptake from plant and soil state"}, {"variable": "water_stress", "reason": "NOT_COUPLED: simplified Feddes stress has no unit-compatible documented SWAT+ plant-table equivalent"}, {"variable": "stomatal_conductance_mmol", "reason": "NOT_COUPLED: FSPM mmol conductance is not converted to SWAT+ stcon_max m/s without a validated conductance conversion"}, {"variable": "thermal_maturity_gdd", "reason": "NOT_COUPLED: provided plants.plt has days_mat, not a GDD/PHU input; exact planted dates are not emitted by this project, so GDD is used only for documented LAI-curve fractions"}, {"variable": "estimated_yield_g_plant", "reason": "NOT_COUPLED: no harvest/output adjustment is made"}, {"variable": "root_distribution", "reason": "NOT_COUPLED: plants.plt exposes maximum root depth but no matching depth-distribution input"}], "workspace_input_files_modified": ["plants.plt"] if changed else [], "input_checksums": {"plants.plt": {"before_sha256": source_sha256, "after_sha256": coupled_sha256}}, "source_sha256": source_sha256, "coupled_sha256": coupled_sha256}

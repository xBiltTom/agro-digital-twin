"""Verifiable South Fork crop-chain diagnostics for copied SWAT+ workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class SwatAutoManagementSeason:
    """A traceable approximation of an annual SWAT+ auto-managed crop season.

    SWAT+ evaluates the decision table dynamically, including soil-water state.
    The FSPM has no access to the executed event log in this TxtInOut, so this
    object exposes an approximate PHU-based window rather than claiming an
    observed planting date.
    """

    decision_table: str
    management_schedule: str
    configured_crop: str
    phu_base0_fraction: float
    harvest_day_of_year: int
    crop_temperature_base_c: float
    phu_trigger_base_c: float = 0.0
    confidence: str = "LIMITED"

    def windows(self, start: date, end: date, temperatures_c: Iterable[float], *, thermal_maturity_gdd: float) -> list[dict[str, Any]]:
        temperatures = tuple(float(value) for value in temperatures_c)
        expected_days = (end - start).days + 1
        if len(temperatures) != expected_days:
            raise ValueError("season-window temperatures must align one-to-one with the requested period")
        if thermal_maturity_gdd <= 0:
            raise ValueError("thermal_maturity_gdd must be positive")
        threshold_gdd = self.phu_base0_fraction * thermal_maturity_gdd
        windows: list[dict[str, Any]] = []
        annual_trigger_gdd, active_start = 0.0, None
        cursor = start
        for temperature in temperatures:
            if cursor.month == 1 and cursor.day == 1:
                # This only resets the *pre-plant trigger accumulator*. Crop
                # GDD/APAR reset exclusively when this policy opens a season.
                annual_trigger_gdd = 0.0
            doy = cursor.timetuple().tm_yday
            if active_start is None:
                # ``phu_base0`` explicitly denotes PHU accumulated above 0 C.
                # The crop tmp_base remains provenance for the FSPM growth
                # clock, but is not substituted for this SWAT decision input.
                annual_trigger_gdd += max(0.0, temperature - self.phu_trigger_base_c)
                if doy <= self.harvest_day_of_year and annual_trigger_gdd >= threshold_gdd:
                    active_start = cursor
            elif doy >= self.harvest_day_of_year:
                windows.append({
                    "start_date": active_start.isoformat(), "end_date": cursor.isoformat(),
                    "status": "APPROXIMATE_PLANTING_WINDOW", "trigger_gdd_c_day": threshold_gdd,
                    "harvest_boundary_day_of_year": self.harvest_day_of_year,
                })
                active_start = None
            cursor += timedelta(days=1)
        if active_start is not None:
            windows.append({
                "start_date": active_start.isoformat(), "end_date": end.isoformat(),
                "status": "APPROXIMATE_PLANTING_WINDOW", "trigger_gdd_c_day": threshold_gdd,
                "harvest_boundary_day_of_year": self.harvest_day_of_year,
            })
        return windows

    def provenance(self, windows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "status": "APPROXIMATE_PLANTING_WINDOW",
            "season_start_method": "SWAT_AUTO_MANAGEMENT_PHU_TRIGGER_APPROXIMATION",
            "source_swat_files": ["management.sch", "lum.dtl", "plants.plt"],
            "management_schedule": self.management_schedule,
            "decision_table": self.decision_table,
            "configured_crop": self.configured_crop,
            "phu_base0_fraction": self.phu_base0_fraction,
            "phu_trigger_base_c": self.phu_trigger_base_c,
            "crop_temperature_base_c": self.crop_temperature_base_c,
            "phu_reference": "SIMPLIFIED_FSPM_THERMAL_MATURITY_GDD",
            "preplant_trigger_reset": "CALENDAR_YEAR_BOUNDARY_FOR_ANNUAL_PHU_ACCUMULATOR_ONLY_NOT_FSPM_SEASON_RESET",
            "harvest_boundary_day_of_year": self.harvest_day_of_year,
            "confidence": self.confidence,
            "season_windows": windows,
            "limitation": "SWAT+ evaluates PHU and soil-water conditions internally; this TxtInOut/print configuration has no executed planting-event log or tabulated PHU maturity total. The PHU fraction uses the simplified-FSPM thermal-maturity reference, so window starts are FSPM approximations, not SWAT+ event dates.",
        }


class SwatCropChainDiagnostic:
    """Validate the configured CDL -> HRU -> crop execution path.

    The diagnostic deliberately reports configured auto-management separately
    from an observed planting-event log: this SWAT+ print configuration does
    not emit a planting-event table, so it never invents planting dates.
    """

    @staticmethod
    def _rows(path: Path) -> list[list[str]]:
        return [line.split() for line in path.read_text(encoding="utf-8", errors="strict").splitlines()[2:] if line.split()]

    @staticmethod
    def auto_management_season(workspace: str | Path, *, target_crop: str = "corn") -> SwatAutoManagementSeason:
        """Read the configured PHU planting/harvest controls without inventing events."""
        root = Path(workspace)
        required = ("management.sch", "lum.dtl", "plants.plt")
        if any(not (root / name).is_file() for name in required):
            raise ValueError("auto-management season requires management.sch, lum.dtl and plants.plt")
        schedules = SwatCropChainDiagnostic._rows(root / "management.sch")
        schedule_name, decision_table, configured_crop = None, None, None
        for index, row in enumerate(schedules):
            if len(row) < 2 or row[0].startswith("pl_"):
                continue
            child = schedules[index + 1] if index + 1 < len(schedules) else []
            if len(child) >= 2 and child[0].startswith("pl_"):
                if child[-1] == target_crop or schedule_name is None:
                    schedule_name, decision_table, configured_crop = row[0], child[0], child[-1]
                    if configured_crop == target_crop:
                        break
        if not all((schedule_name, decision_table, configured_crop)):
            raise ValueError("management.sch does not expose an auto-management crop schedule")
        lum_lines = (root / "lum.dtl").read_text(encoding="utf-8", errors="strict").splitlines()
        start = next((index for index, line in enumerate(lum_lines) if line.split() and line.split()[0] == decision_table), None)
        if start is None:
            raise ValueError(f"lum.dtl does not define decision table {decision_table!r}")
        block = lum_lines[start:next((index for index in range(start + 1, len(lum_lines)) if lum_lines[index].split() and lum_lines[index].split()[0] == "name"), len(lum_lines))]
        phu_fraction, harvest_day = None, None
        for line in block:
            row = line.split()
            if phu_fraction is None and len(row) >= 7 and row[0] == "phu_base0" and row[4] == "-" and row[6] == ">":
                phu_fraction = float(row[5])
            # SWAT+ decision-table rows can include extra comparison operands;
            # the assignment operator is therefore not reliably at column 6.
            if len(row) >= 7 and row[0] == "jday" and row[4] == "-" and "=" in row[6:]:
                harvest_day = int(float(row[5]))
        if phu_fraction is None or harvest_day is None:
            raise ValueError(f"lum.dtl decision table {decision_table!r} lacks PHU planting or fixed harvest controls")
        plant_header, plant_record = None, None
        records = (root / "plants.plt").read_text(encoding="utf-8", errors="strict").splitlines()
        if len(records) >= 3:
            plant_header = records[1].split()
            plant_record = next((line.split() for line in records[2:] if line.split() and line.split()[0] == target_crop), None)
        if not plant_header or not plant_record or "tmp_base" not in plant_header:
            raise ValueError(f"plants.plt does not define tmp_base for {target_crop!r}")
        return SwatAutoManagementSeason(
            decision_table=decision_table, management_schedule=schedule_name, configured_crop=configured_crop,
            phu_base0_fraction=phu_fraction, harvest_day_of_year=harvest_day,
            crop_temperature_base_c=float(plant_record[plant_header.index("tmp_base")]),
        )

    @classmethod
    def input_chain(cls, workspace: str | Path, target_hrus: list[int], *, crop: str = "corn") -> dict[str, Any]:
        root = Path(workspace)
        required = ("hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl", "plants.plt")
        if any(not (root / name).is_file() for name in required):
            raise ValueError("crop-chain diagnostic requires complete SWAT+ land-use, management, decision-table and plant inputs")
        crop_lum, crop_comm, crop_rotation = f"{crop}_lum", f"{crop}_comm", f"{crop}_rot"
        target_names = {f"hru{value:02d}" for value in target_hrus}
        hru_rows = cls._rows(root / "hru-data.hru")
        corn_hru_rows = [row for row in hru_rows if len(row) >= 6 and row[1] in target_names]
        hru_ok = len(corn_hru_rows) == len(target_names) and all(row[5] == crop_lum for row in corn_hru_rows)
        landuse_rows = cls._rows(root / "landuse.lum")
        landuse = next((row for row in landuse_rows if row[0] == crop_lum), [])
        landuse_ok = len(landuse) >= 4 and landuse[2] == crop_comm and landuse[3] == crop_rotation
        plant_rows = cls._rows(root / "plant.ini")
        community_index = next((index for index, row in enumerate(plant_rows) if row[0] == crop_comm), None)
        community_ok = community_index is not None and community_index + 1 < len(plant_rows) and plant_rows[community_index + 1][0] == crop
        schedule_rows = cls._rows(root / "management.sch")
        rotation_index = next((index for index, row in enumerate(schedule_rows) if row[0] == crop_rotation), None)
        schedule_ok = rotation_index is not None and rotation_index + 1 < len(schedule_rows) and schedule_rows[rotation_index + 1][-1] == crop
        decision_text = (root / "lum.dtl").read_text(encoding="utf-8", errors="strict")
        decision_ok = "plant" in decision_text and "harvest_kill" in decision_text and "crop" in decision_text
        plant_input = (root / "plants.plt").read_text(encoding="utf-8", errors="strict").splitlines()
        plant_header = plant_input[1].split()
        plant_rows = [line.split() for line in plant_input[2:] if line.split()]
        crop_record = next((row for row in plant_rows if row[0] == crop), [])
        coupled_parameters = ("lai_pot", "frac_hu1", "lai_max1", "frac_hu2", "lai_max2", "hu_lai_decl", "can_ht_max", "rt_dp_max", "ext_co", "bm_e")
        parameter_columns = {name: plant_header.index(name) for name in coupled_parameters if name in plant_header}
        plant_record_ok = bool(crop_record) and all(index < len(crop_record) for index in parameter_columns.values())
        checks = {
            "cdl_hrus_reference_crop_landuse": hru_ok,
            "landuse_references_community_and_rotation": landuse_ok,
            "community_references_crop": community_ok,
            "management_references_crop_auto_decision": schedule_ok,
            "decision_table_has_plant_and_harvest_actions": decision_ok,
            "plants_record_has_growth_parameters": plant_record_ok and all(name in parameter_columns for name in ("lai_pot", "can_ht_max", "rt_dp_max")),
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL", "crop": crop, "target_hru_count": len(target_names),
            "checks": checks, "planting": {
                "status": "AUTO_MANAGEMENT_CONFIGURED", "mechanism": "temperature/PHU-triggered pl_hv_summer1",
                "harvest_fallback_day_of_year": 350,
                "limitation": "This print configuration has no event log; configured planting is verified, but an exact executed planting date is NOT_AVAILABLE.",
            },
            "plant_growth": {
                "status": "ACTIVE_PLANT_RECORD_CONFIGURED", "parameters": {name: float(crop_record[index]) for name, index in parameter_columns.items()} if plant_record_ok else {},
                "mode": "SWAT+ warm_annual/temp_gro plant record consumed through the active crop community; the diagnostic does not claim source-level access to SWAT+ internals.",
            },
        }

    @classmethod
    def output_chain(cls, workspace: str | Path, *, crop: str = "corn") -> dict[str, Any]:
        path = Path(workspace) / "hru_wb_day.txt"
        if not path.is_file():
            return {"status": "NOT_AVAILABLE", "reason": "hru_wb_day.txt was not printed"}
        rows = cls._rows(path)
        community, rotation = f"{crop}_comm", f"{crop}_rot"
        matched = [row for row in rows if len(row) >= 2 and row[-2:] == [community, rotation]]
        return {"status": "PASS" if matched else "FAIL", "hru_day_records_with_active_community": len(matched),
                "expected_community": community, "expected_rotation": rotation}

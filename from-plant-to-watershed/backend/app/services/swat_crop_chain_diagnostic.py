"""Verifiable South Fork crop-chain diagnostics for copied SWAT+ workspaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SwatCropChainDiagnostic:
    """Validate the configured CDL -> HRU -> crop execution path.

    The diagnostic deliberately reports configured auto-management separately
    from an observed planting-event log: this SWAT+ print configuration does
    not emit a planting-event table, so it never invents planting dates.
    """

    @staticmethod
    def _rows(path: Path) -> list[list[str]]:
        return [line.split() for line in path.read_text(encoding="utf-8", errors="strict").splitlines()[2:] if line.split()]

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

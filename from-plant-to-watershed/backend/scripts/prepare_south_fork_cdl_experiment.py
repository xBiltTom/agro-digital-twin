"""Prepare an isolated CDL-informed South Fork corn-management variant.

The variant is a bounded 2019 management experiment, not a reconstruction of
historical planting events. The source SWAT+ project is only read and hashed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable

from app.services.swat_cdl_hru_mapper import SwatCDLHRUMapper
from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper


_CHECKSUM_INPUTS = (
    "hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl",
    "plants.plt", "file.cio", "time.sim", "print.prt", "weather-sta.cli",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_checksums(project: Path) -> dict[str, str]:
    return {name: _sha256(project / name) for name in _CHECKSUM_INPUTS if (project / name).is_file()}


def _activate_explicit_corn_management(project: Path) -> dict[str, str]:
    """Point only the new corn rotation at the editor's existing corn table."""
    table_name = "pl_hv_summer1_corn"
    decision_path = project / "lum.dtl"
    decision_lines = decision_path.read_text(encoding="utf-8", errors="strict").splitlines()
    table_start = next((index for index, line in enumerate(decision_lines)
                        if line.split() and line.split()[0] == table_name), None)
    if table_start is None:
        raise ValueError(f"lum.dtl has no explicit corn management table {table_name!r}")
    table_end = next((index for index in range(table_start + 1, len(decision_lines))
                      if decision_lines[index].split() and decision_lines[index].split()[0] == "name"), len(decision_lines))
    decision_block = decision_lines[table_start:table_end]
    if not any(line.split() and line.split()[0] == "plant" and "corn" in line.split() for line in decision_block):
        raise ValueError("The explicit corn table has no corn planting action")
    if not any(line.split() and line.split()[0] == "harvest_kill" and "corn" in line.split() for line in decision_block):
        raise ValueError("The explicit corn table has no corn harvest action")

    schedule_path = project / "management.sch"
    schedule_lines = schedule_path.read_text(encoding="utf-8", errors="strict").splitlines()
    rotation_index = next((index for index, line in enumerate(schedule_lines)
                           if line.split() and line.split()[0] == "corn_rot"), None)
    if rotation_index is None:
        raise ValueError("management.sch has no isolated corn rotation")
    operation_index = next((index for index in range(rotation_index + 1, len(schedule_lines))
                            if schedule_lines[index].split()), None)
    if operation_index is None:
        raise ValueError("The isolated corn rotation has no operation")
    operation = schedule_lines[operation_index].split()
    if len(operation) < 2 or operation[0] != "pl_hv_summer1" or operation[-1] != "corn":
        raise ValueError("The isolated corn rotation does not reference the expected corn operation")
    original_name = operation[0]
    indent = schedule_lines[operation_index][:len(schedule_lines[operation_index])
                                             - len(schedule_lines[operation_index].lstrip())]
    schedule_lines[operation_index] = f"{indent}{table_name}   {' '.join(operation[1:])}"
    schedule_path.write_text("\n".join(schedule_lines) + "\n", encoding="utf-8")
    return {
        "rotation": "corn_rot", "original_operation": original_name,
        "effective_decision_table": table_name, "crop": "corn",
    }


def prepare_configuration(
    source_project: str | Path,
    cdl_composition: str | Path | Iterable[dict[str, Any]],
    destination: str | Path,
    *,
    cdl_provenance_path: str | Path | None = None,
    cdl_year: int = 2019,
    threshold: float = 0.50,
) -> dict[str, Any]:
    """Copy source inputs and apply only the CDL-majority HRU crop chain."""
    source = Path(source_project).expanduser().resolve()
    target = Path(destination).expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"SWAT+ source project does not exist: {source}")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite an existing experiment bundle: {target}")
    if not 0 < threshold <= 1:
        raise ValueError("CDL majority threshold must be in (0, 1]")

    mapper = SwatCDLHRUMapper(cdl_composition, threshold=threshold)
    rows = mapper._rows()
    if any(int(row.get("cdl_year", -1)) != cdl_year for row in rows):
        raise ValueError(f"Every CDL composition row must be explicitly classified for {cdl_year}")
    selected_rows = [row for row in rows if float(row["corn_fraction"]) >= threshold]
    if not selected_rows or any(row.get("coverage_quality") != "VALID" for row in selected_rows):
        raise ValueError("Selected CDL-majority HRUs require nonempty, VALID coverage evidence")

    source_before = _input_checksums(source)
    for required in ("hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl", "plants.plt"):
        if required not in source_before:
            raise FileNotFoundError(f"Source SWAT+ project is missing {required}")

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".phase34-build-", dir=target.parent) as temp_root:
        bundle = Path(temp_root) / "bundle"
        project_copy = bundle / "project"
        bundle.mkdir()
        shutil.copytree(source, project_copy)
        mapping = mapper.apply(project_copy)
        effective_management = _activate_explicit_corn_management(project_copy)
        mapping["effective_management"] = effective_management
        selected_ids = sorted(int(row["hru_id"]) for row in selected_rows)
        if mapping["target_hrus"] != selected_ids:
            raise ValueError("CDL selected-HRU manifest differs from the source composition")

        target_names = SwatPlantParameterMapper._active_hrus(project_copy, "corn")
        expected_names = {f"hru{hru_id:02d}" for hru_id in selected_ids}
        if set(target_names) != expected_names:
            raise ValueError("Active corn HRUs differ from the verified CDL-majority HRU selection")
        crop_chain = SwatCropChainDiagnostic.input_chain(project_copy, selected_ids, crop="corn")
        if crop_chain["status"] != "PASS":
            raise ValueError("The isolated corn land-use/community/rotation chain failed validation")
        auto_management = SwatCropChainDiagnostic.auto_management_season(project_copy, target_crop="corn")
        auto_management_manifest = auto_management.provenance([])
        auto_management_manifest["season_windows"] = None
        auto_management_manifest["season_window_evaluation"] = "NOT_EVALUATED_BY_CONFIGURATION_PREPARER"
        auto_management_manifest["season_window_evaluation_reason"] = (
            "The exact requested interval and full daily forcing are evaluated by SWAT+ preflight; "
            "this configuration-only step does not assert crop-active dates."
        )

        copy_after = _input_checksums(project_copy)
        changed = sorted(
            name for name in set(source_before) | set(copy_after)
            if source_before.get(name) != copy_after.get(name)
        )
        expected_changed = ["hru-data.hru", "landuse.lum", "management.sch", "plant.ini"]
        if changed != expected_changed:
            raise ValueError(f"Unexpected source-input changes in isolated config: {changed}")
        source_after = _input_checksums(source)
        if source_after != source_before:
            raise RuntimeError("Source SWAT+ inputs changed while preparing the isolated variant")

        cdl_provenance: dict[str, Any] = {}
        provenance_path = Path(cdl_provenance_path).expanduser().resolve() if cdl_provenance_path else None
        if provenance_path and provenance_path.is_file():
            cdl_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        composition_path = Path(cdl_composition).expanduser().resolve() if isinstance(cdl_composition, (str, Path)) else None
        if composition_path and cdl_provenance.get("raster_sha256"):
            raster_path = Path(cdl_provenance.get("raster_path", ""))
            if not raster_path.is_file() or _sha256(raster_path) != cdl_provenance["raster_sha256"]:
                raise ValueError("The raster checksum does not match the saved CDL provenance")

        manifest = {
            "schema_version": "south-fork-cdl-management-experiment-v1",
            "configuration_status": "PREPARED_AND_VALIDATED",
            "classification": "EXPERIMENTAL_CDL_CORN_MAJORITY_MANAGEMENT_NOT_HISTORICAL_RECONSTRUCTION",
            "period_supported_by_land_cover_snapshot": {"start": f"{cdl_year}-01-01", "end": f"{cdl_year}-12-31"},
            "cdl_year": cdl_year,
            "cdl_threshold": threshold,
            "selected_hru_ids": selected_ids,
            "selected_hru_count": len(selected_ids),
            "cdl_mapping": mapping,
            "cdl_provenance": cdl_provenance,
            "cdl_provenance_file_sha256": _sha256(provenance_path) if provenance_path and provenance_path.is_file() else None,
            "cdl_composition_sha256": _sha256(composition_path) if composition_path and composition_path.is_file() else None,
            "source_project": str(source),
            "source_input_checksums_before_sha256": source_before,
            "source_input_checksums_after_sha256": source_after,
            "experiment_project_input_checksums_after_sha256": copy_after,
            "changed_project_files": changed,
            "unchanged_corn_species_and_decision_table": {
                name: source_before[name] == copy_after[name]
                for name in ("plants.plt", "lum.dtl")
            },
            "crop_chain_diagnostic": crop_chain,
            "auto_management": auto_management_manifest,
            "active_management_operation": effective_management,
            "management_interpretation": (
                "Only HRUs with >= threshold corn share in the static CDL snapshot are assigned the existing corn plant record "
                "and a cloned agricultural community/rotation. The generic agriculture chain is not interpreted as corn."
            ),
            "scientific_scope": {
                "scenario": "Hypothetical 2019 management experiment informed by a static 2019 CDL snapshot",
                "not_claimed": [
                    "observed planting or harvest dates", "historical crop rotation reconstruction",
                    "uniform corn assignment to all 36 HRUs", "full crop-mixture representation within each HRU",
                ],
                "expected_model_effects": [
                    "land-use management references on selected HRUs", "plant community and crop species",
                    "crop cover and growth", "potential evapotranspiration and hydrological response",
                ],
                "date_limitation": "SWAT+ auto-management PHU/soil-water conditions remain model approximations; the input project does not provide an executed sowing-event log.",
            },
        }
        (bundle / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(bundle, target)

    return {**manifest, "experiment_project": str(target / "project"), "manifest_path": str(target / "manifest.json")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-project", required=True)
    parser.add_argument("--cdl-composition", required=True)
    parser.add_argument("--cdl-provenance", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--cdl-year", type=int, default=2019)
    parser.add_argument("--threshold", type=float, default=0.50)
    args = parser.parse_args()
    result = prepare_configuration(
        args.source_project, args.cdl_composition, args.destination,
        cdl_provenance_path=args.cdl_provenance,
        cdl_year=args.cdl_year, threshold=args.threshold,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Apply a recorded CDL crop classification to copied SWAT+ HRU inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


class SwatCDLMappingError(ValueError):
    pass


class SwatCDLHRUMapper:
    """Bridge CDL-majority HRUs to the documented SWAT+ crop tables.

    The mapper operates only inside the adapter's isolated workspace.  It
    creates a corn land-use/community/rotation entry by cloning the existing
    editor-generated agricultural entry, then changes the ``lu_mgt`` field for
    the HRUs classified as corn.  Baseline and coupled runs use this exact
    same classification; only the coupled run subsequently changes
    ``plants.plt`` morphology parameters.
    """

    def __init__(self, composition: str | Path | Iterable[dict[str, Any]], *, threshold: float = 0.50):
        self.composition = composition
        self.threshold = threshold

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _rows(self) -> list[dict[str, Any]]:
        if isinstance(self.composition, (str, Path)):
            path = Path(self.composition)
            try:
                import pandas as pd
                rows = pd.read_parquet(path).to_dict(orient="records")
            except ImportError as exc:  # pragma: no cover - environment contract
                raise SwatCDLMappingError("Parquet composition requires pandas") from exc
        else:
            rows = [dict(row) for row in self.composition]
        if not rows:
            raise SwatCDLMappingError("CDL composition is empty")
        return rows

    @staticmethod
    def _ensure_cloned_table(path: Path, source_tokens: tuple[str, str], replacements: tuple[tuple[str, str], ...]) -> bool:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        # source_tokens is (source_name, target_name); an existing target is
        # idempotent, while the source is expected to be present in the editor
        # project.
        if any(line.split() and line.split()[0] == source_tokens[1] for line in lines):
            return False
        source_index = None
        for index, line in enumerate(lines):
            tokens = line.split()
            if tokens and tokens[0] == source_tokens[0]:
                source_index = index
                break
        if source_index is None:
            raise SwatCDLMappingError(f"{path.name} has no editor-generated source record {source_tokens[0]!r}")
        cloned = lines[source_index]
        for old, new in replacements:
            cloned = cloned.replace(old, new)
        lines.append(cloned)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    @staticmethod
    def _ensure_child_record(path: Path, parent: str, child: str, replacements: tuple[tuple[str, str], ...]) -> bool:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        if any(line.split() and line.split()[0] == child for line in lines):
            return False
        parent_index = next((index for index, line in enumerate(lines) if line.split() and line.split()[0] == parent), None)
        if parent_index is None:
            raise SwatCDLMappingError(f"{path.name} has no source record {parent!r}")
        # The editor writes the plant/operation row immediately after its
        # community/schedule row.  Clone that row, preserving fixed-width
        # formatting and comments exactly as supplied by the project.
        child_index = parent_index + 1
        while child_index < len(lines) and not lines[child_index].split():
            child_index += 1
        if child_index >= len(lines):
            raise SwatCDLMappingError(f"{path.name} source record {parent!r} has no child row")
        cloned = lines[child_index]
        for old, new in replacements:
            cloned = cloned.replace(old, new)
        lines.extend([lines[parent_index].replace(parent, child), cloned])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    def apply(self, workspace: str | Path) -> dict[str, Any]:
        workspace = Path(workspace)
        composition_rows = self._rows()
        corn_rows = [row for row in composition_rows if float(row["corn_fraction"]) >= self.threshold]
        if not corn_rows:
            raise SwatCDLMappingError("CDL overlay has no HRU meeting the corn-majority threshold")
        required = [workspace / name for name in ("hru-data.hru", "landuse.lum", "plant.ini", "management.sch")]
        if not all(path.is_file() for path in required):
            raise SwatCDLMappingError("hru-data.hru, landuse.lum, plant.ini and management.sch are required")

        input_checksums_before = {path.name: self._sha256(path) for path in required}

        target_ids = {str(int(row["hru_id"])) for row in corn_rows}
        hru_path = workspace / "hru-data.hru"
        hru_lines = hru_path.read_text(encoding="utf-8", errors="strict").splitlines()
        original_lu: dict[str, str] = {}
        changed = 0
        updated_lines: list[str] = []
        for line in hru_lines:
            tokens = line.split()
            if len(tokens) >= 6 and tokens[0].isdigit() and tokens[0] in target_ids:
                original_lu[tokens[0]] = tokens[5]
                if tokens[5] != "corn_lum":
                    line = line.replace(tokens[5], "corn_lum", 1)
                    changed += 1
            updated_lines.append(line)
        missing = target_ids - set(original_lu)
        if missing:
            raise SwatCDLMappingError(f"CDL HRUs are absent from hru-data.hru: {sorted(missing)}")
        hru_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

        landuse_changed = self._ensure_cloned_table(
            workspace / "landuse.lum", ("agrl_lum", "corn_lum"),
            (("agrl_lum", "corn_lum"), ("agrl_comm", "corn_comm"), ("agrl_rot", "corn_rot")),
        )
        plant_changed = self._ensure_child_record(
            workspace / "plant.ini", "agrl_comm", "corn_comm", (("agrl_comm", "corn_comm"), ("agrl", "corn")),
        )
        management_changed = self._ensure_child_record(
            workspace / "management.sch", "agrl_rot", "corn_rot", (("agrl_rot", "corn_rot"), ("agrl", "corn")),
        )
        composition_path = str(self.composition) if isinstance(self.composition, (str, Path)) else None
        input_checksums_after = {path.name: self._sha256(path) for path in required}
        by_hru = {str(int(row["hru_id"])): row for row in corn_rows}
        classification_evidence = []
        for hru_id in sorted(target_ids, key=int):
            row = by_hru[hru_id]
            classification_evidence.append({
                "hru_id": int(hru_id),
                "corn_fraction": float(row["corn_fraction"]),
                "soybean_fraction": float(row.get("soybean_fraction", 0.0)),
                "other_crop_fraction": float(row.get("other_crop_fraction", 0.0)),
                "non_crop_fraction": float(row.get("non_crop_fraction", 0.0)),
                "dominant_class": row.get("dominant_class"),
                "dominant_class_name": row.get("dominant_class_name"),
                "cdl_year": int(row.get("cdl_year", 0)),
                "coverage_quality": row.get("coverage_quality", "UNSPECIFIED"),
                "original_lu_mgt": original_lu[hru_id],
                "new_lu_mgt": "corn_lum",
                "new_plant_community": "corn_comm",
                "new_rotation": "corn_rot",
                "new_plant": "corn",
            })
        return {
            "status": "APPLIED",
            "classification": "STATIC_CDL_SNAPSHOT",
            "target_plant_name": "corn",
            "corn_majority_threshold": self.threshold,
            "target_hrus": [int(value) for value in sorted(target_ids, key=int)],
            "classification_evidence": classification_evidence,
            "original_lu_mgt": original_lu,
            "changed_hru_count": changed,
            "created_records": {"landuse.lum": landuse_changed, "plant.ini": plant_changed, "management.sch": management_changed},
            "workspace_input_files_modified": ["hru-data.hru", "landuse.lum", "plant.ini", "management.sch"],
            "workspace_input_checksums": {
                "before_sha256": input_checksums_before,
                "after_sha256": input_checksums_after,
            },
            "composition_parquet": composition_path,
            "composition_sha256": self._sha256(Path(composition_path)) if composition_path else None,
            "mapping": "CDL corn-majority HRU -> corn_lum -> corn_comm -> corn_rot -> corn",
            "scientific_rationale": "A majority-pixel corn classification is the minimum explicit bridge from the official static CDL snapshot to the SWAT+ plant community; no non-corn HRU is changed.",
            "not_coupled": ["soybean and other crop fractions remain classified in the manifest but are not changed because this phase maps maize only"],
        }

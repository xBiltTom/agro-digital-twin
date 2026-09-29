"""Load and prepare published FSPM/SWAT+ result artifacts.

The loader deliberately keeps simulation outputs separate from observations and
from the synthetic development dataset.  It validates the manifest contract,
dates and identifiers before creating a monthly, basin-supported learning
table.  HRU tables remain available independently because the published
artifacts do not provide verifiable per-HRU area weights.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pandas as pd


REQUIRED_ARTIFACTS = (
    "basin_daily.csv",
    "hru_daily.csv",
    "plant_hru_daily.csv",
    "channel_daily.csv",
    "climate_daily.csv",
    "fspm_field_daily.csv",
    "fspm_calendar_group_daily.csv",
    "fspm_plant_samples_daily.csv",
)

REAL_DATASET_CLASSIFICATION = "SWAT_FSPM_SIMULATION_RESULTS"
REAL_DATASET_ORIGIN = "South Fork 2019 published SWAT+ and FSPM result artifacts"

AGGREGATION_RULES = {
    "precip_mm": "sum of daily mm/day values; output mm/month",
    "runoff_mm": "sum of daily mm/day values; output mm/month",
    "evapotranspiration_mm": "sum of daily mm/day values; output mm/month",
    "percolation_mm": "sum of daily mm/day values; output mm/month",
    "streamflow_m3s": "mean of daily m3/s values; output m3/s",
    "temp_c": "mean of daily degC values",
    "solar_rad_mj": "mean of daily MJ/m2/day values",
    "fspm_state": "mean for state variables; sum for daily fluxes",
    "soil_water_mm": "retained as storage in mm; never converted to volumetric percent",
}

VARIABLE_UNITS = {
    "date": "date",
    "temp_c": "degC",
    "precip_mm": "mm/day",
    "solar_rad_mj": "MJ/m2/day",
    "rh_percent": "%",
    "wind_speed_ms": "m/s",
    "pet_mm": "mm/day",
    "streamflow_m3s": "m3/s",
    "runoff_mm": "mm/day",
    "percolation_mm": "mm/day",
    "evapotranspiration_mm": "mm/day",
    "soil_water_mm": "mm storage",
    "soil_water_average_mm": "mm storage",
    "field.soil_moisture_vol": "volumetric percent [0, 100]",
    "field.mean_LAI": "m2_leaf/m2_ground",
    "field.mean_lai": "m2_leaf/m2_ground",
    "field.root_depth_mean_m": "m",
    "field.transpiration_mm_day": "mm/day",
    "field.water_stress": "fraction [0, 1]",
    "field.actual_ET_mm_day": "mm/day",
    "field.biomass_g_plant": "g/plant",
}


@dataclass
class RealArtifactDataset:
    """Validated result files plus provenance used by the laboratory."""

    artifact_dir: Path
    manifest: Dict[str, Any]
    frames: Dict[str, pd.DataFrame]
    metadata: Dict[str, Any]

    @property
    def dataset_id(self) -> str:
        return str(self.manifest.get("run_id", self.artifact_dir.name))

    @property
    def date_start(self) -> pd.Timestamp:
        return min(pd.to_datetime(frame["date"]).min() for frame in self.frames.values())

    @property
    def date_end(self) -> pd.Timestamp:
        return max(pd.to_datetime(frame["date"]).max() for frame in self.frames.values())

    def variable_summary(self) -> pd.DataFrame:
        """Return manifest-backed variable and provenance information."""
        rows = []
        for filename, descriptor in self.manifest.get("artifacts", {}).items():
            if filename not in self.frames:
                continue
            for column in descriptor.get("columns", []):
                rows.append({
                    "archivo": filename,
                    "variable": column,
                    "unidad": VARIABLE_UNITS.get(column, "consultar manifest / columna units"),
                    "origen": descriptor.get("data_origin", "no especificado"),
                    "escala": descriptor.get("spatial_scale", "no especificada"),
                })
        return pd.DataFrame(rows)

    def build_monthly_learning_dataset(self) -> pd.DataFrame:
        """Build a basin-supported monthly table without leaking target values.

        Climate and basin features are complete for 2019.  FSPM states are
        joined for inspection when active, but remain null outside the emitted
        crop window.  Consumers must select a strict complete-case contract;
        this method never fills missing simulation states.
        """
        climate = self.frames["climate_daily.csv"].copy()
        basin = self.frames["basin_daily.csv"].copy()
        climate["month"] = climate["date"].dt.to_period("M")
        basin["month"] = basin["date"].dt.to_period("M")

        climate_monthly = climate.groupby("month", as_index=False).agg(
            precip_mm=("precip_mm", "sum"),
            temp_mean_c=("temp_c", "mean"),
            solar_radiation=("solar_rad_mj", "mean"),
            relative_humidity_percent=("rh_percent", "mean"),
            wind_speed_ms=("wind_speed_ms", "mean"),
        )
        pet_monthly = climate.groupby("month", as_index=False)["pet_mm"].sum(min_count=1)
        climate_monthly = climate_monthly.merge(pet_monthly, on="month", how="left")
        basin_monthly = basin.groupby("month", as_index=False).agg(
            infiltration_mm=("percolation_mm", "sum"),
            et_mm=("evapotranspiration_mm", "sum"),
            monthly_runoff_mm=("runoff_mm", "sum"),
            monthly_streamflow_m3s=("streamflow_m3s", "mean"),
            soil_water_storage_mm=("soil_water_mm", "mean"),
            soil_water_average_mm=("soil_water_average_mm", "mean"),
        )

        monthly = climate_monthly.merge(basin_monthly, on="month", how="inner", validate="one_to_one")
        monthly["date"] = monthly["month"].dt.to_timestamp()

        field = self.frames["fspm_field_daily.csv"].copy()
        field["month"] = field["date"].dt.to_period("M")
        field_values = {
            "soil_moisture": "field.soil_moisture_vol",
            "lai": "field.mean_LAI",
            "root_depth_m": "field.root_depth_mean_m",
            "transpiration_mm": "field.transpiration_mm_day",
            "water_stress": "field.water_stress",
            "fspm_et_mm": "field.actual_ET_mm_day",
            "fspm_biomass_g_plant": "field.biomass_g_plant",
        }
        field_monthly = pd.DataFrame({"month": field["month"].drop_duplicates().to_numpy()})
        for output, source in field_values.items():
            if source not in field.columns:
                continue
            values = pd.to_numeric(field[source], errors="coerce")
            aggregation = "sum" if output in {"transpiration_mm", "fspm_et_mm"} else "mean"
            grouped_frame = field.assign(_value=values).groupby("month")["_value"]
            grouped_values = grouped_frame.sum(min_count=1) if aggregation == "sum" else grouped_frame.mean()
            grouped = grouped_values.rename(output).reset_index()
            field_monthly = field_monthly.merge(grouped, on="month", how="left", validate="one_to_one")
        monthly = monthly.merge(field_monthly, on="month", how="left")

        monthly["watershed_id"] = "south_fork"
        monthly["hru_id"] = "basin"
        monthly["data_classification"] = REAL_DATASET_CLASSIFICATION
        monthly["data_provenance"] = REAL_DATASET_ORIGIN
        monthly["is_synthetic"] = False
        monthly["is_observation"] = False
        monthly["dataset_id"] = self.dataset_id
        monthly = monthly.drop(columns=["month"])
        return monthly.sort_values("date").reset_index(drop=True)

    def hru_monthly_tables(self) -> Dict[str, pd.DataFrame]:
        """Aggregate HRU files while preserving their spatial support."""
        result: Dict[str, pd.DataFrame] = {}
        for filename in ("hru_daily.csv", "plant_hru_daily.csv"):
            frame = self.frames[filename].copy()
            id_column = "hru_unit"
            frame["month"] = frame["date"].dt.to_period("M")
            numeric_columns = frame.select_dtypes(include="number").columns.tolist()
            aggregations = {column: "mean" for column in numeric_columns if column != id_column}
            for column in ("precip_mm", "runoff_mm", "percolation_mm", "evapotranspiration_mm"):
                if column in aggregations:
                    aggregations[column] = "sum"
            result[filename] = frame.groupby([id_column, "month"], as_index=False).agg(aggregations)
        return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_artifact_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root.resolve() not in path.parents:
        raise ValueError(f"Manifest path escapes artifact directory: {relative_path}")
    return path


def _validate_frame(filename: str, frame: pd.DataFrame, descriptor: Mapping[str, Any]) -> None:
    expected_columns = descriptor.get("columns", [])
    missing_columns = sorted(set(expected_columns) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"{filename} is missing manifest columns: {', '.join(missing_columns)}")
    if "date" in frame.columns:
        if frame["date"].isna().any():
            raise ValueError(f"{filename} contains invalid dates")
    date_columns = descriptor.get("date_columns", [])
    for column in date_columns:
        if column in frame.columns and pd.to_datetime(frame[column], errors="coerce").isna().any():
            raise ValueError(f"{filename} contains invalid values in date column '{column}'")

    identifier_columns = [column for column in ("hru_unit", "channel_unit", "calendar_id", "plant.plant_id") if column in frame.columns]
    if "date" in frame.columns and identifier_columns:
        if frame.duplicated(["date", *identifier_columns]).any():
            raise ValueError(f"{filename} has duplicate date/entity identifiers")
    elif "date" in frame.columns and filename == "basin_daily.csv":
        if frame.duplicated(["date"]).any():
            raise ValueError("basin_daily.csv has duplicate dates")


def load_real_artifact_dataset(
    artifact_dir: str | Path,
    verify_checksums: bool = False,
) -> RealArtifactDataset:
    """Load one published run, validating only files within ``artifact_dir``."""
    root = Path(artifact_dir).expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json not found in artifact directory: {root}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    artifacts = manifest.get("artifacts", {})
    missing_descriptors = [filename for filename in REQUIRED_ARTIFACTS if filename not in artifacts]
    if missing_descriptors:
        raise ValueError(f"Manifest does not describe required artifacts: {', '.join(missing_descriptors)}")

    frames: Dict[str, pd.DataFrame] = {}
    for filename in REQUIRED_ARTIFACTS:
        descriptor = artifacts[filename]
        path = _safe_artifact_path(root, descriptor.get("path", filename))
        if not path.is_file():
            raise FileNotFoundError(f"Artifact referenced by manifest is missing: {path}")
        if verify_checksums and descriptor.get("sha256") and _sha256(path) != descriptor["sha256"]:
            raise ValueError(f"Checksum mismatch for artifact: {filename}")
        frame = pd.read_csv(path, low_memory=False)
        for date_column in descriptor.get("date_columns", []):
            if date_column in frame.columns:
                frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        _validate_frame(filename, frame, descriptor)
        frames[filename] = frame

    date_ranges = {
        filename: [str(frame["date"].min().date()), str(frame["date"].max().date())]
        for filename, frame in frames.items()
        if "date" in frame.columns
    }
    metadata = {
        "dataset_id": str(manifest.get("run_id", root.name)),
        "dataset_version": str(manifest.get("run_id", root.name)),
        "source_kind": "simulation_results",
        "artifact_classification": REAL_DATASET_CLASSIFICATION,
        "is_synthetic_training_data": False,
        "is_observation": False,
        "origin": REAL_DATASET_ORIGIN,
        "project": manifest.get("project", {}).get("name"),
        "status": manifest.get("status"),
        "date_ranges": date_ranges,
        "period": [min(value[0] for value in date_ranges.values()), max(value[1] for value in date_ranges.values())],
        "aggregation_rules": AGGREGATION_RULES,
        "limitations": [
            "Resultados simulados de SWAT+ y FSPM; no son observaciones de campo.",
            "La corrida de 2019 cubre un solo periodo anual y no permite validar modelos complejos con solidez.",
            "Las tablas HRU no se agregan espacialmente al basin porque el peso por HRU no está disponible en estos archivos.",
        ],
    }
    return RealArtifactDataset(root, manifest, frames, metadata)


def default_south_fork_artifact_dir() -> Path:
    """Resolve the published run relative to the repository, not a user machine."""
    project_root = Path(__file__).resolve().parents[4]
    return project_root / "from-plant-to-watershed" / "backend" / "data" / "phase1-south-fork-2019" / "results" / "phase1-sf-2019-v3"

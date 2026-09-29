"""Tests for the published South Fork artifact loader and strict contract."""

from pathlib import Path

from src.core.datasets.real_loader import (
    REAL_DATASET_CLASSIFICATION,
    load_real_artifact_dataset,
)
from src.core.features.schema import get_available_feature_schema


def south_fork_artifact_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "from-plant-to-watershed"
        / "backend"
        / "data"
        / "phase1-south-fork-2019"
        / "results"
        / "phase1-sf-2019-v3"
    )


def test_load_south_fork_manifest_and_monthly_contract():
    artifact = load_real_artifact_dataset(south_fork_artifact_dir())
    monthly = artifact.build_monthly_learning_dataset()

    assert artifact.metadata["artifact_classification"] == REAL_DATASET_CLASSIFICATION
    assert artifact.metadata["is_synthetic_training_data"] is False
    assert len(monthly) == 12
    assert monthly["date"].min().strftime("%Y-%m-%d") == "2019-01-01"
    assert monthly["date"].max().strftime("%Y-%m-%d") == "2019-12-01"
    assert monthly["monthly_streamflow_m3s"].notna().all()
    assert monthly["soil_water_storage_mm"].notna().all()
    assert monthly.loc[monthly["date"].dt.month <= 4, "transpiration_mm"].isna().all()

    schema = get_available_feature_schema(monthly, target_name="monthly_runoff_mm")
    assert schema.strict_missing is True
    assert "monthly_runoff_mm" not in schema.feature_names
    assert "soil_moisture" not in schema.feature_names
    assert "infiltration_mm" in schema.feature_names


def test_hru_tables_preserve_spatial_support():
    artifact = load_real_artifact_dataset(south_fork_artifact_dir())
    hru_monthly = artifact.hru_monthly_tables()["hru_daily.csv"]

    assert hru_monthly["hru_unit"].nunique() == 36
    assert len(hru_monthly) == 36 * 12
    assert "month" in hru_monthly.columns

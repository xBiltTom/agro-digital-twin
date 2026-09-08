from pathlib import Path

import pytest

from app.schemas.observation import DatasetArtifactRegister
from app.services.dataset_artifacts import _safe_artifact_path
from scientific_core.climate_file import Cmip6FileProvider


def test_artifact_registration_path_is_confined_to_data_root(tmp_path: Path):
    root = tmp_path / "data"
    root.mkdir()
    artifact = root / "cmip6.csv"
    artifact.write_text("date,precip_mm,temp_c\\n2020-01-01,1,20\\n")
    assert _safe_artifact_path(str(root), str(artifact)) == artifact.resolve()
    outside = tmp_path / "outside.csv"
    outside.write_text("not allowed")
    with pytest.raises(ValueError, match="DATA_ARTIFACT_ROOT"):
        _safe_artifact_path(str(root), str(outside))


def test_dataset_artifact_contract_accepts_cmip6_metadata():
    payload = DatasetArtifactRegister(
        provider="NEX-GDDP-CMIP6", dataset_name="SSP2-4.5 pilot", variable="climate forcing",
        unit="mixed", temporal_resolution="daily", spatial_support="pilot watershed",
        source_reference="https://example.edu/nex-gddp", artifact_path="data/climate/cmip6/ssp245.csv",
        metadata_json={"scenario": "SSP2-4.5", "gcm": "declared", "bias_correction": "declared by source"},
    )
    assert payload.provider == "NEX-GDDP-CMIP6"


def test_cmip6_file_provider_requires_declared_bias_correction(tmp_path: Path):
    csv_path = tmp_path / "ssp245.csv"
    metadata_path = tmp_path / "ssp245.json"
    csv_path.write_text("date,precip_mm,temp_c\\n2020-01-01,1,20\\n")
    metadata_path.write_text('{"scenario":"SSP2-4.5","gcm":"gcm","member":"r1","period":"2020","variables":["pr","tas"],"units":{},"calendar":"gregorian","source":"NEX"}')
    with pytest.raises(ValueError, match="bias_correction"):
        Cmip6FileProvider(csv_path, metadata_path).load()

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class UsgsIngestRequest(BaseModel):
    station_id: str = Field(pattern=r"^\d{8,15}$")
    start_date: date
    end_date: date


class DatasetResponse(BaseModel):
    id: str
    provider: str
    dataset_name: str
    version: Optional[str]
    variable: str
    unit: str
    temporal_resolution: str
    spatial_support: str
    coverage_start: Optional[date]
    coverage_end: Optional[date]
    source_reference: str
    license: Optional[str]
    evidence_type: str
    quality_control: dict[str, Any]
    metadata_json: dict[str, Any]
    retrieved_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DatasetArtifactRegister(BaseModel):
    """Register an operator-provided, local data artifact without inventing observations."""
    provider: str = Field(min_length=2, max_length=80)
    dataset_name: str = Field(min_length=2, max_length=160)
    version: Optional[str] = Field(default=None, max_length=100)
    variable: str = Field(min_length=2, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    temporal_resolution: str = Field(min_length=2, max_length=40)
    spatial_support: str = Field(min_length=2, max_length=160)
    source_reference: str = Field(min_length=8)
    evidence_type: str = Field(default="OBSERVED", pattern="^(OBSERVED|DERIVED|MODELLED)$")
    artifact_kind: str = Field(default="NORMALIZED", pattern="^(RAW|NORMALIZED|DERIVED)$")
    artifact_path: str = Field(min_length=1)
    content_type: str = Field(default="text/csv", max_length=100)
    coverage_start: Optional[date] = None
    coverage_end: Optional[date] = None
    license: Optional[str] = None
    quality_control: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DatasetArtifactResponse(BaseModel):
    id: str
    dataset_id: str
    artifact_kind: str
    storage_path: str
    checksum_sha256: str
    content_type: str
    byte_size: int
    metadata_json: dict[str, Any]
    model_config = ConfigDict(from_attributes=True)


class StreamflowObservationResponse(BaseModel):
    station_id: str
    observed_on: date
    value_m3s: Optional[float]
    original_value: Optional[float]
    original_unit: str
    variable: str
    quality_status: Optional[str]
    source: str
    model_config = ConfigDict(from_attributes=True)

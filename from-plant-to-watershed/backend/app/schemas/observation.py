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

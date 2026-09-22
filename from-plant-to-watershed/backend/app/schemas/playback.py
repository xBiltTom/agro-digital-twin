"""Versioned, source-aware temporal state exposed by the playback API."""

from datetime import date
from enum import Enum
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "twin-playback-v1"
Resolution = Literal["DAILY", "MONTHLY", "ANNUAL"]
Availability = Literal["AVAILABLE", "NOT_AVAILABLE"]


class Evidence(str, Enum):
    OBSERVED = "OBSERVED"
    MODELLED_SWAT_PLUS = "MODELLED_SWAT_PLUS"
    SIMPLIFIED_FSPM = "SIMPLIFIED_FSPM"
    SIMPLIFIED_HYDROLOGY = "SIMPLIFIED_HYDROLOGY"
    DERIVED = "DERIVED"
    ASSUMED = "ASSUMED"
    SYNTHETIC = "SYNTHETIC"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class VariableState(BaseModel):
    value: float | str | None
    unit: str
    evidence: Evidence
    source: str
    availability: Availability
    limitation: str | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def availability_matches_value(self):
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("Playback scientific variables must be finite")
        if (self.value is None) != (self.availability == "NOT_AVAILABLE"):
            raise ValueError("A missing variable must have a null value and NOT_AVAILABLE status")
        if self.value is None and self.evidence != Evidence.NOT_AVAILABLE:
            raise ValueError("A missing variable must have NOT_AVAILABLE evidence")
        return self


class CropState(BaseModel):
    active: bool
    crop: str | None = None
    season_id: str | None = None
    phenological_stage: str | None = None
    window_status: str | None = None
    source: str
    limitation: str | None = None


class PlantSample(BaseModel):
    plant_id: str
    x_m: float
    y_m: float
    variables: dict[str, VariableState]


class HruState(BaseModel):
    hru_id: str
    spatial_support: str
    variables: dict[str, VariableState]
    polygon_id: str | None = None


class PlaybackRecord(BaseModel):
    schema_version: Literal["twin-playback-v1"] = SCHEMA_VERSION
    simulation_id: str
    date: date
    resolution: Resolution
    run_type: str
    watershed_id: str
    watershed_code: str | None = None
    outlet_unit: str | None = None
    spatial_support: str
    weather: dict[str, VariableState] = Field(default_factory=dict)
    crop: CropState | None = None
    field: dict[str, VariableState] = Field(default_factory=dict)
    plant_samples: list[PlantSample] = Field(default_factory=list)
    hydrology: dict[str, VariableState] = Field(default_factory=dict)
    hru_results: list[HruState] = Field(default_factory=list)
    availability: dict[str, Availability] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class PlaybackPage(BaseModel):
    schema_version: Literal["twin-playback-v1"] = SCHEMA_VERSION
    simulation_id: str
    simulation_status: str
    artifact_status: str
    resolution: Resolution | None
    available_resolutions: list[Resolution] = Field(default_factory=list)
    total: int
    offset: int
    limit: int
    records: list[PlaybackRecord]
    variables: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)

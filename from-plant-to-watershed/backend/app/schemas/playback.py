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
    calendar_id: str | None = None
    hru_ids: list[str] = Field(default_factory=list)
    variables: dict[str, VariableState]


class PlantSampleContext(BaseModel):
    population_count: int | None = Field(default=None, ge=0)
    captured_count: int = Field(ge=0)
    selection_method: Literal["NONE", "ALL_REPRESENTATIVE_STATES", "EVENLY_SPACED_STABLE_IDS"]
    identity_scope: Literal["SIMULATION_SLOT", "UNSPECIFIED"] = "UNSPECIFIED"
    identity_semantics: str

    @model_validator(mode="after")
    def sample_count_does_not_exceed_population(self):
        if self.population_count is not None and self.captured_count > self.population_count:
            raise ValueError("captured_count cannot exceed population_count")
        if (self.captured_count == 0) != (self.selection_method == "NONE"):
            raise ValueError("NONE selection is required exactly when no plant samples were captured")
        return self


class HruState(BaseModel):
    hru_id: str
    spatial_support: str
    variables: dict[str, VariableState]
    polygon_id: str | None = None
    gis_id: str | None = None
    calendar_id: str | None = None
    crop: CropState | None = None


class ChannelState(BaseModel):
    channel_id: str
    gis_id: str | None = None
    spatial_support: str = "SWAT_CHANNEL_OUTPUT_UNIT_NO_VERIFIED_GEOMETRY"
    variables: dict[str, VariableState]
    geometry_id: str | None = None


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
    plant_sample_context: PlantSampleContext | None = None
    hydrology: dict[str, VariableState] = Field(default_factory=dict)
    hru_results: list[HruState] = Field(default_factory=list)
    channel_results: list[ChannelState] = Field(default_factory=list)
    availability: dict[str, Availability] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def plant_sample_metadata_matches_record(self):
        identifiers = [sample.plant_id for sample in self.plant_samples]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("plant_samples must have unique stable plant_id values per date")
        if self.plant_sample_context and self.plant_sample_context.captured_count != len(self.plant_samples):
            raise ValueError("plant_sample_context.captured_count must match plant_samples")
        return self


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

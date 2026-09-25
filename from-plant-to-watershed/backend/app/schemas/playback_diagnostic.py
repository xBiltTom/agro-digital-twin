"""Small, owner-scoped availability contract for the 3D client."""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.playback import Resolution


class AvailabilityCode(str, Enum):
    NO_PLAYBACK_ARTIFACT = "NO_PLAYBACK_ARTIFACT"
    ARTIFACT_UNAVAILABLE = "ARTIFACT_UNAVAILABLE"
    ARTIFACT_INVALID = "ARTIFACT_INVALID"
    SWAT_BASELINE_NO_FSPM = "SWAT_BASELINE_NO_FSPM"
    HYDROLOGY_ONLY = "HYDROLOGY_ONLY"
    HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"
    OUTSIDE_CROP_SEASON = "OUTSIDE_CROP_SEASON"
    FSPM_STATE_MISSING = "FSPM_STATE_MISSING"
    DATE_NOT_IN_PLAYBACK = "DATE_NOT_IN_PLAYBACK"
    UNSUPPORTED_CROP_GEOMETRY = "UNSUPPORTED_CROP_GEOMETRY"
    FIELD_HEIGHT_MISSING = "FIELD_HEIGHT_MISSING"
    FIELD_LAI_MISSING = "FIELD_LAI_MISSING"
    NO_PLANT_SAMPLES = "NO_PLANT_SAMPLES"
    SAMPLE_HEIGHT_MISSING = "SAMPLE_HEIGHT_MISSING"
    SCIENTIFIC_STATE_AVAILABLE = "SCIENTIFIC_STATE_AVAILABLE"


class DateInterval(BaseModel):
    start: date
    end: date
    season_id: str | None = None
    approximate: bool = False


class DateAvailability(BaseModel):
    date: date
    resolution: Resolution
    mode: Literal["SCIENTIFIC_ACTIVE", "SCIENTIFIC_FALLOW", "HYDROLOGY_ONLY", "HISTORICAL_REFERENCE", "DATA_UNAVAILABLE"]
    codes: list[AvailabilityCode]
    field_representable: bool = False
    sample_representable: bool = False
    missing_variables: list[str] = Field(default_factory=list)


class ResolutionAvailability(BaseModel):
    resolution: Resolution
    artifact_status: Literal["AVAILABLE", "UNAVAILABLE", "INVALID"]
    record_count: int = 0
    first_record: date | None = None
    last_record: date | None = None
    first_active_crop: date | None = None
    first_representable_field: date | None = None
    first_plant_samples: date | None = None
    crop_intervals: list[DateInterval] = Field(default_factory=list)
    hydrology_available: bool = False
    fspm_trajectory_available: bool = False
    hru_ids: list[str] = Field(default_factory=list)
    selected_date: DateAvailability | None = None
    codes: list[AvailabilityCode] = Field(default_factory=list)


class SimulationAvailability(BaseModel):
    simulation_id: str
    simulation_name: str
    simulation_status: str
    run_type: str
    origin: Literal["EXECUTED", "HISTORICAL_IMPORT", "UNKNOWN"]
    stored_hydrology_available: bool = False
    stored_fspm_summary_available: bool = False
    available_resolutions: list[Resolution] = Field(default_factory=list)
    resolutions: list[ResolutionAvailability] = Field(default_factory=list)
    codes: list[AvailabilityCode] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

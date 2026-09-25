from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- Climate Scenarios ---
class ClimateScenarioResponse(BaseModel):
    id: str
    code: str
    name: str
    pathway: str
    description: str
    temp_anomaly_c: float
    precip_factor: float
    co2_ppm: float
    source_type: str
    model_config = ConfigDict(from_attributes=True)

# --- Plant Species ---
class PlantSpeciesResponse(BaseModel):
    id: str
    name: str
    scientific_name: str
    crop_type: str
    base_kc: float
    max_root_depth_cm: float
    optimal_temp_c: float
    model_config = ConfigDict(from_attributes=True)

# --- Watershed & HRUs ---
class HRUResponse(BaseModel):
    id: str
    hru_number: int
    land_use: str
    soil_type: str
    curve_number_ii: float
    area_fraction: float
    plant_species: Optional[PlantSpeciesResponse] = None
    model_config = ConfigDict(from_attributes=True)

class SubbasinResponse(BaseModel):
    id: str
    subbasin_number: int
    name: str
    area_km2: float
    mean_slope_percent: float
    hrus: List[HRUResponse] = []
    model_config = ConfigDict(from_attributes=True)

class WatershedResponse(BaseModel):
    id: str
    code: str
    name: str
    country: str
    area_km2: float
    elevation_min_m: float
    elevation_max_m: float
    outlet_lat: float
    outlet_lon: float
    dem_metadata: Optional[Dict[str, Any]] = None
    subbasins: List[SubbasinResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Simulation Run ---
class SwatPlusConfiguration(BaseModel):
    """Explicit, portable contract for one real SWAT+ baseline execution."""
    project_path: Optional[str] = None
    executable_path: Optional[str] = None
    working_directory: Optional[str] = None
    warmup_period: int = Field(default=0, ge=0, le=36500)
    output_frequency: Literal["DAILY", "MONTHLY", "ANNUAL"] = "DAILY"
    outlet_unit: Optional[str] = None
    timeout_seconds: int = Field(default=3600, ge=1, le=86400)
    run_type: Literal["SWAT_STANDARD_BASELINE", "SWAT_MULTISCALE_COUPLED"] = "SWAT_STANDARD_BASELINE"
    target_plant_name: str = Field(default="corn", min_length=1, max_length=64)
    model_config = ConfigDict(extra="forbid")

class SimulationRunCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    watershed_id: str
    scenario_id: str
    duration_days: int = Field(default=365, ge=1, le=3650)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    irrigation_efficiency: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None
    mode: str = Field(default="RESEARCH_MULTISCALE", pattern="^(RESEARCH_MULTISCALE|DEVELOPMENT_LEGACY_DEMO|DEMO_MULTISCALE|REAL_OBSERVATION|ML_ASSISTED|SWAT_PLUS)$")
    plant_count: int = Field(default=1000, ge=1, le=10000)
    hydrology_backend: str = Field(default="SIMPLIFIED", pattern="^(SIMPLIFIED|SWAT_PLUS)$")
    external_model_id: Optional[str] = None
    station_id: Optional[str] = Field(default=None, pattern=r"^\d{8,15}$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    management_scenario: Literal["BASELINE", "NO_TILL", "MAIZE_TO_SORGHUM"] = "BASELINE"
    climate_source: Literal["SYNTHETIC", "CMIP6_FILE", "OBSERVED", "OBSERVED_HYBRID", "SWAT_PROJECT"] = "SYNTHETIC"
    dataset_ids: List[str] = Field(default_factory=list, max_length=20)
    dataset_roles: Dict[str, Literal["FORCING", "OBSERVATION", "SOIL_INPUT", "LAND_COVER", "YIELD_OBSERVATION", "VALIDATION", "CONTEXT_ONLY"]] = Field(default_factory=dict)
    swat_plus: Optional[SwatPlusConfiguration] = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_unsupported_irrigation_efficiency(self):
        if self.irrigation_efficiency is not None:
            raise ValueError("irrigation_efficiency is not implemented; use irrigation_mm_per_day in parameters")
        is_swat = self.hydrology_backend == "SWAT_PLUS" or self.mode == "SWAT_PLUS"
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("start_date and end_date must be supplied together")
        if self.start_date is None:
            if is_swat:
                raise ValueError("SWAT+ runs require explicit start_date and end_date")
            # Compatibility for the existing deterministic synthetic/proxy API.
            self.start_date = date(2000, 1, 1)
            self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if (self.end_date - self.start_date).days + 1 != self.duration_days:
            raise ValueError("duration_days must equal the inclusive start_date/end_date period")
        if unknown_role_ids := set(self.dataset_roles) - set(self.dataset_ids):
            raise ValueError(f"dataset_roles reference unselected datasets: {', '.join(sorted(unknown_role_ids))}")
        requires_external_forcing = self.climate_source in {"CMIP6_FILE", "OBSERVED", "OBSERVED_HYBRID"}
        if requires_external_forcing and "FORCING" not in self.dataset_roles.values():
            raise ValueError("a non-synthetic climate_source requires one selected FORCING dataset")
        if self.climate_source == "OBSERVED_HYBRID":
            raise ValueError("OBSERVED_HYBRID is not implemented; use OBSERVED until a documented hybrid forcing transformation exists")
        if is_swat:
            if self.hydrology_backend != "SWAT_PLUS" or self.mode != "SWAT_PLUS":
                raise ValueError("SWAT+ runs require both hydrology_backend and mode to be SWAT_PLUS")
            if self.swat_plus is None:
                raise ValueError("SWAT+ runs require a swat_plus configuration")
            if self.parameters:
                raise ValueError("parameters are only implemented by the SIMPLIFIED backend; SWAT+ uses its documented crop mapper")
            if self.management_scenario != "BASELINE":
                raise ValueError("management_scenario is not yet implemented for SWAT+ runs")
            if self.external_model_id:
                raise ValueError("external_model_id is only implemented by the SIMPLIFIED backend")
            if self.climate_source != "SWAT_PROJECT":
                raise ValueError("SWAT+ runs require climate_source=SWAT_PROJECT because forcing is read from the configured SWAT+ project")
            invalid_swat_dataset_roles = set(self.dataset_roles.values()) - {"CONTEXT_ONLY"}
            if invalid_swat_dataset_roles:
                raise ValueError("SWAT+ dataset attachments are provenance-only until input mappers are implemented; use CONTEXT_ONLY")
        else:
            unsupported_input_roles = set(self.dataset_roles.values()) & {"SOIL_INPUT", "LAND_COVER", "YIELD_OBSERVATION"}
            if unsupported_input_roles:
                raise ValueError("SOIL_INPUT, LAND_COVER and YIELD_OBSERVATION are not yet consumed by the SIMPLIFIED backend; attach them as CONTEXT_ONLY")
        return self

class SimulationResultResponse(BaseModel):
    day_index: int
    date_str: str
    precip_mm: float
    temp_c: float
    solar_rad_mj: float
    potential_et_mm: float
    actual_et_mm: float
    surface_runoff_mm: float
    percolation_mm: float
    streamflow_m3s: float
    soil_moisture_vol: float
    plant_transpiration_mm: float
    root_water_uptake_mm: float
    cwsi_stress_index: float
    sap_flow_velocity_cmh: float
    water_balance_residual_mm: float
    model_config = ConfigDict(from_attributes=True)

class SimulationRunResponse(BaseModel):
    id: str
    user_id: str
    watershed_id: str
    scenario_id: str
    name: str
    status: str
    duration_days: int
    irrigation_efficiency: Optional[float]
    seed: int
    requested_config: Optional[Dict[str, Any]] = None
    effective_config: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    mode: str = "RESEARCH_MULTISCALE"
    plant_count: int = 1000
    hydrology_backend: str = "SIMPLIFIED"
    external_model_id: Optional[str] = None
    field_aggregates: Optional[Dict[str, Any]] = None
    hru_aggregates: Optional[Dict[str, Any]] = None
    plant_sample: Optional[List[Dict[str, Any]]] = None
    monthly_outputs: Optional[List[Dict[str, Any]]] = None
    validation: Optional[Dict[str, Any]] = None
    ml_result: Optional[Dict[str, Any]] = None
    management_scenario: str = "BASELINE"
    climate_source: str = "SYNTHETIC"
    dataset_ids: List[str] = Field(default_factory=list)
    dataset_roles: Dict[str, str] = Field(default_factory=dict)
    station_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    scenario: Optional[ClimateScenarioResponse] = None
    summary_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("dataset_ids", mode="before")
    @classmethod
    def normalize_legacy_dataset_ids(cls, value):
        """Legacy rows predate the manifest field and persist it as NULL."""
        return [] if value is None else value

    @field_validator("dataset_roles", mode="before")
    @classmethod
    def normalize_legacy_dataset_roles(cls, value):
        return {} if value is None else value


class AIInsightsResponse(BaseModel):
    simulation_id: Optional[str] = None
    simulation_name: Optional[str] = None
    provider: str
    generated_at: str
    executive_summary: str
    multiscale_biophysical_diagnosis: Dict[str, str]
    climate_resilience_assessment: str
    policy_recommendations: List[str]
    limitations_and_uncertainty: str
    raw_metrics_analyzed: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


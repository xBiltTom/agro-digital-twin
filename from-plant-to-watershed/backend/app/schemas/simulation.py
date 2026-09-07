from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

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
class SimulationRunCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    watershed_id: str
    scenario_id: str
    duration_days: int = Field(default=365, ge=1, le=3650)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    irrigation_efficiency: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_unsupported_irrigation_efficiency(self):
        if self.irrigation_efficiency is not None:
            raise ValueError("irrigation_efficiency is not implemented; use irrigation_mm_per_day in parameters")
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
    scenario: Optional[ClimateScenarioResponse] = None
    summary_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

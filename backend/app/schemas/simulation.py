from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

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
    name: str
    watershed_id: str
    scenario_id: str
    duration_days: int = 365
    irrigation_efficiency: float = 0.85
    parameters: Optional[Dict[str, Any]] = None

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
    model_config = ConfigDict(from_attributes=True)

class SimulationRunResponse(BaseModel):
    id: str
    user_id: str
    watershed_id: str
    scenario_id: str
    name: str
    status: str
    duration_days: int
    irrigation_efficiency: float
    scenario: Optional[ClimateScenarioResponse] = None
    summary_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

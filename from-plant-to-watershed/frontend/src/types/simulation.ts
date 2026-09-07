export interface ClimateScenario {
  id: string;
  code: string;
  name: string;
  pathway: string;
  description: string;
  temp_anomaly_c: number;
  precip_factor: number;
  co2_ppm: number;
}

export interface PlantSpecies {
  id: string;
  name: string;
  scientific_name: string;
  crop_type: string;
  base_kc: number;
  max_root_depth_cm: number;
  optimal_temp_c: number;
}

export interface HRU {
  id: string;
  hru_number: number;
  land_use: string;
  soil_type: string;
  curve_number_ii: number;
  area_fraction: number;
  plant_species?: PlantSpecies | null;
}

export interface Subbasin {
  id: string;
  subbasin_number: number;
  name: string;
  area_km2: number;
  mean_slope_percent: number;
  hrus: HRU[];
}

export interface Watershed {
  id: string;
  code: string;
  name: string;
  country: string;
  area_km2: number;
  elevation_min_m: number;
  elevation_max_m: number;
  outlet_lat: number;
  outlet_lon: number;
  dem_metadata?: any;
  subbasins: Subbasin[];
}

export interface SimulationResult {
  day_index: number;
  date_str: string;
  precip_mm: number;
  temp_c: number;
  solar_rad_mj: number;
  potential_et_mm: number;
  actual_et_mm: number;
  surface_runoff_mm: number;
  percolation_mm: number;
  streamflow_m3s: number;
  soil_moisture_vol: number;
  plant_transpiration_mm: number;
  root_water_uptake_mm: number;
  cwsi_stress_index: number;
  sap_flow_velocity_cmh: number;
}

export interface SimulationRun {
  id: string;
  user_id: string;
  watershed_id: string;
  scenario_id: string;
  name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  duration_days: number;
  irrigation_efficiency: number;
  scenario?: ClimateScenario;
  summary_metrics?: {
    total_precip_mm: number;
    total_surface_runoff_mm: number;
    total_actual_et_mm: number;
    total_discharge_hm3: number;
    peak_streamflow_m3s: number;
    mean_cwsi: number;
    drought_stress_status: string;
  };
  created_at: string;
}

export interface TwinWebSocketTick {
  type: "TWIN_STATE_TICK" | "ERROR";
  day_index: number;
  date: string;
  weather: {
    precip_mm: number;
    temp_c: number;
    solar_rad_mj: number;
  };
  micro_plant: {
    transpiration_mm: number;
    root_water_uptake_mm: number;
    cwsi_stress_index: number;
    sap_flow_velocity_cmh: number;
  };
  meso_soil: {
    soil_moisture_vol: number;
    soil_water_depth_mm: number;
    percolation_mm: number;
  };
  macro_watershed: {
    surface_runoff_mm: number;
    streamflow_m3s: number;
    actual_et_mm: number;
  };
}

export interface ClimateScenario {
  id: string;
  code: string;
  name: string;
  pathway: string;
  description: string;
  temp_anomaly_c: number;
  precip_factor: number;
  co2_ppm: number;
  source_type: string;
}

export interface DatasetInfo {
  id: string;
  provider: string;
  dataset_name: string;
  version?: string | null;
  variable: string;
  unit: string;
  temporal_resolution: string;
  spatial_support: string;
  evidence_type: string;
  metadata_json: Record<string, unknown>;
  normalized_artifact_count: number;
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
  water_balance_residual_mm: number;
}

export interface SimulationRun {
  id: string;
  user_id: string;
  watershed_id: string;
  scenario_id: string;
  name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  duration_days: number;
  irrigation_efficiency: number | null;
  seed: number;
  requested_config?: Record<string, unknown>;
  effective_config?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
  error?: { type: string; message: string } | null;
  scenario?: ClimateScenario;
  summary_metrics?: {
    total_precip_mm: number;
    total_surface_runoff_mm: number;
    total_actual_et_mm: number;
    total_discharge_hm3: number;
    peak_streamflow_m3s: number;
    mean_cwsi: number;
    cumulative_water_balance_residual_mm: number;
    interpretation_status: string;
    seasonal_crop_yield_proxy_t_ha?: number;
    yield_proxy_evidence_type?: "DERIVED";
  };
  created_at: string;
  mode: "RESEARCH_MULTISCALE" | "DEVELOPMENT_LEGACY_DEMO" | "DEMO_MULTISCALE" | "REAL_OBSERVATION" | "ML_ASSISTED" | "SWAT_PLUS";
  plant_count: number;
  hydrology_backend: "SIMPLIFIED" | "SWAT_PLUS";
  external_model_id?: string | null;
  field_aggregates?: Record<string, any>;
  hru_aggregates?: Record<string, any>;
  plant_sample?: PlantSample[];
  monthly_outputs?: Array<Record<string, any>>;
  validation?: Record<string, any>;
  ml_result?: Record<string, any>;
  management_scenario: "BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM";
  climate_source: "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "OBSERVED_HYBRID";
  dataset_ids: string[];
  dataset_roles: Record<string, "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY">;
  station_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface PlantSample {
  plant_id: number;
  x_m: number;
  y_m: number;
  lai: number;
  stress: number;
  root_depth_cm?: number;
}

export interface ExternalModelInfo {
  id: string; name: string; target: string; framework: string; status: string; metrics: Record<string, number>;
}

export interface TwinWebSocketTick {
  type: "SIMULATION_PLAYBACK_TICK" | "ERROR";
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

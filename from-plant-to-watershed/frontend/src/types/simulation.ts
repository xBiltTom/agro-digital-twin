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

export interface FinalScientificReport {
  report_version: string;
  created_at: string;
  scope: { watershed: string; usgs_gauge: string; huc8: string; statement: string };
  experiment: {
    simulation_period: string[];
    warm_up: string[];
    evaluation: string[];
    calibration: { status: string; procedure: string };
  };
  hypothesis: { conclusion: string; h0: string; h1: string };
  coupling_effect: string;
  runs: Record<string, {
    run_id: string;
    evidence_type: string;
    totals: { et_mm: number; runoff_mm: number; soil_water_mm: number; streamflow_m3s_mean: number; yield_estimated: number | null };
  }>;
  validation: Record<string, {
    matched_count: number;
    imputation: string;
    hypothesis_status: string;
    improvement_percent: number | null;
    baseline: Record<"rmse" | "nse" | "kge" | "pbias" | "r2" | "mae", number | null>;
    coupled: Record<"rmse" | "nse" | "kge" | "pbias" | "r2" | "mae", number | null>;
  }>;
  scenarios: Array<{
    name: string;
    status: string;
    comparison_baseline: string;
    delta_from_historical_coupled_v2: Record<string, { absolute: number | null; percent: number | null }> | null;
  }>;
  cmip6: Record<string, string>;
  nass_yield_validation: { status: string; reason: string };
  limitations: string[];
  statistics: Record<string, {
    status?: string;
    reason?: string;
    interpretation?: string;
    statistic?: number;
    p_value_asymptotic?: number;
    n_observed?: number;
    n_simulated?: number;
    n_pairs?: number;
    parameters?: string[];
  }>;
}

export interface CurrentFinalScientificReportResponse {
  current_contract: {
    contract_version: string;
    current_execution_status: "NOT_EXECUTED" | "EXECUTED";
    result_path: string | null;
    reason?: string | null;
  };
  current_result: FinalScientificReport | null;
  archived_result: {
    report_version: string;
    status: string;
    result_path: string;
    interpretation: string;
  };
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

export type SwatRunType = "SWAT_STANDARD_BASELINE" | "SWAT_MULTISCALE_COUPLED";
export type SwatEvidenceType = "REAL_SWAT_PLUS" | "REAL_SWAT_PLUS_COUPLED";

export interface SwatPlusConfiguration {
  project_path?: string;
  executable_path?: string;
  working_directory?: string;
  warmup_period?: number;
  output_frequency?: "DAILY" | "MONTHLY" | "ANNUAL";
  outlet_unit?: string;
  timeout_seconds?: number;
  run_type: SwatRunType;
  target_plant_name?: string;
}

export interface SwatRecord {
  period: string;
  runoff_mm?: number | null;
  evapotranspiration_mm?: number | null;
  percolation_mm?: number | null;
  soil_water_mm?: number | null;
  streamflow_m3s?: number | null;
}

export interface SwatParameterUpdate {
  hru_id: string[];
  source_variable: string;
  swat_parameter: "lai_pot" | "can_ht_max" | "rt_dp_max";
  input_file: string;
  original_value: number;
  coupled_value: number;
  unit: string;
  transformation: string;
  justification: string;
}

export interface PairedMetric {
  baseline: number | null;
  coupled: number | null;
  delta_absolute: number | null;
  delta_percentage: number | null;
}

export interface PairedComparison {
  experiment_id: string;
  baseline_run_id: string;
  coupled_run_id: string;
  runoff_mm: PairedMetric;
  evapotranspiration_mm: PairedMetric;
  streamflow_m3s: PairedMetric;
}

export interface SwatRunProvenance {
  evidence_type: SwatEvidenceType;
  engine?: string;
  executable_version?: string;
  executable_sha256?: string;
  exit_code?: number;
  output_files?: string[];
  output_checksums?: Record<string, string>;
  output_generation?: Record<string, { sha256: string; mtime_ns: number; generated_after_start: boolean }>;
  configured_control_files?: Record<string, unknown>;
  workspace_modifications?: {
    workspace_input_files_modified?: string[];
    input_checksums?: Record<string, { before_sha256: string; after_sha256: string }>;
    parameter_updates?: SwatParameterUpdate[];
    not_coupled?: Array<{ variable: string; reason: string }>;
  };
  parameter_updates?: SwatParameterUpdate[];
  date_of_peak_LAI?: string;
  date_of_peak_height?: string;
  date_of_peak_root_depth?: string;
  experiment?: PairedComparison;
  [key: string]: unknown;
}

export interface SwatResultsResponse {
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  run_id: string;
  records: SwatRecord[];
  hru_results: Array<Record<string, unknown>>;
  water_balance: {
    status?: string;
    totals_mm?: {
      runoff_mm?: number;
      evapotranspiration_mm?: number;
      percolation_mm?: number;
    };
    mean_streamflow_m3s?: number | null;
    variable_availability?: Record<string, string>;
    warnings?: Array<{ code: string; message: string }>;
  } | null;
  provenance: SwatRunProvenance;
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
  provenance?: Record<string, unknown> | SwatRunProvenance;
  error?: { type: string; message: string } | null;
  scenario?: ClimateScenario;
  summary_metrics?: {
    total_precip_mm?: number;
    total_surface_runoff_mm?: number;
    total_actual_et_mm?: number;
    total_discharge_hm3?: number;
    peak_streamflow_m3s?: number;
    mean_cwsi?: number;
    cumulative_water_balance_residual_mm?: number;
    interpretation_status?: string;
    seasonal_crop_yield_proxy_t_ha?: number;
    yield_proxy_evidence_type?: "DERIVED";
    evidence_type?: SwatEvidenceType;
    period_count?: number;
    total_runoff_mm?: number;
    total_evapotranspiration_mm?: number;
    total_percolation_mm?: number;
    water_balance?: SwatResultsResponse["water_balance"];
    paired_comparison?: PairedComparison;
    [key: string]: unknown;
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
  plant_id: number | string;
  x_m: number;
  y_m: number;
  lai: number;
  stress: number;
  root_depth_cm?: number;
  phenological_stage?: string;
  growing_degree_days_c_day?: number;
  plant_height_m?: number;
  leaf_count?: number;
  leaf_area_m2?: number;
  canopy_cover_fraction?: number;
  root_depth_m?: number;
  biomass_g_plant?: number;
  potential_transpiration_mm_day?: number;
  actual_transpiration_mm_day?: number;
  soil_water_uptake_mm_day?: number;
  estimated_yield_g_plant?: number;
}

export interface ExternalModelInfo {
  id: string;
  name: string;
  target: string;
  framework: string;
  status: string;
  metrics: Record<string, number>;
  artifact_path?: string;
  version?: string | null;
  checksum?: string;
  bundle_contract_version?: string | null;
  learning_mode?: string | null;
  training_data_type?: string | null;
  feature_schema?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
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

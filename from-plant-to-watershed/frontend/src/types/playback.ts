export type PlaybackResolution = "DAILY" | "MONTHLY" | "ANNUAL";
export type Availability = "AVAILABLE" | "NOT_AVAILABLE";
export type Evidence = "OBSERVED" | "MODELLED_SWAT_PLUS" | "SIMPLIFIED_FSPM" | "SIMPLIFIED_HYDROLOGY" | "DERIVED" | "ASSUMED" | "SYNTHETIC" | "NOT_AVAILABLE";

export interface VariableState {
  value: number | string | null;
  unit: string;
  evidence: Evidence;
  source: string;
  availability: Availability;
  limitation: string | null;
}

export interface CropState {
  active: boolean;
  crop: string | null;
  season_id: string | null;
  phenological_stage: string | null;
  window_status: string | null;
  source: string;
  limitation: string | null;
}

export interface PlantSample {
  plant_id: string;
  x_m: number;
  y_m: number;
  variables: Record<string, VariableState>;
}

export interface HruState {
  hru_id: string;
  spatial_support: string;
  polygon_id: string | null;
  variables: Record<string, VariableState>;
}

export interface PlaybackRecord {
  schema_version: "twin-playback-v1";
  simulation_id: string;
  date: string;
  resolution: PlaybackResolution;
  run_type: string;
  watershed_id: string;
  watershed_code: string | null;
  outlet_unit: string | null;
  spatial_support: string;
  weather: Record<string, VariableState>;
  crop: CropState | null;
  field: Record<string, VariableState>;
  plant_samples: PlantSample[];
  hydrology: Record<string, VariableState>;
  hru_results: HruState[];
  availability: Record<string, Availability>;
  limitations: string[];
}

export interface PlaybackPage {
  schema_version: "twin-playback-v1";
  simulation_id: string;
  simulation_status: string;
  artifact_status: string;
  resolution: PlaybackResolution | null;
  available_resolutions: PlaybackResolution[];
  total: number;
  offset: number;
  limit: number;
  records: PlaybackRecord[];
  variables: Record<string, Record<string, unknown>>;
  provenance: Record<string, unknown>;
  limitations: string[];
}

export interface PlaybackQuery {
  date?: string;
  start?: string;
  end?: string;
  resolution?: PlaybackResolution;
  offset?: number;
  limit?: number;
}

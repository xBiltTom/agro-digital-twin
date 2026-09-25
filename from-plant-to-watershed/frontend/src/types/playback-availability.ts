import type { PlaybackResolution } from "./playback";

export type AvailabilityCode =
  | "NO_PLAYBACK_ARTIFACT" | "ARTIFACT_UNAVAILABLE" | "ARTIFACT_INVALID"
  | "SWAT_BASELINE_NO_FSPM" | "HYDROLOGY_ONLY" | "HISTORICAL_REFERENCE"
  | "OUTSIDE_CROP_SEASON" | "FSPM_STATE_MISSING" | "DATE_NOT_IN_PLAYBACK" | "UNSUPPORTED_CROP_GEOMETRY"
  | "FIELD_HEIGHT_MISSING" | "FIELD_LAI_MISSING" | "NO_PLANT_SAMPLES"
  | "SAMPLE_HEIGHT_MISSING" | "SCIENTIFIC_STATE_AVAILABLE";

export type VisualMode = "SCIENTIFIC_ACTIVE" | "SCIENTIFIC_FALLOW" |
  "HYDROLOGY_ONLY" | "HISTORICAL_REFERENCE" | "DATA_UNAVAILABLE";

export interface DateAvailability {
  date: string;
  resolution: PlaybackResolution;
  mode: VisualMode;
  codes: AvailabilityCode[];
  field_representable: boolean;
  sample_representable: boolean;
  missing_variables: string[];
}

export interface ResolutionAvailability {
  resolution: PlaybackResolution;
  artifact_status: "AVAILABLE" | "UNAVAILABLE" | "INVALID";
  record_count: number;
  first_record: string | null;
  last_record: string | null;
  first_active_crop: string | null;
  first_representable_field: string | null;
  first_plant_samples: string | null;
  crop_intervals: { start: string; end: string; season_id: string | null; approximate: boolean }[];
  hydrology_available: boolean;
  fspm_trajectory_available: boolean;
  hru_ids: string[];
  selected_date: DateAvailability | null;
  codes: AvailabilityCode[];
}

export interface SimulationAvailability {
  simulation_id: string;
  simulation_name: string;
  simulation_status: string;
  run_type: string;
  origin: "EXECUTED" | "HISTORICAL_IMPORT" | "UNKNOWN";
  stored_hydrology_available: boolean;
  stored_fspm_summary_available: boolean;
  available_resolutions: PlaybackResolution[];
  resolutions: ResolutionAvailability[];
  codes: AvailabilityCode[];
  limitations: string[];
}

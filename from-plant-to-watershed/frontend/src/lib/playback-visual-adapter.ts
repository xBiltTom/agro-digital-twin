import type { PlaybackRecord, PlaybackResolution, PlantSample, VariableState } from "../types/playback";
import type { AvailabilityCode, SimulationAvailability, VisualMode } from "../types/playback-availability";

/** Official scientific input for Gemini. Scene reference dimensions live in visual-state.ts. */
export interface TwinVisualState {
  mode: VisualMode;
  simulationId: string;
  simulationName: string | null;
  date: string | null;
  periodStart: string | null;
  periodEnd: string | null;
  resolution: PlaybackResolution | null;
  runType: string | null;
  watershedId: string | null;
  watershedCode: string | null;
  precipitation: VariableState | null;
  streamflow: VariableState | null;
  activeCrop: boolean | null;
  representedCrop: string | null;
  seasonId: string | null;
  seasonIsApproximate: boolean;
  phenologicalStage: string | null;
  height: VariableState | null;
  lai: VariableState | null;
  rootDepth: VariableState | null;
  biomass: VariableState | null;
  canopyCover: VariableState | null;
  waterStress: VariableState | null;
  transpiration: VariableState | null;
  fspmMoisturePercent: VariableState | null;
  swatSoilWaterMm: VariableState | null;
  plantSamples: PlantSample[];
  selectedPlant: PlantSample | null;
  hruIds: string[];
  codes: AvailabilityCode[];
  missingVariables: string[];
  limitations: string[];
  fieldRepresentable: boolean;
  sampleRepresentable: boolean;
}

function available(value: VariableState | undefined): boolean {
  return value?.availability === "AVAILABLE" && value.value !== null;
}

function isMaize(crop: string | null | undefined): boolean {
  return /maize|corn|maíz|maiz/i.test(crop ?? "");
}

function endOfPeriod(record: PlaybackRecord): string {
  if (record.resolution === "DAILY") return record.date;
  const year = Number(record.date.slice(0, 4));
  if (record.resolution === "ANNUAL") return `${year}-12-31`;
  const month = Number(record.date.slice(5, 7));
  return new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
}

export function adaptPlaybackVisual(
  record: PlaybackRecord | null,
  options: { simulationId: string; simulationName?: string | null;
    availability?: SimulationAvailability | null; selectedPlantId?: string | null;
    periodStart?: string | null; periodEnd?: string | null;
    watershedId?: string | null; watershedCode?: string | null },
): TwinVisualState {
  const diagnostic = options.availability;
  const selected = record && diagnostic?.resolutions.find((r) => r.resolution === record.resolution)?.selected_date;
  const active = record?.crop?.active ?? null;
  const supported = isMaize(record?.crop?.crop);
  const sample = record?.plant_samples.find((plant) => plant.plant_id === options.selectedPlantId)
    ?? (options.selectedPlantId == null ? record?.plant_samples.find((plant) => available(plant.variables.height_m))
      ?? record?.plant_samples[0] : undefined) ?? null;
  const fieldReady = active === true && supported && available(record?.field.height_m) && available(record?.field.lai);
  const sampleReady = active === true && supported && !!sample && available(sample.variables.height_m);
  const missing: string[] = [];
  const codes: AvailabilityCode[] = selected?.codes.slice() ?? [];
  let mode: VisualMode;
  if (!record) {
    mode = diagnostic?.origin === "HISTORICAL_IMPORT" ? "HISTORICAL_REFERENCE" : "DATA_UNAVAILABLE";
    codes.push(...(diagnostic?.codes ?? ["NO_PLAYBACK_ARTIFACT"]));
  } else if (record.crop?.active === false) {
    mode = "SCIENTIFIC_FALLOW";
    if (!codes.length) codes.push("OUTSIDE_CROP_SEASON");
  } else if (record.crop?.active === true) {
    mode = fieldReady || sampleReady ? "SCIENTIFIC_ACTIVE" : "DATA_UNAVAILABLE";
    if (!supported) codes.push("UNSUPPORTED_CROP_GEOMETRY");
    if (!available(record.field.height_m)) { missing.push("field.height_m"); codes.push("FIELD_HEIGHT_MISSING"); }
    if (!available(record.field.lai)) { missing.push("field.lai"); codes.push("FIELD_LAI_MISSING"); }
    if (!record.plant_samples.length) { missing.push("plant_samples"); codes.push("NO_PLANT_SAMPLES"); }
    else if (!record.plant_samples.some((plant) => available(plant.variables.height_m))) {
      missing.push("plant_samples[*].height_m"); codes.push("SAMPLE_HEIGHT_MISSING");
    }
    if (fieldReady || sampleReady) codes.push("SCIENTIFIC_STATE_AVAILABLE");
  } else if (Object.values(record.hydrology).some(available)) {
    mode = "HYDROLOGY_ONLY";
    if (!codes.length) codes.push(record.run_type === "SWAT_STANDARD_BASELINE" ? "SWAT_BASELINE_NO_FSPM" : "HYDROLOGY_ONLY");
    missing.push("field.height_m", "field.lai", "plant_samples");
  } else {
    mode = "DATA_UNAVAILABLE";
    if (!codes.length) codes.push("FSPM_STATE_MISSING");
    missing.push("field.height_m", "field.lai", "plant_samples");
  }
  return {
    mode, simulationId: options.simulationId, simulationName: options.simulationName ?? diagnostic?.simulation_name ?? null,
    date: record?.date ?? null, periodStart: options.periodStart ?? record?.date ?? null,
    periodEnd: options.periodEnd ?? (record ? endOfPeriod(record) : null), resolution: record?.resolution ?? null,
    runType: record?.run_type ?? diagnostic?.run_type ?? null,
    watershedId: record?.watershed_id ?? options.watershedId ?? null,
    watershedCode: record?.watershed_code ?? options.watershedCode ?? null,
    precipitation: record?.weather.precipitation_mm ?? null, streamflow: record?.hydrology.streamflow_m3s ?? null,
    activeCrop: active, representedCrop: record?.crop?.crop ?? null,
    seasonId: record?.crop?.season_id ?? null,
    seasonIsApproximate: record?.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW",
    phenologicalStage: record?.crop?.phenological_stage ?? null,
    height: record?.field.height_m ?? null, lai: record?.field.lai ?? null,
    rootDepth: record?.field.root_depth_m ?? null, biomass: record?.field.biomass_g_plant ?? null,
    canopyCover: record?.field.canopy_cover_fraction ?? null,
    waterStress: record?.field.water_stress ?? null,
    transpiration: record?.field.actual_transpiration_mm_day ?? null,
    fspmMoisturePercent: record?.field.soil_moisture_vol_percent ?? null,
    swatSoilWaterMm: record?.hydrology.soil_water_mm ?? null,
    plantSamples: record?.plant_samples ?? [], selectedPlant: sample,
    hruIds: record?.hru_results.map((hru) => hru.hru_id) ?? [],
    codes: [...new Set(codes)], missingVariables: selected?.missing_variables ?? missing,
    limitations: [...(record?.limitations ?? []), ...(diagnostic?.limitations ?? [])],
    fieldRepresentable: selected?.field_representable ?? fieldReady,
    sampleRepresentable: selected?.sample_representable ?? sampleReady,
  };
}

import type { PlaybackRecord, PlantSample, VariableState } from "../types/playback";
import { adaptPlaybackVisual, type TwinVisualState } from "./playback-visual-adapter.ts";

export function numeric(state: VariableState | undefined): number | null {
  return state?.availability === "AVAILABLE" && typeof state.value === "number" && Number.isFinite(state.value)
    ? state.value : null;
}

export function variableText(state: VariableState | undefined): string {
  if (!state || state.availability !== "AVAILABLE" || state.value === null) return "No disponible";
  const value = typeof state.value === "number" ? Number(state.value.toFixed(2)).toString() : state.value;
  return `${value} ${state.unit}`.trim();
}

export function periodLabel(record: PlaybackRecord): string {
  return record.resolution === "DAILY" ? record.date
    : record.resolution === "MONTHLY" ? record.date.slice(0, 7)
    : record.date.slice(0, 4);
}

export function hasSouthForkContext(record: PlaybackRecord, stationId?: string | null): boolean {
  return /05451210|south.?fork/i.test(record.watershed_code ?? "") || stationId === "05451210";
}

/** Visual particle density only; millimetres remain unchanged in the HUD. Null means unknown. */
export function rainIntensity(record: PlaybackRecord): number | null {
  if (record.resolution !== "DAILY") return null;
  const mm = numeric(record.weather.precipitation_mm);
  return mm === null ? null : Math.min(1, Math.max(0, mm) / 25);
}

export function activePlantSample(record: PlaybackRecord, selectedId: string | null): PlantSample | null {
  const crop = record.crop?.crop?.toLowerCase() ?? "";
  if (!record.crop?.active || !(crop.includes("maize") || crop.includes("corn") || crop.includes("maíz") || crop.includes("maiz"))) return null;
  if (selectedId !== null) return record.plant_samples.find((sample) => sample.plant_id === selectedId) ?? null;
  return record.plant_samples.find((sample) => numeric(sample.variables.height_m) !== null) ?? record.plant_samples[0] ?? null;
}

export interface SceneState {
  visual: TwinVisualState;
  record: PlaybackRecord;
  rainMm: number | null;
  rainIntensity: number | null;
  streamflowM3s: number | null;
  soilWaterMm: number | null;
  soilMoisturePercent: number | null;
  fieldHeightM: number | null;
  fieldLai: number | null;
  canopyCover: number | null;
  rootDepthM: number | null;
  stress: number | null;
  transpirationMmDay: number | null;
  cropActive: boolean;
  cropSupported: boolean;
  sample: PlantSample | null;
}

export function sceneFromRecord(record: PlaybackRecord, selectedPlantId: string | null): SceneState {
  const visual = adaptPlaybackVisual(record, { simulationId: record.simulation_id, selectedPlantId });
  const cropActive = visual.activeCrop === true;
  const cropName = record.crop?.crop?.toLowerCase() ?? "";
  const cropSupported = cropName.includes("maize") || cropName.includes("corn") || cropName.includes("maíz") || cropName.includes("maiz");
  return {
    visual,
    record,
    rainMm: numeric(record.weather.precipitation_mm),
    rainIntensity: rainIntensity(record),
    streamflowM3s: numeric(record.hydrology.streamflow_m3s),
    soilWaterMm: numeric(record.hydrology.soil_water_mm),
    soilMoisturePercent: numeric(record.field.soil_moisture_vol_percent),
    fieldHeightM: cropActive ? numeric(record.field.height_m) : null,
    fieldLai: cropActive ? numeric(record.field.lai) : null,
    canopyCover: cropActive ? numeric(record.field.canopy_cover_fraction) : null,
    rootDepthM: cropActive ? numeric(record.field.root_depth_m) : null,
    stress: cropActive ? numeric(record.field.water_stress) : null,
    transpirationMmDay: cropActive ? numeric(record.field.actual_transpiration_mm_day) : null,
    cropActive,
    cropSupported,
    sample: activePlantSample(record, selectedPlantId),
  };
}

export function chartPointFromRecord(record: PlaybackRecord) {
  return {
    period: periodLabel(record),
    precipitation: numeric(record.weather.precipitation_mm),
    streamflow: numeric(record.hydrology.streamflow_m3s),
    observed: numeric(record.hydrology.observed_streamflow_m3s),
    runoff: numeric(record.hydrology.runoff_mm),
    evapotranspiration: numeric(record.hydrology.evapotranspiration_mm),
    lai: numeric(record.field.lai),
    stress: numeric(record.field.water_stress),
    transpiration: numeric(record.field.actual_transpiration_mm_day),
  };
}

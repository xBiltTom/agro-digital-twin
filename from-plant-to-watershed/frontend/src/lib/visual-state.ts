import type { VariableState } from "../types/playback.ts";
import { numeric, type SceneState } from "./playback-scene.ts";

/** Dimensions are scene metres. The geometry is illustrative; only supplied dimensions are scientific. */
export interface MaizeVisualState {
  heightM: number | null;
  lai: number | null;
  rootDepthM: number | null;
  stress: number | null;
  stage: string | null;
  transpirationMmDay: number | null;
  soilMoisturePercent: number | null;
  sampleId: string | null;
  reference: boolean;
  leafCount: number | null;
  leafAreaM2: number | null;
  biomassG: number | null;
  calendarId: string | null;
  hruIds: string[];
  variables: Record<string, VariableState>;
}

export const REFERENCE_MAIZE: MaizeVisualState = {
  heightM: 2.1, lai: 3.5, rootDepthM: 1.0, stress: null,
  stage: "REPRODUCTIVE", transpirationMmDay: null, soilMoisturePercent: null,
  sampleId: null, reference: true,
  leafCount: 16, leafAreaM2: 0.45, biomassG: 170,
  calendarId: null, hruIds: [], variables: {},
};

export function maizeFromScene(scene: SceneState | null): MaizeVisualState {
  if (!scene) return REFERENCE_MAIZE;
  const sample = scene.sample;
  if (!scene.cropActive || !scene.cropSupported || !sample) {
    return {
      heightM: null, lai: null, rootDepthM: null, stress: null, stage: null,
      transpirationMmDay: null, soilMoisturePercent: null, sampleId: null, reference: false,
      leafCount: null, leafAreaM2: null, biomassG: null,
      calendarId: null, hruIds: [], variables: {},
    };
  }
  const stageVariable = sample.variables.phenological_stage;
  return {
    heightM: numeric(sample.variables.height_m),
    lai: numeric(sample.variables.lai),
    rootDepthM: numeric(sample.variables.root_depth_m),
    stress: numeric(sample.variables.water_stress),
    stage: stageVariable?.availability === "AVAILABLE" && typeof stageVariable.value === "string"
      ? stageVariable.value : null,
    transpirationMmDay: numeric(sample.variables.actual_transpiration_mm_day),
    soilMoisturePercent: scene.soilMoisturePercent,
    sampleId: sample.plant_id,
    reference: false,
    leafCount: numeric(sample.variables.leaf_count),
    leafAreaM2: numeric(sample.variables.leaf_area_m2),
    biomassG: numeric(sample.variables.biomass_g_plant),
    calendarId: sample.calendar_id ?? null,
    hruIds: sample.hru_ids ?? [],
    variables: sample.variables ?? {},
  };
}

export function fieldCanopyAvailable(scene: SceneState | null): boolean {
  return scene === null || (scene.cropActive && scene.cropSupported &&
    scene.fieldHeightM !== null && scene.fieldLai !== null);
}

export function maizeReproductive(stage: string | null): boolean {
  return stage === "REPRODUCTIVE" || stage === "MATURITY";
}

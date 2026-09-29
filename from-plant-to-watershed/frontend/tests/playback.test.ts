import test from "node:test";
import assert from "node:assert/strict";
import { rainIntensity, sceneFromRecord, periodLabel, variableText, chartPointFromRecord, hasSouthForkContext, activePlantSample, numeric } from "../src/lib/playback-scene.ts";
import { PlaybackClient } from "../src/lib/playback-client.ts";
import { historicalFallbackEligible, simplifiedHistoricalPoints, swatHistoricalPoints } from "../src/lib/historical-charts.ts";
import { accessibleSimulations, collectSimulationPages } from "../src/lib/simulation-access.ts";
import { fieldCanopyAvailable, maizeFromScene, maizeReproductive } from "../src/lib/visual-state.ts";
import type { PlaybackPage, PlaybackRecord, VariableState } from "../src/types/playback.ts";
import type { SimulationResult, SimulationRun } from "../src/types/simulation.ts";
import type { SwatResultsResponse } from "../src/types/simulation.ts";
import type { User } from "../src/types/auth.ts";
import { adaptPlaybackVisual } from "../src/lib/playback-visual-adapter.ts";
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { gunzipSync } from "node:zlib";
// @ts-expect-error node:sqlite is built-in in Node 22+ but not yet declared in installed @types/node
import { DatabaseSync } from "node:sqlite";
import { firstCropNavigation } from "../src/lib/playback-navigation.ts";
import type { SimulationAvailability } from "../src/types/playback-availability.ts";
import { classifySimulationEvidence } from "../src/lib/simulation-evidence.ts";
import { datedMonthlyComparisonRows } from "../src/lib/simulation-chart-data.ts";

function variable(value: number | string | null, unit: string, evidence: VariableState["evidence"] = "SIMPLIFIED_FSPM"): VariableState {
  return { value, unit, evidence: value === null ? "NOT_AVAILABLE" : evidence, source: "fixture",
    availability: value === null ? "NOT_AVAILABLE" : "AVAILABLE", limitation: null };
}

function record(date: string, options: { rain?: number | null; crop?: boolean; height?: number; season?: string } = {}): PlaybackRecord {
  const active = options.crop ?? true;
  return {
    schema_version: "twin-playback-v1", simulation_id: "run-a", date, resolution: "DAILY", run_type: "SWAT_MULTISCALE_COUPLED",
    watershed_id: "basin", watershed_code: null, outlet_unit: null, spatial_support: "WATERSHED_OUTLET_AND_BASIN",
    weather: { precipitation_mm: variable(options.rain ?? null, "mm/day", "DERIVED") },
    crop: { active, crop: active ? "maize" : null, season_id: active ? options.season ?? "season-1" : null,
      phenological_stage: active ? "V6" : null, window_status: "APPROXIMATE_PLANTING_WINDOW", source: "fixture", limitation: null },
    field: active ? {
      lai: variable(options.height ?? 1, "m2_leaf/m2_ground"), height_m: variable(options.height ?? 1, "m"),
      root_depth_m: variable(0.5, "m"), canopy_cover_fraction: variable(0.4, "fraction"),
      water_stress: variable(0.73, "fraction"), actual_transpiration_mm_day: variable(0.84, "mm/day"),
      soil_moisture_vol_percent: variable(24, "volumetric percent", "ASSUMED"),
    } : {},
    plant_samples: active ? [{ plant_id: "p-7", x_m: 1, y_m: 2, variables: {
      height_m: variable(options.height ?? 1, "m"), lai: variable(1.4, "m2_leaf/m2_ground"),
    } }] : [],
    hydrology: { soil_water_mm: variable(170, "mm", "MODELLED_SWAT_PLUS"),
      evapotranspiration_mm: variable(5.8, "mm/day", "MODELLED_SWAT_PLUS"),
      streamflow_m3s: variable(8, "m3/s", "MODELLED_SWAT_PLUS") },
    hru_results: [], channel_results: [], availability: {}, limitations: [],
  };
}

test("daily rain distinguishes dry, wet and unknown; monthly totals do not cause storms", () => {
  assert.equal(rainIntensity(record("2020-02-28", { rain: 0 })), 0);
  assert.ok((rainIntensity(record("2020-02-29", { rain: 5 })) ?? 0) > 0);
  assert.equal(rainIntensity(record("2020-03-01", { rain: null })), null);
  const monthly = { ...record("2020-02-01", { rain: 50 }), resolution: "MONTHLY" as const };
  assert.equal(rainIntensity(monthly), null);
  assert.equal(periodLabel(monthly), "2020-02");
  assert.equal(periodLabel({ ...monthly, resolution: "ANNUAL", date: "2020-01-01" }), "2020");
});

test("FSPM growth follows recorded samples and resets at season boundary", () => {
  const early = sceneFromRecord(record("2020-05-01", { height: 0.2, season: "one" }), "p-7");
  const mature = sceneFromRecord(record("2020-08-01", { height: 2.1, season: "one" }), "p-7");
  const fallow = sceneFromRecord(record("2020-11-01", { crop: false }), "p-7");
  const newSeason = sceneFromRecord(record("2021-05-01", { height: 0.15, season: "two" }), "p-7");
  assert.equal(early.fieldHeightM, 0.2);
  assert.equal(mature.fieldHeightM, 2.1);
  assert.equal(fallow.cropActive, false);
  assert.equal(fallow.sample, null);
  assert.equal(fallow.fieldHeightM, null);
  assert.equal(newSeason.fieldHeightM, 0.15);
  assert.equal(newSeason.record.crop?.season_id, "two");
  assert.equal(sceneFromRecord(record("2021-05-02", { season: "two" }), "missing-id").sample, null);
});

test("South Fork 2019 playback example reaches the visual adapter with all three scales", () => {
  const path = new URL("../../backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/playback_api_example_2019-07-15.json", import.meta.url);
  const page = JSON.parse(readFileSync(path, "utf8")) as PlaybackPage;
  const actual = page.records[0];
  const visual = adaptPlaybackVisual(actual, { simulationId: actual.simulation_id });
  assert.equal(page.total, 1);
  assert.equal(page.resolution, "DAILY");
  assert.equal(page.simulation_id, "phase234-sf-2019-v2");
  assert.equal(actual.date, "2019-07-15");
  assert.equal(visual.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(visual.plantSamples.length, 70);
  assert.equal(visual.hruStates.length, 36);
  assert.equal(visual.channelStates.length, 37);
  assert.equal(visual.fspmMoisturePercent?.evidence, "DERIVED");
  assert.ok((visual.fspmMoisturePercent?.value as number) > 25);
  assert.equal(visual.channelStates.find((channel) => channel.gis_id === "153")?.variables.streamflow_m3s.unit, "m3/s");
});

test("rich plant geometry receives exactly the selected sample dimensions and phenology", () => {
  const early = maizeFromScene(sceneFromRecord(record("2020-05-01", { height: 0.2 }), "p-7"));
  const matureRecord = record("2020-08-01", { height: 2.1 });
  matureRecord.plant_samples[0].variables.phenological_stage = variable("REPRODUCTIVE", "category");
  const mature = maizeFromScene(sceneFromRecord(matureRecord, "p-7"));
  assert.equal(early.heightM, 0.2);
  assert.equal(mature.heightM, 2.1);
  assert.equal(maizeReproductive(early.stage), false);
  assert.equal(maizeReproductive(mature.stage), true);
  assert.equal(mature.sampleId, "p-7");
  assert.equal(mature.reference, false);
});

test("fallow and baseline hide the scientific canopy; historical mode stays labelled reference", () => {
  const fallow = sceneFromRecord(record("2020-11-01", { crop: false }), "p-7");
  const baseline = sceneFromRecord({ ...record("2020-06-01"), crop: null, field: {}, plant_samples: [] }, null);
  assert.equal(fieldCanopyAvailable(fallow), false);
  assert.equal(fieldCanopyAvailable(baseline), false);
  assert.equal(maizeFromScene(fallow).heightM, null);
  assert.equal(maizeFromScene(baseline).reference, false);
  assert.equal(fieldCanopyAvailable(null), true);
  assert.equal(maizeFromScene(null).reference, true);
  assert.equal(maizeFromScene(null).soilMoisturePercent, null);
});

test("baseline has no FSPM; soil-water mm is distinct from assumed volumetric percent", () => {
  const baseline = { ...record("2020-06-01", { rain: 0 }), crop: null, field: {}, plant_samples: [] };
  const view = sceneFromRecord(baseline, "p-7");
  assert.equal(view.cropActive, false);
  assert.equal(view.sample, null);
  assert.equal(view.stress, null);
  assert.equal(view.transpirationMmDay, null);
  assert.equal(view.soilMoisturePercent, null);
  assert.equal(view.soilWaterMm, 170);
  const coupled = sceneFromRecord(record("2020-06-01"), "p-7");
  assert.equal(coupled.soilMoisturePercent, 24);
  assert.equal(coupled.stress, 0.73);
  assert.equal(coupled.transpirationMmDay, 0.84);
});

test("zero is displayed as zero and missing is explicit", () => {
  assert.equal(variableText(variable(0, "mm/day")), "0 mm/day");
  assert.equal(variableText(variable(null, "mm/day")), "No disponible");
});

test("scene, HUD variable and chart point share the same dated record", () => {
  const row = record("2020-06-20", { rain: 4, height: 1.5 });
  const scene = sceneFromRecord(row, "p-7");
  const chart = chartPointFromRecord(row);
  assert.equal(chart.period, periodLabel(scene.record));
  assert.equal(chart.precipitation, scene.rainMm);
  assert.equal(chart.stress, scene.stress);
  assert.equal(variableText(scene.record.weather.precipitation_mm), "4 mm/day");
});

test("South Fork contextual geometry is not assigned to unrelated basins", () => {
  assert.equal(hasSouthForkContext(record("2020-06-20")), false);
  assert.equal(hasSouthForkContext({ ...record("2020-06-20"), watershed_code: "USGS-05451210-PARTIAL" }), true);
});

function page(simulationId: string, offset: number, count = 100): PlaybackPage {
  const dates = Array.from({ length: count }, (_, i) => new Date(Date.UTC(2020, 0, offset + i + 1)).toISOString().slice(0, 10));
  return { schema_version: "twin-playback-v1", simulation_id: simulationId, simulation_status: "COMPLETED",
    artifact_status: "AVAILABLE", resolution: "DAILY", available_resolutions: ["DAILY"], total: 205,
    offset, limit: 100, records: dates.map((date) => ({ ...record(date), simulation_id: simulationId })),
    variables: {}, provenance: {}, limitations: [] };
}

test("pagination keeps exact dates and caches fetched pages", async () => {
  let calls = 0;
  const client = new PlaybackClient(async (id, query) => { calls++; return page(id, query.offset ?? 0); });
  client.select("run-a", "DAILY");
  await client.pageFor(0);
  await client.pageFor(99);
  await client.pageFor(100);
  assert.equal(calls, 2);
  assert.equal(client.recordAt(99)?.date, "2020-04-09");
  assert.equal(client.recordAt(100)?.date, "2020-04-10");
});

test("response from previous simulation is discarded even when network ignores abort", async () => {
  let finishOld: ((result: PlaybackPage) => void) | undefined;
  const client = new PlaybackClient((id, query) => id === "old"
    ? new Promise((resolve) => { finishOld = resolve; })
    : Promise.resolve(page(id, query.offset ?? 0)));
  client.select("old");
  const oldRequest = client.pageFor(0);
  client.select("new");
  await client.pageFor(0);
  finishOld!(page("old", 0));
  assert.equal(await oldRequest, null);
  assert.equal(client.recordAt(0)?.simulation_id, "new");
});

test("date lookup resolves a day inside a monthly period without fetching the whole series", async () => {
  const months = ["2020-01-01", "2020-02-01", "2020-03-01"].map((day) =>
    ({ ...record(day), resolution: "MONTHLY" as const }));
  let calls = 0;
  const client = new PlaybackClient(async (id, query) => {
    calls++;
    const matched = query.date ? months.filter((row) => row.date.slice(0, 7) === query.date?.slice(0, 7)) : months;
    return { ...page(id, query.offset ?? 0, 0), resolution: "MONTHLY", available_resolutions: ["MONTHLY"],
      total: matched.length, records: matched };
  });
  client.select("run-a", "MONTHLY");
  assert.equal(await client.findDate("2020-02-28", 3), 1);
  assert.equal(client.recordAt(1)?.date, "2020-02-01");
  assert.equal(await client.findDate("2020-04-01", 3), null);
  assert.equal(calls, 3);
});

test("historical SWAT+ charts retain real stored variables without rainfall or FSPM proxies", () => {
  const point = swatHistoricalPoints([{ period: "2020-02-01", runoff_mm: 0,
    streamflow_m3s: 4.2, evapotranspiration_mm: 6, soil_water_mm: 170 }])[0];
  assert.equal(point.period, "2020-02-01");
  assert.equal(point.runoff, 0);
  assert.equal(point.precipitation, null);
  assert.equal(point.stress, null);
  assert.equal(point.transpiration, null);
  assert.equal(point.soilWater, 170);
});

test("historical simplified charts use persisted daily values and keep absent SWAT storage null", () => {
  const row: SimulationResult = {
    day_index: 1, date_str: "2020-02-29", precip_mm: 0, temp_c: 12,
    solar_rad_mj: 15, potential_et_mm: 2, actual_et_mm: 1.5,
    surface_runoff_mm: 0.2, percolation_mm: 0.4, streamflow_m3s: 3,
    soil_moisture_vol: 24, plant_transpiration_mm: 0.8, root_water_uptake_mm: 0.7,
    cwsi_stress_index: 0.6, sap_flow_velocity_cmh: 1, water_balance_residual_mm: 0,
  };
  const point = simplifiedHistoricalPoints([row])[0];
  assert.equal(point.period, "2020-02-29");
  assert.equal(point.precipitation, 0);
  assert.equal(point.stress, 0.6);
  assert.equal(point.transpiration, 0.8);
  assert.equal(point.soilWater, null);
});

test("playback selector excludes runs the current user cannot open", () => {
  const runs = [{ id: "own", user_id: "u1" }, { id: "other", user_id: "u2" }] as SimulationRun[];
  const researcher = { id: "u1", roles: [{ id: "r", name: "INVESTIGADOR_HIDROLOGO" }] } as User;
  const admin = { id: "admin", roles: [{ id: "a", name: "SUPERADMIN" }] } as User;
  assert.deepEqual(accessibleSimulations(runs, researcher).map((run) => run.id), ["own"]);
  assert.deepEqual(accessibleSimulations(runs, admin).map((run) => run.id), ["own", "other"]);
});

test("simulation selector follows server pagination past the former 50-run window", async () => {
  const runs = Array.from({ length: 101 }, (_, index) => ({ id: `run-${index}` } as SimulationRun));
  const offsets: number[] = [];
  const result = await collectSimulationPages(async (skip, limit) => {
    offsets.push(skip);
    return runs.slice(skip, skip + limit);
  });
  assert.equal(result.length, 101);
  assert.deepEqual(offsets, [0, 100]);
});

test("simulation evidence keeps historical imports distinct from real executions and simplified runs", () => {
  const imported = {
    hydrology_backend: "SWAT_PLUS",
    provenance: { source_kind: "HISTORICAL_IMPORT", evidence_type: "REAL_SWAT_PLUS_COUPLED" },
  } as unknown as SimulationRun;
  const executed = {
    hydrology_backend: "SWAT_PLUS",
    provenance: { evidence_type: "REAL_SWAT_PLUS_COUPLED" },
  } as unknown as SimulationRun;
  const simplified = {
    hydrology_backend: "SIMPLIFIED",
    provenance: { hydrology: { model: "SimplifiedHydrologyModel" } },
  } as unknown as SimulationRun;
  const legacyImport = {
    hydrology_backend: "SWAT_PLUS",
    requested_config: { swat_plus: { experiment_id: "south-fork-final-coupled-2015-2020" } },
    provenance: { evidence_type: "REAL_SWAT_PLUS_COUPLED" },
  } as unknown as SimulationRun;

  assert.equal(classifySimulationEvidence(imported), "HISTORICAL_IMPORT");
  assert.equal(classifySimulationEvidence(executed), "COUPLED_EXECUTED");
  assert.equal(classifySimulationEvidence(simplified), "SIMPLIFIED");
  assert.equal(classifySimulationEvidence(legacyImport), "HISTORICAL_IMPORT");
});

test("monthly comparison charts read dates and modeled flow from historical SWAT import records", () => {
  const rows = datedMonthlyComparisonRows([
    { period: "2018-01-01", streamflow_m3s: 4.2, observed_streamflow_m3s: 3.8 },
    { streamflow_m3s: 2.1 },
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].month, "2018-01-01");
  assert.equal(rows[0].streamflow_m3s, 4.2);
  assert.equal(rows[0].observed_streamflow_m3s, 3.8);
});

test("historical charts appear only for completed runs without a playback artifact", () => {
  assert.equal(historicalFallbackEligible("COMPLETED", "NOT_AVAILABLE"), true);
  assert.equal(historicalFallbackEligible("COMPLETED", "AVAILABLE"), false);
  assert.equal(historicalFallbackEligible("RUNNING", "NOT_AVAILABLE"), false);
  assert.equal(historicalFallbackEligible(undefined, null), false);
});

test("historical SWAT import charts preserve stored periods and identify the import origin", () => {
  const response: SwatResultsResponse = {
    status: "COMPLETED", origin: "HISTORICAL_IMPORT", run_id: "historical-v2",
    provenance_class: "HISTORICAL_IMPORT",
    temporal_resolution: "monthly", records: [{ period: "2018-01-01", streamflow_m3s: 0, runoff_mm: 1.2,
      evapotranspiration_mm: 3.4, percolation_mm: null, soil_water_mm: 158 }],
    hru_results: [], water_balance: null,
    provenance: { source_kind: "HISTORICAL_IMPORT", schema_version: "south-fork-final-v2" },
  };
  const points = swatHistoricalPoints(response.records);
  assert.equal(response.origin, "HISTORICAL_IMPORT");
  assert.equal(response.temporal_resolution, "monthly");
  assert.equal(points[0].period, "2018-01-01");
  assert.equal(points[0].streamflow, 0);
  assert.equal(points[0].precipitation, null);
  assert.equal(points[0].percolation, null);
});

test("first-crop navigation uses only the selected resolution's representable stored date", () => {
  const availability: SimulationAvailability = {
    simulation_id: "fixture-coupled", simulation_name: "fixture", simulation_status: "COMPLETED",
    run_type: "SWAT_MULTISCALE_COUPLED", origin: "EXECUTED" as const,
    provenance_class: "COUPLED_EXECUTED",
    stored_hydrology_available: true, stored_fspm_summary_available: true,
    stored_fspm_trajectory_available: true, stored_fspm_samples_available: true, fspm_results_available: true,
    available_resolutions: ["MONTHLY", "DAILY"], codes: [], limitations: [],
    resolutions: [
      { resolution: "MONTHLY" as const, artifact_status: "AVAILABLE" as const, record_count: 12,
        first_record: "2020-01-01", last_record: "2020-12-01", first_active_crop: null,
        first_representable_field: null, first_plant_samples: null, crop_intervals: [],
        hydrology_available: true, fspm_trajectory_available: false, plant_samples_available: false,
        hru_ids: [], selected_date: null, codes: [] },
      { resolution: "DAILY" as const, artifact_status: "AVAILABLE" as const, record_count: 365,
        first_record: "2020-01-01", last_record: "2020-12-31", first_active_crop: "2020-05-01",
        first_representable_field: "2020-05-03", first_plant_samples: "2020-05-03", crop_intervals: [],
        hydrology_available: false, fspm_trajectory_available: true, plant_samples_available: true,
        hru_ids: [], selected_date: null, codes: [] },
    ],
  };
  assert.deepEqual(firstCropNavigation(availability, "DAILY"), { status: "READY", date: "2020-05-03" });
  assert.deepEqual(firstCropNavigation(availability, "MONTHLY"), { status: "SELECT_DAILY" });
  const baseline = { ...availability, run_type: "SWAT_STANDARD_BASELINE",
    stored_fspm_summary_available: false, stored_fspm_trajectory_available: false,
    stored_fspm_samples_available: false, fspm_results_available: false,
    resolutions: [{ ...availability.resolutions[0], first_representable_field: null,
      fspm_trajectory_available: false, plant_samples_available: false }] };
  assert.deepEqual(firstCropNavigation(baseline, "MONTHLY"), { status: "UNAVAILABLE" });
});

test("Pydantic generated fixtures feed the official visual adapter and current 3D inputs", () => {
  const data = JSON.parse(readFileSync(new URL("./fixtures/twin-visual-fixtures.json", import.meta.url), "utf8"));
  assert.equal(data.test_only, true);
  const pages = data.pages as Record<string, PlaybackPage>;
  const [young, mature, fallow] = pages.coupled_daily.records;
  const first = adaptPlaybackVisual(young, { simulationId: young.simulation_id, selectedPlantId: "test-plant-1" });
  const second = adaptPlaybackVisual(mature, { simulationId: mature.simulation_id, selectedPlantId: "test-plant-1" });
  assert.equal(first.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(first.height?.value, 0.2);
  assert.equal(first.laiDistribution?.p10?.value, young.field.lai_p10.value);
  assert.equal(first.rootDepthDistribution?.p90?.value, young.field.root_depth_p90_m.value);
  assert.equal(first.representativePlantCount?.value, 1000);
  assert.equal(first.plantSampleContext?.population_count, 1000);
  assert.equal(first.plantSampleContext?.captured_count, 1);
  assert.equal(first.plantSampleContext?.selection_method, "EVENLY_SPACED_STABLE_IDS");
  assert.equal(first.precipitation?.value, 0);
  assert.equal(first.fspmMoisturePercent?.unit, "volumetric percent");
  assert.equal(first.swatSoilWaterMm?.unit, "mm");
  assert.equal(first.biomass?.unit, "g/plant");
  assert.equal(second.phenologicalStage, "REPRODUCTIVE");
  assert.equal(second.precipitation?.value, null);
  assert.equal(adaptPlaybackVisual(fallow, { simulationId: fallow.simulation_id }).mode, "SCIENTIFIC_FALLOW");
  assert.equal(adaptPlaybackVisual(pages.baseline.records[0], { simulationId: "fixture-baseline" }).mode, "HYDROLOGY_ONLY");
  assert.equal(adaptPlaybackVisual(null, { simulationId: "fixture-historical", availability: {
    simulation_id: "fixture-historical", simulation_name: "Historical", simulation_status: "COMPLETED",
    run_type: "SWAT_MULTISCALE_COUPLED", origin: "HISTORICAL_IMPORT",
    provenance_class: "HISTORICAL_IMPORT",
    stored_hydrology_available: true, stored_fspm_summary_available: true,
    stored_fspm_trajectory_available: false, stored_fspm_samples_available: false,
    fspm_results_available: true, available_resolutions: [],
    resolutions: [], codes: ["HISTORICAL_REFERENCE"], limitations: [],
  } }).mode, "HISTORICAL_REFERENCE");
  const incomplete = adaptPlaybackVisual(pages.incomplete.records[0], { simulationId: "fixture-incomplete" });
  assert.equal(incomplete.mode, "DATA_UNAVAILABLE");
  assert.ok(incomplete.missingVariables.includes("field.height_m"));
  assert.equal(incomplete.height?.value, null);
  assert.equal(incomplete.lai?.value, 1.2);
  const monthly = adaptPlaybackVisual(pages.coupled_monthly.records[0], { simulationId: "fixture-coupled" });
  assert.equal(monthly.mode, "HYDROLOGY_ONLY");
  assert.equal(monthly.resolution, "MONTHLY");
  assert.equal(monthly.periodEnd, "2020-05-31");
  assert.equal(sceneFromRecord(young, "test-plant-1").visual.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(maizeFromScene(sceneFromRecord(young, "test-plant-1")).heightM, 0.2);
  assert.equal(fieldCanopyAvailable(sceneFromRecord(young, null)), true);
  assert.equal(fieldCanopyAvailable(sceneFromRecord(fallow, null)), false);
});

// --- Fase 5: Verificación exhaustiva con el contrato real phase234-sf-2019-v2 ---

function loadPhase234Frames(): Map<string, PlaybackRecord> {
  const gzPath = new URL("../../backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/playback.sqlite.gz", import.meta.url);
  const gz = readFileSync(gzPath);
  const tmp = join(tmpdir(), `test_p234_${Date.now()}_${Math.random().toString(36).slice(2)}.sqlite`);
  writeFileSync(tmp, gunzipSync(gz));
  const db = new DatabaseSync(tmp);
  const map = new Map<string, PlaybackRecord>();
  const targetDates = [
    "2019-01-15",
    "2019-05-15",
    "2019-07-15",
    "2019-08-27",
    "2019-08-30",
    "2019-09-03",
    "2019-09-15",
    "2019-12-15",
  ];
  for (const date of targetDates) {
    const row = db.prepare("SELECT payload FROM frames WHERE date = ?").get(date) as { payload: string } | undefined;
    if (row) {
      map.set(date, JSON.parse(row.payload) as PlaybackRecord);
    }
  }
  db.close();
  try { unlinkSync(tmp); } catch {}
  return map;
}

test("phase234-sf-2019-v2: full verification across 8 landmark dates (Jan 15, May 15, Jul 15, Aug 27, Aug 30, Sep 3, Sep 15, Dec 15)", () => {
  const frames = loadPhase234Frames();
  assert.equal(frames.size, 8);

  // 1. 15 de enero: Sin cultivo FSPM activo; hidrología disponible
  const jan15 = frames.get("2019-01-15")!;
  const sceneJan15 = sceneFromRecord(jan15, null);
  const visualJan15 = adaptPlaybackVisual(jan15, { simulationId: jan15.simulation_id });
  assert.equal(jan15.crop?.active, false);
  assert.equal(jan15.plant_samples.length, 0);
  assert.equal(jan15.hru_results.length, 36);
  assert.equal(jan15.channel_results.length, 37);
  assert.equal(visualJan15.mode, "SCIENTIFIC_FALLOW");
  assert.equal(fieldCanopyAvailable(sceneJan15), false);
  const plantJan15 = maizeFromScene(sceneJan15);
  assert.equal(plantJan15.heightM, null);
  assert.equal(plantJan15.reference, false);
  assert.equal(sceneJan15.soilWaterMm, 386.048);
  assert.equal(sceneJan15.streamflowM3s, 0.1172);

  // 2. 15 de mayo: Inicio de temporada (siembra de los primeros 4 calendarios, 40 muestras)
  const may15 = frames.get("2019-05-15")!;
  const sceneMay15 = sceneFromRecord(may15, null);
  const visualMay15 = adaptPlaybackVisual(may15, { simulationId: may15.simulation_id });
  assert.equal(may15.crop?.active, true);
  assert.equal(may15.crop?.phenological_stage, "EMERGENCE");
  assert.equal(may15.plant_samples.length, 40);
  assert.equal(may15.hru_results.length, 36);
  assert.equal(may15.channel_results.length, 37);
  assert.equal(visualMay15.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(fieldCanopyAvailable(sceneMay15), true);
  assert.ok(sceneMay15.fieldHeightM !== null && sceneMay15.fieldHeightM < 0.1); // plántulas ~0.05m
  const plantMay15 = maizeFromScene(sceneMay15);
  assert.ok(plantMay15.leafCount !== null && plantMay15.leafCount < 3); // ~2 hojas emergidas
  assert.ok(plantMay15.leafAreaM2 !== null && plantMay15.leafAreaM2 < 0.05);
  assert.equal(plantMay15.stage, "EMERGENCE");
  assert.equal(plantMay15.calendarId, "corn-2019-05-15-to-2019-08-27-01");
  assert.deepEqual(plantMay15.hruIds, ["19", "26"]);

  // 3. 15 de julio: Crecimiento activo y estados completos (70 muestras, 36 HRUs, 37 canales)
  const jul15 = frames.get("2019-07-15")!;
  const sceneJul15 = sceneFromRecord(jul15, null);
  const visualJul15 = adaptPlaybackVisual(jul15, { simulationId: jul15.simulation_id });
  assert.equal(jul15.crop?.active, true);
  assert.equal(jul15.crop?.phenological_stage, "REPRODUCTIVE");
  assert.equal(jul15.plant_samples.length, 70);
  assert.equal(jul15.hru_results.length, 36);
  assert.equal(jul15.channel_results.length, 37);
  assert.equal(visualJul15.mode, "SCIENTIFIC_ACTIVE");
  // Valores científicos documentados
  assert.ok(Math.abs((jul15.field.soil_moisture_vol_percent.value as number) - 29.23) < 0.1);
  assert.ok(Math.abs((jul15.field.water_stress.value as number) - 0.044) < 0.01);
  assert.ok(Math.abs((jul15.field.biomass_g_plant.value as number) - 167.65) < 0.1);
  assert.ok(Math.abs((jul15.hydrology.streamflow_m3s.value as number) - 0.3202) < 0.01);
  const plantJul15 = maizeFromScene(sceneJul15);
  assert.ok(plantJul15.leafCount !== null && plantJul15.leafCount > 15); // ~16 hojas simuladas
  assert.ok(plantJul15.heightM !== null && plantJul15.heightM > 2.0);
  assert.equal(maizeReproductive(plantJul15.stage), true);

  // 4. 30 de agosto: Periodo de cosecha escalonada (calendarios 1-3 cosechados, 40 muestras activas)
  const aug30 = frames.get("2019-08-30")!;
  const sceneAug30 = sceneFromRecord(aug30, null);
  const visualAug30 = adaptPlaybackVisual(aug30, { simulationId: aug30.simulation_id });
  assert.equal(sceneAug30.visual.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(aug30.crop?.active, true);
  assert.equal(aug30.crop?.phenological_stage, "MATURITY");
  assert.equal(aug30.plant_samples.length, 40);
  assert.equal(visualAug30.mode, "SCIENTIFIC_ACTIVE");
  assert.ok((aug30.field.biomass_g_plant.value as number) > 350); // Madurez fisiológica acumulada
  // Calendarios 1, 2, 3 ya fueron cosechados el 27, 28 y 29 de agosto
  assert.ok(!aug30.plant_samples.some((s) => s.calendar_id === "corn-2019-05-15-to-2019-08-27-01"));
  assert.ok(!aug30.plant_samples.some((s) => s.calendar_id === "corn-2019-05-15-to-2019-08-28-02"));
  assert.ok(!aug30.plant_samples.some((s) => s.calendar_id === "corn-2019-05-15-to-2019-08-29-03"));
  // Calendario 4, 5, 6, 7 están activos
  assert.ok(aug30.plant_samples.some((s) => s.calendar_id === "corn-2019-05-15-to-2019-08-30-04"));

  // 5. 15 de septiembre: Fin de temporada de cultivo; sin plantas FSPM activas
  const sep15 = frames.get("2019-09-15")!;
  const sceneSep15 = sceneFromRecord(sep15, null);
  const visualSep15 = adaptPlaybackVisual(sep15, { simulationId: sep15.simulation_id });
  assert.equal(sep15.crop?.active, false);
  assert.equal(sep15.plant_samples.length, 0);
  assert.equal(visualSep15.mode, "SCIENTIFIC_FALLOW");
  assert.equal(fieldCanopyAvailable(sceneSep15), false);
  assert.equal(maizeFromScene(sceneSep15).heightM, null);
  assert.equal(sceneSep15.streamflowM3s, 0.07147);

  // 6. 15 de diciembre: Condiciones hidrológicas de invierno disponibles sin cultivo
  const dec15 = frames.get("2019-12-15")!;
  const sceneDec15 = sceneFromRecord(dec15, null);
  const visualDec15 = adaptPlaybackVisual(dec15, { simulationId: dec15.simulation_id });
  assert.equal(dec15.crop?.active, false);
  assert.equal(dec15.plant_samples.length, 0);
  assert.equal(dec15.hru_results.length, 36);
  assert.equal(dec15.channel_results.length, 37);
  assert.equal(visualDec15.mode, "SCIENTIFIC_FALLOW");
  assert.equal(sceneDec15.streamflowM3s, 0.9707);
  assert.equal(sceneDec15.soilWaterMm, 408.167);
});

test("Micro scale: simulated leaf count, leaf area, biomass, calendar ID, and HRU IDs extracted to MaizeVisualState", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;

  // Seleccionar la muestra con ID específico
  const targetId = "corn-2019-05-15-to-2019-08-27-01:maize-00001";
  const scene = sceneFromRecord(jul15, targetId);
  const maize = maizeFromScene(scene);

  assert.equal(maize.sampleId, targetId);
  assert.equal(maize.reference, false);
  assert.equal(maize.calendarId, "corn-2019-05-15-to-2019-08-27-01");
  assert.deepEqual(maize.hruIds, ["19", "26"]);
  assert.ok(Math.abs(maize.leafCount! - 16.03) < 0.1); // Simulated leaf count
  assert.ok(Math.abs(maize.leafAreaM2! - 0.4635) < 0.01); // Simulated leaf area
  assert.ok(Math.abs(maize.biomassG! - 170.08) < 0.1); // Simulated biomass
  assert.ok(Math.abs(maize.heightM! - 2.239) < 0.01);
  assert.ok(Math.abs(maize.rootDepthM! - 1.276) < 0.01);
  assert.equal(maize.stage, "REPRODUCTIVE");
  assert.equal(maize.variables.leaf_count.evidence, "SIMPLIFIED_FSPM");
  assert.equal(maize.variables.height_m.unit, "m");
});

test("Meso scale: 1,014 decorative plants governed by field means; sample identity and calendar differences preserved across harvest dates", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;
  const aug30 = frames.get("2019-08-30")!;

  const targetId = "corn-2019-05-15-to-2019-08-27-01:maize-00001";
  // En julio, la muestra está activa
  const sampleJul = activePlantSample(jul15, targetId);
  assert.ok(sampleJul !== null);
  assert.equal(sampleJul.plant_id, targetId);
  assert.equal(sampleJul.calendar_id, "corn-2019-05-15-to-2019-08-27-01");

  // En agosto 30, ese calendario ya se cosechó (27 de agosto), por lo que esa muestra específica no existe
  const sampleAug = activePlantSample(aug30, targetId);
  assert.equal(sampleAug, null);

  // Pero el campo general sigue teniendo 40 muestras activas de calendarios 4-7
  assert.equal(aug30.plant_samples.length, 40);
  const activeFallback = activePlantSample(aug30, null);
  assert.ok(activeFallback !== null);
  assert.equal(activeFallback.calendar_id, "corn-2019-05-15-to-2019-08-30-04");
});

test("Macro scale: 36 HRUs and 37 Channels integrity, outlet channel GIS 153 matching basin streamflow, and unmapped geometry disclaimers", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;

  assert.equal(jul15.hru_results.length, 36);
  assert.equal(jul15.channel_results.length, 37);

  // Cada HRU y canal tiene variables y polígonos/geometrías explícitamente nulos
  jul15.hru_results.forEach((hru) => {
    assert.equal(hru.polygon_id, null); // Sin correspondencia GIS 1:1 inventada
    assert.ok(hru.variables.soil_water_mm);
    assert.ok(hru.variables.soil_water_mm.evidence === "MODELLED_SWAT_PLUS" || hru.variables.soil_water_mm.evidence === "NOT_AVAILABLE");
  });

  jul15.channel_results.forEach((channel) => {
    assert.equal(channel.geometry_id, null); // Sin correspondencia GIS inventada
    assert.ok(channel.variables.streamflow_m3s);
    assert.equal(channel.variables.streamflow_m3s.unit, "m3/s");
    assert.equal(channel.variables.channel_water_storage_m3.unit, "m3");
  });

  // Canal 25 / GIS 153 es el outlet que coincide con el caudal de cuenca publicado
  const outletChannel = jul15.channel_results.find((c) => c.gis_id === "153");
  assert.ok(outletChannel);
  assert.equal(outletChannel.channel_id, "25");
  assert.equal(outletChannel.variables.streamflow_m3s.value, jul15.hydrology.streamflow_m3s.value);
  assert.equal(outletChannel.variables.streamflow_m3s.value, 0.3202);
});

// --- Fase 5.1: Verificación de correcciones y pulido dinámico ---

test("Fase 5.1 - Unified visual classification: distinguishes hydrology-only vs fallow vs active vs data unavailable without false fallow", () => {
  const frames = loadPhase234Frames();
  const jan15 = frames.get("2019-01-15")!;
  const jul15 = frames.get("2019-07-15")!;

  // 1. Simulación acoplada en invierno: SCIENTIFIC_FALLOW (barbecho agronómico real)
  const visualJan = adaptPlaybackVisual(jan15, { simulationId: jan15.simulation_id });
  const sceneJan = sceneFromRecord(jan15, null);
  assert.equal(visualJan.mode, "SCIENTIFIC_FALLOW");
  assert.equal(sceneJan.visual.mode, "SCIENTIFIC_FALLOW");

  // 2. Simulación acoplada en verano: SCIENTIFIC_ACTIVE (cultivo de maíz activo)
  const visualJul = adaptPlaybackVisual(jul15, { simulationId: jul15.simulation_id });
  const sceneJul = sceneFromRecord(jul15, null);
  assert.equal(visualJul.mode, "SCIENTIFIC_ACTIVE");
  assert.equal(sceneJul.visual.mode, "SCIENTIFIC_ACTIVE");

  // 3. Simulación exclusivamente hidrológica (SWAT baseline sin FSPM, crop === null)
  const pureSwatRecord: PlaybackRecord = {
    ...jan15,
    crop: null,
    field: {} as unknown as PlaybackRecord["field"],
    plant_samples: [],
  };
  const visualSwat = adaptPlaybackVisual(pureSwatRecord, { simulationId: "swat-baseline" });
  const sceneSwat = sceneFromRecord(pureSwatRecord, null);
  // Debe ser HYDROLOGY_ONLY, NUNCA SCIENTIFIC_FALLOW
  assert.equal(visualSwat.mode, "HYDROLOGY_ONLY");
  assert.equal(sceneSwat.visual.mode, "HYDROLOGY_ONLY");

  // 4. Registro nulo / sin datos: DATA_UNAVAILABLE
  const visualNull = adaptPlaybackVisual(null, { simulationId: "empty" });
  assert.equal(visualNull.mode, "DATA_UNAVAILABLE");
});

test("Fase 5.1 - Meso scale: progressive harvest via active_crop_area_fraction across Aug 27, Aug 30, Sep 3, Sep 15", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;
  const aug27 = frames.get("2019-08-27")!;
  const aug30 = frames.get("2019-08-30")!;
  const sep03 = frames.get("2019-09-03")!;
  const sep15 = frames.get("2019-09-15")!;

  const sceneJul = sceneFromRecord(jul15, null);
  const sceneAug27 = sceneFromRecord(aug27, null);
  const sceneAug30 = sceneFromRecord(aug30, null);
  const sceneSep03 = sceneFromRecord(sep03, null);
  const sceneSep15 = sceneFromRecord(sep15, null);

  // 1. Plena temporada (15 Jul): 100% superficie activa
  assert.equal(sceneJul.activeCropAreaFraction, 1.0);
  assert.equal(jul15.plant_samples.length, 70);

  // 2. Inicio de cosecha (27 Ago): 100% de superficie activa durante el día
  assert.equal(sceneAug27.activeCropAreaFraction, 1.0);
  assert.equal(aug27.plant_samples.length, 70);

  // 3. Cosecha intermedia (30 Ago): ~43.3% superficie activa (calendarios 1-3 cosechados)
  assert.ok(sceneAug30.activeCropAreaFraction !== null);
  assert.ok(sceneAug30.activeCropAreaFraction > 0.40 && sceneAug30.activeCropAreaFraction < 0.45);
  assert.equal(aug30.plant_samples.length, 40);

  // 4. Último día de cosecha (3 Sep): ~3.65% superficie activa (solo calendario 7)
  assert.ok(sceneSep03.activeCropAreaFraction !== null);
  assert.ok(sceneSep03.activeCropAreaFraction > 0.03 && sceneSep03.activeCropAreaFraction < 0.05);
  assert.equal(sep03.plant_samples.length, 10);

  // 5. Post-cosecha completa (15 Sep): 0% superficie activa, fallow
  assert.equal(sceneSep15.activeCropAreaFraction, 0);
  assert.equal(sep15.plant_samples.length, 0);
  assert.equal(sceneSep15.cropActive, false);

  // Verificación de monotonía decreciente en periodo de cosecha
  assert.ok(sceneAug27.activeCropAreaFraction! >= sceneAug30.activeCropAreaFraction!);
  assert.ok(sceneAug30.activeCropAreaFraction! >= sceneSep03.activeCropAreaFraction!);
  assert.ok(sceneSep03.activeCropAreaFraction! >= sceneSep15.activeCropAreaFraction!);
});

test("Fase 5.1 - Sample identity: sample disappearance after harvest, no silent substitution with field averages", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;
  const aug30 = frames.get("2019-08-30")!;

  const cal1PlantId = "corn-2019-05-15-to-2019-08-27-01:maize-00001";

  // En julio, la muestra está activa
  const sampleJul = activePlantSample(jul15, cal1PlantId);
  assert.ok(sampleJul !== null);
  assert.equal(sampleJul.plant_id, cal1PlantId);
  assert.equal(sampleJul.calendar_id, "corn-2019-05-15-to-2019-08-27-01");

  // En agosto 30, la muestra ya fue cosechada
  const sampleAug = activePlantSample(aug30, cal1PlantId);
  assert.equal(sampleAug, null);

  // sceneFromRecord con cal1PlantId debe retornar sample: null sin sustituirlo silenciosamente
  const sceneAug = sceneFromRecord(aug30, cal1PlantId);
  assert.equal(sceneAug.sample, null);

  // maizeFromScene no debe mostrar la planta como activa ni inventar datos
  const maizeAug = maizeFromScene(sceneAug);
  assert.equal(maizeAug.heightM, null);
  assert.equal(maizeAug.sampleId, null);
  assert.equal(maizeAug.reference, false);

  // El campo meso aún conserva 40 muestras de calendarios 4-7
  assert.equal(aug30.plant_samples.length, 40);
  // Al seleccionar null, activePlantSample devuelve una de las muestras activas
  const fallbackSample = activePlantSample(aug30, null);
  assert.ok(fallbackSample !== null);
  assert.notEqual(fallbackSample.calendar_id, "corn-2019-05-15-to-2019-08-27-01");
});

test("Fase 5.1 - Optional variables safety & Macro Entity Explorer dynamic counts", () => {
  const frames = loadPhase234Frames();
  const jul15 = frames.get("2019-07-15")!;

  // 1. Manejo seguro de variable ausente: variableText devuelve 'No disponible'
  const absentVariable: VariableState = {
    value: null,
    unit: "m3",
    availability: "NOT_AVAILABLE",
    evidence: "NOT_AVAILABLE",
    source: "test",
    limitation: null,
  };
  assert.equal(variableText(absentVariable), "No disponible");
  assert.equal(numeric(absentVariable), null);

  // 2. Variable con valor 0 real se muestra como '0 m3', no 'No disponible'
  const zeroVariable: VariableState = {
    value: 0,
    unit: "m3",
    availability: "AVAILABLE",
    evidence: "MODELLED_SWAT_PLUS",
    source: "test",
    limitation: null,
  };
  assert.equal(variableText(zeroVariable), "0 m3");
  assert.equal(numeric(zeroVariable), 0);

  // 3. Identificación dinámica del outlet a partir de record.outlet_unit
  assert.equal(jul15.outlet_unit, "153");
  const outlet = jul15.channel_results.find(
    (c) => c.gis_id === jul15.outlet_unit || c.channel_id === jul15.outlet_unit
  );
  assert.ok(outlet);
  assert.equal(outlet.channel_id, "25");
  assert.equal(outlet.gis_id, "153");

  // 4. Recuentos dinámicos del registro
  assert.equal(jul15.hru_results.length, 36);
  assert.equal(jul15.channel_results.length, 37);

  // 5. Agrupación dinámica de calendarios de maíz
  const calendarSet = new Set(
    jul15.hru_results.map((h) => h.calendar_id).filter((c): c is string => Boolean(c))
  );
  assert.equal(calendarSet.size, 7);
});

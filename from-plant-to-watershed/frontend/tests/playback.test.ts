import test from "node:test";
import assert from "node:assert/strict";
import { rainIntensity, sceneFromRecord, periodLabel, variableText, chartPointFromRecord, hasSouthForkContext } from "../src/lib/playback-scene.ts";
import { PlaybackClient } from "../src/lib/playback-client.ts";
import type { PlaybackPage, PlaybackRecord, VariableState } from "../src/types/playback.ts";

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
    hru_results: [], availability: {}, limitations: [],
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

import type { SimulationResult, SwatRecord } from "../types/simulation";

export interface HistoricalChartPoint {
  period: string;
  precipitation: number | null;
  streamflow: number | null;
  runoff: number | null;
  evapotranspiration: number | null;
  percolation: number | null;
  soilWater: number | null;
  stress: number | null;
  transpiration: number | null;
}

export function historicalFallbackEligible(simulationStatus: string | undefined, artifactStatus: string | null): boolean {
  return simulationStatus === "COMPLETED" && artifactStatus === "NOT_AVAILABLE";
}

const finite = (value: number | null | undefined): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

/** Historical SWAT+ output has no recoverable precipitation or daily FSPM trajectory. */
export function swatHistoricalPoints(records: SwatRecord[]): HistoricalChartPoint[] {
  return records.map((row) => ({
    period: row.period,
    precipitation: null,
    streamflow: finite(row.streamflow_m3s),
    runoff: finite(row.runoff_mm),
    evapotranspiration: finite(row.evapotranspiration_mm),
    percolation: finite(row.percolation_mm),
    soilWater: finite(row.soil_water_mm),
    stress: null,
    transpiration: null,
  }));
}

/** Only persisted legacy result fields are plotted; no values are reconstructed from SWAT+. */
export function simplifiedHistoricalPoints(records: SimulationResult[]): HistoricalChartPoint[] {
  return records.map((row) => ({
    period: row.date_str,
    precipitation: finite(row.precip_mm),
    streamflow: finite(row.streamflow_m3s),
    runoff: finite(row.surface_runoff_mm),
    evapotranspiration: finite(row.actual_et_mm),
    percolation: finite(row.percolation_mm),
    soilWater: null,
    stress: finite(row.cwsi_stress_index),
    transpiration: finite(row.plant_transpiration_mm),
  }));
}

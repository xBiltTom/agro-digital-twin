"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { historicalFallbackEligible, simplifiedHistoricalPoints, swatHistoricalPoints, type HistoricalChartPoint } from "../lib/historical-charts";
import type { SimulationRun } from "../types/simulation";

interface LoadedSeries {
  simulationId: string;
  kind: "SWAT_PLUS" | "SIMPLIFIED";
  points: HistoricalChartPoint[];
  truncated: boolean;
  error: string | null;
}

export function useHistoricalCharts(simulation: SimulationRun | null, artifactStatus: string | null) {
  const [loaded, setLoaded] = useState<LoadedSeries | null>(null);
  const canLoad = historicalFallbackEligible(simulation?.status, artifactStatus);
  const simulationId = simulation?.id ?? null;
  const backend = simulation?.hydrology_backend;
  const duration = simulation?.duration_days ?? 0;

  useEffect(() => {
    if (!canLoad || !simulationId) return;
    let cancelled = false;
    async function load() {
      try {
        if (backend === "SWAT_PLUS") {
          const result = await api.getSwatResults(simulationId!);
          if (!cancelled) setLoaded({ simulationId: simulationId!, kind: "SWAT_PLUS",
            points: swatHistoricalPoints(result.records), truncated: false, error: null });
        } else {
          const result = await api.getSimulationResults(simulationId!, Math.min(Math.max(duration, 1), 1000));
          if (!cancelled) setLoaded({ simulationId: simulationId!, kind: "SIMPLIFIED",
            points: simplifiedHistoricalPoints(result), truncated: duration > 1000, error: null });
        }
      } catch (cause) {
        if (!cancelled) setLoaded({ simulationId: simulationId!, kind: backend === "SWAT_PLUS" ? "SWAT_PLUS" : "SIMPLIFIED",
          points: [], truncated: false,
          error: cause instanceof Error ? cause.message : "No se pudieron cargar los resultados históricos" });
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [canLoad, simulationId, backend, duration]);

  if (!canLoad) return { status: "idle" as const, data: null };
  if (loaded?.simulationId !== simulationId) return { status: "loading" as const, data: null };
  return { status: loaded.error ? "error" as const : "ready" as const, data: loaded };
}

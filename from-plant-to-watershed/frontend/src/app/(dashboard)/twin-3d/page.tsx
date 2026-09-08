"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { SimulationRun, SimulationResult } from "../../../types/simulation";
import MultiScaleViewer3D, { ScaleMode } from "../../../components/3d/MultiScaleViewer3D";
import TwinHUDOverlay from "../../../components/3d/TwinHUDOverlay";
import { Box, Loader2 } from "lucide-react";

export default function Twin3DPage() {
  const [scaleMode, setScaleMode] = useState<ScaleMode>("MACRO");
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationRun | null>(null);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Timeline & Playback
  const [currentDay, setCurrentDay] = useState(1);
  const [isPlaying, setIsPlaying] = useState(true);

  // Cargar simulaciones y resultados
  useEffect(() => {
    async function loadData() {
      try {
        const sims = await api.getSimulations();
        setSimulations(sims);
        if (sims.length > 0) {
          setSelectedSim(sims[0]);
          const dailyRes = await api.getSimulationResults(sims[0].id, sims[0].duration_days);
          setResults(dailyRes);
        }
      } catch (err) {
        console.error("Error al cargar simulación 3D:", err);
        setLoadError("No se pudieron cargar resultados de simulación desde el backend.");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  // Animación del reproductor temporal
  useEffect(() => {
    if (!isPlaying || results.length === 0) return;

    const interval = setInterval(() => {
      setCurrentDay((prev) => (prev >= results.length ? 1 : prev + 1));
    }, 600);

    return () => clearInterval(interval);
  }, [isPlaying, results.length]);

  const currentData = results[currentDay - 1];

  return (
    <div className="flex flex-col gap-4 max-w-7xl mx-auto h-[calc(100vh-8.5rem)] min-h-[640px]">
      {/* Header Bar */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
            <Box className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              Maíz → campo → HRU → cuenca
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
                WebGL Activo
              </span>
            </h1>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Muestra persistida de plantas y agregados de una corrida multiescala. FSPM y SWAT+ son objetivos de integración, no motores activos.
            </span>
          </div>
        </div>

        {/* Scenario Selector */}
        {simulations.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400 hidden sm:inline">Simulación:</span>
            <select
              value={selectedSim?.id}
              onChange={async (e) => {
                const sim = simulations.find((s) => s.id === e.target.value);
                if (sim) {
                  try {
                    const dailyRes = await api.getSimulationResults(sim.id, sim.duration_days);
                    setSelectedSim(sim);
                    setResults(dailyRes);
                    setCurrentDay(1);
                    setLoadError(null);
                  } catch (err) {
                    console.error("Error al cambiar la simulación 3D:", err);
                    setResults([]);
                    setLoadError("No se pudieron cargar los resultados seleccionados.");
                  }
                }
              }}
              className="px-3 py-1.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 text-xs focus:outline-none focus:border-cyan-500/80 font-mono shadow-sm"
            >
              {simulations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 3D Canvas Area with Overlay HUD */}
      <div className="flex-1 relative rounded-2xl overflow-hidden border border-zinc-300/80 dark:border-zinc-800 shadow-xl dark:shadow-2xl">
        {isLoading ? (
          <div className="w-full h-full bg-zinc-950 flex flex-col items-center justify-center gap-3 text-zinc-400 text-xs">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
            <span>Cargando corrida y muestra de maíz persistida...</span>
          </div>
        ) : currentData ? (
          <>
            <MultiScaleViewer3D
              scaleMode={scaleMode}
              onChangeScale={setScaleMode}
              streamflowM3s={currentData.streamflow_m3s}
              precipMm={currentData.precip_mm}
              soilMoistureVol={currentData.soil_moisture_vol}
              transpirationMm={currentData.plant_transpiration_mm}
              cwsiStress={currentData.cwsi_stress_index}
              sapFlowVelocityCmh={currentData.sap_flow_velocity_cmh}
              plantSample={selectedSim?.plant_sample ?? []}
              plantCount={selectedSim?.plant_count ?? 1000}
              fieldAggregates={selectedSim?.field_aggregates}
              hruAggregates={selectedSim?.hru_aggregates as { hrus?: Array<{ hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string }> } | undefined}
            />

            <TwinHUDOverlay
              scaleMode={scaleMode}
              onChangeScale={setScaleMode}
              streamflowM3s={currentData.streamflow_m3s}
              precipMm={currentData.precip_mm}
              soilMoistureVol={currentData.soil_moisture_vol}
              transpirationMm={currentData.plant_transpiration_mm}
              cwsiStress={currentData.cwsi_stress_index}
              sapFlowVelocityCmh={currentData.sap_flow_velocity_cmh}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying(!isPlaying)}
              currentDay={currentDay}
              totalDays={results.length}
              onSeekDay={setCurrentDay}
            />
          </>
        ) : (
          <div className="w-full h-full bg-zinc-950 flex flex-col items-center justify-center gap-2 text-center p-6">
            <Box className="w-8 h-8 text-zinc-500" />
            <span className="text-sm font-semibold text-zinc-300">NO SIMULATION RESULTS</span>
            <span className="text-xs text-zinc-500 max-w-md">{loadError || "No hay resultados persistidos disponibles para el visor 3D."}</span>
          </div>
        )}
      </div>
    </div>
  );
}

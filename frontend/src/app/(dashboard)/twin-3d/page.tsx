"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { api } from "../../../lib/api";
import { SimulationRun, SimulationResult } from "../../../types/simulation";
import MultiScaleViewer3D, { ScaleMode } from "../../../components/3d/MultiScaleViewer3D";
import TwinHUDOverlay from "../../../components/3d/TwinHUDOverlay";
import { Box, Layers, Loader2, Sparkles } from "lucide-react";

export default function Twin3DPage() {
  const [scaleMode, setScaleMode] = useState<ScaleMode>("MACRO");
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationRun | null>(null);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Timeline & Playback
  const [currentDay, setCurrentDay] = useState(1);
  const [isPlaying, setIsPlaying] = useState(true);

  // Shock Modifiers (Overrides temporales de usuario)
  const [rainShock, setRainShock] = useState(0);
  const [heatShock, setHeatShock] = useState(0);

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

  // Datos del día actual interpolados con forzamientos de choque si existen
  const currentData = results[currentDay - 1] || {
    precip_mm: 12.0,
    streamflow_m3s: 8.5,
    soil_moisture_vol: 28.0,
    plant_transpiration_mm: 3.2,
    cwsi_stress_index: 0.18,
    sap_flow_velocity_cmh: 12.0,
  };

  const activePrecip = currentData.precip_mm + rainShock;
  const activeStreamflow = Math.max(0.8, currentData.streamflow_m3s + (rainShock > 0 ? 18.5 : 0));
  const activeSoilMoisture = Math.min(42.0, Math.max(8.0, currentData.soil_moisture_vol + (rainShock > 0 ? 8.0 : 0) - (heatShock > 0 ? 5.0 : 0)));
  const activeCwsi = Math.min(1.0, Math.max(0.0, currentData.cwsi_stress_index + (heatShock > 0 ? 0.35 : 0) - (rainShock > 0 ? 0.15 : 0)));
  const activeTranspiration = Math.max(0.5, currentData.plant_transpiration_mm + (heatShock > 0 ? 1.5 : 0));
  const activeSapFlow = Math.max(2.0, currentData.sap_flow_velocity_cmh + (heatShock > 0 ? 6.0 : 0));

  const handleInjectRain = () => {
    setRainShock(45.0);
    setHeatShock(0);
  };

  const handleInjectHeatwave = () => {
    setHeatShock(4.0);
    setRainShock(0);
  };

  const handleResetWeather = () => {
    setRainShock(0);
    setHeatShock(0);
  };

  return (
    <div className="flex flex-col gap-4 max-w-7xl mx-auto h-[calc(100vh-8.5rem)] min-h-[640px]">
      {/* Header Bar */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Box className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-base font-bold text-zinc-100 flex items-center gap-2">
              Gemelo Digital 3D Multiescala
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                WebGL Activo
              </span>
            </h1>
            <span className="text-[11px] text-zinc-400">
              Acoplamiento Fisiológico Vegetal (Micro) ⇄ Parcela (Meso) ⇄ Cuenca SWAT (Macro)
            </span>
          </div>
        </div>

        {/* Scenario Selector */}
        {simulations.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-zinc-400 hidden sm:inline">Simulación:</span>
            <select
              value={selectedSim?.id}
              onChange={async (e) => {
                const sim = simulations.find((s) => s.id === e.target.value);
                if (sim) {
                  setSelectedSim(sim);
                  const dailyRes = await api.getSimulationResults(sim.id, sim.duration_days);
                  setResults(dailyRes);
                  setCurrentDay(1);
                }
              }}
              className="px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-cyan-500/80 font-mono"
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
      <div className="flex-1 relative rounded-2xl overflow-hidden border border-zinc-800 shadow-2xl">
        {isLoading ? (
          <div className="w-full h-full bg-zinc-950 flex flex-col items-center justify-center gap-3 text-zinc-400 text-xs">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
            <span>Inicializando motor 3D y cargando malla topográfica DEM...</span>
          </div>
        ) : (
          <>
            <MultiScaleViewer3D
              scaleMode={scaleMode}
              onChangeScale={setScaleMode}
              streamflowM3s={activeStreamflow}
              precipMm={activePrecip}
              soilMoistureVol={activeSoilMoisture}
              transpirationMm={activeTranspiration}
              cwsiStress={activeCwsi}
              sapFlowVelocityCmh={activeSapFlow}
            />

            <TwinHUDOverlay
              scaleMode={scaleMode}
              onChangeScale={setScaleMode}
              streamflowM3s={activeStreamflow}
              precipMm={activePrecip}
              soilMoistureVol={activeSoilMoisture}
              transpirationMm={activeTranspiration}
              cwsiStress={activeCwsi}
              sapFlowVelocityCmh={activeSapFlow}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying(!isPlaying)}
              currentDay={currentDay}
              totalDays={results.length || 365}
              onSeekDay={setCurrentDay}
              onInjectRain={handleInjectRain}
              onInjectHeatwave={handleInjectHeatwave}
              onResetWeather={handleResetWeather}
            />
          </>
        )}
      </div>
    </div>
  );
}

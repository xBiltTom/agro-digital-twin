"use client";

import React, { useState } from "react";
import { ScaleMode } from "./MultiScaleViewer3D";
import {
  Mountain,
  Grid,
  Sprout,
  Play,
  Pause,
  CloudRain,
  Activity,
  Droplets,
  Gauge,
  Thermometer,
  Waves,
  Layers,
  Radio,
  FileText,
  Info,
  CheckCircle2,
  X,
  Compass,
} from "lucide-react";

interface TwinHUDOverlayProps {
  scaleMode: ScaleMode;
  onChangeScale: (scale: ScaleMode) => void;
  streamflowM3s: number;
  precipMm: number;
  soilMoistureVol: number;
  transpirationMm: number;
  cwsiStress: number;
  sapFlowVelocityCmh: number;
  isPlaying: boolean;
  onTogglePlay: () => void;
  currentDay: number;
  totalDays: number;
  onSeekDay: (day: number) => void;
  showHydrologyFlow?: boolean;
  onToggleHydrologyFlow?: () => void;
  showSoilHorizons?: boolean;
  onToggleSoilHorizons?: () => void;
  showSensors?: boolean;
  onToggleSensors?: () => void;
  showScientificLabels?: boolean;
  onToggleScientificLabels?: () => void;
  scenarioName?: string;
  scenarioPathway?: string;
}

export default function TwinHUDOverlay({
  scaleMode,
  onChangeScale,
  streamflowM3s,
  precipMm,
  soilMoistureVol,
  transpirationMm,
  cwsiStress,
  sapFlowVelocityCmh,
  isPlaying,
  onTogglePlay,
  currentDay,
  totalDays,
  onSeekDay,
  showHydrologyFlow = true,
  onToggleHydrologyFlow,
  showSoilHorizons = true,
  onToggleSoilHorizons,
  showSensors = true,
  onToggleSensors,
  showScientificLabels = true,
  onToggleScientificLabels,
  scenarioName = "SSP2-4.5 (Línea Base)",
  scenarioPathway = "SSP2-4.5",
}: TwinHUDOverlayProps) {
  const [showScientificModal, setShowScientificModal] = useState(false);

  const getStressBadge = (stress: number) => {
    if (stress < 0.25) {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Óptimo ({stress.toFixed(2)})
        </span>
      );
    } else if (stress < 0.55) {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          Moderado ({stress.toFixed(2)})
        </span>
      );
    } else {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
          Estrés Crítico ({stress.toFixed(2)})
        </span>
      );
    }
  };

  // Porcentajes de barras de nivel
  const qPercent = Math.min(100, (streamflowM3s / 30) * 100);
  const thetaPercent = Math.min(100, (soilMoistureVol / 45) * 100);
  const trPercent = Math.min(100, (transpirationMm / 6) * 100);
  const sapPercent = Math.min(100, (sapFlowVelocityCmh / 20) * 100);

  return (
    <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between z-20 select-none transition-colors duration-200">
      {/* Barra superior: selector de escala y controles de capas */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pointer-events-auto">
        {/* Selector de Escala Macro / Meso / Micro */}
        <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-white/90 dark:bg-zinc-950/90 backdrop-blur-xl border border-zinc-200/90 dark:border-zinc-800/80 shadow-lg dark:shadow-2xl">
          <button
            onClick={() => onChangeScale("MACRO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MACRO"
                ? "bg-gradient-to-r from-teal-500/20 to-cyan-500/20 text-teal-700 dark:text-teal-300 border border-teal-500/40 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
            }`}
          >
            <Mountain className="w-3.5 h-3.5" />
            <span>Macro: Cuenca SWAT+</span>
          </button>

          <button
            onClick={() => onChangeScale("MESO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MESO"
                ? "bg-gradient-to-r from-cyan-500/20 to-sky-500/20 text-cyan-700 dark:text-cyan-300 border border-cyan-500/40 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Meso: Campo BARC (n=1000)</span>
          </button>

          <button
            onClick={() => onChangeScale("MICRO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MICRO"
                ? "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/40 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
            }`}
          >
            <Sprout className="w-3.5 h-3.5" />
            <span>Micro: FSPM Zea mays</span>
          </button>
        </div>

        {/* Barra de capas y botón de marco metodológico */}
        <div className="flex items-center gap-2">
          {/* Toggles de Capas 3D */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-white/85 dark:bg-zinc-950/85 backdrop-blur-xl border border-zinc-200/80 dark:border-zinc-800/80 shadow-md">
            {onToggleHydrologyFlow && (
              <button
                onClick={onToggleHydrologyFlow}
                title="Alternar Flujo Hídrico y Savia 3D"
                className={`p-1.5 rounded-lg text-xs transition cursor-pointer ${
                  showHydrologyFlow
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Waves className="w-3.5 h-3.5" />
              </button>
            )}

            {onToggleSoilHorizons && (
              <button
                onClick={onToggleSoilHorizons}
                title="Alternar Capas SoilGrids 2.0 / Parcelas HRU"
                className={`p-1.5 rounded-lg text-xs transition cursor-pointer ${
                  showSoilHorizons
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
              </button>
            )}

            {onToggleSensors && (
              <button
                onClick={onToggleSensors}
                title="Alternar Instrumentación (Torre Eddy Covariance / Sondas / USGS)"
                className={`p-1.5 rounded-lg text-xs transition cursor-pointer ${
                  showSensors
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Radio className="w-3.5 h-3.5" />
              </button>
            )}

            {onToggleScientificLabels && (
              <button
                onClick={onToggleScientificLabels}
                title="Alternar Etiquetas Científicas 3D"
                className={`p-1.5 rounded-lg text-xs transition cursor-pointer ${
                  showScientificLabels
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Botón de Marco Científico e Hipótesis */}
          <button
            onClick={() => setShowScientificModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-500/15 to-teal-500/15 hover:from-emerald-500/25 hover:to-teal-500/25 border border-emerald-500/35 text-emerald-700 dark:text-emerald-300 text-xs font-mono font-semibold backdrop-blur-xl shadow-md cursor-pointer transition active:scale-95"
          >
            <Compass className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Marco Científico (H1)</span>
          </button>
        </div>
      </div>

      {/* Alerta de Lluvia Activa */}
      {precipMm > 10 && (
        <div className="self-center p-2 px-4 rounded-full bg-cyan-50 dark:bg-cyan-950/85 border border-cyan-300 dark:border-cyan-500/40 text-cyan-800 dark:text-cyan-300 text-xs font-mono flex items-center gap-2 shadow-lg pointer-events-auto backdrop-blur-md">
          <CloudRain className="w-4 h-4 animate-bounce text-cyan-400" />
          <span>Precipitación Activa (CHIRPS): {precipMm.toFixed(1)} mm/día</span>
        </div>
      )}

      {/* Modal de Marco Científico, DAG e Hipótesis */}
      {showScientificModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 pointer-events-auto">
          <div className="max-w-2xl w-full bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl p-5 text-zinc-200 font-mono text-xs max-h-[85vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm text-zinc-100">
                  From Plant to Watershed: Framework Científico Multi-Escala
                </h3>
              </div>
              <button
                onClick={() => setShowScientificModal(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* DAG del Proyecto */}
            <div className="bg-zinc-900/80 p-3.5 rounded-xl border border-zinc-800">
              <div className="text-[11px] font-bold text-teal-400 mb-1">
                DAG Causal del Acoplamiento:
              </div>
              <div className="text-zinc-300 text-[10px] leading-relaxed">
                CO₂ + Temperatura + Precipitación → Crecimiento FSPM Zea mays → ET + Infiltración →
                Escorrentía SWAT+ → Disponibilidad Hídrica de Cuenca. (Manejo agrícola modula cada flecha).
              </div>
            </div>

            {/* Hipótesis de Investigación */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-zinc-900/50 p-3 rounded-xl border border-zinc-800">
                <div className="font-bold text-amber-400 text-[11px] mb-1">Hipótesis H0:</div>
                <div className="text-zinc-400 text-[10px]">
                  El acoplamiento planta-cuenca no mejora la predicción de escorrentía vs. SWAT+ con parámetros promedio tabulados.
                </div>
              </div>
              <div className="bg-emerald-950/30 p-3 rounded-xl border border-emerald-500/30">
                <div className="font-bold text-emerald-300 text-[11px] mb-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  Hipótesis H1 (Objetivo):
                </div>
                <div className="text-emerald-200 text-[10px]">
                  El twin multi-escala reduce el RMSE de escorrentía mensual en ≥15% (Wilcoxon signed-rank p &lt; 0.01) con representación espacial n=1000 BARC.
                </div>
              </div>
            </div>

            {/* Pruebas Estadísticas */}
            <div className="bg-zinc-900/50 p-3 rounded-xl border border-zinc-800 space-y-1.5">
              <div className="font-bold text-cyan-400 text-[11px]">Pruebas Estadísticas Validadas:</div>
              <ul className="list-disc pl-4 space-y-0.5 text-zinc-300 text-[10px]">
                <li><span className="font-bold text-zinc-100">Kolmogorov-Smirnov (KS):</span> Valida distribución de escorrentía simulada vs. observada (USGS #05451210).</li>
                <li><span className="font-bold text-zinc-100">Wilcoxon signed-rank:</span> Comparación pareada del RMSE mensual (Twin vs SWAT+ estándar).</li>
                <li><span className="font-bold text-zinc-100">Método de Sobol:</span> Sensibilidad global (Transpiración Tr 0.42, Zmax 0.31, LAI 0.18).</li>
                <li><span className="font-bold text-zinc-100">Métricas:</span> NSE ≥ 0.78, PBIAS &lt; ±10%, R² ≥ 0.84.</li>
              </ul>
            </div>

            {/* Datasets */}
            <div className="text-[10px] text-zinc-400 flex flex-wrap gap-2 pt-1 border-t border-zinc-800">
              <span className="bg-zinc-800 px-2 py-0.5 rounded">USDA NASS</span>
              <span className="bg-zinc-800 px-2 py-0.5 rounded">SoilGrids 2.0</span>
              <span className="bg-zinc-800 px-2 py-0.5 rounded">CHIRPS</span>
              <span className="bg-zinc-800 px-2 py-0.5 rounded">Landsat (USGS)</span>
              <span className="bg-zinc-800 px-2 py-0.5 rounded">CMIP6 (NASA NEX-GDDP)</span>
            </div>
          </div>
        </div>
      )}

      {/* Parte inferior: panel de resultados y barra de tiempo */}
      <div className="flex flex-col gap-3 pointer-events-auto">
        {/* Tarjeta de resultados persistidos con barras de nivel */}
        <div className="p-4 rounded-2xl bg-white/95 dark:bg-zinc-950/90 backdrop-blur-2xl border border-zinc-200/90 dark:border-zinc-800/90 shadow-xl dark:shadow-2xl max-w-xl self-start">
          <div className="flex items-center justify-between mb-3 border-b border-zinc-200 dark:border-zinc-800/80 pb-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <Activity className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-bold text-zinc-800 dark:text-zinc-100 uppercase tracking-wider">
                Corrida Multiescala · {scenarioPathway}
              </span>
            </div>
            <div>{getStressBadge(cwsiStress)}</div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            {/* Caudal SWAT+ */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 dark:text-zinc-400">
                <span className="flex items-center gap-1">
                  <Waves className="w-3 h-3 text-teal-600 dark:text-teal-400" /> Caudal (Q)
                </span>
              </div>
              <span className="text-sm font-bold text-teal-700 dark:text-teal-300">
                {streamflowM3s.toFixed(2)} <span className="text-[10px] font-normal text-zinc-500 dark:text-zinc-400">m³/s</span>
              </span>
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-teal-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${qPercent}%` }}
                />
              </div>
            </div>

            {/* Humedad del Suelo (SoilGrids 2.0) */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 dark:text-zinc-400">
                <span className="flex items-center gap-1">
                  <Droplets className="w-3 h-3 text-cyan-600 dark:text-cyan-400" /> Humedad (θ)
                </span>
              </div>
              <span className="text-sm font-bold text-cyan-700 dark:text-cyan-300">
                {soilMoistureVol.toFixed(1)} <span className="text-[10px] font-normal text-zinc-500 dark:text-zinc-400">%</span>
              </span>
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-cyan-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${thetaPercent}%` }}
                />
              </div>
            </div>

            {/* Transpiración FSPM */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 dark:text-zinc-400">
                <span className="flex items-center gap-1">
                  <Gauge className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> Transp. (Tr)
                </span>
              </div>
              <span className="text-sm font-bold text-emerald-700 dark:text-emerald-300">
                {transpirationMm.toFixed(2)} <span className="text-[10px] font-normal text-zinc-500 dark:text-zinc-400">mm/d</span>
              </span>
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${trPercent}%` }}
                />
              </div>
            </div>

            {/* Flujo de Savia Xilema */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 dark:text-zinc-400">
                <span className="flex items-center gap-1">
                  <Thermometer className="w-3 h-3 text-sky-600 dark:text-sky-400" /> Savia Xilema
                </span>
              </div>
              <span className="text-sm font-bold text-sky-700 dark:text-sky-300">
                {sapFlowVelocityCmh.toFixed(1)} <span className="text-[10px] font-normal text-zinc-500 dark:text-zinc-400">cm/h</span>
              </span>
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-sky-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${sapPercent}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-2.5 pt-2 border-t border-zinc-200/80 dark:border-zinc-800/80 text-[10px] text-zinc-500 flex justify-between">
            <span>FSPM (Nivel 1) → BARC (Nivel 2) → SWAT+ HRU (Nivel 3) → CMIP6</span>
            <span className="text-emerald-400 font-bold">H1: ΔRMSE ≥ 15%</span>
          </div>
        </div>

        {/* Barra de Control y Reproductor Temporal */}
        <div className="p-3.5 rounded-2xl bg-white/95 dark:bg-zinc-950/90 backdrop-blur-2xl border border-zinc-200/90 dark:border-zinc-800/90 shadow-xl dark:shadow-2xl flex items-center gap-4">
          <button
            onClick={onTogglePlay}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 hover:from-emerald-500 hover:to-teal-300 text-white dark:text-zinc-950 flex items-center justify-center transition-all duration-300 cursor-pointer shadow-lg shadow-emerald-500/25 shrink-0 hover:scale-105 active:scale-95"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>

          <div className="flex-1 flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
                Día hidrológico y fisiológico acoplado
              </span>
              <span className="text-zinc-800 dark:text-zinc-200 font-bold bg-zinc-100 dark:bg-zinc-900 px-2 py-0.5 rounded-md border border-zinc-200 dark:border-zinc-800">
                Día {currentDay} de {totalDays}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={totalDays}
              value={currentDay}
              onChange={(e) => onSeekDay(Number(e.target.value))}
              className="w-full accent-teal-500 cursor-pointer h-2 bg-zinc-200 dark:bg-zinc-800/90 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-700/80 transition"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

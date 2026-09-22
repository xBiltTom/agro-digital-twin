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
  CheckCircle2,
  X,
  Compass,
  Maximize2,
  Minimize2,
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
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  scenarioPathway?: string;
  evidenceBadge?: string;
  dateStr?: string;
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
  isFullscreen = false,
  onToggleFullscreen,
  scenarioPathway = "NOT_DECLARED",
  evidenceBadge,
  dateStr,
}: TwinHUDOverlayProps) {
  const [showScientificModal, setShowScientificModal] = useState(false);

  const getStressBadge = (stress: number) => {
    if (stress < 0.25) {
      return (
        <span className="px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 font-semibold text-xs flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Óptimo ({stress.toFixed(2)})
        </span>
      );
    } else if (stress < 0.55) {
      return (
        <span className="px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-semibold text-xs flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          Moderado ({stress.toFixed(2)})
        </span>
      );
    } else {
      return (
        <span className="px-2.5 py-1 rounded-full bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30 font-semibold text-xs flex items-center gap-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
          Estrés Crítico ({stress.toFixed(2)})
        </span>
      );
    }
  };

  const qPercent = Math.min(100, (streamflowM3s / 30) * 100);
  const thetaPercent = Math.min(100, (soilMoistureVol / 45) * 100);
  const trPercent = Math.min(100, (transpirationMm / 6) * 100);
  const sapPercent = Math.min(100, (sapFlowVelocityCmh / 20) * 100);

  return (
    <div className="absolute inset-0 pointer-events-none p-4 md:p-5 flex flex-col justify-between z-20 select-none transition-colors duration-200">
      {/* Barra superior: selector de escala, capas y pantalla completa */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pointer-events-auto">
        {/* Selector de Escala Macro / Meso / Micro */}
        <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-zinc-950/90 backdrop-blur-xl border border-zinc-800 shadow-2xl">
          <button
            onClick={() => onChangeScale("MACRO")}
            title="Escala Macro: contexto de cuenca y resultados agregados"
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MACRO"
                ? "bg-gradient-to-r from-teal-500/25 to-cyan-500/25 text-teal-300 border border-teal-500/50 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/70"
            }`}
          >
            <Mountain className="w-4 h-4" />
            <span>Macro: Cuenca SWAT+</span>
          </button>

          <button
            onClick={() => onChangeScale("MESO")}
            title="Escala Meso: población de campo agregada y muestra FSPM persistida"
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MESO"
                ? "bg-gradient-to-r from-cyan-500/25 to-sky-500/25 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/70"
            }`}
          >
            <Grid className="w-4 h-4" />
            <span>Meso: Campo agregado</span>
          </button>

          <button
            onClick={() => onChangeScale("MICRO")}
            title="Escala Micro: estado FSPM de la planta de muestra"
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MICRO"
                ? "bg-gradient-to-r from-emerald-500/25 to-teal-500/25 text-emerald-300 border border-emerald-500/50 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/70"
            }`}
          >
            <Sprout className="w-4 h-4" />
            <span>Micro: FSPM Zea mays</span>
          </button>
        </div>

        {/* Barra de herramientas de capas, pantalla completa y marco científico */}
        <div className="flex items-center gap-2">
          {/* Toggles de Capas 3D */}
          <div className="flex items-center gap-1.5 p-1.5 rounded-xl bg-zinc-950/90 backdrop-blur-xl border border-zinc-800 shadow-xl">
            {onToggleHydrologyFlow && (
              <button
                onClick={onToggleHydrologyFlow}
                title={showHydrologyFlow ? "Ocultar Flujo Físico y Savia" : "Mostrar Flujo Físico y Savia"}
                className={`p-2 rounded-lg text-xs transition cursor-pointer flex items-center gap-1 ${
                  showHydrologyFlow
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                }`}
              >
                <Waves className="w-4 h-4" />
              </button>
            )}

            {onToggleSoilHorizons && (
              <button
                onClick={onToggleSoilHorizons}
                title={showSoilHorizons ? "Ocultar perfil de suelo esquemático" : "Mostrar perfil de suelo esquemático"}
                className={`p-2 rounded-lg text-xs transition cursor-pointer flex items-center gap-1 ${
                  showSoilHorizons
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                }`}
              >
                <Layers className="w-4 h-4" />
              </button>
            )}

            {onToggleSensors && (
              <button
                onClick={onToggleSensors}
                title={showSensors ? "Ocultar Instrumentación (Torre / Sondas / USGS)" : "Mostrar Instrumentación"}
                className={`p-2 rounded-lg text-xs transition cursor-pointer flex items-center gap-1 ${
                  showSensors
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                }`}
              >
                <Radio className="w-4 h-4" />
              </button>
            )}

            {onToggleScientificLabels && (
              <button
                onClick={onToggleScientificLabels}
                title={showScientificLabels ? "Ocultar Rótulos Científicos 3D" : "Mostrar Rótulos Científicos 3D"}
                className={`p-2 rounded-lg text-xs transition cursor-pointer flex items-center gap-1 ${
                  showScientificLabels
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/40"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                }`}
              >
                <FileText className="w-4 h-4" />
              </button>
            )}

            {/* Botón de Pantalla Completa */}
            {onToggleFullscreen && (
              <button
                onClick={onToggleFullscreen}
                title={isFullscreen ? "Salir de Pantalla Completa" : "Expandir a Pantalla Completa"}
                className={`p-2 rounded-lg text-xs transition cursor-pointer flex items-center gap-1 ${
                  isFullscreen
                    ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/50"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                }`}
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            )}
          </div>

          {/* Transparencia científica del visor */}
          <button
            onClick={() => setShowScientificModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-mono font-semibold backdrop-blur-xl shadow-md cursor-pointer transition active:scale-95"
          >
            <Compass className="w-4 h-4" />
            <span className="hidden sm:inline">Estado y límites</span>
          </button>
        </div>
      </div>

      {/* Alerta de Lluvia Activa */}
      {precipMm > 10 && (
        <div className="self-center p-2.5 px-5 rounded-full bg-cyan-950/90 border border-cyan-500/50 text-cyan-200 text-xs font-mono flex items-center gap-2.5 shadow-2xl pointer-events-auto backdrop-blur-md">
          <CloudRain className="w-4 h-4 animate-bounce text-cyan-400" />
          <span>Precipitación del forcing: <b>{precipMm.toFixed(1)} mm/día</b></span>
        </div>
      )}

      {/* Modal Científico */}
      {showScientificModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 pointer-events-auto">
          <div className="max-w-2xl w-full bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl p-6 text-zinc-200 font-sans text-xs max-h-[88vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm text-zinc-100 font-sans">
                  Estado científico del visor multiescala
                </h3>
              </div>
              <button
                onClick={() => setShowScientificModal(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* DAG del Proyecto */}
            <div className="bg-zinc-900/80 p-4 rounded-xl border border-zinc-800">
              <div className="text-xs font-bold text-teal-400 mb-1.5 font-mono">
                Flujo representado:
              </div>
              <div className="text-zinc-300 text-xs leading-relaxed font-sans">
                Forcing → población vegetal → agregado de campo → HRU → hidrología. La evidencia y el tipo de motor de cada corrida se consultan en su manifiesto.
              </div>
            </div>

            {/* Alcance de visualización */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <div className="bg-zinc-900/60 p-3.5 rounded-xl border border-zinc-800">
                <div className="font-bold text-amber-400 text-xs mb-1 font-mono">Geometría:</div>
                <div className="text-zinc-400 text-xs">
                  Terreno, parcelas, raíces, torre y marcadores son contexto visual. No sustituyen DEM, polígonos HRU, estaciones ni sensores reales.
                </div>
              </div>
              <div className="bg-emerald-950/40 p-3.5 rounded-xl border border-emerald-500/40">
                <div className="font-bold text-emerald-300 text-xs mb-1 flex items-center gap-1 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Datos del visor:
                </div>
                <div className="text-emerald-200 text-xs">
                  Visualización de estados multiescala: arquitectura 3D de maíz (FSPM), agregados de 1,000 plantas de campo y respuesta hidrológica de cuenca SWAT+.
                </div>
              </div>
            </div>

            {/* Límites explícitos */}
            <div className="bg-zinc-900/60 p-3.5 rounded-xl border border-zinc-800 space-y-1.5">
              <div className="font-bold text-cyan-400 text-xs font-mono">No afirma:</div>
              <ul className="list-disc pl-4 space-y-1 text-zinc-300 text-xs">
                <li>calibración, validación o mejora de predicción sin una comparación observacional explícita;</li>
                <li>telemetría en tiempo real, datos SoilGrids o CHIRPS si no están declarados en la corrida;</li>
                <li>geometrías GIS o arquitectura foliar individual cuando solo existe un agregado/muestra persistida.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Parte inferior: panel de resultados y reproductor temporal */}
      <div className="flex flex-col gap-3 pointer-events-auto">
        {/* Tarjeta de resultados del día con barras de progreso legibles */}
        <div className="p-4 rounded-2xl bg-zinc-950/92 backdrop-blur-2xl border border-zinc-800 shadow-2xl max-w-xl self-start">
          <div className="flex items-center justify-between mb-3 border-b border-zinc-800 pb-2">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-zinc-100 uppercase tracking-wider font-mono">
                {evidenceBadge ? evidenceBadge : `Corrida Multiescala · ${scenarioPathway}`}
              </span>
            </div>
            <div>{getStressBadge(cwsiStress)}</div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            {/* Caudal SWAT+ */}
            <div className="flex flex-col gap-1 p-2.5 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Waves className="w-3.5 h-3.5 text-teal-400" /> Caudal (Q)
                </span>
              </div>
              <span className="text-sm font-bold text-teal-300">
                {streamflowM3s.toFixed(2)} <span className="text-[10px] font-normal text-zinc-400">m³/s</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden mt-0.5">
                <div className="bg-teal-500 h-full rounded-full transition-all duration-300" style={{ width: `${qPercent}%` }} />
              </div>
            </div>

            {/* Humedad del Suelo */}
            <div className="flex flex-col gap-1 p-2.5 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Droplets className="w-3.5 h-3.5 text-cyan-400" /> Humedad (θ)
                </span>
              </div>
              <span className="text-sm font-bold text-cyan-300">
                {soilMoistureVol.toFixed(1)} <span className="text-[10px] font-normal text-zinc-400">%</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden mt-0.5">
                <div className="bg-cyan-500 h-full rounded-full transition-all duration-300" style={{ width: `${thetaPercent}%` }} />
              </div>
            </div>

            {/* Transpiración FSPM */}
            <div className="flex flex-col gap-1 p-2.5 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Gauge className="w-3.5 h-3.5 text-emerald-400" /> Transp. (Tr)
                </span>
              </div>
              <span className="text-sm font-bold text-emerald-300">
                {transpirationMm.toFixed(2)} <span className="text-[10px] font-normal text-zinc-400">mm/d</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden mt-0.5">
                <div className="bg-emerald-500 h-full rounded-full transition-all duration-300" style={{ width: `${trPercent}%` }} />
              </div>
            </div>

            {/* Flujo de Savia Xilema */}
            <div className="flex flex-col gap-1 p-2.5 rounded-xl bg-zinc-900/70 border border-zinc-800">
              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Thermometer className="w-3.5 h-3.5 text-sky-400" /> Savia Xilema
                </span>
              </div>
              <span className="text-sm font-bold text-sky-300">
                {sapFlowVelocityCmh.toFixed(1)} <span className="text-[10px] font-normal text-zinc-400">cm/h</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden mt-0.5">
                <div className="bg-sky-500 h-full rounded-full transition-all duration-300" style={{ width: `${sapPercent}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Barra de Control y Reproductor Temporal */}
        <div className="p-4 rounded-2xl bg-zinc-950/92 backdrop-blur-2xl border border-zinc-800 shadow-2xl flex items-center gap-4">
          <button
            onClick={onTogglePlay}
            title={isPlaying ? "Pausar avance temporal" : "Iniciar reproducción temporal continua"}
            className="w-11 h-11 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 hover:from-emerald-500 hover:to-teal-300 text-zinc-950 flex items-center justify-center transition-all duration-300 cursor-pointer shadow-lg shadow-emerald-500/25 shrink-0 hover:scale-105 active:scale-95"
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
          </button>

          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                Ciclo hidrológico y fenológico anual
              </span>
              <span className="text-zinc-100 font-bold bg-zinc-900 px-3 py-1 rounded-md border border-zinc-800">
                Día {currentDay} de {totalDays}{dateStr ? ` (${dateStr})` : ""}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={totalDays}
              value={currentDay}
              onChange={(e) => onSeekDay(Number(e.target.value))}
              className="w-full accent-teal-400 cursor-pointer h-2.5 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

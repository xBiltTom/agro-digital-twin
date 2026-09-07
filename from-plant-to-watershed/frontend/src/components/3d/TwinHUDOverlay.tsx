"use client";

import React from "react";
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
  Waves
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
}: TwinHUDOverlayProps) {
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
      {/* Barra superior: selector de escala */}
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
            <span>Macro: Cuenca ilustrativa</span>
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
            <span>Meso: Parcela procedural</span>
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
            <span>Micro: Planta ilustrativa</span>
          </button>
        </div>

      </div>

      {/* Alerta de Lluvia Activa */}
      {precipMm > 15 && (
        <div className="self-center p-2 px-4 rounded-full bg-cyan-50 dark:bg-cyan-950/80 border border-cyan-300 dark:border-cyan-500/40 text-cyan-800 dark:text-cyan-300 text-xs font-mono flex items-center gap-2 shadow-lg pointer-events-auto">
          <CloudRain className="w-4 h-4 animate-bounce" />
          <span>Precipitación Intensa Activa: {precipMm.toFixed(1)} mm/día</span>
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
                Playback de resultados simplificados
              </span>
            </div>
            <div>{getStressBadge(cwsiStress)}</div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            {/* Caudal del modelo hidrológico simplificado */}
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

            {/* Humedad del Suelo */}
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

            {/* Transpiración Real */}
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

            {/* Flujo de Savia */}
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

          <div className="mt-2.5 pt-2 border-t border-zinc-200/80 dark:border-zinc-800/80 text-[10px] text-zinc-500">
            Geometría procedural ilustrativa; no es arquitectura vegetal medida ni recomendación agronómica.
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
                Reproductor de resultados persistidos
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

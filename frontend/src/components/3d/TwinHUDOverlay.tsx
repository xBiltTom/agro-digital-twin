"use client";

import React from "react";
import { ScaleMode } from "./MultiScaleViewer3D";
import {
  Mountain,
  Grid,
  Sprout,
  Play,
  Pause,
  RotateCcw,
  Sun,
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
  onInjectRain: () => void;
  onInjectHeatwave: () => void;
  onResetWeather: () => void;
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
  onInjectRain,
  onInjectHeatwave,
  onResetWeather,
}: TwinHUDOverlayProps) {
  const getStressBadge = (stress: number) => {
    if (stress < 0.25) {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm shadow-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Óptimo ({stress.toFixed(2)})
        </span>
      );
    } else if (stress < 0.55) {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm shadow-amber-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          Moderado ({stress.toFixed(2)})
        </span>
      );
    } else {
      return (
        <span className="px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 font-semibold text-[10px] flex items-center gap-1 shadow-sm shadow-rose-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
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
    <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between z-20 select-none">
      {/* Barra Superior: Selector de Escalas y Forzamiento de Choque */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pointer-events-auto">
        {/* Selector de Escala Macro / Meso / Micro */}
        <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-zinc-950/90 backdrop-blur-xl border border-zinc-800/80 shadow-2xl">
          <button
            onClick={() => onChangeScale("MACRO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MACRO"
                ? "bg-gradient-to-r from-teal-500/25 to-cyan-500/25 text-teal-300 border border-teal-500/50 shadow-lg shadow-teal-500/10"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Mountain className="w-3.5 h-3.5" />
            <span>Macro: Cuenca SWAT</span>
          </button>

          <button
            onClick={() => onChangeScale("MESO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MESO"
                ? "bg-gradient-to-r from-cyan-500/25 to-sky-500/25 text-cyan-300 border border-cyan-500/50 shadow-lg shadow-cyan-500/10"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Meso: Parcela HRU</span>
          </button>

          <button
            onClick={() => onChangeScale("MICRO")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-300 cursor-pointer ${
              scaleMode === "MICRO"
                ? "bg-gradient-to-r from-emerald-500/25 to-teal-500/25 text-emerald-300 border border-emerald-500/50 shadow-lg shadow-emerald-500/10"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Sprout className="w-3.5 h-3.5" />
            <span>Micro: Planta 3D</span>
          </button>
        </div>

        {/* Moduladores de Forzamiento Meteorológico */}
        <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-zinc-950/90 backdrop-blur-xl border border-zinc-800/80 text-xs shadow-2xl">
          <span className="text-[10px] font-mono text-zinc-400 uppercase hidden md:inline px-1">
            Choque Climático:
          </span>
          <button
            onClick={onInjectRain}
            title="Generar tormenta súbita (+40mm)"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-950/70 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800/60 transition-all cursor-pointer text-[11px] shadow-sm hover:shadow-cyan-500/20"
          >
            <CloudRain className="w-3.5 h-3.5" />
            <span>Lluvia +40mm</span>
          </button>
          <button
            onClick={onInjectHeatwave}
            title="Generar ola de calor (+4°C)"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-950/70 hover:bg-amber-900/80 text-amber-300 border border-amber-800/60 transition-all cursor-pointer text-[11px] shadow-sm hover:shadow-amber-500/20"
          >
            <Sun className="w-3.5 h-3.5" />
            <span>Calor +4°C</span>
          </button>
          <button
            onClick={onResetWeather}
            title="Restablecer condiciones base"
            className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60 rounded-lg transition-all cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Alerta de Lluvia Activa */}
      {precipMm > 15 && (
        <div className="self-center p-2 px-4 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-mono flex items-center gap-2 shadow-xl shadow-cyan-950/50 pointer-events-auto">
          <CloudRain className="w-4 h-4 animate-bounce" />
          <span>Precipitación Intensa Activa: {precipMm.toFixed(1)} mm/día</span>
        </div>
      )}

      {/* Parte Inferior: Panel de Telemetría Flotante y Barra de Tiempo */}
      <div className="flex flex-col gap-3 pointer-events-auto">
        {/* Tarjeta de Telemetría Multiescala con Barras de Nivel */}
        <div className="p-4 rounded-2xl bg-zinc-950/90 backdrop-blur-2xl border border-zinc-800/90 shadow-2xl max-w-xl self-start">
          <div className="flex items-center justify-between mb-3 border-b border-zinc-800/80 pb-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-zinc-100 uppercase tracking-wider">
                Telemetría Biofísica del Gemelo
              </span>
            </div>
            <div>{getStressBadge(cwsiStress)}</div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            {/* Caudal SWAT */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-900/60 border border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Waves className="w-3 h-3 text-teal-400" /> Caudal (Q)
                </span>
              </div>
              <span className="text-sm font-bold text-teal-300">
                {streamflowM3s.toFixed(2)} <span className="text-[10px] font-normal text-zinc-400">m³/s</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-teal-400 h-full rounded-full transition-all duration-300"
                  style={{ width: `${qPercent}%` }}
                />
              </div>
            </div>

            {/* Humedad del Suelo */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-900/60 border border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Droplets className="w-3 h-3 text-cyan-400" /> Humedad (θ)
                </span>
              </div>
              <span className="text-sm font-bold text-cyan-300">
                {soilMoistureVol.toFixed(1)} <span className="text-[10px] font-normal text-zinc-400">%</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-cyan-400 h-full rounded-full transition-all duration-300"
                  style={{ width: `${thetaPercent}%` }}
                />
              </div>
            </div>

            {/* Transpiración Real */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-900/60 border border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Gauge className="w-3 h-3 text-emerald-400" /> Transp. (Tr)
                </span>
              </div>
              <span className="text-sm font-bold text-emerald-300">
                {transpirationMm.toFixed(2)} <span className="text-[10px] font-normal text-zinc-400">mm/d</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-emerald-400 h-full rounded-full transition-all duration-300"
                  style={{ width: `${trPercent}%` }}
                />
              </div>
            </div>

            {/* Flujo de Savia */}
            <div className="flex flex-col gap-1 p-2 rounded-xl bg-zinc-900/60 border border-zinc-800/50">
              <div className="flex items-center justify-between text-[10px] text-zinc-400">
                <span className="flex items-center gap-1">
                  <Thermometer className="w-3 h-3 text-sky-400" /> Savia Xilema
                </span>
              </div>
              <span className="text-sm font-bold text-sky-300">
                {sapFlowVelocityCmh.toFixed(1)} <span className="text-[10px] font-normal text-zinc-400">cm/h</span>
              </span>
              <div className="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  className="bg-sky-400 h-full rounded-full transition-all duration-300"
                  style={{ width: `${sapPercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Barra de Control y Reproductor Temporal */}
        <div className="p-3.5 rounded-2xl bg-zinc-950/90 backdrop-blur-2xl border border-zinc-800/90 shadow-2xl flex items-center gap-4">
          <button
            onClick={onTogglePlay}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 hover:from-emerald-500 hover:to-teal-300 text-zinc-950 flex items-center justify-center transition-all duration-300 cursor-pointer shadow-lg shadow-emerald-500/25 shrink-0 hover:scale-105 active:scale-95"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>

          <div className="flex-1 flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                Línea Temporal de Simulación Continua
              </span>
              <span className="text-zinc-200 font-bold bg-zinc-900 px-2 py-0.5 rounded-md border border-zinc-800">
                Día {currentDay} de {totalDays}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={totalDays}
              value={currentDay}
              onChange={(e) => onSeekDay(Number(e.target.value))}
              className="w-full accent-teal-400 cursor-pointer h-2 bg-zinc-800/90 rounded-lg hover:bg-zinc-700/80 transition"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

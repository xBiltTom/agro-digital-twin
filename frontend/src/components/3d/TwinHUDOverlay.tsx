"use client";

import React from "react";
import { ScaleMode } from "./MultiScaleViewer3D";
import {
  Mountain,
  Grid,
  Sprout,
  Droplets,
  Zap,
  Play,
  Pause,
  RotateCcw,
  Sun,
  CloudRain,
  Activity,
  Layers
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
      return <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">Óptimo ({stress})</span>;
    } else if (stress < 0.5) {
      return <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">Moderado ({stress})</span>;
    } else {
      return <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">Crítico ({stress})</span>;
    }
  };

  return (
    <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between z-20">
      {/* Top Bar: Scale Switcher & Active Telemetry */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pointer-events-auto">
        {/* Scale Switcher Tabs */}
        <div className="flex items-center gap-1.5 p-1.5 rounded-xl bg-zinc-950/85 backdrop-blur-md border border-zinc-800 shadow-xl">
          <button
            onClick={() => onChangeScale("MACRO")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              scaleMode === "MACRO"
                ? "bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Mountain className="w-3.5 h-3.5" />
            <span>Macro: Cuenca SWAT</span>
          </button>

          <button
            onClick={() => onChangeScale("MESO")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              scaleMode === "MESO"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Meso: Parcela HRU</span>
          </button>

          <button
            onClick={() => onChangeScale("MICRO")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              scaleMode === "MICRO"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Sprout className="w-3.5 h-3.5" />
            <span>Micro: Planta 3D</span>
          </button>
        </div>

        {/* Shock Injector Controls */}
        <div className="flex items-center gap-2 p-1.5 rounded-xl bg-zinc-950/85 backdrop-blur-md border border-zinc-800 text-xs shadow-xl">
          <span className="text-[11px] font-mono text-zinc-400 hidden md:inline px-1">Forzamiento:</span>
          <button
            onClick={onInjectRain}
            title="Generar tormenta súbita (+40mm)"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-800/50 transition cursor-pointer text-[11px]"
          >
            <CloudRain className="w-3.5 h-3.5" />
            <span>Lluvia +40mm</span>
          </button>
          <button
            onClick={onInjectHeatwave}
            title="Generar ola de calor (+4°C)"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-950/60 hover:bg-amber-900/60 text-amber-300 border border-amber-800/50 transition cursor-pointer text-[11px]"
          >
            <Sun className="w-3.5 h-3.5" />
            <span>Calor +4°C</span>
          </button>
          <button
            onClick={onResetWeather}
            title="Restablecer"
            className="p-1 text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Middle/Bottom Floating Telemetry HUD Card */}
      <div className="flex flex-col gap-3 pointer-events-auto">
        <div className="p-4 rounded-xl bg-zinc-950/85 backdrop-blur-md border border-zinc-800 shadow-2xl max-w-xl self-start">
          <div className="flex items-center justify-between mb-3 border-b border-zinc-800/80 pb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-zinc-100 uppercase tracking-wide">
                Telemetría en Vivo del Gemelo Digital
              </span>
            </div>
            <div className="text-[11px] font-mono">{getStressBadge(cwsiStress)}</div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-zinc-400 block">Caudal SWAT (Q)</span>
              <span className="text-sm font-bold text-teal-300">{streamflowM3s.toFixed(2)} m³/s</span>
            </div>
            <div>
              <span className="text-[10px] text-zinc-400 block">Humedad Suelo (θ)</span>
              <span className="text-sm font-bold text-cyan-300">{soilMoistureVol.toFixed(1)} %</span>
            </div>
            <div>
              <span className="text-[10px] text-zinc-400 block">Transpiración (Tr)</span>
              <span className="text-sm font-bold text-emerald-300">{transpirationMm.toFixed(2)} mm/d</span>
            </div>
            <div>
              <span className="text-[10px] text-zinc-400 block">Flujo Savia Xilema</span>
              <span className="text-sm font-bold text-sky-300">{sapFlowVelocityCmh.toFixed(1)} cm/h</span>
            </div>
          </div>
        </div>

        {/* Timeline Player Bar */}
        <div className="p-3 rounded-xl bg-zinc-950/90 backdrop-blur-md border border-zinc-800 shadow-2xl flex items-center gap-4">
          <button
            onClick={onTogglePlay}
            className="w-9 h-9 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 flex items-center justify-center transition cursor-pointer shadow-lg shadow-emerald-500/20 shrink-0"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>

          <div className="flex-1 flex flex-col gap-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
              <span>Línea Temporal de Simulación</span>
              <span className="text-zinc-200 font-semibold">
                Día {currentDay} de {totalDays}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={totalDays}
              value={currentDay}
              onChange={(e) => onSeekDay(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-zinc-800 rounded-lg"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import type { PlaybackRecord, VariableState } from "../../types/playback";
import { periodLabel, variableText } from "../../lib/playback-scene";
import type { ScaleMode } from "./MultiScaleViewer3D";
import { Mountain, Grid, Sprout, Play, Pause, ChevronLeft, ChevronRight, Maximize2, Minimize2, Layers, Radio, Waves, Info } from "lucide-react";

function Metric({ title, value }: { title: string; value?: VariableState }) {
  return <div className="min-w-0">
    <div className="text-zinc-400 text-[10px]">{title}</div>
    <div className="font-mono text-xs text-zinc-100" title={value ? `${value.evidence} · ${value.source}${value.limitation ? ` · ${value.limitation}` : ""}` : "Sin dato"}>
      {variableText(value)}
    </div>
    <div className="text-[9px] text-cyan-300/80">{value?.evidence ?? "NOT_AVAILABLE"}</div>
  </div>;
}

interface Props {
  record: PlaybackRecord;
  simulationName: string;
  scaleMode: ScaleMode;
  onChangeScale: (scale: ScaleMode) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  index: number;
  total: number;
  onSeek: (index: number) => void;
  showHydrologyFlow: boolean;
  onToggleHydrologyFlow: () => void;
  showSoilHorizons: boolean;
  onToggleSoilHorizons: () => void;
  showSensors: boolean;
  onToggleSensors: () => void;
  showScientificLabels: boolean;
  onToggleScientificLabels: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
}

export default function TwinHUDOverlay({ record, simulationName, scaleMode, onChangeScale, isPlaying,
  onTogglePlay, index, total, onSeek, showHydrologyFlow, onToggleHydrologyFlow, showSoilHorizons,
  onToggleSoilHorizons, showSensors, onToggleSensors, showScientificLabels, onToggleScientificLabels,
  isFullscreen, onToggleFullscreen }: Props) {
  const scaleButtons: [ScaleMode, string, typeof Mountain][] = [
    ["MACRO", "Cuenca", Mountain], ["MESO", "Campo", Grid], ["MICRO", "Planta", Sprout],
  ];
  const period = periodLabel(record);
  return <div className="absolute inset-0 z-20 flex flex-col justify-between p-3 md:p-5 pointer-events-none text-zinc-100">
    <div className="flex flex-wrap justify-between gap-2 pointer-events-auto">
      <div className="flex rounded-xl border border-zinc-700 bg-zinc-950/90 p-1 shadow-xl">
        {scaleButtons.map(([mode, label, Icon]) =>
          <button key={mode} onClick={() => onChangeScale(mode)}
            className={`flex items-center gap-1 rounded-lg px-3 py-2 text-xs ${scaleMode === mode ? "bg-cyan-600/40 text-cyan-200" : "text-zinc-400 hover:text-white"}`}>
            <Icon className="h-4 w-4" />{label}
          </button>)}
      </div>
      <div className="flex gap-1 rounded-xl border border-zinc-700 bg-zinc-950/90 p-1 shadow-xl">
        {[
          [showHydrologyFlow, onToggleHydrologyFlow, Waves, "Efectos de lluvia"],
          [showSoilHorizons, onToggleSoilHorizons, Layers, "Suelo contextual"],
          [showSensors, onToggleSensors, Radio, "Instrumentación contextual"],
          [showScientificLabels, onToggleScientificLabels, Info, "Etiquetas"],
        ].map(([enabled, action, Icon, label]) => {
          const IconComponent = Icon as typeof Waves;
          return <button key={label as string} onClick={action as () => void} title={label as string}
            className={`rounded-lg p-2 ${enabled ? "text-cyan-300 bg-cyan-500/20" : "text-zinc-500"}`}>
            <IconComponent className="h-4 w-4" />
          </button>;
        })}
        <button onClick={onToggleFullscreen} title="Pantalla completa" className="rounded-lg p-2 text-zinc-300">
          {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      </div>
    </div>

    <div className="flex flex-col gap-2 pointer-events-auto">
      <div className="max-w-3xl rounded-xl border border-zinc-700 bg-zinc-950/90 p-3 shadow-xl">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
          <strong className="text-cyan-200">{period} · {record.resolution}</strong>
          <span>{simulationName}</span>
          <span className="text-zinc-400">{record.run_type}</span>
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-6">
          <Metric title="Precipitación" value={record.weather.precipitation_mm} />
          <Metric title="Temperatura" value={record.weather.temperature_c} />
          <Metric title="Caudal de salida" value={record.hydrology.streamflow_m3s} />
          <Metric title="Escorrentía" value={record.hydrology.runoff_mm} />
          <Metric title="ET hidrológica" value={record.hydrology.evapotranspiration_mm} />
          <Metric title="Percolación" value={record.hydrology.percolation_mm} />
          <Metric title="Agua en suelo SWAT+" value={record.hydrology.soil_water_mm} />
          <Metric title="LAI campo" value={record.field.lai} />
          <Metric title="Altura vegetal" value={record.field.height_m} />
          <Metric title="Raíz" value={record.field.root_depth_m} />
          <Metric title="Biomasa" value={record.field.biomass_g_plant} />
          <Metric title="Estrés FSPM" value={record.field.water_stress} />
          <Metric title="Transpiración FSPM" value={record.field.actual_transpiration_mm_day} />
          <Metric title="Transpiración potencial" value={record.field.potential_transpiration_mm_day} />
          <Metric title="Humedad volumétrica FSPM" value={record.field.soil_moisture_vol_percent} />
        </div>
        <div className="mt-2 text-[10px] text-zinc-400">
          {record.crop?.active ? `${record.crop.crop ?? "Cultivo"} · ${record.crop.phenological_stage ?? "etapa no disponible"}` : "Sin cultivo FSPM activo"}
          {record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" && " · Ventana PHU aproximada"}
          {record.resolution !== "DAILY" && " · Acumulados y medias del periodo; sin estado diario inferido"}
          {record.weather.precipitation_mm?.availability !== "AVAILABLE" && " · Precipitación desconocida: ausencia de partículas no significa día seco"}
        </div>
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-950/90 px-3 py-2 shadow-xl">
        <button aria-label="Retroceder" onClick={() => onSeek(index - 1)} disabled={index <= 0}><ChevronLeft className="h-5 w-5" /></button>
        <button aria-label={isPlaying ? "Pausar" : "Reproducir"} onClick={onTogglePlay}>{isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}</button>
        <button aria-label="Avanzar" onClick={() => onSeek(index + 1)} disabled={index >= total - 1}><ChevronRight className="h-5 w-5" /></button>
        <input aria-label="Posición temporal" className="w-full accent-cyan-400" type="range" min={0} max={Math.max(0, total - 1)}
          value={index} onChange={(event) => onSeek(Number(event.target.value))} />
        <span className="shrink-0 font-mono text-[10px]">{index + 1}/{total}</span>
      </div>
    </div>
  </div>;
}

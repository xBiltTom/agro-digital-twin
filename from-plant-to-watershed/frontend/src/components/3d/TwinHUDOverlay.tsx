"use client";

import { useState } from "react";
import type { PlaybackRecord, VariableState } from "../../types/playback";
import { periodLabel, variableText } from "../../lib/playback-scene";
import { adaptPlaybackVisual } from "../../lib/playback-visual-adapter";
import type { VisualMode } from "../../types/playback-availability";
import type { ScaleMode } from "./MultiScaleViewer3D";
import {
  Mountain,
  Grid,
  Sprout,
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Layers,
  Radio,
  Waves,
  Info,
  SlidersHorizontal,
  Table,
} from "lucide-react";

function Metric({ title, value, customNote }: { title: string; value?: VariableState; customNote?: string }) {
  const evidence = value?.evidence ?? "NOT_AVAILABLE";
  const evidenceBadgeClass =
    evidence === "MODELLED_SWAT_PLUS"
      ? "text-teal-300"
      : evidence === "SIMPLIFIED_FSPM"
      ? "text-emerald-300"
      : evidence === "DERIVED"
      ? "text-amber-300"
      : evidence === "OBSERVED"
      ? "text-sky-300"
      : evidence === "ASSUMED"
      ? "text-purple-300"
      : "text-zinc-500";

  return (
    <div className="min-w-0">
      <div className="text-zinc-400 text-[10px] truncate" title={title}>{title}</div>
      <div
        className="font-mono text-xs font-semibold text-zinc-100"
        title={value ? `${value.evidence} · ${value.source}${value.limitation ? ` · ${value.limitation}` : ""}` : "Sin dato"}
      >
        {variableText(value)}
      </div>
      <div className={`text-[9px] font-mono ${evidenceBadgeClass}`}>
        {evidence === "MODELLED_SWAT_PLUS"
          ? "SWAT+"
          : evidence === "SIMPLIFIED_FSPM"
          ? "FSPM"
          : evidence === "DERIVED"
          ? "Derivado"
          : evidence === "OBSERVED"
          ? "Observado"
          : evidence === "ASSUMED"
          ? "Supuesto"
          : "N/D"}
        {customNote && <span className="text-zinc-500 ml-1">({customNote})</span>}
      </div>
    </div>
  );
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
  onOpenExplorer?: () => void;
  selectedPlantId?: string | null;
  onSelectPlant?: (plantId: string) => void;
  visualMode?: VisualMode;
}

export default function TwinHUDOverlay({
  record,
  simulationName,
  scaleMode,
  onChangeScale,
  isPlaying,
  onTogglePlay,
  index,
  total,
  onSeek,
  showHydrologyFlow,
  onToggleHydrologyFlow,
  showSoilHorizons,
  onToggleSoilHorizons,
  showSensors,
  onToggleSensors,
  showScientificLabels,
  onToggleScientificLabels,
  isFullscreen,
  onToggleFullscreen,
  onOpenExplorer,
  selectedPlantId,
  onSelectPlant,
  visualMode,
}: Props) {
  const [showAllVariables, setShowAllVariables] = useState(false);

  const scaleButtons: [ScaleMode, string, typeof Mountain][] = [
    ["MACRO", "Cuenca", Mountain],
    ["MESO", "Campo", Grid],
    ["MICRO", "Planta", Sprout],
  ];

  const period = periodLabel(record);

  // Muestra seleccionada para la escala Micro: si fue cosechada, es null
  const plantSample = selectedPlantId
    ? (record.plant_samples.find((s) => s.plant_id === selectedPlantId) ?? null)
    : (record.plant_samples[0] ?? null);

  const isSelectedPlantHarvested = Boolean(
    selectedPlantId && !plantSample && record.plant_samples.length > 0
  );

  // Modo visual unificado con playback-visual-adapter
  const mode: VisualMode = visualMode ?? adaptPlaybackVisual(record, {
    simulationId: record.simulation_id,
    selectedPlantId,
  }).mode;

  const modeBadge =
    mode === "SCIENTIFIC_ACTIVE" ? (
      <span className="rounded bg-emerald-500/20 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
        SCIENTIFIC_ACTIVE · {record.crop?.crop ?? "Cultivo activo"}
      </span>
    ) : mode === "SCIENTIFIC_FALLOW" ? (
      <span className="rounded bg-amber-500/20 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono text-amber-300">
        SCIENTIFIC_FALLOW · Barbecho
      </span>
    ) : mode === "HYDROLOGY_ONLY" ? (
      <span className="rounded bg-teal-500/20 border border-teal-500/30 px-2 py-0.5 text-[10px] font-mono text-teal-300">
        HYDROLOGY_ONLY · Hidrología SWAT+
      </span>
    ) : mode === "HISTORICAL_REFERENCE" ? (
      <span className="rounded bg-purple-500/20 border border-purple-500/30 px-2 py-0.5 text-[10px] font-mono text-purple-300">
        HISTORICAL_REFERENCE · Referencia histórica
      </span>
    ) : (
      <span className="rounded bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 text-[10px] font-mono text-rose-300">
        DATA_UNAVAILABLE · Sin datos científicos
      </span>
    );

  return (
    <div className="absolute inset-0 z-20 flex flex-col justify-between p-3 md:p-5 pointer-events-none text-zinc-100">
      {/* Barra superior de controles */}
      <div className="flex flex-wrap justify-between gap-2 pointer-events-auto">
        <div className="flex rounded-xl border border-zinc-700 bg-zinc-950/90 p-1 shadow-xl">
          {scaleButtons.map(([modeKey, label, Icon]) => (
            <button
              key={modeKey}
              onClick={() => onChangeScale(modeKey)}
              className={`flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                scaleMode === modeKey
                  ? "bg-cyan-600/40 text-cyan-200 border border-cyan-500/30"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-950/90 p-1 shadow-xl">
          {onOpenExplorer && (
            <button
              onClick={onOpenExplorer}
              title="Abrir Explorador de HRUs y Canales SWAT+"
              className="flex items-center gap-1 rounded-lg bg-teal-600/30 hover:bg-teal-600/50 border border-teal-500/30 px-2.5 py-1.5 text-xs text-teal-200 transition"
            >
              <Table className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">HRUs & Canales</span>
            </button>
          )}

          {[
            [showHydrologyFlow, onToggleHydrologyFlow, Waves, "Efectos de lluvia"],
            [showSoilHorizons, onToggleSoilHorizons, Layers, "Suelo contextual"],
            [showSensors, onToggleSensors, Radio, "Instrumentación contextual"],
            [showScientificLabels, onToggleScientificLabels, Info, "Etiquetas científicas"],
          ].map(([enabled, action, Icon, label]) => {
            const IconComponent = Icon as typeof Waves;
            return (
              <button
                key={label as string}
                onClick={action as () => void}
                title={label as string}
                className={`rounded-lg p-2 transition ${
                  enabled ? "text-cyan-300 bg-cyan-500/20" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <IconComponent className="h-4 w-4" />
              </button>
            );
          })}

          <button
            onClick={onToggleFullscreen}
            title="Pantalla completa"
            className="rounded-lg p-2 text-zinc-300 hover:text-white transition"
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Barra inferior de datos y timeline */}
      <div className="flex flex-col gap-2 pointer-events-auto">
        <div className="max-h-52 max-w-4xl overflow-y-auto rounded-xl border border-zinc-700 bg-zinc-950/92 p-3.5 shadow-2xl backdrop-blur-md">
          {/* Cabecera del HUD */}
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs border-b border-zinc-800 pb-2">
            <div className="flex flex-wrap items-center gap-2">
              <strong className="text-cyan-200 text-sm font-mono">{period}</strong>
              <span className="text-zinc-400 font-mono text-[11px]">{record.resolution}</span>
              <span className="text-zinc-300 truncate max-w-[200px]">{simulationName}</span>
              {modeBadge}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowAllVariables((prev) => !prev)}
                className="flex items-center gap-1 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition"
              >
                <SlidersHorizontal className="h-3 w-3" />
                {showAllVariables ? "Ver por escala" : "Ver todas las variables"}
              </button>
            </div>
          </div>

          {/* Métricas específicas según la escala activa */}
          {!showAllVariables ? (
            <div className="mt-2.5">
              {scaleMode === "MACRO" && (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-7">
                  <Metric title="Precipitación" value={record.weather.precipitation_mm} />
                  <Metric title="Temperatura" value={record.weather.temperature_c} />
                  <Metric title="Caudal outlet Q" value={record.hydrology.streamflow_m3s} />
                  <Metric title="Escorrentía" value={record.hydrology.runoff_mm} />
                  <Metric title="ET hidrológica" value={record.hydrology.evapotranspiration_mm} />
                  <Metric title="Agua suelo SWAT+" value={record.hydrology.soil_water_mm} />
                  <Metric title="Percolación" value={record.hydrology.percolation_mm} />
                </div>
              )}

              {scaleMode === "MESO" && (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-7">
                  <Metric title="LAI medio campo" value={record.field.lai} />
                  <Metric title="Altura vegetal" value={record.field.height_m} />
                  <Metric title="Biomasa media" value={record.field.biomass_g_plant} />
                  <Metric title="Cobertura dosel" value={record.field.canopy_cover_fraction} />
                  <Metric title="Estrés FSPM" value={record.field.water_stress} />
                  <Metric title="Transpiración FSPM" value={record.field.actual_transpiration_mm_day} />
                  <Metric
                    title="Humedad volumétrica"
                    value={record.field.soil_moisture_vol_percent}
                  />
                </div>
              )}

              {scaleMode === "MICRO" && (
                <div>
                  {isSelectedPlantHarvested && (
                    <div className="mb-2 flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-950/40 px-3 py-1.5 text-xs text-amber-200 font-mono">
                      <span>Muestra <b>{selectedPlantId}</b> ya no está activa en esta fecha (calendario cosechado).</span>
                      {onSelectPlant && record.plant_samples[0] && (
                        <button
                          type="button"
                          onClick={() => onSelectPlant(record.plant_samples[0].plant_id)}
                          className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] text-amber-300 hover:bg-amber-500/30 border border-amber-500/40"
                        >
                          Seleccionar muestra activa ({record.plant_samples.length} disp.) →
                        </button>
                      )}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-7">
                    <Metric
                      title="Altura muestra"
                      value={plantSample?.variables.height_m}
                    />
                    <Metric
                      title="LAI muestra"
                      value={plantSample?.variables.lai}
                    />
                    <Metric
                      title="Hojas simuladas"
                      value={plantSample?.variables.leaf_count}
                    />
                    <Metric
                      title="Área foliar"
                      value={plantSample?.variables.leaf_area_m2}
                    />
                    <Metric
                      title="Profundidad raíz"
                      value={plantSample?.variables.root_depth_m}
                    />
                    <Metric
                      title="Estrés CWSI"
                      value={plantSample?.variables.water_stress}
                    />
                    <Metric
                      title="Transpiración"
                      value={plantSample?.variables.actual_transpiration_mm_day}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Vista completa de todas las 15 variables */
            <div className="mt-2.5 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-8">
              <Metric title="Precipitación" value={record.weather.precipitation_mm} />
              <Metric title="Temperatura" value={record.weather.temperature_c} />
              <Metric title="Caudal outlet" value={record.hydrology.streamflow_m3s} />
              <Metric title="Escorrentía" value={record.hydrology.runoff_mm} />
              <Metric title="ET hidrológica" value={record.hydrology.evapotranspiration_mm} />
              <Metric title="Percolación" value={record.hydrology.percolation_mm} />
              <Metric title="Agua suelo SWAT+" value={record.hydrology.soil_water_mm} />
              <Metric title="LAI campo" value={record.field.lai} />
              <Metric title="Altura vegetal" value={record.field.height_m} />
              <Metric title="Raíz campo" value={record.field.root_depth_m} />
              <Metric title="Biomasa campo" value={record.field.biomass_g_plant} />
              <Metric title="Estrés FSPM" value={record.field.water_stress} />
              <Metric title="Transpiración FSPM" value={record.field.actual_transpiration_mm_day} />
              <Metric title="Transpiración pot." value={record.field.potential_transpiration_mm_day} />
              <Metric
                title="Humedad vol. FSPM"
                value={record.field.soil_moisture_vol_percent}
              />
            </div>
          )}

          {/* Pie informativo de limitaciones y fenología */}
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-zinc-800/80 pt-1.5 text-[10px] text-zinc-400">
            <div>
              {record.crop?.active ? (
                <span>
                  Fenología: <b className="text-emerald-300">{record.crop.phenological_stage ?? "Etapa no declarada"}</b>
                  {record.crop.season_id && ` · ${record.crop.season_id}`}
                </span>
              ) : mode === "HYDROLOGY_ONLY" ? (
                <span className="text-teal-300">Simulación hidrológica SWAT+ sin modelo de cultivo FSPM acoplado.</span>
              ) : mode === "DATA_UNAVAILABLE" ? (
                <span className="text-rose-400">Datos científicos no disponibles para este registro.</span>
              ) : (
                <span className="text-amber-300/90">Suelo en descanso / barbecho agrícola fuera de la temporada de cultivo.</span>
              )}
              {record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" && (
                <span> · Ventana agrícola aproximada</span>
              )}
            </div>
            <div className="text-zinc-500 font-mono">
              {record.hru_results.length} HRUs · {record.channel_results.length} Canales · {record.plant_samples.length} Muestras activas
            </div>
          </div>
        </div>

        {/* Timeline Slider y Controles de Reproducción */}
        <div className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-950/90 px-3 py-2 shadow-xl">
          <button
            aria-label="Retroceder"
            onClick={() => onSeek(index - 1)}
            disabled={index <= 0}
            className="rounded p-1 hover:bg-zinc-800 disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            aria-label={isPlaying ? "Pausar" : "Reproducir"}
            onClick={onTogglePlay}
            className="rounded p-1 hover:bg-zinc-800 text-cyan-300"
          >
            {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
          </button>
          <button
            aria-label="Avanzar"
            onClick={() => onSeek(index + 1)}
            disabled={index >= total - 1}
            className="rounded p-1 hover:bg-zinc-800 disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
          <input
            aria-label="Posición temporal"
            className="w-full accent-cyan-400 cursor-pointer"
            type="range"
            min={0}
            max={Math.max(0, total - 1)}
            value={index}
            onChange={(event) => onSeek(Number(event.target.value))}
          />
          <span className="shrink-0 font-mono text-[11px] text-zinc-300">
            Día {index + 1}/{total}
          </span>
        </div>
      </div>
    </div>
  );
}

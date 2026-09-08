"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { SimulationRun, SimulationResult } from "../../../types/simulation";
import MultiScaleViewer3D, { ScaleMode } from "../../../components/3d/MultiScaleViewer3D";
import TwinHUDOverlay from "../../../components/3d/TwinHUDOverlay";
import {
  Box,
  Loader2,
  Sparkles,
  Mountain,
  Grid,
  Sprout,
  Waves,
  Layers,
  Radio,
  FileText,
  Compass,
  Play,
  Pause,
  Sliders,
  Activity,
  Droplets,
  Gauge,
  Thermometer,
  TrendingUp,
  Info,
  HelpCircle,
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";

export default function Twin3DPage() {
  const [scaleMode, setScaleMode] = useState<ScaleMode>("MACRO");
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationRun | null>(null);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fullscreen support
  const viewerContainerRef = React.useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      viewerContainerRef.current?.requestFullscreen?.().catch((err) => {
        console.error("Error al entrar a pantalla completa:", err);
      });
    } else {
      document.exitFullscreen?.().catch((err) => {
        console.error("Error al salir de pantalla completa:", err);
      });
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    return () => document.removeEventListener("fullscreenchange", handleFsChange);
  }, []);

  // Layer Toggles
  const [showHydrologyFlow, setShowHydrologyFlow] = useState(true);
  const [showSoilHorizons, setShowSoilHorizons] = useState(true);
  const [showSensors, setShowSensors] = useState(true);
  const [showScientificLabels, setShowScientificLabels] = useState(true);

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

  // Preparar datos para gráficos temporales (muestreo decenal si son muchos días)
  const chartData = React.useMemo(() => {
    if (results.length === 0) return [];
    // Muestrear o devolver todos
    return results.map((r) => ({
      day: r.day_index,
      streamflow: Number(r.streamflow_m3s.toFixed(2)),
      precip: Number(r.precip_mm.toFixed(1)),
      soil_moisture: Number(r.soil_moisture_vol.toFixed(1)),
      transpiration: Number(r.plant_transpiration_mm.toFixed(2)),
      cwsi: Number(r.cwsi_stress_index.toFixed(2)),
      sap_flow: Number(r.sap_flow_velocity_cmh.toFixed(1)),
    }));
  }, [results]);

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto pb-16">
      {/* Header Bar */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-emerald-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400 shadow-sm">
            <Box className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              From Plant to Watershed: Digital Twin 3D
              <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                MVP · SIMPLIFIED / ILLUSTRATIVE
              </span>
            </h1>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              Planta simplificada · campo n=1000 · HRU proxy · hidrología conceptual · geometría ilustrativa
            </span>
          </div>
        </div>

        {/* Scenario Selector */}
        {simulations.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400 hidden sm:inline">Escenario de corrida:</span>
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
              className="px-3.5 py-2 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 text-xs focus:outline-none focus:border-cyan-500/80 font-mono shadow-sm"
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

      {/* 1. Visor 3D Interactivo con HUD Overlay */}
      <div
        ref={viewerContainerRef}
        className={
          isFullscreen
            ? "fixed inset-0 z-50 w-screen h-screen bg-black"
            : "h-[640px] lg:h-[700px] relative rounded-2xl overflow-hidden border border-zinc-300/80 dark:border-zinc-800 shadow-xl dark:shadow-2xl"
        }
      >
        {isLoading ? (
          <div className="w-full h-full bg-zinc-950 flex flex-col items-center justify-center gap-3 text-zinc-400 text-xs">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
            <span>Cargando corrida multiescala simplificada...</span>
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
              showHydrologyFlow={showHydrologyFlow}
              showSoilHorizons={showSoilHorizons}
              showSensors={showSensors}
              showScientificLabels={showScientificLabels}
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
              showHydrologyFlow={showHydrologyFlow}
              onToggleHydrologyFlow={() => setShowHydrologyFlow(!showHydrologyFlow)}
              showSoilHorizons={showSoilHorizons}
              onToggleSoilHorizons={() => setShowSoilHorizons(!showSoilHorizons)}
              showSensors={showSensors}
              onToggleSensors={() => setShowSensors(!showSensors)}
              showScientificLabels={showScientificLabels}
              onToggleScientificLabels={() => setShowScientificLabels(!showScientificLabels)}
              isFullscreen={isFullscreen}
              onToggleFullscreen={toggleFullscreen}
              scenarioName={selectedSim?.name}
              scenarioPathway={selectedSim?.scenario?.pathway || "SSP2-4.5"}
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

      {/* 2. Sección Inferior: Gráficos Biofísicos Sincronizados con Descripción */}
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Series Temporales Acopladas (Sincronizadas con Día {currentDay})
            </h2>
          </div>
          <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-900 px-2.5 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800">
            Línea roja vertical = Día activo en visor 3D
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico 1: Hidrograma de Cuenca & Precipitación */}
          <div className="rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between shadow-sm">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Waves className="w-4 h-4 text-teal-500" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    Hidrograma de Cuenca (Caudal Q vs Precipitación P)
                  </h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/30">
                  Hidrología conceptual
                </span>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.5} />
                    <XAxis dataKey="day" stroke="#71717a" fontSize={10} tickLine={false} />
                    <YAxis yAxisId="left" stroke="#14b8a6" fontSize={10} tickLine={false} />
                    <YAxis yAxisId="right" orientation="right" stroke="#38bdf8" fontSize={10} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", fontSize: "11px", borderRadius: "8px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
                    <Bar yAxisId="right" dataKey="precip" name="Lluvia P (mm)" fill="#38bdf8" opacity={0.4} />
                    <Line yAxisId="left" type="monotone" dataKey="streamflow" name="Caudal Q (m³/s)" stroke="#14b8a6" strokeWidth={2} dot={false} />
                    <ReferenceLine x={currentDay} stroke="#ef4444" strokeWidth={2} strokeDasharray="4 4" yAxisId="left" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Descripción Detallada del Gráfico */}
            <div className="mt-4 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800/80 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-teal-700 dark:text-teal-300">
                <Info className="w-3.5 h-3.5 shrink-0" />
                <span>¿Qué muestra este gráfico y cómo interpretarlo?</span>
              </div>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                • <b className="text-zinc-800 dark:text-zinc-200">Caudal Q (línea verde-azul, m³/s):</b> Es la descarga calculada por el modelo hidrológico conceptual; no es una medición de estación.
              </p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                • <b className="text-zinc-800 dark:text-zinc-200">Precipitación (barras celestes, mm):</b> Forzamiento diario sintético de la corrida actual. Los artefactos CHIRPS o CMIP6 se identifican por separado en su manifiesto.
              </p>
            </div>
          </div>

          {/* Gráfico 2: Dinámica Fisiológica de la Planta */}
          <div className="rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between shadow-sm">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sprout className="w-4 h-4 text-emerald-500" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    Fisiología del Maíz (Transpiración vs Estrés CWSI)
                  </h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                  Planta simplificada
                </span>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.5} />
                    <XAxis dataKey="day" stroke="#71717a" fontSize={10} tickLine={false} />
                    <YAxis yAxisId="left" stroke="#10b981" fontSize={10} tickLine={false} />
                    <YAxis yAxisId="right" orientation="right" stroke="#f59e0b" fontSize={10} tickLine={false} domain={[0, 1]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#09090b", borderColor: "#27272a", fontSize: "11px", borderRadius: "8px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
                    <Line yAxisId="left" type="monotone" dataKey="transpiration" name="Transp. Tr (mm/d)" stroke="#10b981" strokeWidth={2} dot={false} />
                    <Line yAxisId="left" type="monotone" dataKey="sap_flow" name="Savia Xilema (cm/h)" stroke="#0ea5e9" strokeWidth={1.5} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="cwsi" name="Estrés CWSI [0-1]" stroke="#f59e0b" strokeWidth={1.8} dot={false} strokeDasharray="3 3" />
                    <ReferenceLine x={currentDay} stroke="#ef4444" strokeWidth={2} strokeDasharray="4 4" yAxisId="left" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Descripción Detallada del Gráfico */}
            <div className="mt-4 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800/80 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-emerald-700 dark:text-emerald-300">
                <Info className="w-3.5 h-3.5 shrink-0" />
                <span>¿Qué muestra este gráfico y cómo interpretarlo?</span>
              </div>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                • <b className="text-zinc-800 dark:text-zinc-200">Transpiración Tr (verde, mm/d) y Savia (azul, cm/h):</b> Son salidas/proxies del modelo de planta simplificado, no mediciones fisiológicas.
              </p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                • <b className="text-zinc-800 dark:text-zinc-200">Estrés CWSI (línea punteada ámbar):</b> Es un índice proxy de estrés. La respuesta visual de hojas es ilustrativa y no constituye un FSPM.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Sección Inferior: Guía Completa del Sistema — ¿Qué hace cada cosa y cada botón? */}
      <div className="rounded-2xl bg-gradient-to-br from-zinc-50 via-white to-zinc-50 dark:from-zinc-900/80 dark:via-zinc-950 dark:to-zinc-900/80 border border-zinc-200 dark:border-zinc-800 p-6 md:p-8 space-y-6 shadow-sm">
        <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-4">
          <HelpCircle className="w-5 h-5 text-cyan-500" />
          <div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Guía del Sistema: ¿Qué hace cada control, botón y métrica?
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Manual interactivo de operación del gemelo digital multiescala y sus 3 niveles acoplados.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 text-xs">
          {/* Bloque 1: Selector de Escalas (3 Tamaños) */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 space-y-3">
            <div className="flex items-center gap-2 font-bold text-teal-600 dark:text-teal-400 text-xs">
              <Mountain className="w-4 h-4" />
              <span>1. Selector de Escala (3 Tamaños)</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              Permite cambiar la cámara cinemática entre los tres niveles espaciales del gemelo:
            </p>
            <ul className="space-y-2 text-[11px] text-zinc-700 dark:text-zinc-300">
              <li className="flex items-start gap-1.5">
                <b className="text-teal-500 shrink-0">🏔️ Macro:</b> Cuenca procedural con HRU proxy y red fluvial ilustrativa; no representa geometría SWAT+ ni una estación real.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-cyan-500 shrink-0">🌾 Meso:</b> Parcela agrícola con 1000 plantas, siembra directa (mulch) y torre micrometeorológica Eddy Covariance.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-emerald-500 shrink-0">🌱 Micro:</b> Planta individual de maíz y perfil de suelo procedurales que visualizan variables simplificadas.
              </li>
            </ul>
          </div>

          {/* Bloque 2: Botones de Capas 3D */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 space-y-3">
            <div className="flex items-center gap-2 font-bold text-cyan-600 dark:text-cyan-400 text-xs">
              <Layers className="w-4 h-4" />
              <span>2. Botones de Capas 3D</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              Botones con iconos situados en la esquina superior derecha del visor 3D:
            </p>
            <ul className="space-y-2 text-[11px] text-zinc-700 dark:text-zinc-300">
              <li className="flex items-start gap-1.5">
                <span className="p-1 rounded bg-cyan-500/10 text-cyan-400"><Waves className="w-3 h-3" /></span>
                <span><b className="text-zinc-900 dark:text-zinc-100">Flujo Físico:</b> Activa/apaga las partículas de savia xilemática, lluvia 3D y canal fluvial.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="p-1 rounded bg-amber-500/10 text-amber-400"><Layers className="w-3 h-3" /></span>
                <span><b className="text-zinc-900 dark:text-zinc-100">Suelo / HRU proxy:</b> Alterna horizontes y bordes procedurales; no son capas SoilGrids ni polígonos GIS.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="p-1 rounded bg-emerald-500/10 text-emerald-400"><Radio className="w-3 h-3" /></span>
                <span><b className="text-zinc-900 dark:text-zinc-100">Marcadores:</b> Muestra elementos ilustrativos, no instrumentación conectada.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="p-1 rounded bg-purple-500/10 text-purple-400"><FileText className="w-3 h-3" /></span>
                <span><b className="text-zinc-900 dark:text-zinc-100">Etiquetas 3D:</b> Muestra u oculta los carteles con datos cuantitativos en la escena.</span>
              </li>
            </ul>
          </div>

          {/* Bloque 3: Controles del Reproductor Temporal */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 space-y-3">
            <div className="flex items-center gap-2 font-bold text-emerald-600 dark:text-emerald-400 text-xs">
              <Play className="w-4 h-4" />
              <span>3. Reproductor Temporal</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              Barra inferior flotante que controla la evolución temporal del ciclo agrícola:
            </p>
            <ul className="space-y-2 text-[11px] text-zinc-700 dark:text-zinc-300">
              <li className="flex items-start gap-1.5">
                <b className="text-emerald-500 shrink-0">▶️ Play / ⏸️ Pausa:</b> Inicia o detiene la simulación temporal en bucle continuo (avanza 1 día cada 600 ms).
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-teal-500 shrink-0">🎚️ Slider de Días:</b> Desliza entre el Día 1 y el Día 365 para saltar instantáneamente a fechas de sequía, lluvias intensas o cosecha.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-cyan-500 shrink-0">🔄 Sincronización:</b> Al mover el slider, los gráficos inferiores y el modelo 3D superior se sincronizan al unísono.
              </li>
            </ul>
          </div>

          {/* Bloque 4: Variables Biofísicas del HUD */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/80 space-y-3">
            <div className="flex items-center gap-2 font-bold text-sky-600 dark:text-sky-400 text-xs">
              <Activity className="w-4 h-4" />
              <span>4. Métricas Biofísicas del HUD</span>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              Tarjeta flotante que reporta las 4 variables clave del día actual:
            </p>
            <ul className="space-y-2 text-[11px] text-zinc-700 dark:text-zinc-300">
              <li className="flex items-start gap-1.5">
                <b className="text-teal-500 shrink-0">🌊 Caudal (Q):</b> Descarga fluvial simulada en m³/s por el modelo conceptual.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-cyan-500 shrink-0">💧 Humedad (θ):</b> Contenido volumétrico (%) de agua del estado de suelo simulado.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-emerald-500 shrink-0">⏱️ Transp. (Tr):</b> Tasa de transpiración vegetal proxy en mm/d del modelo simplificado.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-sky-500 shrink-0">🌡️ Savia Xilema:</b> Velocidad del flujo ascendente en cm/h a través del culmo.
              </li>
              <li className="flex items-start gap-1.5">
                <b className="text-amber-500 shrink-0">🟢🟡🔴 CWSI:</b> Semáforo de estrés: Óptimo (&lt;0.25), Moderado o Crítico (&gt;0.55).
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

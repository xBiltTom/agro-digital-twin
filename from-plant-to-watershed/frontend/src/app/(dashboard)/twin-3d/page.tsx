"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Box, Loader2, Sprout, Waves, AlertCircle, Calendar as CalendarIcon, Table } from "lucide-react";
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from "recharts";
import { api } from "../../../lib/api";
import { chartPointFromRecord, periodLabel, sceneFromRecord } from "../../../lib/playback-scene";
import { useTwinPlayback } from "../../../hooks/useTwinPlayback";
import { useHistoricalCharts } from "../../../hooks/useHistoricalCharts";
import type { PlaybackResolution } from "../../../types/playback";
import type { SimulationRun } from "../../../types/simulation";
import MultiScaleViewer3D, { type ScaleMode } from "../../../components/3d/MultiScaleViewer3D";
import TwinHUDOverlay from "../../../components/3d/TwinHUDOverlay";
import HistoricalTwinCharts from "../../../components/3d/HistoricalTwinCharts";
import HistoricalContext3D from "../../../components/3d/HistoricalContext3D";
import MacroEntityExplorer from "../../../components/3d/MacroEntityExplorer";
import { useAuth } from "../../../context/AuthContext";
import { accessibleSimulations } from "../../../lib/simulation-access";
import { historicalFallbackEligible } from "../../../lib/historical-charts";
import { firstCropNavigation, preferredPlaybackResolution } from "../../../lib/playback-navigation";

const SCIENTIFIC_LANDMARKS_2019 = [
  { date: "2019-01-15", label: "15 Ene", desc: "Invierno · Barbecho" },
  { date: "2019-05-15", label: "15 May", desc: "Inicio siembra FSPM" },
  { date: "2019-07-15", label: "15 Jul", desc: "Pleno desarrollo" },
  { date: "2019-08-30", label: "30 Ago", desc: "Cosecha escalonada" },
  { date: "2019-09-15", label: "15 Sep", desc: "Post-cosecha" },
  { date: "2019-12-15", label: "15 Dic", desc: "Hidrología anual" },
];

function explainPlaybackError(error: string | null): string | null {
  if (!error) return null;
  if (error.includes("PostgreSQL playback count differs from the published manifest")) {
    return "El manifiesto anuncia estados temporales que no están en la base. Los resultados hidrológicos guardados pueden seguir disponibles, pero el playback necesita reparación.";
  }
  if (error.includes("Playback state unavailable or invalid")) {
    return "El backend no pudo validar los estados temporales de esta corrida.";
  }
  return error;
}

export default function Twin3DPage() {
  const { user } = useAuth();
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [simulationsLoaded, setSimulationsLoaded] = useState(false);
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [scaleMode, setScaleMode] = useState<ScaleMode>("MACRO");
  const [plantId, setPlantId] = useState<string | null>(null);
  const [showHydrologyFlow, setShowHydrologyFlow] = useState(true);
  const [showSoilHorizons, setShowSoilHorizons] = useState(true);
  const [showSensors, setShowSensors] = useState(true);
  const [showScientificLabels, setShowScientificLabels] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dateMessage, setDateMessage] = useState<string | null>(null);
  const [navigatingToCrop, setNavigatingToCrop] = useState(false);
  const [isExplorerOpen, setIsExplorerOpen] = useState(false);
  const viewerRef = useRef<HTMLDivElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const autoResolutionSimulation = useRef<string | null>(null);
  const playback = useTwinPlayback(simulationId);
  const setPlaybackResolution = playback.setResolution;
  const simulation = simulations.find((item) => item.id === simulationId) ?? null;
  const record = playback.record;
  const scene = useMemo(() => record ? sceneFromRecord(record, plantId) : null, [record, plantId]);
  const currentAvailability = playback.availability?.simulation_id === simulationId ? playback.availability : null;
  const playbackArtifactStatus = playback.page?.artifact_status ?? (
    currentAvailability?.codes.includes("ARTIFACT_INVALID") || currentAvailability?.resolutions.some((item) => item.artifact_status === "INVALID")
      ? "INVALID"
      : null
  );
  const historical = useHistoricalCharts(simulation, playbackArtifactStatus);
  const selectedResolution = playback.resolution ?? playback.page?.resolution ?? undefined;
  const cropNavigation = firstCropNavigation(currentAvailability, selectedResolution);
  const playbackReadyForResolution = Boolean(playback.page && playback.page.resolution === selectedResolution);
  const playbackErrorMessage = explainPlaybackError(playback.error);

  useEffect(() => {
    if (!simulationId || !currentAvailability || playback.availabilityLoading || autoResolutionSimulation.current === simulationId) return;
    const preferred = preferredPlaybackResolution(currentAvailability);
    autoResolutionSimulation.current = simulationId;
    if (preferred && preferred !== playback.page?.resolution) {
      queueMicrotask(() => setPlaybackResolution(preferred));
    }
  }, [simulationId, currentAvailability, playback.availabilityLoading, playback.resolution, playback.page?.resolution, setPlaybackResolution]);

  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    api.getSimulations().then((runs) => {
      if (controller.signal.aborted) return;
      const accessible = accessibleSimulations(runs, user);
      setSimulations(accessible);
      const requestedId = new URLSearchParams(window.location.search).get("simId");
      const requestedRun = requestedId ? accessible.find((run) => run.id === requestedId) : null;
      setSelectionError(requestedId && !requestedRun ? "La corrida del enlace no está disponible para este usuario." : null);
      // Prefer the latest accessible completed coupled research run.
      const currentRun = accessible.find((run) => run.status === "COMPLETED" && run.name.startsWith("South Fork · reproducción B")) ?? accessible.find((run) => run.id === "sf-test-v1-b-2025");
      const initialRun = requestedRun ?? (requestedId ? null : currentRun ?? accessible[0] ?? null);
      setSimulationId(initialRun?.id ?? null);
      setSimulationsLoaded(true);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) {
        setSimError(cause instanceof Error ? cause.message : "Error de conexión con el backend FastAPI (localhost:8000)");
        setSimulationsLoaded(true);
      }
    });
    return () => controller.abort();
  }, [user]);

  useEffect(() => {
    const sync = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  const chartData = useMemo(() => playback.recordsForChart.map(chartPointFromRecord), [playback.recordsForChart]);

  const selectSimulation = (id: string) => {
    playback.setPlaying(false);
    playback.setResolution(undefined);
    autoResolutionSimulation.current = null;
    setPlantId(null);
    setScaleMode("MACRO");
    setDateMessage(null);
    setSelectionError(null);
    setSimulationId(id);
    const url = new URL(window.location.href);
    url.searchParams.set("simId", id);
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  };

  return <div className="mx-auto flex max-w-7xl flex-col gap-6 pb-16">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-cyan-500/10"><Box className="h-5 w-5 text-cyan-400" /></div>
        <div>
          <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">From Plant to Watershed · Gemelo 3D</h1>
          <p className="text-xs text-zinc-500">Reproducción científica twin-playback-v1 · escenas ilustrativas basadas en estados persistidos</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-zinc-500">Simulación
          <select aria-label="Simulación" value={simulationId ?? ""} onChange={(event) => selectSimulation(event.target.value)}
            className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100">
            {simulations.map((run) => (
              <option key={run.id} value={run.id}>
                {run.id === "phase234-sf-2019-v2"
                  ? `${run.name} (Archivo 2019 · v2 · FSPM/SWAT+ Histórica)`
                  : run.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-zinc-500">Detalle temporal
          <select aria-label="Detalle temporal" value={selectedResolution ?? ""} onChange={(event) => {
            setDateMessage(null);
            autoResolutionSimulation.current = simulationId;
            playback.setResolution(event.target.value as PlaybackResolution);
          }}
            disabled={!playback.page?.available_resolutions.length}
            className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100">
            {!playback.page?.available_resolutions.length && <option value="">No disponible</option>}
            {playback.page?.available_resolutions.map((value) => {
              const availability = currentAvailability?.resolutions.find((item) => item.resolution === value);
              const label = value === "DAILY" ? "Diario" : value === "MONTHLY" ? "Mensual" : "Anual";
              return <option key={value} value={value}>{label}{availability?.fspm_trajectory_available ? " · incluye estados de cultivo" : ""}</option>;
            })}
          </select>
        </label>
        {record && <form className="flex items-center gap-1 text-xs text-zinc-500" onSubmit={(event) => {
          event.preventDefault();
          const date = dateInputRef.current?.value;
          if (date) void playback.jumpToDate(date).then((found) => setDateMessage(found ? null : "No hay registro para esa fecha en la resolución seleccionada."));
        }}>
          <label htmlFor="playback-date">Ir a fecha</label>
          <input id="playback-date" key={`${simulationId}-${record.date}`} ref={dateInputRef} type="date" defaultValue={record.date}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-zinc-100" />
          <button type="submit" className="rounded-lg bg-cyan-700 px-2 py-1.5 text-white cursor-pointer hover:bg-cyan-600 transition">Ir</button>
        </form>}
        {cropNavigation.status === "READY" && <button type="button"
          disabled={playback.availabilityLoading || playback.loading || !playbackReadyForResolution || navigatingToCrop}
          onClick={() => {
            setNavigatingToCrop(true);
            playback.setPlaying(false);
            void playback.jumpToFirstCrop().then((found) => {
              setDateMessage(found ? null : "No se pudo cargar la primera fecha con campo FSPM representable.");
            }).finally(() => setNavigatingToCrop(false));
          }}
          className="rounded-lg bg-emerald-700 px-2 py-1.5 text-xs text-white disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer hover:bg-emerald-600 transition">
          {navigatingToCrop ? "Buscando cultivo…" : "Ir al primer cultivo"}
        </button>}
        {record && (
          <button
            type="button"
            onClick={() => setIsExplorerOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-teal-500/40 bg-teal-600/20 hover:bg-teal-600/40 px-3 py-1.5 text-xs font-semibold text-teal-200 transition cursor-pointer"
          >
            <Table className="h-3.5 w-3.5" />
            <span>{record.hru_results.length} HRUs / {record.channel_results.length} canales</span>
          </button>
        )}
      </div>
    </header>
    <p className="text-xs text-zinc-400">Estados físicos diarios modelados. La corrección ML mensual se consulta en Simulaciones y no modifica este visor. Anatomía y terreno ilustrativos.</p>

    {/* Barra de hitos científicos del año 2019 */}
    {(simulationId === "phase234-sf-2019-v2" || (record && record.date.startsWith("2019"))) && (
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-teal-500/30 bg-teal-950/20 px-3 py-2 text-xs">
        <span className="font-semibold text-teal-300 flex items-center gap-1 mr-1">
          <CalendarIcon className="h-3.5 w-3.5" /> Hitos 2019:
        </span>
        {SCIENTIFIC_LANDMARKS_2019.map((lm) => {
          const isCurrent = record?.date === lm.date;
          return (
            <button
              key={lm.date}
              type="button"
              onClick={() => {
                setDateMessage(null);
                void playback.jumpToDate(lm.date).then((found) => {
                  if (!found) setDateMessage(`No se encontró registro para ${lm.date}`);
                });
              }}
              className={`rounded-lg px-2.5 py-1 text-xs font-mono transition flex items-center gap-1 cursor-pointer ${
                isCurrent
                  ? "bg-teal-500 text-zinc-950 font-bold shadow-md"
                  : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white"
              }`}
              title={lm.desc}
            >
              <span>{lm.label}</span>
              <span className="text-[10px] opacity-75 hidden sm:inline">· {lm.desc}</span>
            </button>
          );
        })}
      </div>
    )}

    {dateMessage && <p className="text-xs text-amber-600">{dateMessage}</p>}
    {cropNavigation.status === "SELECT_DAILY" && <p className="text-xs text-amber-600">Los estados del cultivo están guardados por día. Selecciona «Diario» para verlos por fecha.</p>}
    {playback.availabilityLoading && <p className="text-xs text-zinc-500">Consultando disponibilidad FSPM…</p>}
    {selectionError && (
      <div role="alert" className="border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
        {selectionError}
      </div>
    )}
    {playbackErrorMessage && (
      <div role="alert" className="border border-rose-300 bg-rose-50 p-3 text-xs text-rose-900 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-200">
        {playbackErrorMessage}
      </div>
    )}
    {simError && (
      <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-200">
        <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
        <div>
          <b>Estado de conexión FastAPI:</b> {simError}. Asegúrese de que el backend esté en ejecución y cuente con autenticación activa.
        </div>
      </div>
    )}

    {record?.plant_samples.length ? <div className="flex items-center gap-3 text-xs text-zinc-500">
      <label>Muestra individual persistida
        <select aria-label="Muestra de planta" className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-zinc-100"
          value={scene?.sample?.plant_id ?? ""} onChange={(event) => setPlantId(event.target.value)}>
          {!scene?.sample && <option value="">Muestra seleccionada no activa en esta fecha</option>}
          {record.plant_samples.map((sample) => (
            <option key={sample.plant_id} value={sample.plant_id}>
              {sample.plant_id} {sample.calendar_id ? `(${sample.calendar_id.split("-").pop()})` : ""}
            </option>
          ))}
        </select>
      </label>
      <span>{record.plant_samples.length} muestras activas hoy; el campo meso usa promedios ponderados.</span>
    </div> : null}

    <div ref={viewerRef} className={isFullscreen
      ? "fixed inset-0 z-50 h-screen w-screen bg-black"
      : "relative h-[640px] overflow-hidden rounded-2xl border border-zinc-300/80 shadow-xl dark:border-zinc-800 lg:h-[700px]"}>
      {scene && playback.page?.artifact_status === "AVAILABLE" ? <>
        <MultiScaleViewer3D scaleMode={scaleMode} onChangeScale={setScaleMode} scene={scene}
          stationId={simulation?.station_id}
          onSelectPlant={(id) => { if (id) setPlantId(id); }}
          showHydrologyFlow={showHydrologyFlow} showSoilHorizons={showSoilHorizons}
          showSensors={showSensors} showScientificLabels={showScientificLabels}
          onOpenExplorer={() => setIsExplorerOpen(true)}
          selectedPlantId={plantId} />
        <TwinHUDOverlay record={record!} simulationName={simulation?.name ?? record!.simulation_id}
          scaleMode={scaleMode} onChangeScale={setScaleMode} isPlaying={playback.playing}
          onTogglePlay={() => playback.setPlaying((old) => !old)} index={playback.index}
          total={playback.page!.total} onSeek={(next) => { setDateMessage(null); playback.seek(next); }}
          showHydrologyFlow={showHydrologyFlow} onToggleHydrologyFlow={() => setShowHydrologyFlow((old) => !old)}
          showSoilHorizons={showSoilHorizons} onToggleSoilHorizons={() => setShowSoilHorizons((old) => !old)}
          showSensors={showSensors} onToggleSensors={() => setShowSensors((old) => !old)}
          showScientificLabels={showScientificLabels} onToggleScientificLabels={() => setShowScientificLabels((old) => !old)}
          isFullscreen={isFullscreen} onToggleFullscreen={() => {
            if (document.fullscreenElement) void document.exitFullscreen();
            else void viewerRef.current?.requestFullscreen();
          }}
          onOpenExplorer={() => setIsExplorerOpen(true)}
          selectedPlantId={plantId}
          onSelectPlant={(id) => { if (id) setPlantId(id); }}
          visualMode={scene.visual.mode} />
      </> : simulation && historicalFallbackEligible(simulation.status, playbackArtifactStatus) ? <HistoricalContext3D simulation={simulation} playbackStatus={playbackArtifactStatus}
        scaleMode={scaleMode} onChangeScale={setScaleMode}
        onToggleFullscreen={() => {
          if (document.fullscreenElement) void document.exitFullscreen();
          else void viewerRef.current?.requestFullscreen();
        }} /> : <div className="flex h-full flex-col items-center justify-center gap-3 bg-zinc-950 p-8 text-center text-zinc-300">
        {!simulationsLoaded || playback.loading ? <Loader2 className="h-8 w-8 animate-spin text-cyan-400" /> : <AlertCircle className="h-8 w-8 text-amber-400" />}
        <strong>{!simulationsLoaded ? "Cargando simulaciones…" : selectionError ? "No se abrió la corrida solicitada" : playback.loading ? "Cargando periodo…" :
          simulations.length === 0 ? (simError ? "Error de conexión con FastAPI" : "No hay simulaciones accesibles") : playback.page?.artifact_status === "NOT_AVAILABLE"
          ? "Esta corrida no tiene playback temporal" : playbackArtifactStatus === "INVALID" ? "Los estados temporales no superaron la validación" : "No hay estado temporal para mostrar"}</strong>
        <p className="max-w-xl text-xs text-zinc-400">{selectionError ?? (simError ? `No se pudo conectar con FastAPI: ${simError}. Verifique que el servicio backend esté en ejecución.` : playbackErrorMessage ??
          playback.page?.limitations.join(" · ") ?? "Se requiere un artefacto twin-playback-v1. No se generan estados vegetales o meteorológicos sustitutos.")}</p>
        {playback.page && <span className="text-xs">Estado de simulación: {playback.page.simulation_status}</span>}
        {historical.status === "ready" && <span className="text-xs text-cyan-300">Los gráficos históricos de esta corrida están debajo del visor.</span>}
      </div>}
    </div>

    {/* Modal Explorador Multiescala de HRUs y Canales */}
    {record && (
      <MacroEntityExplorer
        record={record}
        isOpen={isExplorerOpen}
        onClose={() => setIsExplorerOpen(false)}
        onSelectPlant={(id) => {
          setPlantId(id);
          setScaleMode("MICRO");
        }}
        onNavigateToScale={(scale) => setScaleMode(scale)}
      />
    )}

    {record && <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900/60">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Waves className="h-4 w-4 text-cyan-500" /> Meteorología e hidrología · ventana cargada</h2>
        <div className="h-56"><ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}><CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis yAxisId="left" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} /><Tooltip /><Legend />
            <Bar yAxisId="right" dataKey="precipitation" name={`Precipitación (${record.weather.precipitation_mm?.unit ?? "mm"})`} fill="#38bdf8" />
            <Line yAxisId="left" dataKey="streamflow" name="Caudal modelado (m³/s)" stroke="#14b8a6" dot={false} connectNulls={false} />
            <Line yAxisId="left" dataKey="observed" name="Caudal observado USGS (m³/s)" stroke="#f97316" dot={false} connectNulls={false} />
            <ReferenceLine yAxisId="left" x={periodLabel(record)} stroke="#ef4444" />
          </ComposedChart>
        </ResponsiveContainer></div>
      </div>
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900/60">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Sprout className="h-4 w-4 text-emerald-500" /> Estado FSPM · ventana cargada</h2>
        {chartData.some((point) => point.lai !== null) ? <div className="h-56"><ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}><CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Legend />
            <Line dataKey="lai" name="LAI" stroke="#22c55e" dot={false} connectNulls={false} />
            <Line dataKey="stress" name="Estrés FSPM" stroke="#f59e0b" dot={false} connectNulls={false} />
            <Line dataKey="transpiration" name="Transpiración FSPM (mm/día)" stroke="#06b6d4" dot={false} connectNulls={false} />
            <ReferenceLine x={periodLabel(record)} stroke="#ef4444" />
          </ComposedChart>
        </ResponsiveContainer></div> :
          <div className="flex h-56 items-center justify-center text-center text-xs text-zinc-500">No hay trayectoria FSPM en esta resolución o corrida.</div>}
      </div>
    </div>}

    {record && <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900/50 dark:text-zinc-400">
      <b className="text-zinc-800 dark:text-zinc-200">Disponibilidad y límites</b>
      <p className="mt-1">Periodo {periodLabel(record)} ({record.resolution}). Las gráficas muestran solo la página de {playback.recordsForChart.length} registros cargada, sin interpolar periodos. HRU: {record.hru_results.length} resultados identificados ({record.hru_results.map((hru) => hru.hru_id).slice(0, 12).join(", ") || "ninguno"}); no se asignan a polígonos. Outlet: {record.outlet_unit ?? "no declarado"}.</p>
      <p className="mt-1">La iluminación, el cielo, el relieve, los surcos y la geometría foliar son ilustrativos; no representan radiación, viento, nubosidad ni arquitectura vegetal observados.</p>
      {record.resolution === "DAILY" && record.availability.hydrology === "NOT_AVAILABLE" &&
        <p className="mt-1 text-amber-600">La hidrología diaria no está disponible en esta serie FSPM.</p>}
      {record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" &&
        <p className="mt-1 text-amber-600">La ventana de siembra/cosecha es una aproximación PHU, no un evento agrícola observado.</p>}
      {[...record.limitations, ...(playback.page?.limitations ?? [])].map((item, index) => <p key={index} className="mt-1">• {item}</p>)}
    </div>}
    {simulation && historicalFallbackEligible(simulation.status, playbackArtifactStatus) && <>
      {historical.status === "loading" && <p className="text-sm text-zinc-500">Cargando gráficos históricos…</p>}
      {historical.status === "error" && <p className="rounded-xl border border-rose-500/30 p-4 text-sm text-rose-600">No se pudieron cargar los gráficos históricos: {historical.data?.error}</p>}
      {historical.status === "ready" && historical.data && <HistoricalTwinCharts
        points={historical.data.points} kind={historical.data.kind} origin={historical.data.origin}
        frequency={historical.data.frequency}
        truncated={historical.data.truncated} />}
    </>}
  </div>;
}

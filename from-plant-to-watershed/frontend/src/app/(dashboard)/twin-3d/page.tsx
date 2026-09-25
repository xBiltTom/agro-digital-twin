"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Box, Loader2, Sprout, Waves, AlertCircle } from "lucide-react";
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
import { useAuth } from "../../../context/AuthContext";
import { accessibleSimulations } from "../../../lib/simulation-access";
import { historicalFallbackEligible } from "../../../lib/historical-charts";

export default function Twin3DPage() {
  const { user } = useAuth();
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [simulationsLoaded, setSimulationsLoaded] = useState(false);
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [scaleMode, setScaleMode] = useState<ScaleMode>("MACRO");
  const [plantId, setPlantId] = useState<string | null>(null);
  const [showHydrologyFlow, setShowHydrologyFlow] = useState(true);
  const [showSoilHorizons, setShowSoilHorizons] = useState(true);
  const [showSensors, setShowSensors] = useState(true);
  const [showScientificLabels, setShowScientificLabels] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dateMessage, setDateMessage] = useState<string | null>(null);
  const viewerRef = useRef<HTMLDivElement>(null);
  const dateInputRef = useRef<HTMLInputElement>(null);
  const playback = useTwinPlayback(simulationId);
  const simulation = simulations.find((item) => item.id === simulationId) ?? null;
  const historical = useHistoricalCharts(simulation, playback.page?.artifact_status ?? null);
  const record = playback.record;
  const scene = useMemo(() => record ? sceneFromRecord(record, plantId) : null, [record, plantId]);

  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    api.getSimulations().then((runs) => {
      if (controller.signal.aborted) return;
      const accessible = accessibleSimulations(runs, user);
      setSimulations(accessible);
      setSimulationId(accessible[0]?.id ?? null);
      setSimulationsLoaded(true);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) {
        setSimError(cause instanceof Error ? cause.message : "No se pudieron cargar simulaciones");
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
    setPlantId(null);
    setScaleMode("MACRO");
    setDateMessage(null);
    setSimulationId(id);
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
      <div className="flex flex-wrap gap-2">
        <label className="text-xs text-zinc-500">Simulación
          <select aria-label="Simulación" value={simulationId ?? ""} onChange={(event) => selectSimulation(event.target.value)}
            className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100">
            {simulations.map((run) => <option key={run.id} value={run.id}>{run.name}</option>)}
          </select>
        </label>
        <label className="text-xs text-zinc-500">Resolución
          <select aria-label="Resolución" value={playback.resolution ?? ""} onChange={(event) => { setDateMessage(null); playback.setResolution(event.target.value as PlaybackResolution); }}
            disabled={!playback.page?.available_resolutions.length}
            className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-zinc-100">
            {!playback.resolution && <option value="">No disponible</option>}
            {playback.page?.available_resolutions.map((value) => <option key={value} value={value}>{value}</option>)}
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
          <button type="submit" className="rounded-lg bg-cyan-700 px-2 py-1.5 text-white">Ir</button>
        </form>}
      </div>
    </header>
    {dateMessage && <p className="text-xs text-amber-600">{dateMessage}</p>}
    {playback.error && record && <p className="text-xs text-rose-600">Error de reproducción: {playback.error}</p>}

    {record?.plant_samples.length ? <div className="flex items-center gap-3 text-xs text-zinc-500">
      <label>Muestra individual persistida
        <select aria-label="Muestra de planta" className="ml-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-zinc-100"
          value={scene?.sample?.plant_id ?? ""} onChange={(event) => setPlantId(event.target.value)}>
          {!scene?.sample && <option value="">Muestra seleccionada no disponible</option>}
          {record.plant_samples.map((sample) => <option key={sample.plant_id} value={sample.plant_id}>{sample.plant_id}</option>)}
        </select>
      </label>
      <span>{record.plant_samples.length} muestras en este registro; el campo usa promedios.</span>
    </div> : null}

    <div ref={viewerRef} className={isFullscreen
      ? "fixed inset-0 z-50 h-screen w-screen bg-black"
      : "relative h-[640px] overflow-hidden rounded-2xl border border-zinc-300/80 shadow-xl dark:border-zinc-800 lg:h-[700px]"}>
      {scene && playback.page?.artifact_status === "AVAILABLE" ? <>
        <MultiScaleViewer3D scaleMode={scaleMode} onChangeScale={setScaleMode} scene={scene}
          stationId={simulation?.station_id}
          onSelectPlant={(id) => { if (id) setPlantId(id); }}
          showHydrologyFlow={showHydrologyFlow} showSoilHorizons={showSoilHorizons}
          showSensors={showSensors} showScientificLabels={showScientificLabels} />
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
          }} />
      </> : simulation && historicalFallbackEligible(simulation.status, playback.page?.artifact_status ?? null) ? <HistoricalContext3D simulation={simulation}
        scaleMode={scaleMode} onChangeScale={setScaleMode}
        onToggleFullscreen={() => {
          if (document.fullscreenElement) void document.exitFullscreen();
          else void viewerRef.current?.requestFullscreen();
        }} /> : <div className="flex h-full flex-col items-center justify-center gap-3 bg-zinc-950 p-8 text-center text-zinc-300">
        {!simulationsLoaded || playback.loading ? <Loader2 className="h-8 w-8 animate-spin text-cyan-400" /> : <AlertCircle className="h-8 w-8 text-amber-400" />}
        <strong>{!simulationsLoaded ? "Cargando simulaciones…" : playback.loading ? "Cargando periodo…" :
          simulations.length === 0 ? "No hay simulaciones accesibles" : playback.page?.artifact_status === "NOT_AVAILABLE"
          ? "Reproducción científica no disponible para esta corrida" : "No hay estado temporal para mostrar"}</strong>
        <p className="max-w-xl text-xs text-zinc-400">{simError ?? playback.error ??
          playback.page?.limitations.join(" · ") ?? "Se requiere un artefacto twin-playback-v1. No se generan estados vegetales o meteorológicos sustitutos."}</p>
        {playback.page && <span className="text-xs">Estado de simulación: {playback.page.simulation_status}</span>}
        {historical.status === "ready" && <span className="text-xs text-cyan-300">Los gráficos históricos de esta corrida están debajo del visor.</span>}
      </div>}
    </div>

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
    {simulation && historicalFallbackEligible(simulation.status, playback.page?.artifact_status ?? null) && <>
      {historical.status === "loading" && <p className="text-sm text-zinc-500">Cargando gráficos históricos…</p>}
      {historical.status === "error" && <p className="rounded-xl border border-rose-500/30 p-4 text-sm text-rose-600">No se pudieron cargar los gráficos históricos: {historical.data?.error}</p>}
      {historical.status === "ready" && historical.data && <HistoricalTwinCharts
        points={historical.data.points} kind={historical.data.kind}
        frequency={simulation.hydrology_backend === "SWAT_PLUS"
          ? typeof simulation.effective_config?.output_frequency === "string" ? simulation.effective_config.output_frequency : null
          : "DAILY"}
        truncated={historical.data.truncated} />}
    </>}
  </div>;
}

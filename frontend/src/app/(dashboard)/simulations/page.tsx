"use client";

import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../../../context/AuthContext";
import { api } from "../../../lib/api";
import {
  SimulationRun,
  SimulationResult,
  ClimateScenario,
  Watershed,
  TwinWebSocketTick
} from "../../../types/simulation";
import {
  Sliders,
  Play,
  Pause,
  Plus,
  BarChart3,
  Calendar,
  Layers,
  Droplets,
  Mountain,
  SunMedium,
  Sprout,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Radio,
  RefreshCw,
  TrendingUp,
  Activity
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
  Area,
  AreaChart
} from "recharts";

export default function SimulationsPage() {
  const { hasAnyRole } = useAuth();

  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationRun | null>(null);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [scenarios, setScenarios] = useState<ClimateScenario[]>([]);
  const [watersheds, setWatersheds] = useState<Watershed[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New Simulation Form State
  const [formName, setFormName] = useState("Escenario Futuro CMIP6 SSP2-4.5");
  const [formWatershedId, setFormWatershedId] = useState("");
  const [formScenarioId, setFormScenarioId] = useState("");
  const [formDuration, setFormDuration] = useState(365);
  const [formIrrigationEff, setFormIrrigationEff] = useState(0.85);

  // Live WebSocket State
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [liveTick, setLiveTick] = useState<TwinWebSocketTick | null>(null);
  const [wsSpeed, setWsSpeed] = useState(1);
  const wsRef = useRef<WebSocket | null>(null);

  const canRunSimulations = hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"]);

  // Carga inicial de datos
  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const [simsData, scenData, watersData] = await Promise.all([
        api.getSimulations(),
        api.getClimateScenarios(),
        api.getWatersheds(),
      ]);
      setSimulations(simsData);
      setScenarios(scenData);
      setWatersheds(watersData);

      if (watersData.length > 0) setFormWatershedId(watersData[0].id);
      if (scenData.length > 0) setFormScenarioId(scenData[0].id);

      if (simsData.length > 0) {
        selectSimulation(simsData[0]);
      }
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Error al cargar datos de simulación" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const selectSimulation = async (sim: SimulationRun) => {
    setSelectedSim(sim);
    setIsLoadingResults(true);
    // Desconectar WS previo si existía
    if (wsRef.current) {
      wsRef.current.close();
      setIsWsConnected(false);
      setLiveTick(null);
    }

    try {
      const dailyResults = await api.getSimulationResults(sim.id, sim.duration_days);
      setResults(dailyResults);
    } catch (err: any) {
      console.error("Error al cargar resultados diarios:", err);
    } finally {
      setIsLoadingResults(false);
    }
  };

  const handleCreateSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setFeedbackMsg(null);

    try {
      const newSim = await api.createSimulation({
        name: formName,
        watershed_id: formWatershedId,
        scenario_id: formScenarioId,
        duration_days: Number(formDuration),
        irrigation_efficiency: Number(formIrrigationEff),
        parameters: { crop: "Palto Hass", system: "Goteo Automatizado" }
      });
      setSimulations([newSim, ...simulations]);
      setIsModalOpen(false);
      setFeedbackMsg({ type: "success", text: `Simulación "${newSim.name}" acoplada y ejecutada exitosamente.` });
      selectSimulation(newSim);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Error al ejecutar simulación" });
    } finally {
      setIsSubmitting(false);
    }
  };

  // WebSocket Live Stream Handlers
  const toggleWebSocket = () => {
    if (isWsConnected) {
      if (wsRef.current) wsRef.current.close();
      setIsWsConnected(false);
      setLiveTick(null);
    } else {
      if (!selectedSim) return;
      const wsUrl = `ws://localhost:8000/api/v1/twin/ws/${selectedSim.id}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsWsConnected(true);
        ws.send(JSON.stringify({ command: "play", speed: wsSpeed }));
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === "TWIN_STATE_TICK") {
            setLiveTick(data);
          }
        } catch (e) {
          console.error("Error parsing WS frame", e);
        }
      };

      ws.onclose = () => {
        setIsWsConnected(false);
        setLiveTick(null);
      };

      wsRef.current = ws;
    }
  };

  const handleWsSpeedChange = (speed: number) => {
    setWsSpeed(speed);
    if (wsRef.current && isWsConnected) {
      wsRef.current.send(JSON.stringify({ command: "play", speed }));
    }
  };

  // Reducir serie para gráficos si es muy grande
  const chartData = results.filter((_, idx) => idx % Math.max(1, Math.floor(results.length / 90)) === 0);

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              Estudio de Modelado SWAT & Proyecciones Climáticas
            </h1>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
            Simulación biofísica acoplada: Fisiología de Planta (Micro) ⇄ Parcela (Meso) ⇄ Cuenca SWAT (Macro) bajo CMIP6.
          </p>
        </div>

        {canRunSimulations && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-zinc-950 text-xs font-semibold shadow-md shadow-emerald-500/20 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Nueva Simulación Acoplada</span>
          </button>
        )}
      </div>

      {feedbackMsg && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 ${
            feedbackMsg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300"
          }`}
        >
          {feedbackMsg.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span>{feedbackMsg.text}</span>
        </div>
      )}

      {/* Grid: Simulations List (Left) + Detail & Charts (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Simulations List */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400 font-medium">
              Simulaciones Ejecutadas ({simulations.length})
            </span>
            <button
              onClick={loadInitialData}
              className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 p-1 cursor-pointer"
              title="Refrescar lista"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="flex flex-col gap-2.5 max-h-[780px] overflow-y-auto pr-1">
            {simulations.map((sim) => {
              const isSelected = selectedSim?.id === sim.id;
              return (
                <div
                  key={sim.id}
                  onClick={() => selectSimulation(sim)}
                  className={`p-4 rounded-xl border text-left cursor-pointer transition flex flex-col gap-2.5 ${
                    isSelected
                      ? "bg-emerald-50 dark:bg-zinc-900 border-emerald-400 dark:border-emerald-500/60 shadow-md ring-1 ring-emerald-400/40 dark:ring-emerald-500/30"
                      : "bg-white dark:bg-zinc-950/60 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-900/40 shadow-xs"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-200 line-clamp-1">
                      {sim.name}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-800/50 shrink-0 font-medium">
                      {sim.scenario?.code || "CMIP6"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-500 dark:text-zinc-400 font-mono">
                    <div>
                      <span className="text-zinc-500 dark:text-zinc-400">Duración: </span>
                      <span className="text-zinc-800 dark:text-zinc-300 font-semibold">{sim.duration_days} días</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 dark:text-zinc-400">Lluvia Total: </span>
                      <span className="text-zinc-800 dark:text-zinc-300 font-semibold">
                        {sim.summary_metrics?.total_precip_mm ?? "-"} mm
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 dark:text-zinc-400">Volumen Río: </span>
                      <span className="text-teal-600 dark:text-teal-400 font-semibold">
                        {sim.summary_metrics?.total_discharge_hm3 ?? "-"} hm³
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 dark:text-zinc-400">Estrés CWSI: </span>
                      <span
                        className={`font-semibold ${
                          (sim.summary_metrics?.mean_cwsi ?? 0) < 0.25
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-amber-600 dark:text-amber-400"
                        }`}
                      >
                        {sim.summary_metrics?.mean_cwsi ?? "-"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Active Simulation Analysis & Charts */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {selectedSim ? (
            <>
              {/* Selected Simulation Card & Live WebSocket Stream Bar */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-4 shadow-sm dark:shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800/80">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">{selectedSim.name}</h2>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-500/30 font-medium">
                        {selectedSim.status}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                      Escenario: {selectedSim.scenario?.name} ({selectedSim.scenario?.pathway})
                    </span>
                  </div>

                  {/* WebSocket Toggle & Live Controls */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={toggleWebSocket}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer border ${
                        isWsConnected
                          ? "bg-rose-500/10 text-rose-300 border-rose-500/40 hover:bg-rose-500/20"
                          : "bg-emerald-500/10 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/20"
                      }`}
                    >
                      <Radio className={`w-3.5 h-3.5 ${isWsConnected ? "animate-pulse text-rose-400" : ""}`} />
                      <span>{isWsConnected ? "Detener Transmisión" : "Sincronizar Gemelo WS"}</span>
                    </button>

                    {isWsConnected && (
                      <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-950 px-2 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800 text-[11px] font-mono">
                        <button
                          onClick={() => handleWsSpeedChange(1)}
                          className={`px-1.5 py-0.5 rounded cursor-pointer transition ${wsSpeed === 1 ? "bg-white text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white font-bold" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}
                        >
                          1x
                        </button>
                        <button
                          onClick={() => handleWsSpeedChange(5)}
                          className={`px-1.5 py-0.5 rounded cursor-pointer transition ${wsSpeed === 5 ? "bg-white text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white font-bold" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}
                        >
                          5x
                        </button>
                        <button
                          onClick={() => handleWsSpeedChange(20)}
                          className={`px-1.5 py-0.5 rounded cursor-pointer transition ${wsSpeed === 20 ? "bg-white text-zinc-900 shadow-xs dark:bg-zinc-800 dark:text-white font-bold" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}
                        >
                          20x
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Live WebSocket Telemetry Ticker (if active) */}
                {isWsConnected && liveTick && (
                  <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-50 via-white to-cyan-50 dark:from-emerald-950/40 dark:via-zinc-950 dark:to-cyan-950/40 border border-emerald-300 dark:border-emerald-500/40 grid grid-cols-2 sm:grid-cols-4 gap-3 animate-fadeIn shadow-sm">
                    <div className="flex flex-col">
                      <span className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400">Día / Fecha</span>
                      <span className="text-xs font-mono font-bold text-zinc-900 dark:text-zinc-100">
                        Día {liveTick.day_index} ({liveTick.date})
                      </span>
                      <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                        {liveTick.weather.temp_c}°C | {liveTick.weather.precip_mm} mm
                      </span>
                    </div>

                    <div className="flex flex-col">
                      <span className="text-[10px] uppercase font-mono text-emerald-700 dark:text-emerald-400 font-semibold">Micro (Planta)</span>
                      <span className="text-xs font-mono font-bold text-emerald-700 dark:text-emerald-300">
                        Tr: {liveTick.micro_plant.transpiration_mm} mm/d
                      </span>
                      <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                        CWSI: {liveTick.micro_plant.cwsi_stress_index}
                      </span>
                    </div>

                    <div className="flex flex-col">
                      <span className="text-[10px] uppercase font-mono text-cyan-700 dark:text-cyan-400 font-semibold">Meso (Suelo)</span>
                      <span className="text-xs font-mono font-bold text-cyan-700 dark:text-cyan-300">
                        θ: {liveTick.meso_soil.soil_moisture_vol} %
                      </span>
                      <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                        Percol: {liveTick.meso_soil.percolation_mm} mm
                      </span>
                    </div>

                    <div className="flex flex-col">
                      <span className="text-[10px] uppercase font-mono text-teal-700 dark:text-teal-400 font-semibold">Macro (SWAT)</span>
                      <span className="text-xs font-mono font-bold text-teal-700 dark:text-teal-300">
                        Q: {liveTick.macro_watershed.streamflow_m3s} m³/s
                      </span>
                      <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                        Qsurf: {liveTick.macro_watershed.surface_runoff_mm} mm
                      </span>
                    </div>
                  </div>
                )}

                {/* Summary KPIs */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Precipitación Total</span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">
                      {selectedSim.summary_metrics?.total_precip_mm ?? "-"} mm
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Volumen en Río</span>
                    <span className="text-sm font-bold text-teal-600 dark:text-teal-400 mt-1 block">
                      {selectedSim.summary_metrics?.total_discharge_hm3 ?? "-"} hm³
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Caudal Máximo Pico</span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">
                      {selectedSim.summary_metrics?.peak_streamflow_m3s ?? "-"} m³/s
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Evapotranspiración</span>
                    <span className="text-sm font-bold text-cyan-600 dark:text-cyan-400 mt-1 block">
                      {selectedSim.summary_metrics?.total_actual_et_mm ?? "-"} mm
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Estrés de Sequía</span>
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-1.5 block truncate">
                      {selectedSim.summary_metrics?.drought_stress_status ?? "Normal"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Chart 1: Hidrograma de Cuenca SWAT (Caudal vs Lluvia) */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm dark:shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Mountain className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                      Hidrograma de Cuenca SWAT: Caudal Fluvial (m³/s) y Precipitación (mm)
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">Escala Macro</span>
                </div>

                {isLoadingResults ? (
                  <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                    <Loader2 className="w-5 h-5 animate-spin mr-2 text-emerald-400" />
                    Cargando hidrograma SWAT...
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" className="dark:stroke-zinc-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis
                          yAxisId="left"
                          stroke="#0d9488"
                          fontSize={10}
                          tickLine={false}
                          label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 10 }}
                        />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          stroke="#0284c7"
                          fontSize={10}
                          tickLine={false}
                          label={{ value: "Lluvia (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }}
                        />
                        <Tooltip
                          contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }}
                        />
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                        <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación (mm)" fill="#0284c7" opacity={0.7} />
                        <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal Exutorio (m³/s)" stroke="#14b8a6" fill="#14b8a6" fillOpacity={0.2} strokeWidth={2} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Chart 2: Fisiología de la Planta (Transpiración vs Demanda ET0) */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm dark:shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sprout className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                      Fisiología Vegetal: Transpiración Real vs Demanda Evaporativa (ET0) y Flujo de Savia
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">Escala Micro</span>
                </div>

                {isLoadingResults ? (
                  <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                    <Loader2 className="w-5 h-5 animate-spin mr-2 text-emerald-400" />
                    Cargando curvas de transpiración...
                  </div>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" className="dark:stroke-zinc-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} label={{ value: "mm / día", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }}
                        />
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                        <Line type="monotone" dataKey="potential_et_mm" name="Demanda Atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="plant_transpiration_mm" name="Transpiración Real Planta (mm/d)" stroke="#059669" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad Savia (cm/h)" stroke="#0284c7" strokeWidth={1.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Chart 3: Dinámica de Humedad del Suelo (Feddes Root Uptake) */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm dark:shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Droplets className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                      Humedad de Suelo (θ % vol) e Índice de Estrés Hídrico (CWSI)
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">Escala Meso (Parcela)</span>
                </div>

                {isLoadingResults ? (
                  <div className="h-60 flex items-center justify-center text-zinc-400 text-xs">
                    <Loader2 className="w-5 h-5 animate-spin mr-2 text-emerald-400" />
                    Cargando perfil edáfico...
                  </div>
                ) : (
                  <div className="h-60 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" className="dark:stroke-zinc-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Humedad θ (%)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }}
                        />
                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                        <Area type="monotone" dataKey="soil_moisture_vol" name="Humedad Volumétrica (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.2} strokeWidth={2} />
                        <Line type="monotone" dataKey="cwsi_stress_index" name="Estrés CWSI (0 a 1)" stroke="#e11d48" strokeWidth={1.5} dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 text-center text-zinc-500 text-xs bg-white dark:bg-transparent">
              Selecciona una simulación de la lista izquierda para visualizar su análisis multiescala.
            </div>
          )}
        </div>
      </div>

      {/* Modal: New Simulation Run */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-2xl flex flex-col gap-4 text-zinc-900 dark:text-zinc-100">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                  Configurar Nuevo Experimento Biofísico SWAT
                </h3>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 cursor-pointer">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSimulation} className="flex flex-col gap-4 text-xs">
              <div>
                <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Nombre de la Simulación
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Escenario Clima Extremo SSP5-8.5"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 focus:outline-none focus:border-emerald-500/80 shadow-sm"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Cuenca Hidrográfica SWAT
                  </label>
                  <select
                    value={formWatershedId}
                    onChange={(e) => setFormWatershedId(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 focus:outline-none focus:border-emerald-500/80 shadow-sm"
                  >
                    {watersheds.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name} ({w.area_km2} km²)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Escenario Climático CMIP6
                  </label>
                  <select
                    value={formScenarioId}
                    onChange={(e) => setFormScenarioId(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 focus:outline-none focus:border-emerald-500/80 shadow-sm"
                  >
                    {scenarios.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.code}: {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Horizonte Temporal (Días)
                  </label>
                  <select
                    value={formDuration}
                    onChange={(e) => setFormDuration(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 focus:outline-none focus:border-emerald-500/80 shadow-sm"
                  >
                    <option value={30}>30 días (Mes)</option>
                    <option value={90}>90 días (Campaña Agrícola)</option>
                    <option value={180}>180 días (Semestre)</option>
                    <option value={365}>365 días (Año Hidrológico Completo)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Eficiencia de Riego: {(formIrrigationEff * 100).toFixed(0)}%
                  </label>
                  <input
                    type="range"
                    min={0.6}
                    max={0.95}
                    step={0.05}
                    value={formIrrigationEff}
                    onChange={(e) => setFormIrrigationEff(Number(e.target.value))}
                    className="w-full mt-2 accent-emerald-500"
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500">
                    <span>60% (Gravedad)</span>
                    <span>95% (Goteo Alta Precisión)</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-600 dark:text-zinc-400 flex flex-col gap-1">
                <span className="font-semibold text-zinc-800 dark:text-zinc-300">Cultivo acoplado: Palto Hass (Persea americana)</span>
                <span>Dinámica radicular calculada mediante función de reducción de Feddes a 120 cm de profundidad.</span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium transition cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-zinc-950 font-semibold transition flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-md shadow-emerald-500/20"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Ejecutando Modelos SWAT...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Ejecutar Simulación</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

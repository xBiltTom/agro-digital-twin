"use client";

import React, { useEffect, useState, useRef } from "react";
import { useAuth } from "../../../context/AuthContext";
import { api } from "../../../lib/api";
import {
  SimulationRun,
  SimulationResult,
  ClimateScenario,
  Watershed,
  TwinWebSocketTick,
  SwatResultsResponse,
  SwatRunType,
  ExternalModelInfo,
  DatasetInfo,
  CurrentFinalScientificReportResponse,
} from "../../../types/simulation";
import SwatRunEvidencePanel from "../../../components/scientific/SwatRunEvidencePanel";
import HypothesisValidationPanel from "../../../components/scientific/HypothesisValidationPanel";
import ClimateScenariosPanel from "../../../components/scientific/ClimateScenariosPanel";
import StatisticalBatteryPanel from "../../../components/scientific/StatisticalBatteryPanel";
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
  Activity,
  Scale,
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
  const [swatResults, setSwatResults] = useState<SwatResultsResponse | null>(null);
  const [scenarios, setScenarios] = useState<ClimateScenario[]>([]);
  const [watersheds, setWatersheds] = useState<Watershed[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, { status: string; evidence_type?: string }>>({});
  const [externalModels, setExternalModels] = useState<ExternalModelInfo[]>([]);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"RUNS" | "VALIDATION" | "SCENARIOS" | "STATISTICS">("RUNS");

  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New Simulation Form State
  const [formName, setFormName] = useState("Experimento multiescala de maíz");
  const [formWatershedId, setFormWatershedId] = useState("");
  const [formScenarioId, setFormScenarioId] = useState("");
  const [formStartDate, setFormStartDate] = useState("");
  const [formEndDate, setFormEndDate] = useState("");
  const [formStationId, setFormStationId] = useState("");
  const [formSeed, setFormSeed] = useState(42);
  const [formPlantCount, setFormPlantCount] = useState(1000);
  const [formClimateSource, setFormClimateSource] = useState<"SYNTHETIC" | "CMIP6_FILE" | "OBSERVED">("SYNTHETIC");
  const [formHydrologyBackend, setFormHydrologyBackend] = useState<"SIMPLIFIED" | "SWAT_PLUS">("SIMPLIFIED");
  const [formSwatRunType, setFormSwatRunType] = useState<SwatRunType>("SWAT_MULTISCALE_COUPLED");
  const [formExternalModel, setFormExternalModel] = useState("");
  const [formManagement, setFormManagement] = useState<"BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM">("BASELINE");
  const [formDatasetIds, setFormDatasetIds] = useState<string[]>([]);
  const [formDatasetRoles, setFormDatasetRoles] = useState<Record<string, "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY">>({});

  // Live WebSocket State
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [liveTick, setLiveTick] = useState<TwinWebSocketTick | null>(null);
  const [wsSpeed, setWsSpeed] = useState(1);
  const wsRef = useRef<WebSocket | null>(null);

  const canRunSimulations = hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"]);
  const isRealSwat = (sim: SimulationRun) => {
    const evidence = (sim.provenance as { evidence_type?: string } | undefined)?.evidence_type;
    return sim.hydrology_backend === "SWAT_PLUS" && ["REAL_SWAT_PLUS", "REAL_SWAT_PLUS_COUPLED"].includes(evidence ?? "");
  };

  // Carga inicial de datos
  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const [simsData, scenData, watersData, capabilityData, modelsData, datasetsData, finalReportData] = await Promise.all([
        api.getSimulations(),
        api.getClimateScenarios(),
        api.getWatersheds(),
        api.getCapabilities(),
        api.getExternalModels(),
        api.getDatasets(),
        api.getFinalScientificReport().catch(() => null),
      ]);
      setSimulations(simsData);
      setScenarios(scenData);
      setWatersheds(watersData);
      setCapabilities(capabilityData);
      setExternalModels(modelsData);
      setDatasets(datasetsData);
      setFinalReport(finalReportData);

      if (watersData.length > 0) {
        setFormWatershedId(watersData[0].id);
        const gauge = watersData[0].dem_metadata?.gauge;
        if (typeof gauge === "string") setFormStationId(gauge);
      }
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
    setSwatResults(null);
    // Desconectar WS previo si existía
    if (wsRef.current) {
      wsRef.current.close();
      setIsWsConnected(false);
      setLiveTick(null);
    }

    try {
      if (isRealSwat(sim)) {
        const normalizedSwat = await api.getSwatResults(sim.id);
        setSwatResults(normalizedSwat);
        setResults([]);
      } else {
        const dailyResults = await api.getSimulationResults(sim.id, sim.duration_days);
        setResults(dailyResults);
      }
    } catch (err: any) {
      console.error("Error al cargar resultados diarios:", err);
    } finally {
      setIsLoadingResults(false);
    }
  };

  const handleCreateSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    const durationDays = formStartDate && formEndDate
      ? Math.floor((Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000) + 1
      : 0;
    if (durationDays < 1) {
      setFeedbackMsg({ type: "error", text: "Selecciona un periodo inicial y final válido." });
      return;
    }
    setIsSubmitting(true);
    setFeedbackMsg(null);

    try {
      const newSim = await api.createSimulation({
        name: formName,
        watershed_id: formWatershedId,
        scenario_id: formScenarioId,
        duration_days: durationDays,
        seed: formSeed,
        parameters: {},
        mode: formHydrologyBackend === "SWAT_PLUS" ? "SWAT_PLUS" : "RESEARCH_MULTISCALE",
        plant_count: formPlantCount,
        hydrology_backend: formHydrologyBackend,
        external_model_id: formExternalModel || undefined,
        management_scenario: formManagement,
        climate_source: formClimateSource,
        dataset_ids: formDatasetIds,
        dataset_roles: formDatasetRoles,
        station_id: formStationId || undefined,
        start_date: formStartDate,
        end_date: formEndDate,
        swat_plus: formHydrologyBackend === "SWAT_PLUS" ? {
          run_type: formSwatRunType,
          output_frequency: "DAILY",
          warmup_period: 0,
          target_plant_name: "corn",
        } : undefined,
      });
      setSimulations([newSim, ...simulations]);
      setIsModalOpen(false);
      setFeedbackMsg({ type: "success", text: `Experimento "${newSim.name}" ejecutado y versionado.` });
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
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const token = localStorage.getItem("digitaltwin_token") || "";
      const wsUrl = `${apiUrl.replace(/^http/, "ws")}/twin/ws/${selectedSim.id}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsWsConnected(true);
        ws.send(JSON.stringify({ command: "play", speed: wsSpeed }));
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === "SIMULATION_PLAYBACK_TICK") {
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
  const monthlyComparisonData = selectedSim?.monthly_outputs ?? [];
  const isSelectedRealSwat = selectedSim ? isRealSwat(selectedSim) : false;
  const hasObservedForcing = datasets.some((dataset) => ["CHIRPS", "OBSERVED_CLIMATE"].includes(dataset.provider) && dataset.normalized_artifact_count > 0);
  const hasCmip6Forcing = datasets.some((dataset) => dataset.provider === "NEX-GDDP-CMIP6" && dataset.normalized_artifact_count > 0);

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              Experimento multiescala Planta → Cuenca
            </h1>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
            Clima → población de maíz → campo → HRU → hidrología. Cada corrida declara si usa el proxy legado o SWAT+ real.
          </p>
        </div>

        {canRunSimulations && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-zinc-950 text-xs font-semibold shadow-md shadow-emerald-500/20 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Nuevo experimento</span>
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

      {/* Tab Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-3">
        <button
          onClick={() => setActiveTab("RUNS")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "RUNS"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          <Play className="w-3.5 h-3.5" />
          <span>Simulador y Corridas Activas</span>
        </button>
        <button
          onClick={() => setActiveTab("VALIDATION")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "VALIDATION"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Validación e Hipótesis (H0/H1)</span>
        </button>
        <button
          onClick={() => setActiveTab("SCENARIOS")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "SCENARIOS"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          <SunMedium className="w-3.5 h-3.5" />
          <span>Escenarios Climáticos</span>
        </button>
        <button
          onClick={() => setActiveTab("STATISTICS")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "STATISTICS"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 hover:text-zinc-900 dark:hover:text-zinc-100"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Batería Estadística</span>
        </button>
      </div>

      {activeTab === "RUNS" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
        {Object.entries(capabilities).map(([name, item]) => (
          <div key={name} className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-3 bg-white dark:bg-zinc-950">
            <div className="text-[10px] uppercase font-mono text-zinc-500">{name.replaceAll("_", " ")}</div>
            <div className={`text-[11px] mt-1 font-bold ${item.status === "ACTIVE" ? "text-emerald-600" : "text-amber-600"}`}>{item.status}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
        {[`CLIMATE · ${selectedSim?.climate_source ?? "NOT_SELECTED"}`, `PLANT ×${selectedSim?.plant_count ?? 1000} · ${isSelectedRealSwat ? "FSPM" : "SIMPLIFIED"}`, "FIELD · DERIVED", `HRU · ${isSelectedRealSwat ? "SWAT+ REAL" : "COARSE PROXY"}`, `HYDROLOGY · ${selectedSim?.hydrology_backend ?? "NOT_SELECTED"}`, `USGS · ${selectedSim?.validation?.status ?? "NOT_LINKED"}`].map((stage, index) => (
          <React.Fragment key={stage}><span className="px-3 py-2 rounded-lg border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30">{stage}</span>{index < 5 && <span>→</span>}</React.Fragment>
        ))}
      </div>

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
                      {sim.climate_source || sim.scenario?.source_type || "NOT_DECLARED"}
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
              {isSelectedRealSwat && swatResults ? (
                <SwatRunEvidencePanel simulation={selectedSim} result={swatResults} />
              ) : (
                <>
              {/* Selected simulation card and persisted-result WebSocket playback */}
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
                    <span className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                      Manejo: {selectedSim.management_scenario} · Fuente climática: {selectedSim.climate_source} · Datos: {selectedSim.dataset_ids?.length ?? 0} artefacto(s)
                    </span>
                  </div>

                  {/* WebSocket playback controls; this is not live telemetry. */}
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
                      <span>{isWsConnected ? "Detener reproducción WS" : "Iniciar reproducción WS"}</span>
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

                {/* WebSocket playback ticker of persisted results (if active). */}
                {isWsConnected && liveTick && (
                  <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-50 via-white to-cyan-50 dark:from-emerald-950/40 dark:via-zinc-950 dark:to-cyan-950/40 border border-emerald-300 dark:border-emerald-500/40 grid grid-cols-2 sm:grid-cols-4 gap-3 animate-fadeIn shadow-sm">
                    <div className="col-span-full text-[10px] font-mono text-zinc-500 dark:text-zinc-400">
                      Reproducción cronológica de balance hídrico y estados fenológicos de la corrida.
                    </div>
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
                      <span className="text-[10px] uppercase font-mono text-teal-700 dark:text-teal-400 font-semibold">Hidrología (Cuenca)</span>
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
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Precipitación Total</span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">
                      {selectedSim.summary_metrics?.total_precip_mm ?? "-"} mm
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Rendimiento de cultivo</span>
                    <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400 mt-1 block">
                      {selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha?.toFixed?.(2) ?? "-"} t/ha
                    </span>
                    <span className="text-[9px] text-amber-700 dark:text-amber-300">DERIVED, no NASS observado</span>
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
                    <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 block">Interpretación científica</span>
                    <span className="text-xs font-bold text-amber-600 dark:text-amber-400 mt-1.5 block truncate">
                      {selectedSim.summary_metrics?.interpretation_status ?? "NOT_VALIDATED"}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <div className="font-mono text-emerald-600">PLANT → FIELD</div>
                    <div className="mt-2">{selectedSim.plant_count} plantas · LAI medio {Number(selectedSim.field_aggregates?.mean_lai ?? 0).toFixed(3)}</div>
                    <div>Raíz {Number(selectedSim.field_aggregates?.mean_root_depth_cm ?? 0).toFixed(1)} cm · estrés {Number(selectedSim.field_aggregates?.mean_stress ?? 0).toFixed(3)}</div>
                  </div>
                  <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <div className="font-mono text-cyan-600">FIELD → HRU</div>
                    <div className="mt-2">{selectedSim.hru_aggregates?.count ?? 0} HRUs · COARSE_HRU_PROXY</div>
                    <div>Fracción total {Number(selectedSim.hru_aggregates?.area_fraction_sum ?? 0).toFixed(2)}</div>
                  </div>
                  <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <div className="font-mono text-amber-600">VALIDATION</div>
                    <div className="mt-2">{selectedSim.validation?.interpretation ?? (isRealSwat(selectedSim) ? "SWAT+ VALIDATED" : "EVALUACIÓN EXPERIMENTAL")}</div>
                    <div>Meses alineados: {selectedSim.validation?.aligned_months ?? 0} · mejora {selectedSim.validation?.improvement_percent?.value?.toFixed?.(2) ?? "0.00"}%</div>
                  </div>
                </div>
                <details className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-3 text-[11px] text-zinc-600 dark:text-zinc-400">
                  <summary className="cursor-pointer font-mono text-zinc-800 dark:text-zinc-200">MANIFIESTO Y PROVENANCE DE LA CORRIDA</summary>
                  <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                    <span>Periodo: {selectedSim.start_date ?? "2015-01-01"} → {selectedSim.end_date ?? "2020-12-31"}</span>
                    <span>Estación USGS: {selectedSim.station_id ?? "05451210"} · seed {selectedSim.seed}</span>
                    <span>Datos: {Object.entries(selectedSim.dataset_roles ?? {}).map(([id, role]) => `${role} (${id.slice(0, 8)})`).join(", ") || "GridMET / CDL / USGS"}</span>
                    <span>ML: {selectedSim.ml_result?.status ?? "no seleccionado"} · entrenamiento {selectedSim.ml_result?.training_data_type ?? "-"}</span>
                  </div>
                  <p className="mt-2 text-zinc-600 dark:text-zinc-400">
                    {isRealSwat(selectedSim)
                      ? "Corrida física con SWAT+ 61.0.2 real sobre cuenca South Fork Iowa River con 32 HRUs de maíz informadas por FSPM."
                      : "Corrida con motor hidrológico integrado. Las corridas de validación de cuenca ejecutan el backend SWAT+ con acoplamiento FSPM."}
                  </p>
                </details>
              </div>

              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm dark:shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">Comparación mensual: Observado · Baseline · Twin · ML</h3>
                    <p className="text-[10px] text-zinc-500 mt-1">Las series solo aparecen cuando su fuente/modelo existe; no se imputan observaciones ausentes.</p>
                  </div>
                  <span className="text-[10px] font-mono text-amber-700 dark:text-amber-300">{selectedSim.validation?.interpretation ?? "NOT_VALIDATED"}</span>
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyComparisonData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" vertical={false} />
                      <XAxis dataKey="month" stroke="#71717a" fontSize={10} tickLine={false} />
                      <YAxis stroke="#71717a" fontSize={10} tickLine={false} label={{ value: "m³/s", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 10 }} />
                      <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }} />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      <Line type="monotone" dataKey="observed_streamflow_m3s" name="OBSERVED USGS" stroke="#111827" strokeWidth={2} dot={false} connectNulls={false} />
                      <Line type="monotone" dataKey="baseline_streamflow_m3s" name="BASELINE" stroke="#f97316" strokeWidth={1.8} dot={false} />
                      <Line type="monotone" dataKey="twin_streamflow_m3s" name="MULTISCALE TWIN" stroke="#059669" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="ML ASSISTED" stroke="#7c3aed" strokeWidth={1.8} strokeDasharray="4 3" dot={false} connectNulls={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Hidrograma de forcing declarado y caudal del twin simplificado. */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm dark:shadow-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Mountain className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                      Hidrograma: caudal simulado (m³/s) y precipitación de forzamiento (mm)
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">Escala Macro</span>
                </div>

                {isLoadingResults ? (
                  <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                    <Loader2 className="w-5 h-5 animate-spin mr-2 text-emerald-400" />
                    Cargando resultados de la simulación...
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
              )}
            </>
          ) : (
            <div className="p-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 text-center text-zinc-500 text-xs bg-white dark:bg-transparent">
              Selecciona una simulación de la lista izquierda para visualizar su análisis multiescala.
            </div>
          )}
        </div>
      </div>
        </>
      )}

      {activeTab === "VALIDATION" && (
        <HypothesisValidationPanel report={finalReport} />
      )}

      {activeTab === "SCENARIOS" && (
        <ClimateScenariosPanel report={finalReport} />
      )}

      {activeTab === "STATISTICS" && (
        <StatisticalBatteryPanel report={finalReport} />
      )}

      {/* Modal: New Simulation Run */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-2xl flex flex-col gap-4 text-zinc-900 dark:text-zinc-100">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                  Configurar experimento multiescala
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
                    Cuenca representativa
                  </label>
                  <select
                    value={formWatershedId}
                    onChange={(e) => {
                      const watershedId = e.target.value;
                      setFormWatershedId(watershedId);
                      const gauge = watersheds.find((item) => item.id === watershedId)?.dem_metadata?.gauge;
                      setFormStationId(typeof gauge === "string" ? gauge : "");
                    }}
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
                    Escenario de perturbación
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

              {formHydrologyBackend === "SWAT_PLUS" && (
                <div className="rounded-xl border border-teal-300 bg-teal-50/70 p-3 dark:border-teal-800 dark:bg-teal-950/20">
                  <label className="block font-mono uppercase text-[10px] text-teal-800 dark:text-teal-300">Modo de experimento SWAT+</label>
                  <select value={formSwatRunType} onChange={(e) => setFormSwatRunType(e.target.value as SwatRunType)} className="mt-2 w-full rounded-lg border border-teal-300 bg-white px-3 py-2.5 text-xs text-zinc-900 dark:border-teal-800 dark:bg-zinc-950 dark:text-zinc-200">
                    <option value="SWAT_MULTISCALE_COUPLED">SWAT_MULTISCALE_COUPLED — crea primero el baseline pareado</option>
                    <option value="SWAT_STANDARD_BASELINE">SWAT_STANDARD_BASELINE — control SWAT+ sin FSPM</option>
                  </select>
                  <p className="mt-2 text-[10px] text-teal-800 dark:text-teal-300">Se usa el proyecto, engine y workspace configurados en el servidor. El modo acoplado conserva forcing y periodo y solo modifica `plants.plt` dentro de una copia aislada.</p>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Fuente climática</label>
                  <select value={formClimateSource} onChange={(e) => setFormClimateSource(e.target.value as "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED")} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <option value="SYNTHETIC">SYNTHETIC — fallback reproducible</option>
                    <option value="OBSERVED" disabled={!hasObservedForcing}>OBSERVED — {hasObservedForcing ? "FORCING disponible" : "NOT_AVAILABLE: falta CHIRPS normalizado"}</option>
                    <option value="CMIP6_FILE" disabled={!hasCmip6Forcing}>CMIP6_FILE — {hasCmip6Forcing ? "FORCING disponible" : "NOT_AVAILABLE: falta NEX-GDDP normalizado"}</option>
                  </select>
                </div>
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Backend hidrológico</label>
                  <select value={formHydrologyBackend} onChange={(e) => setFormHydrologyBackend(e.target.value as "SIMPLIFIED" | "SWAT_PLUS")} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <option value="SIMPLIFIED">SIMPLIFIED — por HRU proxy</option>
                    <option value="SWAT_PLUS" disabled={capabilities.swat_plus?.status !== "ACTIVE"}>SWAT_PLUS — {capabilities.swat_plus?.status ?? "NOT_AVAILABLE"}</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Estación USGS</label>
                  <input type="text" inputMode="numeric" pattern="\d{8,15}" value={formStationId} onChange={(e) => setFormStationId(e.target.value)} placeholder="Selecciona una estación" className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800" />
                </div>
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Inicio</label>
                  <input type="date" required value={formStartDate} onChange={(e) => setFormStartDate(e.target.value)} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800" />
                </div>
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Fin</label>
                  <input type="date" required value={formEndDate} onChange={(e) => setFormEndDate(e.target.value)} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Seed reproducible</label>
                  <input type="number" min={0} value={formSeed} onChange={(e) => setFormSeed(Number(e.target.value))} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800" />
                </div>
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Plantas</label>
                  <input type="number" min={1} max={10000} value={formPlantCount} onChange={(e) => setFormPlantCount(Number(e.target.value))} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800" />
                </div>
              </div>

              <div>
                <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">Manejo agrícola MVP</label>
                <select value={formManagement} onChange={(e) => setFormManagement(e.target.value as "BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM")} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                  <option value="BASELINE">BASELINE — maíz</option>
                  <option value="NO_TILL">NO_TILL — proxy CN −4</option>
                  <option value="MAIZE_TO_SORGHUM">MAIZE_TO_SORGHUM — proxy de sustitución</option>
                </select>
                <p className="mt-1 text-[10px] text-zinc-500">Los ajustes son proxies reproducibles del MVP; no operaciones calibradas de SWAT+.</p>
              </div>

              <fieldset className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-3">
                <legend className="px-1 font-mono uppercase text-[10px] text-zinc-600 dark:text-zinc-400">Artefactos y rol dentro del experimento</legend>
                {datasets.length === 0 ? (
                  <p className="text-[11px] text-zinc-500">No hay artefactos externos registrados. Solo está disponible SYNTHETIC.</p>
                ) : datasets.map((dataset) => (
                  <div key={dataset.id} className="flex items-center gap-2 py-1 text-[11px] text-zinc-700 dark:text-zinc-300">
                    <input type="checkbox" checked={formDatasetIds.includes(dataset.id)} onChange={(event) => {
                      setFormDatasetIds((current) => event.target.checked ? [...current, dataset.id] : current.filter((id) => id !== dataset.id));
                      setFormDatasetRoles((current) => {
                        const next = { ...current };
                        if (event.target.checked) next[dataset.id] = "CONTEXT_ONLY";
                        else delete next[dataset.id];
                        return next;
                      });
                    }} />
                    <span className="flex-1">{dataset.provider}: {dataset.dataset_name} · {dataset.evidence_type}</span>
                    {formDatasetIds.includes(dataset.id) && <select value={formDatasetRoles[dataset.id] ?? "CONTEXT_ONLY"} onChange={(event) => setFormDatasetRoles((current) => ({ ...current, [dataset.id]: event.target.value as "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY" }))} className="rounded border border-zinc-300 dark:border-zinc-700 bg-transparent px-1 py-0.5 text-[10px]">
                      <option value="FORCING">FORCING</option><option value="OBSERVATION">OBSERVATION</option><option value="VALIDATION">VALIDATION</option><option value="SOIL_INPUT">SOIL_INPUT</option><option value="LAND_COVER">LAND_COVER</option><option value="YIELD_OBSERVATION">YIELD_OBSERVATION</option><option value="CONTEXT_ONLY">CONTEXT_ONLY</option>
                    </select>}
                  </div>
                ))}
                <p className="mt-1 text-[10px] text-amber-700 dark:text-amber-300">OBSERVED y CMIP6_FILE requieren exactamente un artefacto FORCING normalizado. USGS debe ser OBSERVATION o VALIDATION.</p>
              </fieldset>

              <div>
                <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-medium">ModelBundle externo opcional</label>
                <select value={formExternalModel} onChange={(e) => setFormExternalModel(e.target.value)} className="w-full px-3 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                  <option value="">No usar modelo externo</option>
                  {externalModels.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.target} · {model.framework}</option>)}
                </select>
              </div>

              <div className="p-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300">
                El periodo, la estación y los roles de datos quedan en el manifiesto. El riego sigue deshabilitado porque el modelo no implementa planes de manejo.
              </div>

              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-600 dark:text-zinc-400 flex flex-col gap-1">
                <span className="font-semibold text-zinc-800 dark:text-zinc-300">{formHydrologyBackend === "SWAT_PLUS" ? "Acoplamiento Multiescala FSPM → SWAT+" : "Población FSPM de maíz y balance hídrico"}</span>
                <span>{formHydrologyBackend === "SWAT_PLUS" ? "Calcula la población FSPM (1000 plantas), mapea parámetros fenológicos a plants.plt en un workspace aislado y ejecuta el modelo físico SWAT+." : "Calcula la población de plantas y ejecuta el balance ecohidrológico acoplado."}</span>
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
                      <span>{formHydrologyBackend === "SWAT_PLUS" ? "Ejecutando SWAT+ acoplado..." : "Ejecutando simulación..."}</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Ejecutar experimento</span>
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

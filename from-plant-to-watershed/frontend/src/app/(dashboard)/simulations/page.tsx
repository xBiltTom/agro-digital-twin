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
import { AIInsightsCard } from "../../../components/simulations/AIInsightsCard";
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
  Info,
  Leaf,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Waves,
  Filter,
  Sparkles,
  Check,
  Gauge,
  Search,
  X,
  Database,
  Zap,
  Clock,
  CalendarRange,
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
  AreaChart,
  ReferenceLine,
} from "recharts";

const CAPABILITY_INFO: Record<string, { label: string; desc: string; category: "Física & Dinámica" | "Datos & Sensores" | "Inteligencia Artificial" | "Infraestructura" }> = {
  postgresql: { label: "Base de Datos Relacional", desc: "Almacenamiento persistente de series temporales de clima, cuencas y corridas", category: "Infraestructura" },
  fastapi: { label: "Motor API Asíncrono", desc: "Orquestación de ejecuciones concurrentes y streaming de gemelo digital", category: "Infraestructura" },
  nextjs: { label: "Panel React Dashboard", desc: "Sincronización reactiva de estado y visualización multiescala", category: "Infraestructura" },
  usgs: { label: "Estación USGS 05451210", desc: "Aforo hidrográfico observado del río South Fork Iowa para contraste y calibración", category: "Datos & Sensores" },
  dataset_registry: { label: "Catálogo Espacial y Satelital", desc: "GridMET, CDL, SSURGO y CHIRPS con verificación criptográfica de procedencia", category: "Datos & Sensores" },
  cmip6: { label: "Proyecciones CMIP6 (NEX-GDDP)", desc: "Escenarios de cambio climático SSP2-4.5 y SSP5-8.5 desagregados espacialmente", category: "Datos & Sensores" },
  plant_population: { label: "Fisiología Individual de Maíz", desc: "Modelado micro: transpiración foliar, balance hídrico, LAI y dinámica de biomasa", category: "Física & Dinámica" },
  plant_to_field: { label: "Agregación Planta → Parcela", desc: "Escalamiento espacial y promediado de biomasa y estrés de la población", category: "Física & Dinámica" },
  field_to_hru: { label: "Mapeo Parcela → HRU Cuenca", desc: "Transferencia de parámetros a Unidades de Respuesta Hidrológica de suelo", category: "Física & Dinámica" },
  simplified_hydrology: { label: "Balance Hídrico Feddes/CN", desc: "Infiltración SCS-CN, absorción radicular de Feddes y percolación en el perfil", category: "Física & Dinámica" },
  swat_plus: { label: "Simulador SWAT+ v2024", desc: "Modelo físico semidistribuido de cuenca acoplado con el gemelo de cultivo", category: "Física & Dinámica" },
  ml_joblib: { label: "Módulo Híbrido Scikit-Learn", desc: "Modelos supervisados de aceleración y corrección de sesgo hidrológico", category: "Inteligencia Artificial" },
  ml_keras: { label: "Redes Profundas TensorFlow/Keras", desc: "Modelos neuronales recurrentes (LSTM) para predicción de caudales", category: "Inteligencia Artificial" },
  ml_hybrid: { label: "Acoplamiento Físico-ML", desc: "Hibridación que combina leyes de conservación física con residuales ML", category: "Inteligencia Artificial" },
  external_ml: { label: "Modelos ML Externos", desc: "Repositorio de artefactos serializados ONNX / PyTorch para ensamble", category: "Inteligencia Artificial" },
};

const DEFAULT_SIMPLIFIED_PARAMETERS = {
  base_kc: 1.05,
  max_root_depth_cm: 120,
  curve_number: 74,
  initial_soil_moisture_vol: 24.5,
};

interface PeriodPreset {
  id: "3M" | "4M" | "6M" | "1Y" | "5Y" | "CUSTOM";
  label: string;
  durationBadge: string;
  days: number;
  monthsApprox: number;
  startDate: string;
  endDate: string;
  shortDesc: string;
  scientificPurpose: string;
  agronomicScope: string;
  protocolBadge: string;
}

const SIMULATION_PERIOD_PRESETS: PeriodPreset[] = [
  {
    id: "3M",
    label: "3 Meses",
    durationBadge: "92 días",
    days: 92,
    monthsApprox: 3,
    startDate: "2018-06-01",
    endDate: "2018-08-31",
    shortDesc: "Ventana crítica de floración y llenado de grano (Jun–Ago)",
    scientificPurpose: "Evalúa la máxima demanda transpiratoria y la sensibilidad de Sobol sobre el índice de estrés hídrico CWSI.",
    agronomicScope: "Floración (VT) a llenado de grano (R1–R5)",
    protocolBadge: "Estrés y Transpiración",
  },
  {
    id: "4M",
    label: "4 Meses (Ciclo Maíz)",
    durationBadge: "123 días",
    days: 123,
    monthsApprox: 4,
    startDate: "2018-05-01",
    endDate: "2018-08-31",
    shortDesc: "Ciclo fenológico completo del cultivo de maíz (May–Ago)",
    scientificPurpose: "Modela las 1,000 plantas FSPM desde emergencia hasta madurez para contrastar biomasa con rendimientos USDA NASS.",
    agronomicScope: "Emergencia (VE) a madurez fisiológica (R6)",
    protocolBadge: "FSPM Completo",
  },
  {
    id: "6M",
    label: "6 Meses",
    durationBadge: "183 días",
    days: 183,
    monthsApprox: 6,
    startDate: "2018-04-01",
    endDate: "2018-09-30",
    shortDesc: "Temporada agronómica estival completa (Abr–Sep)",
    scientificPurpose: "Permite evaluar la respuesta hidrológica del suelo ante prácticas de manejo como Siembra Directa (No-Till).",
    agronomicScope: "Siembra, desarrollo vegetativo y cosecha",
    protocolBadge: "Manejo y Suelos",
  },
  {
    id: "1Y",
    label: "1 Año Completo",
    durationBadge: "365 días",
    days: 365,
    monthsApprox: 12,
    startDate: "2018-01-01",
    endDate: "2018-12-31",
    shortDesc: "Año hidrológico continuo (Ene–Dic)",
    scientificPurpose: "Cierra el balance hídrico completo de la cuenca: precipitación, evapotranspiración, percolación y escorrentía.",
    agronomicScope: "Ciclo hidrológico con recarga invernal y estiaje",
    protocolBadge: "Balance Hídrico",
  },
  {
    id: "5Y",
    label: "5 Años (Validación H1)",
    durationBadge: "2,192 días",
    days: 2192,
    monthsApprox: 72,
    startDate: "2015-01-01",
    endDate: "2020-12-31",
    shortDesc: "Horizonte multianual del protocolo (2015–2020)",
    scientificPurpose: "Sustenta el contraste formal de la Hipótesis H1 de la Ficha Técnica: reducción de RMSE mensual ≥15% contra aforo USGS 05451210.",
    agronomicScope: "Serie histórica multianual con variabilidad climática",
    protocolBadge: "Validación H0 / H1",
  },
];

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
  const [chartViewMode, setChartViewMode] = useState<"ALL" | "STREAMFLOW" | "PLANT" | "SOIL" | "MONTHLY">("ALL");
  const [showCapabilities, setShowCapabilities] = useState(false);
  const [simSearchTerm, setSimSearchTerm] = useState("");
  const [simFilterModel, setSimFilterModel] = useState<"ALL" | "TWIN" | "SWAT">("ALL");

  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New Simulation Form State
  const [formName, setFormName] = useState("Experimento multiescala de maíz");
  const [formWatershedId, setFormWatershedId] = useState("");
  const [formScenarioId, setFormScenarioId] = useState("");
  const [selectedPeriodPreset, setSelectedPeriodPreset] = useState<"3M" | "4M" | "6M" | "1Y" | "5Y" | "CUSTOM">("3M");
  const [formStartDate, setFormStartDate] = useState("2018-06-01");
  const [formEndDate, setFormEndDate] = useState("2018-08-31");
  const [formStationId, setFormStationId] = useState("");
  const [formSeed, setFormSeed] = useState(42);
  const [formPlantCount, setFormPlantCount] = useState(1000);
  const [formClimateSource, setFormClimateSource] = useState<"SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "SWAT_PROJECT">("SYNTHETIC");
  const [formHydrologyBackend, setFormHydrologyBackend] = useState<"SIMPLIFIED" | "SWAT_PLUS">("SIMPLIFIED");
  const [formSwatRunType, setFormSwatRunType] = useState<SwatRunType>("SWAT_MULTISCALE_COUPLED");
  const [formExternalModel, setFormExternalModel] = useState("");
  const [formManagement, setFormManagement] = useState<"BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM">("BASELINE");
  const [formParameters, setFormParameters] = useState(DEFAULT_SIMPLIFIED_PARAMETERS);
  const [formDatasetIds, setFormDatasetIds] = useState<string[]>([]);
  const [formDatasetRoles, setFormDatasetRoles] = useState<Record<string, "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY">>({});

  // Live WebSocket State
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [liveTick, setLiveTick] = useState<TwinWebSocketTick | null>(null);
  const [wsSpeed, setWsSpeed] = useState(1);
  const wsRef = useRef<WebSocket | null>(null);

  const canRunSimulations = hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"]);
  const usesSimplifiedModel = formHydrologyBackend === "SIMPLIFIED";
  const isRealSwat = (sim: SimulationRun) => {
    const evidence = (sim.provenance as { evidence_type?: string } | undefined)?.evidence_type;
    return sim.hydrology_backend === "SWAT_PLUS" && ["REAL_SWAT_PLUS", "REAL_SWAT_PLUS_COUPLED"].includes(evidence ?? "");
  };

  const changeHydrologyBackend = (backend: "SIMPLIFIED" | "SWAT_PLUS") => {
    setFormHydrologyBackend(backend);
    if (backend === "SWAT_PLUS") {
      // These switches are not applied by the current SWAT+ adapter.
      setFormManagement("BASELINE");
      setFormClimateSource("SWAT_PROJECT");
      setFormExternalModel("");
      setFormDatasetRoles((current) => Object.fromEntries(Object.keys(current).map((id) => [id, "CONTEXT_ONLY"])) as typeof current);
    } else if (formClimateSource === "SWAT_PROJECT") {
      setFormClimateSource("SYNTHETIC");
    }
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

  const handleSelectPeriodPreset = (preset: PeriodPreset) => {
    setSelectedPeriodPreset(preset.id);
    setFormStartDate(preset.startDate);
    setFormEndDate(preset.endDate);
  };

  const handleStartDateChange = (newStart: string) => {
    setFormStartDate(newStart);
    const preset = SIMULATION_PERIOD_PRESETS.find((p) => p.id === selectedPeriodPreset);
    if (preset && newStart) {
      const startDateObj = new Date(`${newStart}T00:00:00Z`);
      if (!isNaN(startDateObj.getTime())) {
        const endDateObj = new Date(startDateObj.getTime() + (preset.days - 1) * 86_400_000);
        setFormEndDate(endDateObj.toISOString().split("T")[0]);
        return;
      }
    }
    checkPresetMatch(newStart, formEndDate);
  };

  const handleEndDateChange = (newEnd: string) => {
    setFormEndDate(newEnd);
    checkPresetMatch(formStartDate, newEnd);
  };

  const checkPresetMatch = (startStr: string, endStr: string) => {
    if (!startStr || !endStr) {
      setSelectedPeriodPreset("CUSTOM");
      return;
    }
    const days = Math.floor((Date.parse(`${endStr}T00:00:00Z`) - Date.parse(`${startStr}T00:00:00Z`)) / 86_400_000) + 1;
    const match = SIMULATION_PERIOD_PRESETS.find((p) => Math.abs(p.days - days) <= 2);
    if (match) {
      setSelectedPeriodPreset(match.id);
    } else {
      setSelectedPeriodPreset("CUSTOM");
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
    const selectedScenario = scenarios.find((scenario) => scenario.id === formScenarioId);
    const usesExternalForcing = formClimateSource === "OBSERVED" || formClimateSource === "CMIP6_FILE";
    if (usesExternalForcing && selectedScenario && (selectedScenario.temp_anomaly_c !== 0 || selectedScenario.precip_factor !== 1)) {
      setFeedbackMsg({ type: "error", text: "El forcing externo ya contiene su señal climática. Selecciona un escenario neutro (0 °C, precipitación ×1) hasta implementar transformaciones climáticas." });
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
        // The simplified route consumes these values. SWAT+ has its own
        // documented mapper and must not receive inert controls from this form.
        parameters: usesSimplifiedModel ? formParameters : {},
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
          outlet_unit: "153",
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

  const filteredSimulations = simulations.filter((sim) => {
    const term = simSearchTerm.trim().toLowerCase();
    const matchesSearch =
      !term ||
      sim.name.toLowerCase().includes(term) ||
      (sim.scenario?.name?.toLowerCase().includes(term) ?? false) ||
      (sim.climate_source?.toLowerCase().includes(term) ?? false) ||
      (sim.station_id?.includes(term) ?? false) ||
      (sim.id?.toLowerCase().includes(term) ?? false);
    const matchesModel =
      simFilterModel === "ALL"
        ? true
        : simFilterModel === "SWAT"
        ? isRealSwat(sim)
        : !isRealSwat(sim);
    return matchesSearch && matchesModel;
  });

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
            Configura una corrida, revisa qué datos se usaron y entiende cómo los cambios en el cultivo llegan al agua de la cuenca.
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

      {/* Tab Navigation Segmented Bar */}
      <div className="flex flex-wrap items-center gap-1.5 p-1.5 rounded-2xl bg-zinc-100 dark:bg-zinc-900/90 border border-zinc-200 dark:border-zinc-800">
        <button
          onClick={() => setActiveTab("RUNS")}
          className={`flex-1 min-w-[180px] px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
            activeTab === "RUNS"
              ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-sm border border-zinc-200/60 dark:border-zinc-700/60 font-bold"
              : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/40"
          }`}
        >
          <Play className="w-3.5 h-3.5 shrink-0" />
          <div className="flex flex-col items-start leading-tight">
            <span>Corridas y Resultados</span>
            <span className="text-[10px] font-normal text-zinc-400 dark:text-zinc-500">
              Micro → Macro · Series Diarias
            </span>
          </div>
        </button>

        <button
          onClick={() => setActiveTab("VALIDATION")}
          className={`flex-1 min-w-[180px] px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
            activeTab === "VALIDATION"
              ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-sm border border-zinc-200/60 dark:border-zinc-700/60 font-bold"
              : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/40"
          }`}
        >
          <Scale className="w-3.5 h-3.5 shrink-0" />
          <div className="flex flex-col items-start leading-tight">
            <span>Validación e Hipótesis</span>
            <span className="text-[10px] font-normal text-zinc-400 dark:text-zinc-500">
              H₀ vs H₁ · NSE, KGE, PBIAS
            </span>
          </div>
        </button>

        <button
          onClick={() => setActiveTab("SCENARIOS")}
          className={`flex-1 min-w-[180px] px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
            activeTab === "SCENARIOS"
              ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-sm border border-zinc-200/60 dark:border-zinc-700/60 font-bold"
              : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/40"
          }`}
        >
          <SunMedium className="w-3.5 h-3.5 shrink-0" />
          <div className="flex flex-col items-start leading-tight">
            <span>Escenarios Climáticos</span>
            <span className="text-[10px] font-normal text-zinc-400 dark:text-zinc-500">
              SSP2-4.5 / SSP5-8.5 · Manejo
            </span>
          </div>
        </button>

        <button
          onClick={() => setActiveTab("STATISTICS")}
          className={`flex-1 min-w-[180px] px-3.5 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 ${
            activeTab === "STATISTICS"
              ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-sm border border-zinc-200/60 dark:border-zinc-700/60 font-bold"
              : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/40"
          }`}
        >
          <Activity className="w-3.5 h-3.5 shrink-0" />
          <div className="flex flex-col items-start leading-tight">
            <span>Batería Estadística</span>
            <span className="text-[10px] font-normal text-zinc-400 dark:text-zinc-500">
              Sobol, KS, Wilcoxon, Bootstrap
            </span>
          </div>
        </button>
      </div>

      {activeTab === "RUNS" && (
        <>
          {/* Hero: 5-Stage Multiscale Coupling Architecture */}
          <section className="rounded-2xl border border-emerald-200/80 dark:border-emerald-900/50 bg-white dark:bg-zinc-900/70 p-5 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-100 dark:border-zinc-800">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-200 dark:border-emerald-800/60">
                  <Leaf className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    Arquitectura de Acoplamiento Multiescala: ¿Cómo viaja el agua de la Planta a la Cuenca?
                  </h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    El clima impulsa la transpiración foliar; las raíces absorben agua del perfil edáfico; y el balance de humedad resultante define la escorrentía superficial y el flujo base hacia el río.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setShowCapabilities(!showCapabilities)}
                className="self-start md:self-auto flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
              >
                <Layers className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Capacidades del Sistema ({Object.values(capabilities).filter(c => c.status === "ACTIVE" || c.status === "ACTIVE_IN_STACK" || c.status === "READY").length}/{Object.keys(capabilities).length || 14})</span>
                {showCapabilities ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* 5-Step Visual Multiscale Pipeline */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-5 gap-3">
              <div className="p-3.5 rounded-xl border border-sky-200 dark:border-sky-900/50 bg-sky-50/50 dark:bg-sky-950/20 flex flex-col justify-between">
                <div className="flex items-center justify-between text-sky-700 dark:text-sky-400 mb-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider">1. Clima & Forzamiento</span>
                  <SunMedium className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  {selectedSim?.climate_source ?? "GridMET / Sintético"}
                </div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Lluvia, T° y demanda evaporativa (ET0) que aportan agua y radiación solar al ecosistema.
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/50 dark:bg-emerald-950/20 flex flex-col justify-between">
                <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400 mb-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider">2. Micro (Planta de Maíz)</span>
                  <Sprout className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  {selectedSim?.plant_count ?? 1000} plantas individuales
                </div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Transpiración estomática, succión de savia por xilema (cm/h) y desarrollo del índice foliar (LAI).
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/50 dark:bg-amber-950/20 flex flex-col justify-between">
                <div className="flex items-center justify-between text-amber-700 dark:text-amber-400 mb-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider">3. Meso (Suelo & Raíces)</span>
                  <Droplets className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  Absorción Feddes & Estrés
                </div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Humedad volumétrica del perfil θ (%), índice de estrés CWSI y recarga por percolación profunda.
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-teal-200 dark:border-teal-900/50 bg-teal-50/50 dark:bg-teal-950/20 flex flex-col justify-between">
                <div className="flex items-center justify-between text-teal-700 dark:text-teal-400 mb-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider">4. Macro (Cuenca)</span>
                  <Mountain className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  {isSelectedRealSwat ? "SWAT+ Hidrología Física" : `${selectedSim?.hru_aggregates?.count ?? 6} HRUs Agregadas`}
                </div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Escorrentía superficial (SCS-CN), retención edáfica y enrutamiento por red de drenaje.
                </div>
              </div>

              <div className="p-3.5 rounded-xl border border-indigo-200 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-950/20 flex flex-col justify-between">
                <div className="flex items-center justify-between text-indigo-700 dark:text-indigo-400 mb-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider">5. Aforo & Salida</span>
                  <Waves className="w-3.5 h-3.5" />
                </div>
                <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  USGS 05451210
                </div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Caudal descargado en South Fork Iowa: evaluación de precisión empírica y balance hídrico final.
                </div>
              </div>
            </div>

            {/* Collapsible Technical Capabilities Drawer */}
            {showCapabilities && (
              <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 animate-fadeIn">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-3">
                  <span className="text-xs font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                    Módulos y Componentes Técnicos del Sistema
                  </span>
                  <span className="text-[10px] text-zinc-500 dark:text-zinc-400 font-mono">
                    Auditoría de estado vía <code className="bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded text-emerald-600">GET /api/v1/system/capabilities</code>
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                  {Object.entries(capabilities).map(([key, item]) => {
                    const info = CAPABILITY_INFO[key] || {
                      label: key.replaceAll("_", " "),
                      desc: `Estado del componente: ${item.status}`,
                      category: "Infraestructura",
                    };
                    const isActive = item.status === "ACTIVE" || item.status === "ACTIVE_IN_STACK" || item.status === "READY";
                    return (
                      <div
                        key={key}
                        className="p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/50 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                              {info.label}
                            </span>
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold shrink-0 ${
                                isActive
                                  ? "bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                                  : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border border-zinc-200 dark:border-zinc-700"
                              }`}
                            >
                              {item.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1.5 leading-relaxed">
                            {info.desc}
                          </p>
                        </div>
                        <div className="mt-3 pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500">
                          <span className="font-semibold text-zinc-600 dark:text-zinc-300">{info.category}</span>
                          {item.evidence_type && (
                            <span className="text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-800/40">{item.evidence_type}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          {/* Grid: Simulations List (Left) + Detail & Charts (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Simulations List */}
            <div className="lg:col-span-4 flex flex-col gap-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono uppercase text-zinc-700 dark:text-zinc-300 font-bold tracking-wide">
                    Experimentos Registrados
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-200/80 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-semibold">
                    {filteredSimulations.length}
                    {filteredSimulations.length !== simulations.length ? ` / ${simulations.length}` : ""}
                  </span>
                </div>
                <button
                  onClick={loadInitialData}
                  className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
                  title="Refrescar lista de simulaciones"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                </button>
              </div>

              {/* Búsqueda y Filtros Rápidos */}
              <div className="flex flex-col gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  <input
                    type="text"
                    value={simSearchTerm}
                    onChange={(e) => setSimSearchTerm(e.target.value)}
                    placeholder="Buscar experimento, escenario..."
                    className="w-full pl-8 pr-7 py-1.5 text-xs rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                  />
                  {simSearchTerm && (
                    <button
                      type="button"
                      onClick={() => setSimSearchTerm("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 p-0.5 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {/* Filtro por motor / backend */}
                <div className="flex items-center gap-1 p-1 bg-zinc-100 dark:bg-zinc-900/80 rounded-xl border border-zinc-200 dark:border-zinc-800 text-[11px] font-medium">
                  <button
                    type="button"
                    onClick={() => setSimFilterModel("ALL")}
                    className={`flex-1 py-1 px-2 rounded-lg text-center transition cursor-pointer ${
                      simFilterModel === "ALL"
                        ? "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-xs font-semibold"
                        : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
                    }`}
                  >
                    Todos ({simulations.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setSimFilterModel("TWIN")}
                    className={`flex-1 py-1 px-2 rounded-lg text-center transition cursor-pointer flex items-center justify-center gap-1 ${
                      simFilterModel === "TWIN"
                        ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-xs font-semibold"
                        : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
                    }`}
                  >
                    <Sprout className="w-3 h-3" />
                    <span>Gemelo ({simulations.filter((s) => !isRealSwat(s)).length})</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSimFilterModel("SWAT")}
                    className={`flex-1 py-1 px-2 rounded-lg text-center transition cursor-pointer flex items-center justify-center gap-1 ${
                      simFilterModel === "SWAT"
                        ? "bg-white dark:bg-zinc-800 text-purple-700 dark:text-purple-400 shadow-xs font-semibold"
                        : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200"
                    }`}
                  >
                    <Waves className="w-3 h-3" />
                    <span>SWAT+ ({simulations.filter((s) => isRealSwat(s)).length})</span>
                  </button>
                </div>
              </div>

              {/* Lista con scroll */}
              <div className="flex flex-col gap-2.5 max-h-[820px] overflow-y-auto pr-1">
                {filteredSimulations.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col items-center gap-2">
                    <AlertCircle className="w-6 h-6 text-zinc-400" />
                    <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      No se encontraron experimentos
                    </span>
                    <p className="text-[11px] text-zinc-400 max-w-xs">
                      Ninguna simulación coincide con el criterio de búsqueda o filtro seleccionado.
                    </p>
                    {(simSearchTerm || simFilterModel !== "ALL") && (
                      <button
                        type="button"
                        onClick={() => {
                          setSimSearchTerm("");
                          setSimFilterModel("ALL");
                        }}
                        className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 underline cursor-pointer"
                      >
                        Limpiar filtros
                      </button>
                    )}
                  </div>
                ) : (
                  filteredSimulations.map((sim) => {
                    const isSelected = selectedSim?.id === sim.id;
                    const simIsSwat = isRealSwat(sim);
                    const isLatest = sim.id === simulations[0]?.id;
                    return (
                      <div
                        key={sim.id}
                        onClick={() => selectSimulation(sim)}
                        className={`p-4 rounded-xl border text-left cursor-pointer transition relative flex flex-col gap-2.5 ${
                          isSelected
                            ? "bg-emerald-50/70 dark:bg-zinc-900 border-emerald-500 dark:border-emerald-500 shadow-md ring-2 ring-emerald-500/20"
                            : "bg-white dark:bg-zinc-950/60 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50/80 dark:hover:bg-zinc-900/40 shadow-xs"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex flex-col flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {isLatest && (
                                <span className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                                  <Zap className="w-2.5 h-2.5 text-amber-600 fill-amber-500" />
                                  Más reciente
                                </span>
                              )}
                              <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 truncate">
                                {sim.name}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] text-zinc-500 dark:text-zinc-400 mt-1">
                              <span className="inline-flex items-center gap-1">
                                <Clock className="w-3 h-3 text-zinc-400" />
                                {sim.duration_days} días
                              </span>
                              <span>·</span>
                              <span className="inline-flex items-center gap-1">
                                <Sprout className="w-3 h-3 text-zinc-400" />
                                {sim.plant_count?.toLocaleString?.() ?? sim.plant_count} plantas
                              </span>
                              {sim.climate_source && (
                                <>
                                  <span>·</span>
                                  <span className="font-mono text-[9px] px-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                                    {sim.climate_source}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold shrink-0 border uppercase tracking-wider ${
                              simIsSwat
                                ? "bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-800"
                                : "bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                            }`}
                          >
                            {simIsSwat ? "SWAT+ FÍSICO" : "GEMELO MULTIESCALA"}
                          </span>
                        </div>

                        {(() => {
                          const precipVal = sim.summary_metrics?.total_precip_mm ?? sim.summary_metrics?.total_precipitation_mm;
                          const runoffVal = sim.summary_metrics?.total_runoff_mm ?? sim.summary_metrics?.total_surface_runoff_mm;
                          const col1Label = precipVal != null ? "Lluvia" : (runoffVal != null ? "Escorrentía" : "Lluvia");
                          const col1Value = precipVal != null
                            ? `${Number(precipVal).toFixed(0)} mm`
                            : (runoffVal != null ? `${Number(runoffVal).toFixed(0)} mm` : "—");

                          const dischargeHm3 = sim.summary_metrics?.total_discharge_hm3 != null
                            ? Number(sim.summary_metrics.total_discharge_hm3)
                            : (sim.summary_metrics?.water_balance?.mean_streamflow_m3s != null && sim.duration_days
                              ? (Number(sim.summary_metrics.water_balance.mean_streamflow_m3s) * sim.duration_days * 86400) / 1_000_000
                              : (runoffVal != null ? (Number(runoffVal) * 580.15) / 1000 : null));
                          const col2Value = dischargeHm3 != null ? `${dischargeHm3.toFixed(1)} hm³` : "—";

                          const cwsiVal = sim.summary_metrics?.mean_cwsi ?? sim.field_aggregates?.mean_water_stress;
                          const etVal = sim.summary_metrics?.total_evapotranspiration_mm ?? sim.summary_metrics?.total_actual_et_mm;
                          const col3Label = cwsiVal != null ? "CWSI Medio" : (etVal != null ? "ET Real" : "CWSI");
                          const col3Value = cwsiVal != null
                            ? Number(cwsiVal).toFixed(3)
                            : (etVal != null ? `${Number(etVal).toFixed(0)} mm` : "—");
                          const col3IsGood = cwsiVal != null ? Number(cwsiVal) < 0.25 : true;

                          return (
                            <div className="grid grid-cols-3 gap-1.5 p-2 rounded-lg bg-zinc-50/80 dark:bg-zinc-900/60 border border-zinc-200/60 dark:border-zinc-800/60 text-[11px] font-mono">
                              <div>
                                <span className="text-[9px] text-zinc-400 uppercase block truncate">{col1Label}</span>
                                <span className="text-zinc-800 dark:text-zinc-200 font-bold">
                                  {col1Value}
                                </span>
                              </div>
                              <div>
                                <span className="text-[9px] text-zinc-400 uppercase block truncate">Descarga</span>
                                <span className="text-teal-600 dark:text-teal-400 font-bold">
                                  {col2Value}
                                </span>
                              </div>
                              <div>
                                <span className="text-[9px] text-zinc-400 uppercase block truncate">{col3Label}</span>
                                <span className={`font-bold ${col3IsGood ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                                  {col3Value}
                                </span>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Column: Active Simulation Analysis & Charts */}
            <div className="lg:col-span-8 flex flex-col gap-5">
              {selectedSim ? (
                <>
                  <AIInsightsCard
                    key={selectedSim.id}
                    simulationId={selectedSim.id}
                    initialInsights={(selectedSim.provenance as Record<string, any>)?.ai_insights}
                  />

                  {isSelectedRealSwat && swatResults ? (
                    <SwatRunEvidencePanel simulation={selectedSim} result={swatResults} />
                  ) : (
                    <>
                      {/* Selected Simulation Card & Controls */}
                      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-4 shadow-sm">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-100 dark:border-zinc-800">
                          <div className="flex flex-col">
                            <div className="flex items-center gap-2">
                              <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">{selectedSim.name}</h2>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800 font-semibold">
                                {selectedSim.status}
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-800 font-medium">
                                {selectedSim.climate_source || "SINTÉTICO"}
                              </span>
                            </div>
                            <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                              <b>Escenario:</b> {selectedSim.scenario?.name || "Línea Base"} ({selectedSim.scenario?.pathway || "Histórico"}) · <b>Manejo:</b> {selectedSim.management_scenario === "BASELINE" ? "Convencional (Línea Base)" : selectedSim.management_scenario === "NO_TILL" ? "Siembra Directa (No-Till)" : "Rotación Maíz-Sorgo"}
                            </span>
                            <span className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                              <b>Cuenca:</b> South Fork Iowa River (USGS 05451210) · <b>Población:</b> {selectedSim.plant_count} plantas de maíz · <b>Duración:</b> {selectedSim.duration_days} días
                            </span>
                          </div>

                          {/* WebSocket Controls */}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={toggleWebSocket}
                              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer border shadow-xs ${
                                isWsConnected
                                  ? "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-800 hover:bg-rose-100"
                                  : "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800 hover:bg-emerald-100"
                              }`}
                            >
                              <Radio className={`w-3.5 h-3.5 ${isWsConnected ? "animate-pulse text-rose-500" : ""}`} />
                              <span>{isWsConnected ? "Pausar WS" : "Reproducir WS"}</span>
                            </button>

                            {isWsConnected && (
                              <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-950 px-2 py-1 rounded-xl border border-zinc-200 dark:border-zinc-800 text-[11px] font-mono">
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

                        {/* WebSocket Playback Ticker */}
                        {isWsConnected && liveTick && (
                          <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-50 via-white to-cyan-50 dark:from-emerald-950/40 dark:via-zinc-950 dark:to-cyan-950/40 border border-emerald-300 dark:border-emerald-700/50 grid grid-cols-2 sm:grid-cols-4 gap-3 animate-fadeIn shadow-sm">
                            <div className="col-span-full text-[10px] font-mono text-zinc-500 dark:text-zinc-400">
                              Reproducción temporal cronológica: variables sincronizadas día a día
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400 font-bold">Día / Clima</span>
                              <span className="text-xs font-mono font-bold text-zinc-900 dark:text-zinc-100">
                                Día {liveTick.day_index} ({liveTick.date})
                              </span>
                              <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                                {liveTick.weather.temp_c}°C · {liveTick.weather.precip_mm} mm
                              </span>
                            </div>

                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase font-mono text-emerald-700 dark:text-emerald-400 font-bold">Micro (Planta)</span>
                              <span className="text-xs font-mono font-bold text-emerald-700 dark:text-emerald-300">
                                Tr: {liveTick.micro_plant.transpiration_mm} mm/d
                              </span>
                              <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                                CWSI: {liveTick.micro_plant.cwsi_stress_index}
                              </span>
                            </div>

                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase font-mono text-cyan-700 dark:text-cyan-400 font-bold">Meso (Suelo)</span>
                              <span className="text-xs font-mono font-bold text-cyan-700 dark:text-cyan-300">
                                θ: {liveTick.meso_soil.soil_moisture_vol} %
                              </span>
                              <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                                Percol: {liveTick.meso_soil.percolation_mm} mm
                              </span>
                            </div>

                            <div className="flex flex-col">
                              <span className="text-[10px] uppercase font-mono text-teal-700 dark:text-teal-400 font-bold">Macro (Cuenca)</span>
                              <span className="text-xs font-mono font-bold text-teal-700 dark:text-teal-300">
                                Q: {liveTick.macro_watershed.streamflow_m3s} m³/s
                              </span>
                              <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                                Qsurf: {liveTick.macro_watershed.surface_runoff_mm} mm
                              </span>
                            </div>
                          </div>
                        )}

                        {/* Water Balance & Multiscale Performance Ribbon */}
                        <div>
                          <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400 font-bold tracking-wider block mb-2">
                            Balance Hídrico y Métricas de la Corrida
                          </span>
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Precipitación Total</span>
                              <span className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                                {selectedSim.summary_metrics?.total_precip_mm != null ? `${Number(selectedSim.summary_metrics.total_precip_mm).toFixed(0)} mm` : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">Lluvia acumulada</span>
                            </div>

                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Evapotranspiración</span>
                              <span className="text-base font-bold text-cyan-600 dark:text-cyan-400 mt-1">
                                {selectedSim.summary_metrics?.total_actual_et_mm != null ? `${Number(selectedSim.summary_metrics.total_actual_et_mm).toFixed(1)} mm` : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">Consumo vegetal real</span>
                            </div>

                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Volumen en Río</span>
                              <span className="text-base font-bold text-teal-600 dark:text-teal-400 mt-1">
                                {selectedSim.summary_metrics?.total_discharge_hm3 != null ? `${Number(selectedSim.summary_metrics.total_discharge_hm3).toFixed(1)} hm³` : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">Descarga en exutorio</span>
                            </div>

                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Caudal Máximo Pico</span>
                              <span className="text-base font-bold text-amber-600 dark:text-amber-400 mt-1">
                                {selectedSim.summary_metrics?.peak_streamflow_m3s != null ? `${Number(selectedSim.summary_metrics.peak_streamflow_m3s).toFixed(2)} m³/s` : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">Pico instantáneo</span>
                            </div>

                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Estrés CWSI Medio</span>
                              <span
                                className={`text-base font-bold mt-1 ${
                                  (selectedSim.summary_metrics?.mean_cwsi ?? 0) < 0.25
                                    ? "text-emerald-600 dark:text-emerald-400"
                                    : "text-amber-600 dark:text-amber-400"
                                }`}
                              >
                                {selectedSim.summary_metrics?.mean_cwsi != null ? Number(selectedSim.summary_metrics.mean_cwsi).toFixed(3) : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">
                                {(selectedSim.summary_metrics?.mean_cwsi ?? 0) < 0.25 ? "Confort hídrico" : "Déficit hídrico"}
                              </span>
                            </div>

                            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between">
                              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400">Rendimiento Estimado</span>
                              <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                                {selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha != null ? `${Number(selectedSim.summary_metrics.seasonal_crop_yield_proxy_t_ha).toFixed(2)} t/ha` : "-"}
                              </span>
                              <span className="text-[9px] text-zinc-400 mt-0.5">Biomasa foliar modelo</span>
                            </div>
                          </div>
                        </div>

                        {/* Multiscale Transfer Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                          <div className="p-3.5 rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-emerald-50/30 dark:bg-emerald-950/10 flex flex-col justify-between">
                            <div className="flex items-center gap-1.5 font-mono text-emerald-700 dark:text-emerald-400 font-bold text-[11px]">
                              <Sprout className="w-3.5 h-3.5" />
                              MICRO → MESO (PLANTA A PARCELA)
                            </div>
                            <div className="mt-2 text-zinc-800 dark:text-zinc-200">
                              <b>{selectedSim.plant_count}</b> plantas de maíz simuladas
                            </div>
                            <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                              LAI medio: <b>{Number(selectedSim.field_aggregates?.mean_lai ?? 0).toFixed(3)}</b> · Raíz: <b>{Number(selectedSim.field_aggregates?.mean_root_depth_cm ?? 0).toFixed(1)} cm</b>
                            </div>
                          </div>

                          <div className="p-3.5 rounded-xl border border-cyan-200/80 dark:border-cyan-900/50 bg-cyan-50/30 dark:bg-cyan-950/10 flex flex-col justify-between">
                            <div className="flex items-center gap-1.5 font-mono text-cyan-700 dark:text-cyan-400 font-bold text-[11px]">
                              <Droplets className="w-3.5 h-3.5" />
                              MESO → MACRO (PARCELA A HRU)
                            </div>
                            <div className="mt-2 text-zinc-800 dark:text-zinc-200">
                              <b>{selectedSim.hru_aggregates?.count ?? 0}</b> HRUs de suelo acopladas
                            </div>
                            <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                              Fracción cuenca: <b>{Number(selectedSim.hru_aggregates?.area_fraction_sum ?? 0).toFixed(2)}</b> (SCS-CN = {(selectedSim as any).parameters?.curve_number ?? 74})
                            </div>
                          </div>

                          <div className="p-3.5 rounded-xl border border-amber-200/80 dark:border-amber-900/50 bg-amber-50/30 dark:bg-amber-950/10 flex flex-col justify-between">
                            <div className="flex items-center gap-1.5 font-mono text-amber-700 dark:text-amber-400 font-bold text-[11px]">
                              <Scale className="w-3.5 h-3.5" />
                              VALIDACIÓN (AJUSTE CON USGS)
                            </div>
                            <div className="mt-2 text-zinc-800 dark:text-zinc-200 font-semibold">
                              {selectedSim.validation?.interpretation ?? (isSelectedRealSwat ? "SWAT+ CALIBRADO" : "EVALUACIÓN EXPERIMENTAL")}
                            </div>
                            <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
                              Meses alineados: <b>{selectedSim.validation?.aligned_months ?? 0}</b> · Mejora: <b>{selectedSim.validation?.improvement_percent?.value?.toFixed?.(2) ?? "0.00"}%</b>
                            </div>
                          </div>
                        </div>

                        {/* Provenance Manifest Collapsible */}
                        <details className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-3 text-[11px] text-zinc-600 dark:text-zinc-400">
                          <summary className="cursor-pointer font-mono text-zinc-800 dark:text-zinc-200 font-medium">
                            Ver Manifiesto de Procedencia y Datos de la Corrida
                          </summary>
                          <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 font-mono text-[10px]">
                            <div><span className="text-zinc-400">Periodo:</span> {selectedSim.start_date ?? "2015-01-01"} → {selectedSim.end_date ?? "2020-12-31"}</div>
                            <div><span className="text-zinc-400">Estación USGS:</span> {selectedSim.station_id ?? "05451210"}</div>
                            <div><span className="text-zinc-400">Semilla Aleatoria:</span> seed {selectedSim.seed}</div>
                            <div><span className="text-zinc-400">Dataset Roles:</span> {Object.entries(selectedSim.dataset_roles ?? {}).length || 3} asignados</div>
                          </div>
                        </details>
                      </div>

                      {/* Segmented Chart Scale Navigator */}
                      <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-2xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 ml-2 mr-2 flex items-center gap-1.5">
                            <Filter className="w-3.5 h-3.5 text-emerald-600" />
                            Visualizar Gráficos:
                          </span>
                          <button
                            onClick={() => setChartViewMode("ALL")}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                              chartViewMode === "ALL"
                                ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-xs"
                                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                            }`}
                          >
                            📊 Todas las Escalas
                          </button>
                          <button
                            onClick={() => setChartViewMode("STREAMFLOW")}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                              chartViewMode === "STREAMFLOW"
                                ? "bg-white dark:bg-zinc-800 text-teal-700 dark:text-teal-400 shadow-xs"
                                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                            }`}
                          >
                            🌊 Hidrograma (Macro)
                          </button>
                          <button
                            onClick={() => setChartViewMode("PLANT")}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                              chartViewMode === "PLANT"
                                ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-400 shadow-xs"
                                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                            }`}
                          >
                            🌱 Fisiología Planta (Micro)
                          </button>
                          <button
                            onClick={() => setChartViewMode("SOIL")}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                              chartViewMode === "SOIL"
                                ? "bg-white dark:bg-zinc-800 text-cyan-700 dark:text-cyan-400 shadow-xs"
                                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                            }`}
                          >
                            🌾 Suelo & CWSI (Meso)
                          </button>
                          <button
                            onClick={() => setChartViewMode("MONTHLY")}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                              chartViewMode === "MONTHLY"
                                ? "bg-white dark:bg-zinc-800 text-amber-700 dark:text-amber-400 shadow-xs"
                                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-200/60 dark:hover:bg-zinc-800/60"
                            }`}
                          >
                            📈 Validación Mensual
                          </button>
                        </div>
                      </div>

                      {/* CHART 1: VALIDACIÓN MENSUAL (USGS vs MODELOS) */}
                      {(chartViewMode === "ALL" || chartViewMode === "MONTHLY") && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-100 dark:border-zinc-800">
                            <div>
                              <div className="flex items-center gap-2">
                                <Activity className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                                  Validación Empírica Mensual: Caudales Observados (USGS) vs Modelos Simulados
                                </h3>
                              </div>
                              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                                Compara el registro real de aforo en la estación <b>USGS 05451210</b> contra la línea base sin acoplar, el Gemelo Digital Multiescala acoplado y la predicción híbrida ML.
                              </p>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 font-semibold shrink-0 self-start sm:self-auto">
                              {selectedSim.validation?.interpretation ?? "EVALUACIÓN MENSUAL"}
                            </span>
                          </div>

                          <div className="h-64 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={monthlyComparisonData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" vertical={false} />
                                <XAxis dataKey="month" stroke="#71717a" fontSize={10} tickLine={false} />
                                <YAxis stroke="#71717a" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#71717a", fontSize: 10 }} />
                                <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }} />
                                <Legend wrapperStyle={{ fontSize: "11px" }} />
                                <Line type="monotone" dataKey="observed_streamflow_m3s" name="OBSERVADO REAL (USGS)" stroke="#111827" strokeWidth={2.5} dot={false} connectNulls={false} />
                                <Line type="monotone" dataKey="baseline_streamflow_m3s" name="LÍNEA BASE (Sin acoplar)" stroke="#f97316" strokeWidth={1.8} dot={false} />
                                <Line type="monotone" dataKey="twin_streamflow_m3s" name="GEMELO MULTIESCALA" stroke="#059669" strokeWidth={2.5} dot={false} />
                                <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="ASISTIDO POR ML" stroke="#7c3aed" strokeWidth={1.8} strokeDasharray="4 3" dot={false} connectNulls={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}

                      {/* CHART 2: HIDROGRAMA DE CUENCA (MACROESCALA) */}
                      {(chartViewMode === "ALL" || chartViewMode === "STREAMFLOW") && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-100 dark:border-zinc-800">
                            <div>
                              <div className="flex items-center gap-2">
                                <Mountain className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                                  Hidrograma de Cuenca: Caudal en Exutorio (m³/s) vs Lluvia de Forzamiento (mm)
                                </h3>
                              </div>
                              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                                Respuesta hidrológica global de la cuenca ante tormentas. Las barras de precipitación (azul) generan picos de escorrentía superficial seguidos por la recesión del caudal hacia el caudal base (área turquesa).
                              </p>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-950/80 text-teal-800 dark:text-teal-300 border border-teal-300 dark:border-teal-800 font-semibold shrink-0 self-start sm:self-auto">
                              ESCALA MACRO
                            </span>
                          </div>

                          {isLoadingResults ? (
                            <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                              <Loader2 className="w-5 h-5 animate-spin mr-2 text-teal-500" />
                              Cargando hidrograma de cuenca...
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
                                    label={{ value: "Lluvia Diaria (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }}
                                  />
                                  <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }} />
                                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                                  <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación Diaria (mm)" fill="#0284c7" opacity={0.65} />
                                  <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal Exutorio Simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.2} strokeWidth={2} />
                                </ComposedChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </div>
                      )}

                      {/* CHART 3: FISIOLOGÍA VEGETAL (MICROESCALA) - DUAL Y-AXES */}
                      {(chartViewMode === "ALL" || chartViewMode === "PLANT") && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-100 dark:border-zinc-800">
                            <div>
                              <div className="flex items-center gap-2">
                                <Sprout className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                                  Fisiología Vegetal: Transpiración Real vs Demanda Evaporativa (ET0) y Flujo de Savia
                                </h3>
                              </div>
                              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                                Contrasta la demanda meteorológica ($ET_0$, naranja, mm/d) con la transpiración real del maíz (verde, mm/d) en el eje izquierdo, y la velocidad de ascenso de savia por el tallo (azul, cm/h) en el eje derecho.
                              </p>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 font-semibold shrink-0 self-start sm:self-auto">
                              ESCALA MICRO
                            </span>
                          </div>

                          {isLoadingResults ? (
                            <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                              <Loader2 className="w-5 h-5 animate-spin mr-2 text-emerald-500" />
                              Cargando curvas fisiológicas foliares...
                            </div>
                          ) : (
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" className="dark:stroke-zinc-800" vertical={false} />
                                  <XAxis dataKey="date_str" stroke="#71717a" fontSize={10} tickLine={false} />
                                  <YAxis
                                    yAxisId="left"
                                    stroke="#059669"
                                    fontSize={10}
                                    tickLine={false}
                                    label={{ value: "Agua (mm/día)", angle: -90, position: "insideLeft", fill: "#059669", fontSize: 10 }}
                                  />
                                  <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    stroke="#0284c7"
                                    fontSize={10}
                                    tickLine={false}
                                    label={{ value: "Velocidad Savia (cm/h)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }}
                                  />
                                  <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }} />
                                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                                  <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda Atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                                  <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración Real Cultivo (mm/d)" stroke="#059669" strokeWidth={2.5} dot={false} />
                                  <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad Savia Xilema (cm/h)" stroke="#0284c7" strokeWidth={1.8} dot={false} />
                                </ComposedChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </div>
                      )}

                      {/* CHART 4: DINÁMICA DE HUMEDAD Y CWSI (MESOESCALA) - DUAL Y-AXES + REFERENCE LINES */}
                      {(chartViewMode === "ALL" || chartViewMode === "SOIL") && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/70 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-100 dark:border-zinc-800">
                            <div>
                              <div className="flex items-center gap-2">
                                <Droplets className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                                  Dinámica Edáfica: Humedad Volumétrica del Suelo (θ %) e Índice de Estrés Hídrico (CWSI)
                                </h3>
                              </div>
                              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                                Registra el contenido de agua en la zona radicular (% vol, eje izquierdo) y el índice de estrés CWSI del maíz (0 a 1, eje derecho). Valores de CWSI &gt; 0.25 marcan estrés hídrico; &gt; 0.50 cierre estomático crítico.
                              </p>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950/80 text-cyan-800 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800 font-semibold shrink-0 self-start sm:self-auto">
                              ESCALA MESO (PARCELA)
                            </span>
                          </div>

                          {isLoadingResults ? (
                            <div className="h-64 flex items-center justify-center text-zinc-400 text-xs">
                              <Loader2 className="w-5 h-5 animate-spin mr-2 text-cyan-500" />
                              Cargando perfil edáfico y estrés hídrico...
                            </div>
                          ) : (
                            <div className="h-64 w-full">
                              <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" className="dark:stroke-zinc-800" vertical={false} />
                                  <XAxis dataKey="date_str" stroke="#71717a" fontSize={10} tickLine={false} />
                                  <YAxis
                                    yAxisId="left"
                                    stroke="#0284c7"
                                    fontSize={10}
                                    tickLine={false}
                                    domain={[0, 45]}
                                    label={{ value: "Humedad Suelo θ (% vol)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 10 }}
                                  />
                                  <YAxis
                                    yAxisId="right"
                                    orientation="right"
                                    stroke="#e11d48"
                                    fontSize={10}
                                    tickLine={false}
                                    domain={[0, 1]}
                                    label={{ value: "Estrés CWSI (0 a 1)", angle: 90, position: "insideRight", fill: "#e11d48", fontSize: 10 }}
                                  />
                                  <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e4e4e7", borderRadius: "8px", fontSize: "11px", color: "var(--foreground)" }} />
                                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                                  <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad Volumétrica Suelo θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.2} strokeWidth={2} />
                                  <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Índice Estrés Hídrico CWSI (0-1)" stroke="#e11d48" strokeWidth={2} dot={false} />
                                  <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Estrés Moderado (0.25)", position: "top", fill: "#f59e0b", fontSize: 9 }} />
                                  <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Estrés Severo (0.50)", position: "top", fill: "#ef4444", fontSize: 9 }} />
                                </ComposedChart>
                              </ResponsiveContainer>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : (
                <div className="p-16 rounded-2xl border border-dashed border-zinc-300 dark:border-zinc-800 text-center text-zinc-500 text-xs bg-white dark:bg-zinc-900/40 flex flex-col items-center justify-center gap-2">
                  <Sliders className="w-8 h-8 text-zinc-400 stroke-1" />
                  <span className="font-semibold text-zinc-700 dark:text-zinc-300 text-sm">Ninguna simulación seleccionada</span>
                  <span>Selecciona una corrida en la lista de la izquierda para desplegar su balance hídrico y gráficos multiescala.</span>
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
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-3 sm:p-6 overflow-hidden">
          <div className="w-full max-w-2xl max-h-[90vh] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl flex flex-col text-zinc-900 dark:text-zinc-100 overflow-hidden">
            {/* Header Fijo */}
            <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 shrink-0 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-950/40">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center border border-emerald-500/20">
                  <Sliders className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                    Crear una corrida
                  </h3>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Primero elige cómo calcular; luego verás solamente las opciones que sí se aplican.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer text-base"
              >
                ✕
              </button>
            </div>

            {/* Contenido con Scroll Propio e Independiente */}
            <form id="simulation-form" onSubmit={handleCreateSimulation} className="flex-1 min-h-0 overflow-y-auto p-6 flex flex-col gap-5 text-xs">
              {/* Tarjeta 1: Identificación y Ámbito Espaciotemporal */}
              <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-4">
                <div className="flex items-center gap-2 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80">
                  <div className="w-6 h-6 rounded-md bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                    1
                  </div>
                  <div>
                    <h4 className="font-bold text-zinc-900 dark:text-zinc-100 text-xs">
                      Identificación y Horizonte Temporal de Simulación
                    </h4>
                    <p className="text-[10px] text-zinc-500">
                      Define el experimento, la cuenca de estudio y el periodo temporal según la Ficha Técnica (ventanas de 3 o más meses).
                    </p>
                  </div>
                </div>

                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                    Nombre del Experimento *
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Evaluación multiescala maíz con siembra directa SSP2-4.5"
                    className="w-full px-3.5 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Cuenca Hidrográfica Representativa
                    </label>
                    <select
                      value={formWatershedId}
                      onChange={(e) => {
                        const watershedId = e.target.value;
                        setFormWatershedId(watershedId);
                        const gauge = watersheds.find((item) => item.id === watershedId)?.dem_metadata?.gauge;
                        setFormStationId(typeof gauge === "string" ? gauge : "");
                      }}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    >
                      {watersheds.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} ({w.area_km2} km²)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Estación USGS de Aforo (Gauge)
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="\d{8,15}"
                      value={formStationId}
                      onChange={(e) => setFormStationId(e.target.value)}
                      placeholder="05451210"
                      className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    />
                  </div>
                </div>

                {/* Horizontes Temporales Estandarizados (Ficha Técnica) */}
                <div className="flex flex-col gap-2 pt-1">
                  <div className="flex items-center justify-between">
                    <label className="block font-mono uppercase text-zinc-700 dark:text-zinc-300 font-bold text-[10px] tracking-wide">
                      Horizontes Fijos del Protocolo Científico
                    </label>
                    <span className="text-[10px] text-zinc-400 font-mono hidden sm:inline">
                      Ficha Técnica: ventanas fijas de 3 a más meses
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
                    {SIMULATION_PERIOD_PRESETS.map((preset) => {
                      const isSelected = selectedPeriodPreset === preset.id;
                      return (
                        <button
                          key={preset.id}
                          type="button"
                          onClick={() => handleSelectPeriodPreset(preset)}
                          className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between gap-1.5 ${
                            isSelected
                              ? "bg-emerald-50/80 dark:bg-emerald-950/60 border-emerald-500 text-emerald-900 dark:text-emerald-200 shadow-xs ring-2 ring-emerald-500/20"
                              : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 text-zinc-700 dark:text-zinc-300"
                          }`}
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-xs font-bold truncate">{preset.label}</span>
                            <span
                              className={`text-[9px] font-mono px-1 py-0.2 rounded font-semibold shrink-0 ${
                                isSelected
                                  ? "bg-emerald-200/80 dark:bg-emerald-800/80 text-emerald-900 dark:text-emerald-100"
                                  : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500"
                              }`}
                            >
                              {preset.durationBadge}
                            </span>
                          </div>
                          <span className="text-[10px] text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-tight">
                            {preset.shortDesc}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Fechas Manuales y Sincronizadas */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Fecha de Inicio *
                    </label>
                    <input
                      type="date"
                      required
                      value={formStartDate}
                      onChange={(e) => handleStartDateChange(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Fecha de Término *
                    </label>
                    <input
                      type="date"
                      required
                      value={formEndDate}
                      onChange={(e) => handleEndDateChange(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs font-mono"
                    />
                  </div>
                </div>

                {/* Diagnóstico del Periodo según la Ficha Técnica */}
                {formStartDate && formEndDate && (
                  <div
                    className={`p-3 rounded-xl border flex flex-col gap-1.5 transition ${
                      Date.parse(`${formEndDate}T00:00:00Z`) < Date.parse(`${formStartDate}T00:00:00Z`)
                        ? "bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300"
                        : "bg-gradient-to-r from-emerald-50/90 via-white to-cyan-50/90 dark:from-emerald-950/40 dark:via-zinc-900 dark:to-cyan-950/40 border-emerald-300 dark:border-emerald-800 text-zinc-800 dark:text-zinc-200"
                    }`}
                  >
                    {Date.parse(`${formEndDate}T00:00:00Z`) < Date.parse(`${formStartDate}T00:00:00Z`) ? (
                      <div className="flex items-center gap-2 text-xs font-semibold">
                        <AlertCircle className="w-4 h-4 text-rose-600" />
                        <span>Error en rango de fechas: La fecha de término no puede ser anterior a la fecha de inicio.</span>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-1.5 font-bold text-xs text-zinc-900 dark:text-zinc-100">
                            <Clock className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                            <span>
                              Horizonte Calculado:{" "}
                              <b className="font-mono text-emerald-700 dark:text-emerald-400">
                                {Math.max(
                                  0,
                                  Math.floor(
                                    (Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000
                                  ) + 1
                                )}{" "}
                                días
                              </b>{" "}
                              (
                              {(
                                Math.max(
                                  0,
                                  Math.floor(
                                    (Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000
                                  ) + 1
                                ) / 30.4
                              ).toFixed(1)}{" "}
                              meses hidrológicos)
                            </span>
                          </div>

                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 font-semibold">
                            {SIMULATION_PERIOD_PRESETS.find((p) => p.id === selectedPeriodPreset)?.protocolBadge ?? "Horizonte Personalizado"}
                          </span>
                        </div>

                        <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                          {SIMULATION_PERIOD_PRESETS.find((p) => p.id === selectedPeriodPreset)?.scientificPurpose ??
                            (Math.floor((Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000) + 1 < 90
                              ? "⚠️ Atención: Periodos menores a 3 meses (90 días) pueden no capturar el ciclo completo de transpiración y estrés de la planta ni la dinámica mensual de escorrentía para validar la hipótesis H1."
                              : "Horizonte temporal adecuado para la captura del balance hídrico multiescala planta-cuenca.")}
                        </p>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Tarjeta 2: Motor de Simulación y Clima */}
              <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3.5">
                <div className="flex items-center gap-2 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80">
                  <div className="w-6 h-6 rounded-md bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-400 flex items-center justify-center font-bold text-xs">
                    2
                  </div>
                  <div>
                    <h4 className="font-bold text-zinc-900 dark:text-zinc-100 text-xs">
                      Motor de Simulación y Forzamiento Climático
                    </h4>
                    <p className="text-[10px] text-zinc-500">
                      Selecciona la arquitectura de cálculo hidrológico y la procedencia de las series de temperatura y precipitación.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Método de Cálculo Hidrológico
                    </label>
                    <select
                      value={formHydrologyBackend}
                      onChange={(e) => changeHydrologyBackend(e.target.value as "SIMPLIFIED" | "SWAT_PLUS")}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs font-medium"
                    >
                      <option value="SIMPLIFIED">Exploración Rápida (Gemelo Multiescala Acoplado)</option>
                      <option value="SWAT_PLUS" disabled={capabilities.swat_plus?.status !== "ACTIVE"}>
                        Ejecución Física SWAT+ — {capabilities.swat_plus?.status ?? "No disponible"}
                      </option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Escenario Climático {usesSimplifiedModel ? "" : "(Referencia en Manifiesto)"}
                    </label>
                    <select
                      value={formScenarioId}
                      onChange={(e) => setFormScenarioId(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    >
                      {scenarios.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.code}: {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* SWAT+ Specific Config */}
                {formHydrologyBackend === "SWAT_PLUS" ? (
                  <div className="rounded-xl border border-purple-200 bg-purple-50/70 p-3.5 dark:border-purple-900/60 dark:bg-purple-950/30 flex flex-col gap-2">
                    <label className="block font-mono uppercase text-[10px] text-purple-900 dark:text-purple-300 font-bold">
                      Modalidad de Corrida SWAT+
                    </label>
                    <select
                      value={formSwatRunType}
                      onChange={(e) => setFormSwatRunType(e.target.value as SwatRunType)}
                      className="w-full rounded-lg border border-purple-300 bg-white px-3 py-2 text-xs text-zinc-900 dark:border-purple-800 dark:bg-zinc-950 dark:text-zinc-100"
                    >
                      <option value="SWAT_MULTISCALE_COUPLED">Comparar cultivo acoplado contra un control (Doble Corrida)</option>
                      <option value="SWAT_STANDARD_BASELINE">Solo control SWAT+ físico (sin sobreescritura de parámetros)</option>
                    </select>
                    <p className="text-[10px] text-purple-800 dark:text-purple-300 leading-relaxed">
                      💡 <b>Acoplamiento bidireccional:</b> Genera una réplica aislada de <code>plants.plt</code> inyectando los parámetros fenológicos derivados del cultivo antes de invocar el binario SWAT+.
                    </p>
                  </div>
                ) : (
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Fuente de Forzamiento Climático
                    </label>
                    <select
                      value={formClimateSource}
                      onChange={(e) => setFormClimateSource(e.target.value as "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED")}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    >
                      <option value="SYNTHETIC">SYNTHETIC — Generador estocástico reproducible con estacionalidad de Iowa</option>
                      <option value="OBSERVED" disabled={!hasObservedForcing}>
                        OBSERVED — {hasObservedForcing ? "CHIRPS / GridMET observado disponible" : "No disponible: Requiere dataset CHIRPS"}
                      </option>
                      <option value="CMIP6_FILE" disabled={!hasCmip6Forcing}>
                        CMIP6_FILE — {hasCmip6Forcing ? "Proyecciones NEX-GDDP-CMIP6 disponibles" : "No disponible: Requiere dataset CMIP6"}
                      </option>
                    </select>
                  </div>
                )}
              </div>

              {/* Tarjeta 3: Fisiología Vegetal y Práctica Agronómica */}
              <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3.5">
                <div className="flex items-center gap-2 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80">
                  <div className="w-6 h-6 rounded-md bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 flex items-center justify-center font-bold text-xs">
                    3
                  </div>
                  <div>
                    <h4 className="font-bold text-zinc-900 dark:text-zinc-100 text-xs">
                      Fisiología Vegetal y Manejo Agrícola
                    </h4>
                    <p className="text-[10px] text-zinc-500">
                      Configura la densidad de la población celular y las prácticas de labranza o cobertura.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Población de Plantas ({formPlantCount.toLocaleString()})
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10000}
                      value={formPlantCount}
                      onChange={(e) => setFormPlantCount(Number(e.target.value))}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    />
                    <span className="text-[10px] text-zinc-500 mt-0.5 block">
                      Rango permitido: 1 a 10,000 plantas individuales representadas.
                    </span>
                  </div>

                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Semilla Aleatoria (Seed Monte Carlo)
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={formSeed}
                      onChange={(e) => setFormSeed(Number(e.target.value))}
                      className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    />
                    <span className="text-[10px] text-zinc-500 mt-0.5 block">
                      Permite reproducibilidad determinista idéntica entre corridas.
                    </span>
                  </div>
                </div>

                {/* Manejo Agronómico */}
                {usesSimplifiedModel ? (
                  <div>
                    <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                      Escenario de Manejo Agronómico
                    </label>
                    <select
                      value={formManagement}
                      onChange={(e) => setFormManagement(e.target.value as "BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM")}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:border-emerald-500/80 shadow-xs"
                    >
                      <option value="BASELINE">🌽 Maíz Convencional (Línea Base: labranza intensiva estándar)</option>
                      <option value="NO_TILL">🌱 Siembra Directa / No-Till (Mayor retención edáfica y reducción de escorrentía CN)</option>
                      <option value="MAIZE_TO_SORGHUM">🌾 Transición Maíz → Sorgo (Cultivo C4 más tolerante a sequía, menor Kc)</option>
                    </select>
                    <p className="mt-1 text-[10px] text-zinc-500">
                      Modifica directamente los coeficientes biológicos y la tasa de infiltración del suelo en el gemelo digital.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[11px] text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                    <div className="flex items-center gap-1.5 font-semibold">
                      <Info className="h-3.5 w-3.5" /> Manejo agronómico en SWAT+
                    </div>
                    <p className="mt-1 text-[10px]">
                      El modelo físico SWAT+ utiliza las operaciones agronómicas (fertilización, siembra y cosecha) preconfiguradas en sus archivos de management (<code>management.sch</code>).
                    </p>
                  </div>
                )}

                {/* ML Estimator (Optional) */}
                <div>
                  <label className="block font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1 font-semibold text-[10px]">
                    Estimador ML Externo Opcional {usesSimplifiedModel ? "" : "(No aplicable a SWAT+)"}
                  </label>
                  <select
                    value={formExternalModel}
                    onChange={(e) => setFormExternalModel(e.target.value)}
                    disabled={!usesSimplifiedModel}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 disabled:opacity-50 shadow-xs"
                  >
                    <option value="">Ninguno (usar solver puramente biofísico)</option>
                    {externalModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name} · {model.target} · {model.framework}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Tarjeta 4: Parámetros Biofísicos Explicados */}
              {usesSimplifiedModel && (
                <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3.5">
                  <div className="flex items-center gap-2 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80">
                    <div className="w-6 h-6 rounded-md bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                      4
                    </div>
                    <div>
                      <h4 className="font-bold text-zinc-900 dark:text-zinc-100 text-xs">
                        Parámetros Biofísicos de Suelo y Cultivo (Sensibilidad)
                      </h4>
                      <p className="text-[10px] text-zinc-500">
                        Ajusta los coeficientes físicos que gobiernan la transpiración vegetal, el enraizamiento y la escorrentía superficial.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    {/* Demanda de agua Kc */}
                    <div className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-xs">
                          Demanda de Agua (Kc Base)
                        </span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-bold text-emerald-700 dark:text-emerald-400">
                          {formParameters.base_kc}
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500">
                        Coeficiente de transpiración FAO-56. Rango: 0.1 a 2.0 (Maíz en floración ≈ 1.05 - 1.20).
                      </p>
                      <input
                        type="number"
                        step={0.01}
                        min={0.1}
                        max={2.0}
                        value={formParameters.base_kc}
                        onChange={(e) =>
                          setFormParameters((prev) => ({ ...prev, base_kc: Number(e.target.value) }))
                        }
                        className="mt-1 w-full rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                      />
                    </div>

                    {/* Profundidad radicular */}
                    <div className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-xs">
                          Profundidad Radicular (Z_root)
                        </span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-bold text-cyan-700 dark:text-cyan-400">
                          {formParameters.max_root_depth_cm} cm
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500">
                        Profundidad máxima de absorción radicular. Rango: 1 a 500 cm (Maíz maduro ≈ 120 cm).
                      </p>
                      <input
                        type="number"
                        step={1}
                        min={1}
                        max={500}
                        value={formParameters.max_root_depth_cm}
                        onChange={(e) =>
                          setFormParameters((prev) => ({ ...prev, max_root_depth_cm: Number(e.target.value) }))
                        }
                        className="mt-1 w-full rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                      />
                    </div>

                    {/* Número de Curva CN */}
                    <div className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-xs">
                          Número de Curva SCS (CN)
                        </span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-bold text-teal-700 dark:text-teal-400">
                          {formParameters.curve_number}
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500">
                        Potencial de escorrentía USDA-SCS. A mayor CN, menor infiltración y mayor descarga. Rango: 30 a 98 (Iowa agrícola ≈ 74).
                      </p>
                      <input
                        type="number"
                        step={1}
                        min={30}
                        max={98}
                        value={formParameters.curve_number}
                        onChange={(e) =>
                          setFormParameters((prev) => ({ ...prev, curve_number: Number(e.target.value) }))
                        }
                        className="mt-1 w-full rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                      />
                    </div>

                    {/* Humedad inicial edáfica */}
                    <div className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 text-xs">
                          Humedad Inicial del Suelo (θ₀)
                        </span>
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 font-bold text-blue-700 dark:text-blue-400">
                          {formParameters.initial_soil_moisture_vol}%
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500">
                        Contenido hídrico volumétrico inicial en los primeros 100 cm. Rango: 0 a 44% (Capacidad de campo ≈ 24.5%).
                      </p>
                      <input
                        type="number"
                        step={0.1}
                        min={0}
                        max={44}
                        value={formParameters.initial_soil_moisture_vol}
                        onChange={(e) =>
                          setFormParameters((prev) => ({ ...prev, initial_soil_moisture_vol: Number(e.target.value) }))
                        }
                        className="mt-1 w-full rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Tarjeta 5: Datasets y Sensores Vinculados */}
              <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3.5">
                <div className="flex items-center gap-2 pb-2 border-b border-zinc-200/80 dark:border-zinc-800/80">
                  <div className="w-6 h-6 rounded-md bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                    5
                  </div>
                  <div>
                    <h4 className="font-bold text-zinc-900 dark:text-zinc-100 text-xs">
                      Vinculación de Evidencia y Datos de Sensores
                    </h4>
                    <p className="text-[10px] text-zinc-500">
                      Asigna el rol funcional que cumplirá cada artefacto espacial o sensor hidrométrico en esta corrida.
                    </p>
                  </div>
                </div>

                {datasets.length === 0 ? (
                  <p className="text-[11px] text-zinc-500 py-2">
                    No hay artefactos externos registrados en el catálogo. Se utilizará el modo estocástico SYNTHETIC.
                  </p>
                ) : (
                  <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                    {datasets.map((dataset) => {
                      const isChecked = formDatasetIds.includes(dataset.id);
                      return (
                        <div
                          key={dataset.id}
                          className={`p-2.5 rounded-lg border text-[11px] transition flex items-center justify-between gap-2 ${
                            isChecked
                              ? "bg-white dark:bg-zinc-900 border-emerald-300 dark:border-emerald-800/60 shadow-xs"
                              : "bg-zinc-100/50 dark:bg-zinc-900/30 border-zinc-200/60 dark:border-zinc-800/50 text-zinc-600 dark:text-zinc-400"
                          }`}
                        >
                          <label className="flex items-center gap-2.5 flex-1 min-w-0 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={(event) => {
                                setFormDatasetIds((current) =>
                                  event.target.checked ? [...current, dataset.id] : current.filter((id) => id !== dataset.id)
                                );
                                setFormDatasetRoles((current) => {
                                  const next = { ...current };
                                  if (event.target.checked) next[dataset.id] = "CONTEXT_ONLY";
                                  else delete next[dataset.id];
                                  return next;
                                });
                              }}
                              className="rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                            />
                            <div className="flex flex-col min-w-0">
                              <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                                {dataset.provider}: {dataset.dataset_name}
                              </span>
                              <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                                {dataset.evidence_type} · {dataset.normalized_artifact_count} archivos normalizados
                              </span>
                            </div>
                          </label>

                          {isChecked && (
                            <div className="shrink-0">
                              {formHydrologyBackend === "SWAT_PLUS" ? (
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                                  EVIDENCIA
                                </span>
                              ) : (
                                <select
                                  value={formDatasetRoles[dataset.id] ?? "CONTEXT_ONLY"}
                                  onChange={(event) =>
                                    setFormDatasetRoles((current) => ({
                                      ...current,
                                      [dataset.id]: event.target.value as any,
                                    }))
                                  }
                                  className="rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-1 text-[10px] font-medium"
                                >
                                  <option value="FORCING">FORCING (Clima primario)</option>
                                  <option value="OBSERVATION">OBSERVATION (Aforo real)</option>
                                  <option value="VALIDATION">VALIDATION (Calibración)</option>
                                  <option value="CONTEXT_ONLY">CONTEXT_ONLY (Referencia)</option>
                                </select>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 text-[10px] text-amber-800 dark:text-amber-300">
                  {usesSimplifiedModel
                    ? "📌 Para forzar el clima observado o CMIP6, selecciona al menos un artefacto con rol FORCING. Para comparar el caudal estimado contra el hidrograma real, vincula el dataset de USGS como OBSERVATION."
                    : "📌 En corridas físicas SWAT+, los datasets seleccionados se registran en el manifiesto criptográfico de procedencia, respetando la estructura hidrológica nativa de SWAT+."}
                </div>
              </div>

              {/* Resumen de Ejecución */}
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-50/80 via-white to-cyan-50/80 dark:from-emerald-950/30 dark:via-zinc-900 dark:to-cyan-950/30 border border-emerald-200 dark:border-emerald-800/60 text-[11px] text-zinc-700 dark:text-zinc-300 flex flex-col gap-1 shadow-xs">
                <span className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  {formHydrologyBackend === "SWAT_PLUS"
                    ? "Flujo de Ejecución: Micro-Fisiología Vegetal → Calibración plants.plt → Binario SWAT+"
                    : "Flujo de Ejecución: Célula/Planta → Lote Agrícola → HRU Hidrológica → Aforo de Cuenca"}
                </span>
                <p className="text-[10px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {formHydrologyBackend === "SWAT_PLUS"
                    ? `Simulará la dinámica transpiratoria de ${formPlantCount.toLocaleString()} plantas, derivará coeficientes fenológicos y ejecutará el motor SWAT+ sobre la cuenca South Fork Iowa.`
                    : `Simulará de forma integrada la fenología celular de ${formPlantCount.toLocaleString()} plantas acoplándolas con el balance edáfico diario de la cuenca.`}
                </p>
              </div>
            </form>

            {/* Footer Fijo con Botones Siempre Visibles */}
            <div className="px-6 py-3.5 border-t border-zinc-200 dark:border-zinc-800 shrink-0 bg-zinc-50 dark:bg-zinc-950/60 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                <span className="hidden sm:inline">
                  Duración:{" "}
                  <b className="text-zinc-800 dark:text-zinc-200 font-mono">
                    {formStartDate && formEndDate
                      ? `${Math.max(0, Math.floor((Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000) + 1)} días`
                      : "0 días"}
                  </b>
                </span>
                <span className="hidden sm:inline">·</span>
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 font-semibold">
                  {formHydrologyBackend === "SWAT_PLUS" ? "SWAT+ FÍSICO" : "GEMELO MULTIESCALA"}
                </span>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium transition cursor-pointer text-xs"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  form="simulation-form"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-zinc-950 font-semibold transition flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-md shadow-emerald-500/20 text-xs"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{formHydrologyBackend === "SWAT_PLUS" ? "Ejecutando SWAT+..." : "Ejecutando..."}</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Ejecutar experimento</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

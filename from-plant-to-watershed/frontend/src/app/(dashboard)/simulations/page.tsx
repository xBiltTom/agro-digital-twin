"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
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
  Plus,
  Play,
  Pause,
  RefreshCw,
  Search,
  X,
  ExternalLink,
  Layers,
  Database,
  Sprout,
  Droplets,
  Mountain,
  Waves,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Clock,
  Radio,
  FileText,
  SlidersHorizontal,
  LayoutGrid,
  Square,
  Rows3,
  Maximize2,
  PanelLeftClose,
  PanelLeftOpen,
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
  ReferenceLine,
} from "recharts";

const CAPABILITY_INFO: Record<string, { label: string; desc: string; category: string }> = {
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

  // Navegación de vistas y disposición innovadora
  const [activeTab, setActiveTab] = useState<"RUNS" | "VALIDATION" | "SCENARIOS" | "STATISTICS">("RUNS");
  const [simDetailTab, setSimDetailTab] = useState<"CHARTS" | "AI" | "SPECIFICATIONS">("CHARTS");
  const [chartViewMode, setChartViewMode] = useState<"ALL" | "STREAMFLOW" | "PLANT" | "SOIL" | "MONTHLY">("STREAMFLOW");
  const [chartLayout, setChartLayout] = useState<"GRID" | "SPOTLIGHT" | "STACK">("GRID");
  const [expandedChartModal, setExpandedChartModal] = useState<"MONTHLY" | "STREAMFLOW" | "PLANT" | "SOIL" | null>(null);
  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false);

  // Listener para cerrar modal con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setExpandedChartModal(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Estado colapsable para arquitectura del sistema
  const [showArchitectureOverview, setShowArchitectureOverview] = useState(false);

  // Búsqueda y filtrado
  const [simSearchTerm, setSimSearchTerm] = useState("");
  const [simFilterModel, setSimFilterModel] = useState<"ALL" | "TWIN" | "SWAT">("ALL");

  // Estados de carga y modal
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Formulario de nueva corrida
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

  // Transmisión WebSocket
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
      setFormManagement("BASELINE");
      setFormClimateSource("SWAT_PROJECT");
      setFormExternalModel("");
      setFormDatasetRoles((current) => Object.fromEntries(Object.keys(current).map((id) => [id, "CONTEXT_ONLY"])) as typeof current);
    } else if (formClimateSource === "SWAT_PROJECT") {
      setFormClimateSource("SYNTHETIC");
    }
  };

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
  };

  const handleCreateSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    const durationDays = formStartDate && formEndDate
      ? Math.floor((Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000) + 1
      : 0;
    if (durationDays < 1) {
      setFeedbackMsg({ type: "error", text: "Selecciona un rango de fechas válido." });
      return;
    }
    const selectedScenario = scenarios.find((s) => s.id === formScenarioId);
    const usesExternalForcing = formClimateSource === "OBSERVED" || formClimateSource === "CMIP6_FILE";
    if (usesExternalForcing && selectedScenario && (selectedScenario.temp_anomaly_c !== 0 || selectedScenario.precip_factor !== 1)) {
      setFeedbackMsg({ type: "error", text: "El forzamiento externo ya incluye su anomalía. Elige un escenario neutro." });
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
      setFeedbackMsg({ type: "success", text: `Experimento "${newSim.name}" guardado.` });
      selectSimulation(newSim);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message || "Error al ejecutar experimento" });
    } finally {
      setIsSubmitting(false);
    }
  };

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
          console.error("Error al procesar tick WS:", e);
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

  const chartData = results.filter((_, idx) => idx % Math.max(1, Math.floor(results.length / 90)) === 0);
  const monthlyComparisonData = selectedSim?.monthly_outputs ?? [];
  const isSelectedRealSwat = selectedSim ? isRealSwat(selectedSim) : false;
  const hasObservedForcing = datasets.some((d) => ["CHIRPS", "OBSERVED_CLIMATE"].includes(d.provider) && d.normalized_artifact_count > 0);
  const hasCmip6Forcing = datasets.some((d) => d.provider === "NEX-GDDP-CMIP6" && d.normalized_artifact_count > 0);

  const filteredSimulations = simulations.filter((sim) => {
    const term = simSearchTerm.trim().toLowerCase();
    const matchesSearch =
      !term ||
      sim.name.toLowerCase().includes(term) ||
      (sim.scenario?.name?.toLowerCase().includes(term) ?? false) ||
      (sim.climate_source?.toLowerCase().includes(term) ?? false) ||
      (sim.station_id?.includes(term) ?? false);
    const matchesModel =
      simFilterModel === "ALL"
        ? true
        : simFilterModel === "SWAT"
        ? isRealSwat(sim)
        : !isRealSwat(sim);
    return matchesSearch && matchesModel;
  });

  return (
    <div className="flex flex-col border-x border-slate-300 dark:border-slate-800 w-full max-w-full min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* 1. Barra de Navegación de Vistas y Acciones Principales */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-5 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-serif text-slate-900 dark:text-slate-100 tracking-tight">
            Consola de simulaciones ecohidrológicas
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Acoplamiento multiescala desde fisiología celular hasta el balance de cuenca.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {canRunSimulations && (
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-none bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-medium transition cursor-pointer shadow-none"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Configurar corrida</span>
            </button>
          )}
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3 rounded-none border text-xs flex items-center gap-2 ${
            feedbackMsg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200"
          }`}
        >
          {feedbackMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{feedbackMsg.text}</span>
        </div>
      )}

      {/* 2. Pestañas de Nivel Superior */}
      <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab("RUNS")}
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer ${
            activeTab === "RUNS"
              ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
          }`}
        >
          Corridas de simulación
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("VALIDATION")}
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer ${
            activeTab === "VALIDATION"
              ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
          }`}
        >
          Validación de hipótesis (H0 / H1)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("SCENARIOS")}
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer ${
            activeTab === "SCENARIOS"
              ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
          }`}
        >
          Escenarios climáticos
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("STATISTICS")}
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer ${
            activeTab === "STATISTICS"
              ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
          }`}
        >
          Batería estadística
        </button>

        <button
          type="button"
          onClick={() => setShowArchitectureOverview(!showArchitectureOverview)}
          className="ml-auto text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-300 px-2 py-1 transition cursor-pointer"
        >
          {showArchitectureOverview ? "Ocultar arquitectura de acoplamiento" : "Ver arquitectura de acoplamiento"}
        </button>
      </div>

      {activeTab === "RUNS" && (
        <>
          {/* Explicación de Arquitectura de Acoplamiento (Opcional colapsable) */}
          {showArchitectureOverview && (
            <div className="p-4 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/40 text-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  Esquema de acoplamiento multiescala (5 fases)
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  14 componentes activos en el stack
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 text-slate-600 dark:text-slate-400 text-xs">
                <div className="p-2.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">1. Clima y forzamiento</span>
                  Precipitación, temperatura y demanda evaporativa de referencia (ET0).
                </div>
                <div className="p-2.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">2. Micro (Planta FSPM)</span>
                  Transpiración estomática, succión de xilema y desarrollo de área foliar (LAI).
                </div>
                <div className="p-2.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">3. Meso (Parcela y suelo)</span>
                  Extracción radicular según Feddes, humedad volumétrica edáfica y estrés CWSI.
                </div>
                <div className="p-2.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">4. Macro (Cuenca)</span>
                  Infiltración SCS-CN, retención edáfica y balance en Unidades de Respuesta Hidrológica (HRUs).
                </div>
                <div className="p-2.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900">
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">5. Aforo USGS 05451210</span>
                  Caudal descargado en exutorio y contraste contra aforos observados.
                </div>
              </div>
            </div>
          )}

          {/* 3. Área de Trabajo Principal: Catálogo (Izquierda) + Consola de Análisis (Derecha) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch border-t border-slate-300 dark:border-slate-800">
            {/* Panel Izquierdo: Catálogo de Corridas Registradas (Colapsable) */}
            {!isCatalogCollapsed ? (
              <div className="lg:col-span-4 xl:col-span-3 flex flex-col border-r border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
                <div className="flex items-center justify-between p-3 border-b border-slate-300 dark:border-slate-800">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Experimentos ({filteredSimulations.length})
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={loadInitialData}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-none transition cursor-pointer"
                      title="Refrescar catálogo"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsCatalogCollapsed(true)}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-none transition cursor-pointer"
                      title="Ocultar catálogo para ganar espacio"
                    >
                      <PanelLeftClose className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

              {/* Buscador */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={simSearchTerm}
                  onChange={(e) => setSimSearchTerm(e.target.value)}
                  placeholder="Filtrar por nombre o escenario..."
                  className="w-full pl-8 pr-7 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-slate-400"
                />
                {simSearchTerm && (
                  <button
                    type="button"
                    onClick={() => setSimSearchTerm("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Filtro por Modelo */}
              <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-800/70 rounded-none text-xs">
                <button
                  type="button"
                  onClick={() => setSimFilterModel("ALL")}
                  className={`flex-1 py-1 rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "ALL"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  Todos ({simulations.length})
                </button>
                <button
                  type="button"
                  onClick={() => setSimFilterModel("TWIN")}
                  className={`flex-1 py-1 rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "TWIN"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  Gemelo ({simulations.filter((s) => !isRealSwat(s)).length})
                </button>
                <button
                  type="button"
                  onClick={() => setSimFilterModel("SWAT")}
                  className={`flex-1 py-1 rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "SWAT"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  SWAT+ ({simulations.filter((s) => isRealSwat(s)).length})
                </button>
              </div>

              {/* Lista de Experimentos */}
              <div className="flex flex-col gap-1.5 max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
                {filteredSimulations.length === 0 ? (
                  <div className="p-6 text-center rounded-none border border-dashed border-slate-200 dark:border-slate-800 text-xs text-slate-400">
                    No se encontraron simulaciones que coincidan con la búsqueda.
                  </div>
                ) : (
                  filteredSimulations.map((sim) => {
                    const isSelected = selectedSim?.id === sim.id;
                    const simIsSwat = isRealSwat(sim);

                    const precipVal = sim.summary_metrics?.total_precip_mm ?? sim.summary_metrics?.total_precipitation_mm;
                    const runoffVal = sim.summary_metrics?.total_runoff_mm ?? sim.summary_metrics?.total_surface_runoff_mm;
                    const precipStr = precipVal != null ? `${Number(precipVal).toFixed(0)} mm` : (runoffVal != null ? `${Number(runoffVal).toFixed(0)} mm` : "—");

                    const dischargeHm3 = sim.summary_metrics?.total_discharge_hm3 != null
                      ? Number(sim.summary_metrics.total_discharge_hm3)
                      : (sim.summary_metrics?.water_balance?.mean_streamflow_m3s != null && sim.duration_days
                        ? (Number(sim.summary_metrics.water_balance.mean_streamflow_m3s) * sim.duration_days * 86400) / 1_000_000
                        : (runoffVal != null ? (Number(runoffVal) * 580.15) / 1000 : null));
                    const dischargeStr = dischargeHm3 != null ? `${dischargeHm3.toFixed(1)} hm³` : "—";

                    const cwsiVal = sim.summary_metrics?.mean_cwsi ?? sim.field_aggregates?.mean_water_stress;
                    const cwsiStr = cwsiVal != null ? Number(cwsiVal).toFixed(3) : "—";

                    return (
                      <div
                        key={sim.id}
                        onClick={() => selectSimulation(sim)}
                        className={`p-3 rounded-none border text-left cursor-pointer transition flex flex-col gap-1.5 ${
                          isSelected
                            ? "bg-slate-50 dark:bg-slate-800/60 border-slate-400 dark:border-slate-600 shadow-none"
                            : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                            {sim.name}
                          </span>
                          <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-none border shrink-0 ${
                            simIsSwat
                              ? "bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800"
                              : "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                          }`}>
                            {simIsSwat ? "SWAT+" : "Gemelo"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                          <span>{sim.duration_days} días</span>
                          <span>·</span>
                          <span>{sim.plant_count?.toLocaleString()} plantas</span>
                          <span>·</span>
                          <span className="font-mono text-[10px]">{sim.climate_source || "SINTÉTICO"}</span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] font-mono pt-1 border-t border-slate-100 dark:border-slate-800/80 text-slate-600 dark:text-slate-400">
                          <span>Lluvia: <strong className="text-slate-800 dark:text-slate-200 font-normal">{precipStr}</strong></span>
                          <span>Descarga: <strong className="text-slate-800 dark:text-slate-200 font-normal">{dischargeStr}</strong></span>
                          <span>CWSI: <strong className="text-slate-800 dark:text-slate-200 font-normal">{cwsiStr}</strong></span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
            ) : (
              <div className="w-10 border-r border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col items-center py-3">
                <button
                  type="button"
                  onClick={() => setIsCatalogCollapsed(false)}
                  className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                  title="Expandir catálogo de experimentos"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
                <div className="mt-8 [writing-mode:vertical-rl] text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                  Catálogo ({filteredSimulations.length})
                </div>
              </div>
            )}

            {/* Panel Derecho: Consola de Trabajo del Experimento */}
            <div className={`${!isCatalogCollapsed ? "lg:col-span-8 xl:col-span-9" : "lg:col-span-12 flex-1"} flex flex-col bg-slate-50 dark:bg-slate-950 min-h-[700px]`}>
              {selectedSim ? (
                <>
                  {/* Encabezado del Experimento Activo */}
                  <div className="p-4 rounded-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-3">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                            {selectedSim.name}
                          </h2>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-none bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            {selectedSim.status}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-none bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            {isSelectedRealSwat ? "SWAT+ Físico" : "Gemelo Multiescala"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-1 flex-wrap">
                          <span>Cuenca: South Fork Iowa (USGS {selectedSim.station_id || "05451210"})</span>
                          <span>·</span>
                          <span>Escenario: {selectedSim.scenario?.name || "Línea Base"}</span>
                          <span>·</span>
                          <span>Periodo: {selectedSim.start_date || "2018-06-01"} a {selectedSim.end_date || "2018-08-31"}</span>
                        </div>
                      </div>

                      {/* Controles de Acción: 3D y WebSocket Scrubber */}
                      <div className="flex items-center gap-2 shrink-0">
                        <Link
                          href={`/twin-3d?simId=${selectedSim.id}`}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-none border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>Abrir en gemelo 3D</span>
                        </Link>

                        <button
                          type="button"
                          onClick={toggleWebSocket}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-none text-xs font-medium border transition cursor-pointer ${
                            isWsConnected
                              ? "bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800"
                              : "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700 hover:bg-slate-200"
                          }`}
                        >
                          <Radio className={`w-3.5 h-3.5 ${isWsConnected ? "text-rose-500 animate-pulse" : ""}`} />
                          <span>{isWsConnected ? "Pausar streaming" : "Reproducir streaming"}</span>
                        </button>

                        {isWsConnected && (
                          <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-none text-xs font-mono">
                            <button
                              type="button"
                              onClick={() => handleWsSpeedChange(1)}
                              className={`px-1.5 py-0.5 rounded-none cursor-pointer ${wsSpeed === 1 ? "bg-white dark:bg-slate-900 font-bold" : "text-slate-500"}`}
                            >1x</button>
                            <button
                              type="button"
                              onClick={() => handleWsSpeedChange(5)}
                              className={`px-1.5 py-0.5 rounded-none cursor-pointer ${wsSpeed === 5 ? "bg-white dark:bg-slate-900 font-bold" : "text-slate-500"}`}
                            >5x</button>
                            <button
                              type="button"
                              onClick={() => handleWsSpeedChange(20)}
                              className={`px-1.5 py-0.5 rounded-none cursor-pointer ${wsSpeed === 20 ? "bg-white dark:bg-slate-900 font-bold" : "text-slate-500"}`}
                            >20x</button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Barra de Reproducción en Vivo Sincronizada */}
                    {isWsConnected && liveTick && (
                      <div className="p-3 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/50 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                        <div>
                          <span className="text-[10px] text-slate-400 block">Día y clima</span>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            Día {liveTick.day_index} ({liveTick.date})
                          </span>
                          <span className="text-[10px] text-slate-500 block">
                            {liveTick.weather.temp_c}°C · {liveTick.weather.precip_mm} mm
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Planta micro</span>
                          <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                            {liveTick.micro_plant.transpiration_mm} mm/d
                          </span>
                          <span className="text-[10px] text-slate-500 block">
                            CWSI: {liveTick.micro_plant.cwsi_stress_index}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Suelo meso</span>
                          <span className="font-semibold text-amber-700 dark:text-amber-400">
                            θ: {liveTick.meso_soil.soil_moisture_vol}%
                          </span>
                          <span className="text-[10px] text-slate-500 block">
                            Percol: {liveTick.meso_soil.percolation_mm} mm
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block">Cuenca macro</span>
                          <span className="font-semibold text-blue-700 dark:text-blue-400">
                            Q: {liveTick.macro_watershed.streamflow_m3s} m³/s
                          </span>
                          <span className="text-[10px] text-slate-500 block">
                            Escorrentía: {liveTick.macro_watershed.surface_runoff_mm} mm
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Strip de Balance Hídrico (6 Variables Consolidadas) */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Precipitación</span>
                        <span className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5 block">
                          {selectedSim.summary_metrics?.total_precip_mm != null ? `${Number(selectedSim.summary_metrics.total_precip_mm).toFixed(0)} mm` : "—"}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Evapotranspiración</span>
                        <span className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5 block">
                          {selectedSim.summary_metrics?.total_actual_et_mm != null ? `${Number(selectedSim.summary_metrics.total_actual_et_mm).toFixed(1)} mm` : "—"}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Volumen en río</span>
                        <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400 mt-0.5 block">
                          {selectedSim.summary_metrics?.total_discharge_hm3 != null ? `${Number(selectedSim.summary_metrics.total_discharge_hm3).toFixed(1)} hm³` : "—"}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Caudal pico</span>
                        <span className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5 block">
                          {selectedSim.summary_metrics?.peak_streamflow_m3s != null ? `${Number(selectedSim.summary_metrics.peak_streamflow_m3s).toFixed(2)} m³/s` : "—"}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Estrés CWSI</span>
                        <span className="text-sm font-semibold font-mono text-amber-700 dark:text-amber-400 mt-0.5 block">
                          {selectedSim.summary_metrics?.mean_cwsi != null ? Number(selectedSim.summary_metrics.mean_cwsi).toFixed(3) : "—"}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-none border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30">
                        <span className="text-[11px] text-slate-500 block">Rendimiento</span>
                        <span className="text-sm font-semibold font-mono text-emerald-700 dark:text-emerald-400 mt-0.5 block">
                          {selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha != null ? `${Number(selectedSim.summary_metrics.seasonal_crop_yield_proxy_t_ha).toFixed(2)} t/ha` : "—"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Sub-Pestañas de la Consola de Trabajo */}
                  <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800 text-xs">
                    <button
                      type="button"
                      onClick={() => setSimDetailTab("CHARTS")}
                      className={`px-3 py-2 font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
                        simDetailTab === "CHARTS"
                          ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
                          : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
                      }`}
                    >
                      <Waves className="w-3.5 h-3.5" />
                      <span>Series temporales e hidrograma</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSimDetailTab("AI")}
                      className={`px-3 py-2 font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
                        simDetailTab === "AI"
                          ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
                          : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>Diagnóstico científico y políticas</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSimDetailTab("SPECIFICATIONS")}
                      className={`px-3 py-2 font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
                        simDetailTab === "SPECIFICATIONS"
                          ? "border-slate-900 dark:border-slate-100 text-slate-900 dark:text-slate-100 dark:border-slate-100"
                          : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"
                      }`}
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>Acoplamiento multiescala y procedencia</span>
                    </button>
                  </div>

                  {/* CONTENIDO DE LA SUB-PESTAÑA 1: SERIES TEMPORALES Y WORKBENCH */}
                  {simDetailTab === "CHARTS" && (
                    <>
                      {isSelectedRealSwat && swatResults ? (
                        <SwatRunEvidencePanel simulation={selectedSim} result={swatResults} />
                      ) : (
                        <div className="flex flex-col gap-3">
                          {/* Barra de Control de Disposición y Modos de Visualización */}
                          <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[11px] font-mono text-slate-500 mr-1">Disposición:</span>
                              <button
                                type="button"
                                onClick={() => setChartLayout("GRID")}
                                className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                  chartLayout === "GRID"
                                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                }`}
                                title="Cuadrante 2x2: Permite ver las 4 escalas simultáneas sin scrollear"
                              >
                                <LayoutGrid className="w-3.5 h-3.5" />
                                <span>Cuadrante 2x2</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => setChartLayout("SPOTLIGHT")}
                                className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                  chartLayout === "SPOTLIGHT"
                                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                }`}
                                title="Foco único: Un gráfico ampliado con conmutador rápido"
                              >
                                <Square className="w-3.5 h-3.5" />
                                <span>Foco único</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => setChartLayout("STACK")}
                                className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                  chartLayout === "STACK"
                                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                }`}
                                title="Pila vertical: Visualización continua estándar"
                              >
                                <Rows3 className="w-3.5 h-3.5" />
                                <span>Pila vertical</span>
                              </button>
                            </div>

                            {chartLayout === "SPOTLIGHT" && (
                              <div className="flex items-center gap-1 text-xs font-mono">
                                <span className="text-[11px] text-slate-500 mr-1">Variable activa:</span>
                                <button
                                  type="button"
                                  onClick={() => setChartViewMode("STREAMFLOW")}
                                  className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "STREAMFLOW" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                >
                                  Hidrograma
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setChartViewMode("PLANT")}
                                  className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "PLANT" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                >
                                  Fisiología
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setChartViewMode("SOIL")}
                                  className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "SOIL" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                >
                                  Suelo/Estrés
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setChartViewMode("MONTHLY")}
                                  className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "MONTHLY" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                >
                                  Validación USGS
                                </button>
                              </div>
                            )}

                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
                              Haz clic en <Maximize2 className="w-3 h-3 inline text-slate-500" /> en cualquier gráfico para inspección modal
                            </span>
                          </div>

                          {/* Renderizado Condicional según Disposición */}
                          {chartLayout === "GRID" && (
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                              {/* 1. Validación USGS */}
                              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">USGS</span>
                                      <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Validación mensual: Aforo vs Gemelo</h3>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate mt-0.5">Estación USGS 05451210 South Fork Iowa</p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("MONTHLY")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer shrink-0"
                                    title="Inspeccionar en modal"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-48 sm:h-52 w-full p-2">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={monthlyComparisonData}>
                                      <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                      <XAxis dataKey="month" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                      <YAxis stroke="#9ca3af" fontSize={9} tickLine={false} />
                                      <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                      <Legend wrapperStyle={{ fontSize: "10px" }} />
                                      <Line type="monotone" dataKey="observed_streamflow_m3s" name="USGS Observado" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={1.8} dot={false} />
                                      <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base" stroke="#ea580c" strokeWidth={1.2} dot={false} />
                                      <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={1.8} dot={false} />
                                      <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Híbrido ML" stroke="#7c3aed" strokeWidth={1.2} strokeDasharray="3 3" dot={false} />
                                    </LineChart>
                                  </ResponsiveContainer>
                                </div>
                              </div>

                              {/* 2. Hidrograma de Cuenca */}
                              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Macro</span>
                                      <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Hidrograma de cuenca: Caudal y lluvia</h3>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate mt-0.5">Respuesta de caudal en exutorio y lluvia diaria</p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("STREAMFLOW")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer shrink-0"
                                    title="Inspeccionar en modal"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-48 sm:h-52 w-full p-2">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando hidrograma...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0d9488" fontSize={9} tickLine={false} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={9} tickLine={false} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "10px" }} />
                                        <Bar yAxisId="right" dataKey="precip_mm" name="Lluvia (mm)" fill="#0284c7" opacity={0.6} />
                                        <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.5} />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>

                              {/* 3. Fisiología Vegetal */}
                              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Micro</span>
                                      <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Fisiología: Transpiración vs ET0</h3>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate mt-0.5">Dinámica estomática celular y flujo de savia</p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("PLANT")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer shrink-0"
                                    title="Inspeccionar en modal"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-48 sm:h-52 w-full p-2">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando fisiología...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#059669" fontSize={9} tickLine={false} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={9} tickLine={false} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "10px" }} />
                                        <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda ET0" stroke="#ea580c" strokeWidth={1.2} dot={false} strokeDasharray="3 3" />
                                        <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración" stroke="#059669" strokeWidth={1.8} dot={false} />
                                        <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Savia (cm/h)" stroke="#0284c7" strokeWidth={1.2} dot={false} />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>

                              {/* 4. Dinámica de Suelo y CWSI */}
                              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-1.5">
                                      <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Meso</span>
                                      <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Dinámica de suelo: Humedad θ y CWSI</h3>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate mt-0.5">Umbrales de déficit: 0.25 (moderado) y 0.50 (crítico)</p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("SOIL")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer shrink-0"
                                    title="Inspeccionar en modal"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-48 sm:h-52 w-full p-2">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando suelo...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0284c7" fontSize={9} tickLine={false} domain={[0, 45]} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={9} tickLine={false} domain={[0, 1]} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "10px" }} />
                                        <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.15} strokeWidth={1.5} />
                                        <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Estrés CWSI" stroke="#e11d48" strokeWidth={1.5} dot={false} />
                                        <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                        <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Modo SPOTLIGHT: Foco Único */}
                          {chartLayout === "SPOTLIGHT" && (
                            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                                    {chartViewMode === "STREAMFLOW" ? "Escala Macro" : chartViewMode === "PLANT" ? "Escala Micro" : chartViewMode === "SOIL" ? "Escala Meso" : "Validación USGS"}
                                  </span>
                                  <h3 className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100">
                                    {chartViewMode === "STREAMFLOW" && "Hidrograma de cuenca: Caudal en exutorio y precipitación diaria"}
                                    {chartViewMode === "PLANT" && "Fisiología vegetal: Transpiración foliar real vs demanda evaporativa (ET0)"}
                                    {chartViewMode === "SOIL" && "Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés CWSI"}
                                    {chartViewMode === "MONTHLY" && "Validación mensual: Aforo observado USGS vs Gemelo digital"}
                                  </h3>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => setExpandedChartModal(chartViewMode as any)}
                                  className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer flex items-center gap-1 text-xs font-mono"
                                  title="Inspeccionar en modal completo"
                                >
                                  <Maximize2 className="w-3.5 h-3.5" />
                                  <span className="hidden sm:inline">Inspeccionar</span>
                                </button>
                              </div>

                              <div className="h-72 sm:h-80 w-full p-3">
                                {isLoadingResults && chartViewMode !== "MONTHLY" ? (
                                  <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando serie temporal...
                                  </div>
                                ) : (
                                  <ResponsiveContainer width="100%" height="100%">
                                    {chartViewMode === "MONTHLY" ? (
                                      <LineChart data={monthlyComparisonData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="month" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Line type="monotone" dataKey="observed_streamflow_m3s" name="Observado real (USGS)" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={2} dot={false} />
                                        <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base sin acoplar" stroke="#ea580c" strokeWidth={1.5} dot={false} />
                                        <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={2} dot={false} />
                                        <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Predicción híbrida ML" stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                                      </LineChart>
                                    ) : chartViewMode === "STREAMFLOW" ? (
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0d9488" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Lluvia (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación diaria (mm)" fill="#0284c7" opacity={0.6} />
                                        <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.8} />
                                      </ComposedChart>
                                    ) : chartViewMode === "PLANT" ? (
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#059669" fontSize={10} tickLine={false} label={{ value: "Agua (mm/d)", angle: -90, position: "insideLeft", fill: "#059669", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Savia (cm/h)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
                                        <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración real (mm/d)" stroke="#059669" strokeWidth={2} dot={false} />
                                        <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad savia (cm/h)" stroke="#0284c7" strokeWidth={1.5} dot={false} />
                                      </ComposedChart>
                                    ) : (
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0284c7" fontSize={10} tickLine={false} domain={[0, 45]} label={{ value: "Humedad θ (%)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={10} tickLine={false} domain={[0, 1]} label={{ value: "Estrés CWSI (0-1)", angle: 90, position: "insideRight", fill: "#e11d48", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad volumétrica θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.15} strokeWidth={1.8} />
                                        <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Índice estrés CWSI" stroke="#e11d48" strokeWidth={1.8} dot={false} />
                                        <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                        <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                      </ComposedChart>
                                    )}
                                  </ResponsiveContainer>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Modo STACK: Pila Vertical */}
                          {chartLayout === "STACK" && (
                            <div className="flex flex-col gap-4">
                              {/* Gráfico 1: Validación Mensual USGS */}
                              <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                  <div>
                                    <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                      Validación mensual: Aforo observado USGS vs Gemelo digital multiescala
                                    </h3>
                                    <p className="text-[11px] text-slate-500 mt-0.5">
                                      Contraste directo contra la estación USGS 05451210 en el exutorio del río South Fork Iowa.
                                    </p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("MONTHLY")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-60 w-full">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={monthlyComparisonData}>
                                      <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                      <XAxis dataKey="month" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                      <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#6b7280", fontSize: 10 }} />
                                      <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                                      <Line type="monotone" dataKey="observed_streamflow_m3s" name="Observado real (USGS)" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={2} dot={false} />
                                      <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base sin acoplar" stroke="#ea580c" strokeWidth={1.5} dot={false} />
                                      <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={2} dot={false} />
                                      <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Predicción híbrida ML" stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                                    </LineChart>
                                  </ResponsiveContainer>
                                </div>
                              </div>

                              {/* Gráfico 2: Hidrograma de Cuenca */}
                              <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                  <div>
                                    <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                      Hidrograma de cuenca: Caudal en exutorio y precipitación diaria
                                    </h3>
                                    <p className="text-[11px] text-slate-500 mt-0.5">
                                      Respuesta hidrológica superficial y recesión del caudal base ante eventos de lluvia.
                                    </p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("STREAMFLOW")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-60 w-full">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                                      <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando hidrograma...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0d9488" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Lluvia (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación diaria (mm)" fill="#0284c7" opacity={0.6} />
                                        <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.8} />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>

                              {/* Gráfico 3: Fisiología de Cultivo */}
                              <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                  <div>
                                    <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                      Fisiología vegetal: Transpiración foliar real vs demanda evaporativa (ET0) y flujo de savia
                                    </h3>
                                    <p className="text-[11px] text-slate-500 mt-0.5">
                                      Dinámica estomática del maíz acoplada con el flujo xilemático de la población celular.
                                    </p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("PLANT")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-60 w-full">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                                      <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando fisiología...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#059669" fontSize={10} tickLine={false} label={{ value: "Agua (mm/d)", angle: -90, position: "insideLeft", fill: "#059669", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Savia (cm/h)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
                                        <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración real (mm/d)" stroke="#059669" strokeWidth={2} dot={false} />
                                        <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad savia (cm/h)" stroke="#0284c7" strokeWidth={1.5} dot={false} />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>

                              {/* Gráfico 4: Dinámica de Suelo y CWSI */}
                              <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                  <div>
                                    <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                      Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés hídrico CWSI
                                    </h3>
                                    <p className="text-[11px] text-slate-500 mt-0.5">
                                      Umbrales de estrés: CWSI &gt; 0.25 déficit moderado; CWSI &gt; 0.50 cierre estomático crítico.
                                    </p>
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setExpandedChartModal("SOIL")}
                                    className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                  >
                                    <Maximize2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                                <div className="h-60 w-full">
                                  {isLoadingResults ? (
                                    <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                                      <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando suelo...
                                    </div>
                                  ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <ComposedChart data={chartData}>
                                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                        <YAxis yAxisId="left" stroke="#0284c7" fontSize={10} tickLine={false} domain={[0, 45]} label={{ value: "Humedad θ (%)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 10 }} />
                                        <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={10} tickLine={false} domain={[0, 1]} label={{ value: "Estrés CWSI (0-1)", angle: 90, position: "insideRight", fill: "#e11d48", fontSize: 10 }} />
                                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                        <Legend wrapperStyle={{ fontSize: "11px" }} />
                                        <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad volumétrica θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.15} strokeWidth={1.8} />
                                        <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Índice estrés CWSI" stroke="#e11d48" strokeWidth={1.8} dot={false} />
                                        <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                        <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                      </ComposedChart>
                                    </ResponsiveContainer>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}

                  {/* CONTENIDO DE LA SUB-PESTAÑA 2: DIAGNÓSTICO CIENTÍFICO (LANGCHAIN) */}
                  {simDetailTab === "AI" && (
                    <AIInsightsCard
                      key={selectedSim.id}
                      simulationId={selectedSim.id}
                      initialInsights={(selectedSim.provenance as Record<string, any>)?.ai_insights}
                    />
                  )}

                  {/* CONTENIDO DE LA SUB-PESTAÑA 3: ESPECIFICACIONES & PROCEDENCIA */}
                  {simDetailTab === "SPECIFICATIONS" && (
                    <div className="flex flex-col gap-4">
                      {/* Tarjetas de Transferencia de Escala */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                        <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                          <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                            <Sprout className="w-3.5 h-3.5 text-emerald-600" />
                            Micro a meso: Planta a parcela
                          </span>
                          <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                            <div>Población simulada: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.plant_count?.toLocaleString()} plantas FSPM</strong></div>
                            <div>Índice foliar medio: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.field_aggregates?.mean_lai ?? 0).toFixed(3)} m²/m²</strong></div>
                            <div>Profundidad radicular: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.field_aggregates?.mean_root_depth_cm ?? 0).toFixed(1)} cm</strong></div>
                          </div>
                        </div>

                        <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                          <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                            <Droplets className="w-3.5 h-3.5 text-blue-600" />
                            Meso a macro: Parcela a HRU
                          </span>
                          <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                            <div>Unidades de respuesta de suelo: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.hru_aggregates?.count ?? 0} HRUs</strong></div>
                            <div>Fracción de área de cuenca: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.hru_aggregates?.area_fraction_sum ?? 0).toFixed(2)}</strong></div>
                            <div>Número de curva SCS: <strong className="text-slate-800 dark:text-slate-200">CN = {(selectedSim as any).parameters?.curve_number ?? 74}</strong></div>
                          </div>
                        </div>

                        <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                          <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                            <Waves className="w-3.5 h-3.5 text-teal-600" />
                            Macro a aforo: Contraste USGS
                          </span>
                          <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                            <div>Estación de referencia: <strong className="text-slate-800 dark:text-slate-200">USGS {selectedSim.station_id || "05451210"}</strong></div>
                            <div>Meses alineados de aforo: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.aligned_months ?? 0} meses</strong></div>
                            <div>Reducción de RMSE vs baseline: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.improvement_percent?.value?.toFixed?.(2) ?? "0.00"}%</strong></div>
                          </div>
                        </div>
                      </div>

                      {/* Parámetros Criptográficos y Datos de Entrada */}
                      <div className="p-4 rounded-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-3 text-xs">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">
                            Auditoría de parámetros y procedencia
                          </span>
                          <span className="font-mono text-[10px] text-slate-400">
                            Identificador: {selectedSim.id}
                          </span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                          <div>
                            <span className="text-slate-400 block text-[10px]">Semilla estocástica</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">seed = {selectedSim.seed}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Motor numérico</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.hydrology_backend}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Fuente climática</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.climate_source || "SINTÉTICO"}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Duración total</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.duration_days} días</span>
                          </div>
                        </div>

                        {/* Detalle JSON de Procedencia */}
                        <details className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-slate-500">
                          <summary className="cursor-pointer font-medium hover:text-slate-800 dark:hover:text-slate-300">
                            Inspeccionar registro completo de procedencia (JSON)
                          </summary>
                          <pre className="mt-2 p-3 rounded-none bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto max-h-56">
                            {JSON.stringify(selectedSim.provenance, null, 2)}
                          </pre>
                        </details>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-12 rounded-none border border-dashed border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
                  Selecciona una corrida en la lista de la izquierda para desplegar sus series temporales y diagnóstico.
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

      {/* Modal Interactivo de Telemetría e Inspección Detallada */}
      {expandedChartModal && selectedSim && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
          <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
            {/* Cabecera del Modal de Gráfico */}
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                  {expandedChartModal === "MONTHLY" ? "Validación USGS" : expandedChartModal === "STREAMFLOW" ? "Escala Macro" : expandedChartModal === "PLANT" ? "Escala Micro" : "Escala Meso"}
                </span>
                <div>
                  <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                    {expandedChartModal === "MONTHLY" && "Validación mensual: Aforo observado USGS vs Gemelo digital multiescala"}
                    {expandedChartModal === "STREAMFLOW" && "Hidrograma de cuenca: Caudal en exutorio y precipitación diaria"}
                    {expandedChartModal === "PLANT" && "Fisiología vegetal: Transpiración foliar real vs demanda evaporativa (ET0) y flujo de savia"}
                    {expandedChartModal === "SOIL" && "Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés hídrico CWSI"}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Experimento: {selectedSim.name} · Periodo: {selectedSim.start_date || "2018-06-01"} a {selectedSim.end_date || "2018-08-31"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                <button
                  type="button"
                  onClick={() => setExpandedChartModal(null)}
                  className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                  title="Cerrar modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Cuerpo del Modal con Gráfico en Alta Resolución */}
            <div className="p-5 flex-1 min-h-0 flex flex-col gap-4 overflow-y-auto">
              <div className="h-80 sm:h-[400px] w-full bg-slate-50/40 dark:bg-slate-950/40 p-3 border border-slate-200 dark:border-slate-800">
                {isLoadingResults && expandedChartModal !== "MONTHLY" ? (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando telemetría en alta resolución...
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    {expandedChartModal === "MONTHLY" ? (
                      <LineChart data={monthlyComparisonData}>
                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                        <XAxis dataKey="month" stroke="#9ca3af" fontSize={11} tickLine={false} />
                        <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} label={{ value: "Caudal mensual (m³/s)", angle: -90, position: "insideLeft", fill: "#6b7280", fontSize: 11 }} />
                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "12px", color: "var(--foreground)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        <Line type="monotone" dataKey="observed_streamflow_m3s" name="Observado real (USGS 05451210)" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={2.5} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base sin acoplar" stroke="#ea580c" strokeWidth={2} dot={{ r: 3 }} />
                        <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo digital multiescala" stroke="#059669" strokeWidth={2.5} dot={{ r: 4 }} />
                        <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Predicción híbrida ML" stroke="#7c3aed" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
                      </LineChart>
                    ) : expandedChartModal === "STREAMFLOW" ? (
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={11} tickLine={false} />
                        <YAxis yAxisId="left" stroke="#0d9488" fontSize={11} tickLine={false} label={{ value: "Caudal descargado (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 11 }} />
                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={11} tickLine={false} label={{ value: "Precipitación diaria (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 11 }} />
                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "12px", color: "var(--foreground)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación diaria (mm)" fill="#0284c7" opacity={0.65} />
                        <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.18} strokeWidth={2.2} />
                      </ComposedChart>
                    ) : expandedChartModal === "PLANT" ? (
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={11} tickLine={false} />
                        <YAxis yAxisId="left" stroke="#059669" fontSize={11} tickLine={false} label={{ value: "Lámina de agua (mm/d)", angle: -90, position: "insideLeft", fill: "#059669", fontSize: 11 }} />
                        <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={11} tickLine={false} label={{ value: "Velocidad de savia (cm/h)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 11 }} />
                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "12px", color: "var(--foreground)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={2} dot={false} strokeDasharray="4 4" />
                        <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración real maíz (mm/d)" stroke="#059669" strokeWidth={2.5} dot={false} />
                        <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad de flujo xilemático (cm/h)" stroke="#0284c7" strokeWidth={2} dot={false} />
                      </ComposedChart>
                    ) : (
                      <ComposedChart data={chartData}>
                        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                        <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={11} tickLine={false} />
                        <YAxis yAxisId="left" stroke="#0284c7" fontSize={11} tickLine={false} domain={[0, 45]} label={{ value: "Humedad volumétrica θ (%)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 11 }} />
                        <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={11} tickLine={false} domain={[0, 1]} label={{ value: "Índice de estrés CWSI (0-1)", angle: 90, position: "insideRight", fill: "#e11d48", fontSize: 11 }} />
                        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "12px", color: "var(--foreground)" }} />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad volumétrica edáfica θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.2} strokeWidth={2.2} />
                        <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Índice de estrés hídrico CWSI" stroke="#e11d48" strokeWidth={2.2} dot={false} />
                        <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Umbral Déficit (0.25)", fill: "#f59e0b", fontSize: 10 }} />
                        <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "Cierre Estomático (0.50)", fill: "#ef4444", fontSize: 10 }} />
                      </ComposedChart>
                    )}
                  </ResponsiveContainer>
                )}
              </div>

              {/* Barra de Estadísticas Clave del Gráfico Expandido */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-xs font-mono">
                {expandedChartModal === "MONTHLY" ? (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Meses evaluados:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.aligned_months ?? 0} meses</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Reducción RMSE:</span><strong className="text-emerald-700 dark:text-emerald-400">{selectedSim.validation?.improvement_percent?.value?.toFixed?.(2) ?? "0.00"}%</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Criterio H1:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.criterion_met ? "CUMPLE (≥15%)" : "NO CUMPLE"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Estación:</span><strong className="text-slate-800 dark:text-slate-200">USGS 05451210</strong></div>
                  </>
                ) : expandedChartModal === "STREAMFLOW" ? (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Caudal pico:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.peak_streamflow_m3s != null ? `${Number(selectedSim.summary_metrics.peak_streamflow_m3s).toFixed(2)} m³/s` : "—"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Volumen descargado:</span><strong className="text-blue-700 dark:text-blue-400">{selectedSim.summary_metrics?.total_discharge_hm3 != null ? `${Number(selectedSim.summary_metrics.total_discharge_hm3).toFixed(1)} hm³` : "—"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Precipitación total:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.total_precip_mm != null ? `${Number(selectedSim.summary_metrics.total_precip_mm).toFixed(0)} mm` : "—"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Duración:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.duration_days} días</strong></div>
                  </>
                ) : expandedChartModal === "PLANT" ? (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Población modelada:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.plant_count?.toLocaleString()} plantas</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Evapotranspiración:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.total_actual_et_mm != null ? `${Number(selectedSim.summary_metrics.total_actual_et_mm).toFixed(1)} mm` : "—"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Índice foliar LAI:</span><strong className="text-emerald-700 dark:text-emerald-400">{Number(selectedSim.field_aggregates?.mean_lai ?? 0).toFixed(2)} m²/m²</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Rendimiento prox:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha != null ? `${Number(selectedSim.summary_metrics.seasonal_crop_yield_proxy_t_ha).toFixed(2)} t/ha` : "—"}</strong></div>
                  </>
                ) : (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Estrés medio CWSI:</span><strong className="text-amber-700 dark:text-amber-400">{selectedSim.summary_metrics?.mean_cwsi != null ? Number(selectedSim.summary_metrics.mean_cwsi).toFixed(3) : "—"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Umbral estrés crítico:</span><strong className="text-rose-700 dark:text-rose-400">CWSI &gt; 0.50</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Profundidad raíz:</span><strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.field_aggregates?.mean_root_depth_cm ?? 0).toFixed(1)} cm</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Número de curva SCS:</span><strong className="text-slate-800 dark:text-slate-200">CN = {(selectedSim as any).parameters?.curve_number ?? 74}</strong></div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Configuración de Corrida de Simulación */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-3 sm:p-6 overflow-hidden">
          <div className="w-full max-w-2xl max-h-[90vh] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-none shadow-none flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
            {/* Cabecera del Modal */}
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/40">
              <div>
                <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                  Configurar corrida de simulación
                </h3>
                <p className="text-[11px] text-slate-500">
                  Define la cuenca, periodo temporal, población de cultivo y motor hidrológico.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="w-7 h-7 rounded-none flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            {/* Formulario */}
            <form id="simulation-form" onSubmit={handleCreateSimulation} className="flex-1 min-h-0 overflow-y-auto p-5 flex flex-col gap-4 text-xs">
              {/* Sección 1: Identificación y Horizonte */}
              <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-col gap-3">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  1. Ámbito temporal y cuenca de estudio
                </span>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                    Nombre del experimento *
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Evaluación multiescala maíz con siembra directa SSP2-4.5"
                    className="w-full px-3 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-slate-400"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Cuenca hidrográfica
                    </label>
                    <select
                      value={formWatershedId}
                      onChange={(e) => {
                        const watershedId = e.target.value;
                        setFormWatershedId(watershedId);
                        const gauge = watersheds.find((w) => w.id === watershedId)?.dem_metadata?.gauge;
                        setFormStationId(typeof gauge === "string" ? gauge : "");
                      }}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      {watersheds.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name} ({w.area_km2} km²)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Estación USGS de aforo
                    </label>
                    <input
                      type="text"
                      value={formStationId}
                      onChange={(e) => setFormStationId(e.target.value)}
                      placeholder="05451210"
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                </div>

                {/* Presets de Periodo */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <label className="block text-slate-600 dark:text-slate-400 font-medium text-[11px]">
                    Horizonte temporal estandarizado
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
                    {SIMULATION_PERIOD_PRESETS.map((p) => {
                      const isSel = selectedPeriodPreset === p.id;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => handleSelectPeriodPreset(p)}
                          className={`p-2 rounded-none border text-left transition cursor-pointer flex flex-col justify-between ${
                            isSel
                              ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 border-slate-900 dark:border-slate-100 font-medium"
                              : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-300"
                          }`}
                        >
                          <span className="text-xs font-semibold">{p.label}</span>
                          <span className="text-[10px] opacity-75">{p.durationBadge}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Fecha de inicio
                    </label>
                    <input
                      type="date"
                      required
                      value={formStartDate}
                      onChange={(e) => handleStartDateChange(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Fecha de término
                    </label>
                    <input
                      type="date"
                      required
                      value={formEndDate}
                      onChange={(e) => setFormEndDate(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                </div>
              </div>

              {/* Sección 2: Motor Hidrológico y Clima */}
              <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-col gap-3">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  2. Motor numérico y escenario climático
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Motor hidrológico
                    </label>
                    <select
                      value={formHydrologyBackend}
                      onChange={(e) => changeHydrologyBackend(e.target.value as "SIMPLIFIED" | "SWAT_PLUS")}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-medium"
                    >
                      <option value="SIMPLIFIED">Gemelo Digital Multiescala Acoplado</option>
                      <option value="SWAT_PLUS" disabled={capabilities.swat_plus?.status !== "ACTIVE"}>
                        Simulador Físico SWAT+ ({capabilities.swat_plus?.status ?? "No disponible"})
                      </option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Escenario climático
                    </label>
                    <select
                      value={formScenarioId}
                      onChange={(e) => setFormScenarioId(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      {scenarios.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.code}: {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {formHydrologyBackend === "SWAT_PLUS" ? (
                  <div className="p-3 rounded-none border border-purple-200 dark:border-purple-900/60 bg-purple-50/50 dark:bg-purple-950/20 text-xs text-purple-900 dark:text-purple-200">
                    <span className="font-semibold block mb-1">Modalidad SWAT+</span>
                    <select
                      value={formSwatRunType}
                      onChange={(e) => setFormSwatRunType(e.target.value as SwatRunType)}
                      className="w-full rounded-none border border-purple-300 dark:border-purple-800 bg-white dark:bg-slate-950 px-2 py-1 text-xs text-slate-900 dark:text-slate-100"
                    >
                      <option value="SWAT_MULTISCALE_COUPLED">Acoplamiento bidireccional (Doble corrida con plants.plt)</option>
                      <option value="SWAT_STANDARD_BASELINE">Control SWAT+ físico sin sobreescritura</option>
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Fuente de forzamiento meteorológico
                    </label>
                    <select
                      value={formClimateSource}
                      onChange={(e) => setFormClimateSource(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value="SYNTHETIC">SYNTHETIC — Generador estocástico reproducible con estacionalidad de Iowa</option>
                      <option value="OBSERVED" disabled={!hasObservedForcing}>
                        OBSERVED — {hasObservedForcing ? "CHIRPS / GridMET observado disponible" : "Requiere dataset CHIRPS"}
                      </option>
                      <option value="CMIP6_FILE" disabled={!hasCmip6Forcing}>
                        CMIP6_FILE — {hasCmip6Forcing ? "Proyecciones NEX-GDDP-CMIP6" : "Requiere dataset CMIP6"}
                      </option>
                    </select>
                  </div>
                )}
              </div>

              {/* Sección 3: Fisiología de Cultivo y Parámetros */}
              <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-col gap-3">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  3. Fisiología vegetal y manejo agronómico
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Población de plantas
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10000}
                      value={formPlantCount}
                      onChange={(e) => setFormPlantCount(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Semilla aleatoria (Monte Carlo)
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={formSeed}
                      onChange={(e) => setFormSeed(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                    />
                  </div>
                </div>

                {usesSimplifiedModel && (
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Práctica agronómica de manejo
                    </label>
                    <select
                      value={formManagement}
                      onChange={(e) => setFormManagement(e.target.value as any)}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value="BASELINE">Maíz convencional (labranza tradicional)</option>
                      <option value="NO_TILL">Siembra directa / No-Till (mayor retención edáfica)</option>
                      <option value="MAIZE_TO_SORGHUM">Transición a sorgo (cultivo C4 tolerante a sequía)</option>
                    </select>
                  </div>
                )}
              </div>
            </form>

            {/* Pie Fijo del Modal */}
            <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 shrink-0 bg-slate-50 dark:bg-slate-950/60 flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 font-mono">
                {formHydrologyBackend === "SWAT_PLUS" ? "SWAT+ FÍSICO" : "GEMELO MULTIESCALA"}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-none border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  form="simulation-form"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-none bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-medium transition cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? "Ejecutando..." : "Ejecutar experimento"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

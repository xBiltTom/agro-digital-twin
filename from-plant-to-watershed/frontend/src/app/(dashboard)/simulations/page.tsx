"use client";

import React, { useCallback, useEffect, useState, useRef } from "react";
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
  DatasetInfo,
  CurrentFinalScientificReportResponse,
  AIInsightsResponse,
  SimulationCreatePayload,
  SimulationPreflightResponse,
  SwatComparisonMonth,
} from "../../../types/simulation";
import SwatRunEvidencePanel from "../../../components/scientific/SwatRunEvidencePanel";
import HypothesisValidationPanel from "../../../components/scientific/HypothesisValidationPanel";
import ClimateScenariosPanel from "../../../components/scientific/ClimateScenariosPanel";
import StatisticalBatteryPanel from "../../../components/scientific/StatisticalBatteryPanel";
import { AIInsightsCard } from "../../../components/simulations/AIInsightsCard";
import { classifySimulationEvidence, simulationEvidenceLabel } from "../../../lib/simulation-evidence";
import { datedMonthlyComparisonRows } from "../../../lib/simulation-chart-data";
import {
  Plus,
  RefreshCw,
  Search,
  X,
  ExternalLink,
  Layers,
  Sprout,
  Droplets,
  Waves,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Radio,
  FileText,
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

const DEFAULT_SIMPLIFIED_PARAMETERS = {
  base_kc: 1.05,
  max_root_depth_cm: 120,
  curve_number: 74,
  initial_soil_moisture_vol: 24.5,
  irrigation_mm_per_day: 0,
};

type SimplifiedParameterInputs = Record<keyof typeof DEFAULT_SIMPLIFIED_PARAMETERS, string>;

const INITIAL_SIMPLIFIED_PARAMETER_INPUTS: SimplifiedParameterInputs = {
  base_kc: String(DEFAULT_SIMPLIFIED_PARAMETERS.base_kc),
  max_root_depth_cm: String(DEFAULT_SIMPLIFIED_PARAMETERS.max_root_depth_cm),
  curve_number: String(DEFAULT_SIMPLIFIED_PARAMETERS.curve_number),
  initial_soil_moisture_vol: String(DEFAULT_SIMPLIFIED_PARAMETERS.initial_soil_moisture_vol),
  irrigation_mm_per_day: String(DEFAULT_SIMPLIFIED_PARAMETERS.irrigation_mm_per_day),
};

const PREFLIGHT_INPUT_LABELS: Record<string, string> = {
  "SWAT+ project forcing": "Clima configurado en el proyecto SWAT+",
  "SWAT+ project HRUs/soils/management": "HRU, suelo y manejo del proyecto SWAT+",
  "start_date": "Fecha inicial",
  "end_date": "Fecha final",
  "watershed area": "Área de la cuenca",
  "climate forcing": "Datos de clima",
  "seed": "Semilla de reproducibilidad",
  "plant_count": "Población de plantas",
  "base_kc": "Coeficiente de cultivo (Kc)",
  "max_root_depth_cm": "Profundidad máxima de raíces",
  "curve_number": "Número de curva SCS",
  "initial_soil_moisture_vol": "Humedad inicial del suelo",
  "irrigation_mm_per_day": "Riego diario",
  "management scenario": "Práctica de manejo",
  "plant population -> plants.plt": "Parámetros vegetales aplicados en SWAT+",
};

const PREFLIGHT_BLOCKER_LABELS: Record<string, string> = {
  SWAT_CONFIGURATION_MISSING: "El servidor no tiene configurados el ejecutable y el proyecto SWAT+.",
  SWAT_EXECUTABLE_NOT_FOUND: "El servidor no encuentra el ejecutable SWAT+.",
  SWAT_PROJECT_NOT_FOUND: "El servidor no encuentra el proyecto SWAT+.",
  SWAT_PROJECT_INVALID: "El proyecto SWAT+ tiene archivos requeridos ausentes o no válidos.",
  SWAT_CONTROL_FILES_MISSING: "El proyecto SWAT+ debe incluir time.sim y print.prt.",
  SWAT_WORK_DIRECTORY_NOT_WRITABLE: "El servidor no puede escribir en el directorio de trabajo SWAT+.",
  SWAT_WORKSPACE_DISK_SPACE_LOW: "El servidor no tiene suficiente espacio para copiar el proyecto SWAT+.",
  COUPLED_CROP_CONFIGURATION_INVALID: "No se pudo validar la configuración de manejo del cultivo para el acoplamiento.",
  COUPLED_FSPM_FORCING_INVALID: "Faltan datos climáticos diarios para completar el acoplamiento vegetal.",
};

function preflightBlockerLabel(blocker: string | { code?: string; message?: string }): string {
  if (typeof blocker === "string") {
    if (blocker.includes("NORMALIZED forcing artifact")) return "Elige un conjunto de datos climáticos preparado para una corrida.";
    if (blocker.includes("neutral catalog scenario")) return "El conjunto de datos ya contiene el clima y no hay un escenario neutro disponible para combinarlo.";
    return blocker;
  }
  return (blocker.code && PREFLIGHT_BLOCKER_LABELS[blocker.code]) || blocker.message || blocker.code || "El servidor no pudo validar este requisito.";
}

function preflightInputLabel(input: string): string {
  return PREFLIGHT_INPUT_LABELS[input] ?? input;
}

function climateSourceLabel(source: SimulationRun["climate_source"] | null | undefined): string {
  switch (source) {
    case undefined:
    case null: return "Origen no registrado";
    case "SYNTHETIC": return "Clima sintético";
    case "OBSERVED": return "Clima observado";
    case "CMIP6_FILE": return "Proyección CMIP6";
    case "OBSERVED_HYBRID": return "Clima observado híbrido";
    case "SWAT_PROJECT": return "Clima del proyecto SWAT+";
  }
}

interface PeriodPreset {
  id: "3M" | "4M" | "6M" | "1Y" | "5Y" | "CUSTOM";
  label: string;
  durationBadge: string;
  days: number;
  startDate: string;
  endDate: string;
  shortDesc: string;
}

const SIMULATION_PERIOD_PRESETS: PeriodPreset[] = [
  {
    id: "3M",
    label: "3 Meses",
    durationBadge: "92 días",
    days: 92,
    startDate: "2018-06-01",
    endDate: "2018-08-31",
    shortDesc: "Ventana crítica de floración y llenado de grano (Jun–Ago)",
  },
  {
    id: "4M",
    label: "4 Meses (Ciclo Maíz)",
    durationBadge: "123 días",
    days: 123,
    startDate: "2018-05-01",
    endDate: "2018-08-31",
    shortDesc: "Ciclo fenológico completo del cultivo de maíz (May–Ago)",
  },
  {
    id: "6M",
    label: "6 Meses",
    durationBadge: "183 días",
    days: 183,
    startDate: "2018-04-01",
    endDate: "2018-09-30",
    shortDesc: "Temporada agronómica estival completa (Abr–Sep)",
  },
  {
    id: "1Y",
    label: "1 Año Completo",
    durationBadge: "365 días",
    days: 365,
    startDate: "2018-01-01",
    endDate: "2018-12-31",
    shortDesc: "Año hidrológico continuo (Ene–Dic)",
  },
  {
    id: "5Y",
    label: "2018–2020",
    durationBadge: "1,096 días de evaluación",
    days: 1096,
    startDate: "2018-01-01",
    endDate: "2020-12-31",
    shortDesc: "Ventana de evaluación del informe vigente; una corrida nueva no reproduce automáticamente ese informe.",
  },
  {
    id: "CUSTOM",
    label: "A medida",
    durationBadge: "Fechas propias",
    days: 0,
    startDate: "",
    endDate: "",
    shortDesc: "El rango lo definen las fechas de inicio y término.",
  },
];

function MonthlyComparisonChart({
  rows,
  stationId,
}: {
  rows: SwatComparisonMonth[];
  stationId?: string | null;
}) {
  const chartRows = datedMonthlyComparisonRows(rows);
  const hasObserved = chartRows.some((row) => typeof row.observed_streamflow_m3s === "number");
  const hasBaseline = chartRows.some((row) => typeof row.baseline_streamflow_m3s === "number");
  const hasCoupled = chartRows.some((row) => typeof row.twin_streamflow_m3s === "number");
  const hasRunStreamflow = chartRows.some((row) => typeof row.streamflow_m3s === "number");
  const hasMl = chartRows.some((row) => typeof row.ml_assisted_streamflow_m3s === "number");

  if (!hasObserved && !hasBaseline && !hasCoupled && !hasRunStreamflow && !hasMl) {
    return (
      <div className="flex h-full items-center justify-center px-5 text-center text-xs text-slate-500 dark:text-slate-400">
        Esta corrida no incluye una serie mensual para comparar.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chartRows}>
        <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
        <XAxis dataKey="month" stroke="#9ca3af" fontSize={10} tickLine={false} />
        <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} />
        <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
        <Legend wrapperStyle={{ fontSize: "11px" }} />
        {hasObserved && <Line type="monotone" dataKey="observed_streamflow_m3s" name={stationId ? `USGS ${stationId} observado` : "Caudal observado"} stroke="#176b78" strokeWidth={2} dot={false} connectNulls={false} />}
        {hasBaseline && <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base SWAT+" stroke="#8a5d28" strokeWidth={1.5} dot={false} connectNulls={false} />}
        {hasCoupled && <Line type="monotone" dataKey="twin_streamflow_m3s" name="SWAT+ acoplado" stroke="#5f7c3d" strokeWidth={2} dot={false} connectNulls={false} />}
        {hasRunStreamflow && <Line type="monotone" dataKey="streamflow_m3s" name="Corrida seleccionada" stroke="#5f7c3d" strokeWidth={2} dot={false} connectNulls={false} />}
        {hasMl && <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Modelo ML" stroke="#68758a" strokeWidth={1.5} strokeDasharray="3 3" dot={false} connectNulls={false} />}
      </LineChart>
    </ResponsiveContainer>
  );
}

function isSwatBackend(simulation: SimulationRun) {
  return simulation.hydrology_backend === "SWAT_PLUS";
}

function runIncludesPlantPopulation(simulation: SimulationRun) {
  if (simulation.hydrology_backend === "SIMPLIFIED") return true;
  const swatConfig = simulation.requested_config?.swat_plus;
  const evidence = simulation.provenance && "evidence_type" in simulation.provenance
    ? simulation.provenance.evidence_type
    : undefined;
  return (typeof swatConfig === "object" && swatConfig !== null && "run_type" in swatConfig && swatConfig.run_type === "SWAT_MULTISCALE_COUPLED")
    || evidence === "REAL_SWAT_PLUS_COUPLED";
}

export default function SimulationsPage() {
  const { hasAnyRole } = useAuth();

  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSim, setSelectedSim] = useState<SimulationRun | null>(null);
  const [results, setResults] = useState<SimulationResult[]>([]);
  const [swatResults, setSwatResults] = useState<SwatResultsResponse | null>(null);
  const [scenarios, setScenarios] = useState<ClimateScenario[]>([]);
  const [watersheds, setWatersheds] = useState<Watershed[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, { status: string; evidence_type?: string }>>({});
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);

  // Navegación de vistas y disposición por modales
  const [activeTab, setActiveTab] = useState<"RUNS" | "VALIDATION" | "SCENARIOS" | "STATISTICS">("RUNS");
  const [activeModalTab, setActiveModalTab] = useState<"CHARTS" | "AI" | "SPECIFICATIONS" | null>(null);
  const [chartViewMode, setChartViewMode] = useState<"ALL" | "STREAMFLOW" | "PLANT" | "SOIL" | "MONTHLY">("STREAMFLOW");
  const [chartLayout, setChartLayout] = useState<"GRID" | "SPOTLIGHT" | "STACK">("GRID");
  const [expandedChartModal, setExpandedChartModal] = useState<"MONTHLY" | "STREAMFLOW" | "PLANT" | "SOIL" | null>(null);
  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false);

  // Listener para cerrar modales con tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveModalTab(null);
        setExpandedChartModal(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Estado colapsable para arquitectura del sistema
  const [showArchitectureOverview, setShowArchitectureOverview] = useState(false);

  // Búsqueda y filtrado
  const [simSearchTerm, setSimSearchTerm] = useState("");
  const [simFilterModel, setSimFilterModel] = useState<"ALL" | "SIMPLIFIED" | "SWAT">("ALL");

  // Estados de carga y modal
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPreflighting, setIsPreflighting] = useState(false);
  const [preflight, setPreflight] = useState<SimulationPreflightResponse | null>(null);
  const [preflightSignature, setPreflightSignature] = useState("");
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isLoadingFinalReport, setIsLoadingFinalReport] = useState(true);
  const [finalReportError, setFinalReportError] = useState<string | null>(null);

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
  const [formWarmupYears, setFormWarmupYears] = useState(3);
  const [formOutputFrequency, setFormOutputFrequency] = useState<"DAILY" | "MONTHLY" | "ANNUAL">("DAILY");
  const [formOutletUnit, setFormOutletUnit] = useState("");
  const [formClimateSource, setFormClimateSource] = useState<"SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "SWAT_PROJECT">("SYNTHETIC");
  const [formHydrologyBackend, setFormHydrologyBackend] = useState<"SIMPLIFIED" | "SWAT_PLUS">("SIMPLIFIED");
  const [formSwatRunType, setFormSwatRunType] = useState<SwatRunType>("SWAT_MULTISCALE_COUPLED");
  const [formParameters, setFormParameters] = useState<SimplifiedParameterInputs>(INITIAL_SIMPLIFIED_PARAMETER_INPUTS);
  const [formManagement, setFormManagement] = useState<"BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM">("BASELINE");
  const [formDatasetIds, setFormDatasetIds] = useState<string[]>([]);
  const [formForcingDatasetId, setFormForcingDatasetId] = useState("");
  const [formDatasetRoles, setFormDatasetRoles] = useState<Record<string, "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY">>({});

  // Transmisión WebSocket
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [liveTick, setLiveTick] = useState<TwinWebSocketTick | null>(null);
  const [wsSpeed, setWsSpeed] = useState(1);
  const wsRef = useRef<WebSocket | null>(null);

  const canRunSimulations = hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"]);
  const usesSimplifiedModel = formHydrologyBackend === "SIMPLIFIED";

  const changeHydrologyBackend = (backend: "SIMPLIFIED" | "SWAT_PLUS") => {
    setFormHydrologyBackend(backend);
    if (backend === "SWAT_PLUS") {
      setFormManagement("BASELINE");
      setFormClimateSource("SWAT_PROJECT");
      setFormForcingDatasetId("");
      const neutralScenario = scenarios.find((scenario) => scenario.temp_anomaly_c === 0 && scenario.precip_factor === 1);
      if (neutralScenario) setFormScenarioId(neutralScenario.id);
      setFormDatasetRoles((current) => Object.fromEntries(Object.keys(current).map((id) => [id, "CONTEXT_ONLY"])) as typeof current);
    } else if (formClimateSource === "SWAT_PROJECT") {
      setFormClimateSource("SYNTHETIC");
    }
  };

  const changeClimateSource = (source: "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "SWAT_PROJECT") => {
    setFormClimateSource(source);
    if (source !== "SYNTHETIC") {
      const neutralScenario = scenarios.find((scenario) => scenario.temp_anomaly_c === 0 && scenario.precip_factor === 1);
      if (neutralScenario) setFormScenarioId(neutralScenario.id);
    }
    setFormForcingDatasetId("");
    setFormDatasetIds([]);
    setFormDatasetRoles({});
  };

  const selectForcingDataset = (datasetId: string) => {
    setFormForcingDatasetId(datasetId);
    setFormDatasetIds(datasetId ? [datasetId] : []);
    setFormDatasetRoles(datasetId ? { [datasetId]: "FORCING" } : {});
  };

  const selectSimulation = useCallback(async (sim: SimulationRun) => {
    setSelectedSim(sim);
    setIsLoadingResults(true);
    setResultsError(null);
    setSwatResults(null);
    setResults([]);
    if (wsRef.current) {
      wsRef.current.close();
      setIsWsConnected(false);
      setLiveTick(null);
    }

    try {
      if (sim.status !== "COMPLETED") {
        setResultsError(sim.error?.message ?? `La corrida está ${sim.status.toLowerCase()}; aún no hay resultados para mostrar.`);
      } else if (isSwatBackend(sim)) {
        const normalizedSwat = await api.getSwatResults(sim.id);
        setSwatResults(normalizedSwat);
      } else {
        const dailyResults = await api.getSimulationResults(sim.id, sim.duration_days);
        setResults(dailyResults);
      }
    } catch (err: unknown) {
      setResultsError(err instanceof Error ? err.message : "No se pudieron cargar los resultados de esta corrida.");
    } finally {
      setIsLoadingResults(false);
    }
  }, []);

  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    setIsLoadingFinalReport(true);
    setFinalReport(null);
    setFinalReportError(null);
    try {
      const reportRequest = api.getFinalScientificReport()
        .then((report) => ({ report, error: null as string | null }))
        .catch((error: unknown) => ({
          report: null,
          error: error instanceof Error ? error.message : "No se pudo cargar el informe científico vigente.",
        }));
      const [simsData, scenData, watersData, capabilityData, datasetsData, reportResult] = await Promise.all([
        api.getSimulations(),
        api.getClimateScenarios(),
        api.getWatersheds(),
        api.getCapabilities(),
        api.getDatasets(),
        reportRequest,
      ]);
      setSimulations(simsData);
      setScenarios(scenData);
      setWatersheds(watersData);
      setCapabilities(capabilityData);
      setDatasets(datasetsData);
      setFinalReport(reportResult.report);
      setFinalReportError(reportResult.error);
      setIsLoadingFinalReport(false);

      if (watersData.length > 0) {
        setFormWatershedId(watersData[0].id);
        const gauge = watersData[0].dem_metadata?.gauge;
        if (typeof gauge === "string") setFormStationId(gauge);
      }
      if (scenData.length > 0) {
        const neutralScenario = scenData.find((scenario) => scenario.temp_anomaly_c === 0 && scenario.precip_factor === 1);
        setFormScenarioId((neutralScenario ?? scenData[0]).id);
      }

      if (simsData.length > 0) {
        selectSimulation(simsData[0]);
      }
    } catch (err: unknown) {
      setFeedbackMsg({ type: "error", text: err instanceof Error ? err.message : "Error al cargar datos de simulación" });
      setFinalReportError("No se pudo cargar el informe científico vigente.");
      setIsLoadingFinalReport(false);
    } finally {
      setIsLoading(false);
    }
  }, [selectSimulation]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadInitialData(), 0);
    return () => window.clearTimeout(timer);
  }, [loadInitialData]);

  const handleSelectPeriodPreset = (preset: PeriodPreset) => {
    setSelectedPeriodPreset(preset.id);
    if (preset.id === "CUSTOM") return;
    setFormStartDate(preset.startDate);
    setFormEndDate(preset.endDate);
  };

  const handleStartDateChange = (newStart: string) => {
    setFormStartDate(newStart);
    const preset = SIMULATION_PERIOD_PRESETS.find((p) => p.id === selectedPeriodPreset);
    if (preset && preset.id !== "CUSTOM" && newStart) {
      const startDateObj = new Date(`${newStart}T00:00:00Z`);
      if (!isNaN(startDateObj.getTime())) {
        const endDateObj = new Date(startDateObj.getTime() + (preset.days - 1) * 86_400_000);
        setFormEndDate(endDateObj.toISOString().split("T")[0]);
        return;
      }
    }
  };

  const handleEndDateChange = (newEnd: string) => {
    setSelectedPeriodPreset("CUSTOM");
    setFormEndDate(newEnd);
  };

  const buildSimulationPayload = (): SimulationCreatePayload | null => {
    const durationDays = formStartDate && formEndDate
      ? Math.floor((Date.parse(`${formEndDate}T00:00:00Z`) - Date.parse(`${formStartDate}T00:00:00Z`)) / 86_400_000) + 1
      : 0;
    if (durationDays < 1 || durationDays > 3650 || !formWatershedId || !formScenarioId) return null;
    if (usesSimplifiedModel && Object.values(formParameters).some((value) => !value.trim() || !Number.isFinite(Number(value)))) return null;

    const simplifiedParameters: Record<string, number> = {
      base_kc: Number(formParameters.base_kc),
      max_root_depth_cm: Number(formParameters.max_root_depth_cm),
      curve_number: Number(formParameters.curve_number),
      initial_soil_moisture_vol: Number(formParameters.initial_soil_moisture_vol),
      irrigation_mm_per_day: Number(formParameters.irrigation_mm_per_day),
    };

    return {
      name: formName,
      watershed_id: formWatershedId,
      scenario_id: formScenarioId,
      duration_days: durationDays,
      seed: formSeed,
      parameters: usesSimplifiedModel ? simplifiedParameters : {},
      mode: formHydrologyBackend === "SWAT_PLUS" ? "SWAT_PLUS" : "RESEARCH_MULTISCALE",
      plant_count: formPlantCount,
      hydrology_backend: formHydrologyBackend,
      management_scenario: formManagement,
      climate_source: formClimateSource,
      dataset_ids: formForcingDatasetId ? [formForcingDatasetId] : formDatasetIds,
      dataset_roles: formForcingDatasetId ? { [formForcingDatasetId]: "FORCING" } : formDatasetRoles,
      station_id: formStationId || undefined,
      start_date: formStartDate,
      end_date: formEndDate,
      swat_plus: formHydrologyBackend === "SWAT_PLUS" ? {
        run_type: formSwatRunType,
        output_frequency: formOutputFrequency,
        warmup_period: formWarmupYears,
        target_plant_name: "corn",
        outlet_unit: formOutletUnit || (watersheds.find((watershed) => watershed.id === formWatershedId)?.code.includes("05451210") ? "153" : undefined),
      } : undefined,
    };
  };

  const currentFormPayload = buildSimulationPayload();
  const currentPeriodPreset = SIMULATION_PERIOD_PRESETS.find((preset) => preset.id === selectedPeriodPreset);
  const maxSimulationEndDate = formStartDate
    ? new Date(Date.parse(`${formStartDate}T00:00:00Z`) + 3649 * 86_400_000).toISOString().slice(0, 10)
    : undefined;
  const currentPayloadSignature = currentFormPayload ? JSON.stringify(currentFormPayload) : "";
  const preflightMatchesCurrentForm = Boolean(
    preflight && currentPayloadSignature && preflightSignature === currentPayloadSignature,
  );
  const preflightReady = preflightMatchesCurrentForm && preflight?.status === "READY";

  const runPreflight = async () => {
    const payload = buildSimulationPayload();
    if (!payload) {
      setFeedbackMsg({ type: "error", text: "Completa los campos obligatorios y corrige los valores marcados." });
      return;
    }
    setIsPreflighting(true);
    setFeedbackMsg(null);
    try {
      const result = await api.preflightSimulation(payload);
      setPreflight(result);
      setPreflightSignature(JSON.stringify(payload));
      if (result.status === "BLOCKED") {
        setFeedbackMsg({ type: "error", text: "La configuración tiene requisitos pendientes. Revisa el detalle antes de ejecutar." });
      }
    } catch (err: unknown) {
      setPreflight(null);
      setPreflightSignature("");
      setFeedbackMsg({ type: "error", text: err instanceof Error ? err.message : "No se pudo validar la configuración." });
    } finally {
      setIsPreflighting(false);
    }
  };

  const handleCreateSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = buildSimulationPayload();
    if (!payload) {
      setFeedbackMsg({ type: "error", text: "Completa los campos obligatorios y corrige los valores marcados." });
      return;
    }
    if (!preflightReady || preflightSignature !== JSON.stringify(payload)) {
      await runPreflight();
      return;
    }

    setIsSubmitting(true);
    setFeedbackMsg(null);
    try {
      const newSim = await api.createSimulation(payload);
      setSimulations([newSim, ...simulations]);
      setIsModalOpen(false);
      setPreflight(null);
      setPreflightSignature("");
      setFeedbackMsg({ type: "success", text: `Experimento "${newSim.name}" guardado.` });
      selectSimulation(newSim);
    } catch (err: unknown) {
      setFeedbackMsg({ type: "error", text: err instanceof Error ? err.message : "No se pudo ejecutar la corrida." });
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
  const isSelectedSwatBackend = selectedSim ? isSwatBackend(selectedSim) : false;
  const selectedWatershed = selectedSim
    ? watersheds.find((watershed) => watershed.id === selectedSim.watershed_id)
    : undefined;
  const selectedGauge = selectedSim?.station_id ?? (
    typeof selectedWatershed?.dem_metadata?.gauge === "string"
      ? selectedWatershed.dem_metadata.gauge
      : null
  );
  const selectedPeriodLabel = selectedSim
    ? selectedSim.start_date && selectedSim.end_date
      ? `${selectedSim.start_date} a ${selectedSim.end_date}`
      : `Fechas no registradas · ${selectedSim.duration_days} días`
    : "";
  const selectedEvidence = selectedSim ? classifySimulationEvidence(selectedSim) : null;
  const requestedParameters = (selectedSim?.requested_config?.parameters as Record<string, unknown> | undefined) ?? {};
  const curveNumber = typeof requestedParameters.curve_number === "number" ? requestedParameters.curve_number : null;
  const criterionMet = selectedSim?.validation?.criterion_met;
  const meanLai = selectedSim?.field_aggregates?.mean_lai ?? selectedSim?.field_aggregates?.mean_LAI ?? null;
  const meanRootDepth = selectedSim?.field_aggregates?.mean_root_depth_cm != null
    ? `${Number(selectedSim.field_aggregates.mean_root_depth_cm).toFixed(1)} cm`
    : selectedSim?.field_aggregates?.mean_root_depth_m != null
      ? `${Number(selectedSim.field_aggregates.mean_root_depth_m).toFixed(2)} m`
      : "No disponible";
  const observedForcingDatasets = datasets.filter((dataset) =>
    ["CHIRPS", "OBSERVED_CLIMATE"].includes(dataset.provider) && dataset.normalized_artifact_count === 1,
  );
  const cmip6ForcingDatasets = datasets.filter((dataset) =>
    dataset.provider === "NEX-GDDP-CMIP6" && dataset.normalized_artifact_count === 1,
  );
  const hasObservedForcing = observedForcingDatasets.length > 0;
  const hasCmip6Forcing = cmip6ForcingDatasets.length > 0;
  const availableForcingDatasets = formClimateSource === "CMIP6_FILE" ? cmip6ForcingDatasets : observedForcingDatasets;

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
        ? isSwatBackend(sim)
        : !isSwatBackend(sim);
    return matchesSearch && matchesModel;
  });

  return (
    <div className="flex min-h-[calc(100vh-6rem)] w-full max-w-full flex-col">
      {/* 1. Barra de Navegación de Vistas y Acciones Principales */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-5 border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div>
          <h1 className="text-xl font-serif text-slate-900 dark:text-slate-100 tracking-tight">
            Consola de simulaciones ecohidrológicas
          </h1>
          <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
            Configura el motor, consulta sus resultados y revisa la procedencia de cada corrida.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {canRunSimulations && (
            <button
              type="button"
                  onClick={() => {
                    setPreflight(null);
                    setPreflightSignature("");
                    setFeedbackMsg(null);
                    setIsModalOpen(true);
                  }}
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
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 ${
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
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 ${
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
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 ${
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
          className={`px-3.5 py-2 font-medium border-b-2 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 ${
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
                   {isLoading ? "Consultando capacidades…" : `${Object.values(capabilities).filter((capability) => capability.status === "ACTIVE").length} capacidades activas reportadas por el backend`}
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
                  <span className="font-semibold text-slate-900 dark:text-slate-100 block mb-0.5">5. {formStationId ? `Aforo USGS ${formStationId}` : "Aforo de la cuenca"}</span>
                  Caudal descargado en exutorio y contraste contra aforos observados.
                </div>
              </div>
            </div>
          )}

          {/* 3. Área de Trabajo Principal: Catálogo (Izquierda) + Consola de Análisis (Derecha) */}
          <div className="flex-1 min-h-0 flex flex-col lg:flex-row items-stretch border-t border-slate-300 dark:border-slate-800">
            {/* Panel Izquierdo: Catálogo de Corridas Registradas (Colapsable) */}
            {!isCatalogCollapsed ? (
              <div className="w-full lg:w-80 xl:w-96 shrink-0 flex flex-col border-b lg:border-b-0 lg:border-r border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
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
              <div className="relative p-2.5 border-b border-slate-200 dark:border-slate-800 shrink-0">
                <Search className="w-3.5 h-3.5 absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={simSearchTerm}
                  onChange={(e) => setSimSearchTerm(e.target.value)}
                  placeholder="Filtrar por nombre o escenario..."
                  className="w-full pl-8 pr-7 py-1.5 text-xs rounded-none bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-slate-400"
                />
                {simSearchTerm && (
                  <button
                    type="button"
                    onClick={() => setSimSearchTerm("")}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Filtro por Modelo */}
              <div className="flex items-center gap-1 p-2 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 text-xs shrink-0">
                <button
                  type="button"
                  onClick={() => setSimFilterModel("ALL")}
                  className={`flex-1 py-1 text-[11px] font-mono rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "ALL"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  Todos ({simulations.length})
                </button>
                <button
                  type="button"
                  onClick={() => setSimFilterModel("SIMPLIFIED")}
                  className={`flex-1 py-1 text-[11px] font-mono rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "SIMPLIFIED"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  Simplificado ({simulations.filter((s) => !isSwatBackend(s)).length})
                </button>
                <button
                  type="button"
                  onClick={() => setSimFilterModel("SWAT")}
                  className={`flex-1 py-1 text-[11px] font-mono rounded-none text-center transition cursor-pointer ${
                    simFilterModel === "SWAT"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                      : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  }`}
                >
                  SWAT+ ({simulations.filter((s) => isSwatBackend(s)).length})
                </button>
              </div>

              {/* Lista de Experimentos */}
              <div className="p-2.5 space-y-1.5">
                {filteredSimulations.length === 0 ? (
                  <div className="p-6 text-center rounded-none border border-dashed border-slate-200 dark:border-slate-800 text-xs text-slate-400">
                    No se encontraron simulaciones que coincidan con la búsqueda.
                  </div>
                ) : (
                  filteredSimulations.map((sim) => {
                    const isSelected = selectedSim?.id === sim.id;
                    const evidence = classifySimulationEvidence(sim);
                    const includesPlantPopulation = runIncludesPlantPopulation(sim);
                    const statusLabel = sim.status === "COMPLETED" ? "Completada" : sim.status === "FAILED" ? "Fallida" : sim.status === "RUNNING" ? "En ejecución" : "Pendiente";
                    const statusTone = sim.status === "COMPLETED"
                      ? "text-emerald-700 dark:text-emerald-300"
                      : sim.status === "FAILED"
                        ? "text-rose-700 dark:text-rose-300"
                        : "text-slate-500 dark:text-slate-400";

                    const precipVal = sim.summary_metrics?.total_precip_mm ?? sim.summary_metrics?.total_precipitation_mm;
                    const precipStr = precipVal != null ? `${Number(precipVal).toFixed(0)} mm` : "No disponible";
                    const dischargeVal = sim.summary_metrics?.total_discharge_hm3;
                    const dischargeStr = dischargeVal != null ? `${Number(dischargeVal).toFixed(1)} hm³` : "No disponible";
                    const cwsiVal = sim.summary_metrics?.mean_cwsi;
                    const cwsiStr = cwsiVal != null ? Number(cwsiVal).toFixed(3) : "No disponible";

                    return (
                      <button
                        type="button"
                        key={sim.id}
                        onClick={() => selectSimulation(sim)}
                        aria-pressed={isSelected}
                        className={`w-full p-3 rounded-none border text-left cursor-pointer transition flex flex-col gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 ${
                          isSelected
                            ? "bg-slate-50 dark:bg-slate-800/60 border-slate-400 dark:border-slate-600 shadow-none"
                            : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                            {sim.name}
                          </span>
                          <span className={`shrink-0 text-[10px] font-medium ${statusTone}`} title={sim.error?.message}>
                            {statusLabel}
                          </span>
                        </div>

                        <span className="w-fit border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {simulationEvidenceLabel(evidence)}
                        </span>

                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                          <span>{sim.duration_days} días</span>
                          <span className="border-l border-slate-300 pl-2 dark:border-slate-700">
                            {includesPlantPopulation ? `${sim.plant_count?.toLocaleString() ?? "No disponible"} plantas` : "Sin modelo de planta"}
                          </span>
                          <span className="border-l border-slate-300 pl-2 dark:border-slate-700">{climateSourceLabel(sim.climate_source)}</span>
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-[11px] pt-2 border-t border-slate-100 dark:border-slate-800/80">
                          <span className="text-slate-500 dark:text-slate-400">Lluvia<strong className="mt-0.5 block font-mono font-medium text-slate-800 dark:text-slate-200">{precipStr}</strong></span>
                          <span className="text-slate-500 dark:text-slate-400">Descarga<strong className="mt-0.5 block font-mono font-medium text-slate-800 dark:text-slate-200">{dischargeStr}</strong></span>
                          <span className="text-slate-500 dark:text-slate-400">CWSI<strong className="mt-0.5 block font-mono font-medium text-slate-800 dark:text-slate-200">{cwsiStr}</strong></span>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
            ) : (
              <div className="w-full lg:w-10 shrink-0 border-b lg:border-b-0 lg:border-r border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-row lg:flex-col items-center justify-between lg:justify-start p-2 lg:py-3">
                <button
                  type="button"
                  onClick={() => setIsCatalogCollapsed(false)}
                  className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
                  title="Expandir catálogo de experimentos"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
                <div className="lg:mt-8 [writing-mode:horizontal-tb] lg:[writing-mode:vertical-rl] text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                  Catálogo ({filteredSimulations.length})
                </div>
              </div>
            )}

            {/* Panel Derecho: Consola de Trabajo del Experimento */}
            <div className="flex-1 min-w-0 flex flex-col bg-slate-50 dark:bg-slate-950">
              {selectedSim ? (
                <>
                  {/* Encabezado del Experimento Activo */}
                  <div className="p-3.5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2.5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h2 className="text-sm sm:text-base font-semibold text-slate-900 dark:text-slate-100">
                            {selectedSim.name}
                          </h2>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-none bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            {selectedSim.status === "COMPLETED" ? "Completada" : selectedSim.status === "FAILED" ? "Fallida" : selectedSim.status === "RUNNING" ? "En ejecución" : "Pendiente"}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-none bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            {selectedEvidence ? simulationEvidenceLabel(selectedEvidence) : "Procedencia no confirmada"}
                          </span>
                        </div>

                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                          <span>{selectedWatershed?.name ?? "Cuenca no especificada"}</span>
                          {selectedGauge && <span className="border-l border-slate-300 pl-3 dark:border-slate-700">USGS {selectedGauge}</span>}
                          <span className="border-l border-slate-300 pl-3 dark:border-slate-700">{selectedSim.scenario?.name ?? "Escenario no registrado"}</span>
                          <span className="border-l border-slate-300 pl-3 dark:border-slate-700">{selectedPeriodLabel}</span>
                        </div>
                      </div>

                      {/* Controles de Acción: 3D y WebSocket Scrubber */}
                      <div className="flex items-center gap-2 shrink-0 flex-wrap">
                        <Link
                          href={`/twin-3d?simId=${selectedSim.id}`}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-none border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
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

                    {resultsError && (
                      <div role="alert" className="border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                        {resultsError}
                      </div>
                    )}

                    {/* Barra de Reproducción en Vivo Sincronizada */}
                    {isWsConnected && liveTick && (
                      <div className="p-2.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/50 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
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
                    <dl className="grid grid-cols-2 border-y border-slate-200 bg-white text-xs divide-x divide-y divide-slate-200 sm:grid-cols-3 lg:grid-cols-6 lg:divide-y-0 dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Precipitación</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                          {(selectedSim.summary_metrics?.total_precip_mm ?? selectedSim.summary_metrics?.total_precipitation_mm) != null ? `${Number(selectedSim.summary_metrics?.total_precip_mm ?? selectedSim.summary_metrics?.total_precipitation_mm).toFixed(0)} mm` : "No disponible"}
                        </dd>
                      </div>

                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Evapotranspiración</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                          {selectedSim.summary_metrics?.total_actual_et_mm != null ? `${Number(selectedSim.summary_metrics.total_actual_et_mm).toFixed(1)} mm` : "No disponible"}
                        </dd>
                      </div>

                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Volumen en río</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-blue-700 dark:text-blue-400 mt-0.5">
                          {selectedSim.summary_metrics?.total_discharge_hm3 != null ? `${Number(selectedSim.summary_metrics.total_discharge_hm3).toFixed(1)} hm³` : "No disponible"}
                        </dd>
                      </div>

                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Caudal pico</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                          {selectedSim.summary_metrics?.peak_streamflow_m3s != null ? `${Number(selectedSim.summary_metrics.peak_streamflow_m3s).toFixed(2)} m³/s` : "No disponible"}
                        </dd>
                      </div>

                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Estrés CWSI</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-amber-700 dark:text-amber-400 mt-0.5">
                          {selectedSim.summary_metrics?.mean_cwsi != null ? Number(selectedSim.summary_metrics.mean_cwsi).toFixed(3) : "No disponible"}
                        </dd>
                      </div>

                      <div className="px-3 py-2">
                        <dt className="text-[11px] text-slate-500">Rendimiento estimado</dt>
                        <dd className="text-xs sm:text-sm font-semibold font-mono text-emerald-700 dark:text-emerald-400 mt-0.5">
                          {selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha != null ? `${Number(selectedSim.summary_metrics.seasonal_crop_yield_proxy_t_ha).toFixed(2)} t/ha` : "No disponible"}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  {/* Pestañas de la Consola de Trabajo (3 Botones que abren los Modales) */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800 shadow-xs">
                    <button
                      type="button"
                      onClick={() => setActiveModalTab("CHARTS")}
                      className="py-3 px-4 font-medium text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-blue-600 dark:hover:text-blue-400 transition flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Waves className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      <span>Series temporales e hidrograma</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveModalTab("AI")}
                      className="py-3 px-4 font-medium text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-emerald-600 dark:hover:text-emerald-400 transition flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      <span>Diagnóstico científico y políticas</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveModalTab("SPECIFICATIONS")}
                      className="py-3 px-4 font-medium text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-purple-600 dark:hover:text-purple-400 transition flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Layers className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      <span>Acoplamiento multiescala y procedencia</span>
                    </button>
                  </div>

                  {/* MODAL 1: SERIES TEMPORALES E HIDROGRAMA */}
                  {activeModalTab === "CHARTS" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-6xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de Series Temporales */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 font-semibold uppercase">
                              Modal 1
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Series temporales e hidrograma multiescala
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                {selectedSim.name} · {selectedPeriodLabel}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal (Esc)"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Cuerpo del Modal de Series Temporales */}
                        <div className="p-5 flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto">
                          {isLoadingResults ? (
                            <div role="status" className="flex min-h-48 items-center justify-center border border-slate-200 bg-white text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Consultando resultados de esta corrida…
                            </div>
                          ) : resultsError ? (
                            <div role="alert" className="border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                              {resultsError}
                            </div>
                          ) : isSelectedSwatBackend ? (
                            swatResults
                              ? <SwatRunEvidencePanel simulation={selectedSim} result={swatResults} />
                              : <div className="border border-slate-200 bg-white p-4 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">El backend no devolvió resultados SWAT+ para esta corrida.</div>
                          ) : chartData.length === 0 ? (
                            <div className="border border-slate-200 bg-white p-4 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">La corrida no tiene registros diarios disponibles.</div>
                          ) : (
                            <div className="flex flex-col gap-3">
                              {/* Barra de Control de Disposición */}
                              <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-slate-50/50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 text-xs">
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
                                      Series mensuales
                                    </button>
                                  </div>
                                )}
                              </div>

                              {/* Cuadrante 2x2 */}
                              {chartLayout === "GRID" && (
                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                                  {/* 1. Validación USGS */}
                                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                    <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold">Caudal</span>
                                          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Series mensuales disponibles</h3>
                                        </div>
                                          <p className="text-[10px] text-slate-500 truncate mt-0.5">
                                            {selectedGauge ? `Aforo USGS ${selectedGauge}` : "La corrida no declara una estación de aforo"}
                                          </p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("MONTHLY")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-48 sm:h-52 w-full p-2">
                                      <MonthlyComparisonChart rows={monthlyComparisonData} stationId={selectedGauge} />
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
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
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
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">Variables vegetales registradas por el modelo</p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("PLANT")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
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
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
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

                              {/* Modo SPOTLIGHT */}
                              {chartLayout === "SPOTLIGHT" && (
                                <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                  <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                    <div className="flex items-center gap-2">
                                      <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                                        {chartViewMode === "STREAMFLOW" ? "Escala Macro" : chartViewMode === "PLANT" ? "Escala Micro" : chartViewMode === "SOIL" ? "Escala Meso" : "Series mensuales"}
                                      </span>
                                      <h3 className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100">
                                        {chartViewMode === "STREAMFLOW" && "Hidrograma de cuenca: Caudal en exutorio y precipitación diaria"}
                                        {chartViewMode === "PLANT" && "Variables vegetales modeladas y demanda evaporativa (ET0)"}
                                        {chartViewMode === "SOIL" && "Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés CWSI"}
                                        {chartViewMode === "MONTHLY" && "Series mensuales de caudal disponibles"}
                                      </h3>
                                    </div>
                                    <button
                                      type="button"
                                       onClick={() => setExpandedChartModal(chartViewMode === "ALL" ? "STREAMFLOW" : chartViewMode)}
                                      className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer flex items-center gap-1 text-xs font-mono"
                                    >
                                      <Maximize2 className="w-3.5 h-3.5" />
                                      <span>Inspeccionar</span>
                                    </button>
                                  </div>

                                  <div className="h-72 sm:h-80 w-full p-3">
                                    {isLoadingResults && chartViewMode !== "MONTHLY" ? (
                                      <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando serie temporal...
                                      </div>
                                    ) : chartViewMode === "MONTHLY" ? (
                                      <MonthlyComparisonChart rows={monthlyComparisonData} stationId={selectedGauge} />
                                    ) : chartData.length === 0 ? (
                                      <div className="flex h-full items-center justify-center px-5 text-center text-xs text-slate-500">
                                        No hay registros diarios disponibles para esta corrida.
                                      </div>
                                    ) : (
                                      <ResponsiveContainer width="100%" height="100%">
                                        {chartViewMode === "STREAMFLOW" ? (
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
                                            <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración modelada (mm/d)" stroke="#059669" strokeWidth={2} dot={false} />
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
                                            <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Estrés CWSI" stroke="#e11d48" strokeWidth={1.8} dot={false} />
                                            <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                            <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                          </ComposedChart>
                                        )}
                                      </ResponsiveContainer>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Modo STACK */}
                              {chartLayout === "STACK" && (
                                <div className="flex flex-col gap-4">
                                  <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                      <div>
                                        <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                          Series mensuales de caudal
                                        </h3>
                                        <p className="text-[11px] text-slate-500 mt-0.5">
                                          {selectedGauge ? `Aforo USGS ${selectedGauge} y salidas del modelo disponibles.` : "La corrida no declara una estación de aforo."}
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
                                      <MonthlyComparisonChart rows={monthlyComparisonData} stationId={selectedGauge} />
                                    </div>
                                  </div>

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
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL 2: DIAGNÓSTICO CIENTÍFICO (LANGCHAIN) */}
                  {activeModalTab === "AI" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de IA */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200 font-semibold uppercase">
                              Modal 2 · IA
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Diagnóstico biofísico y recomendaciones de manejo
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                Experimento: {selectedSim.name} · Protocolo Ficha Técnica
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Contenido del Diagnóstico */}
                        <div className="p-5 flex-1 min-h-0 overflow-y-auto">
                          <AIInsightsCard
                            key={selectedSim.id}
                            simulationId={selectedSim.id}
                            initialInsights={(selectedSim.provenance as Record<string, unknown> | undefined)?.ai_insights as AIInsightsResponse | undefined}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL 3: ACOPLAMIENTO MULTIESCALA & PROCEDENCIA */}
                  {activeModalTab === "SPECIFICATIONS" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de Procedencia */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 font-semibold uppercase">
                              Modal 3 · Procedencia
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Acoplamiento multiescala y trazabilidad de procedencia
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                Identificador: {selectedSim.id} · Motor: {selectedSim.hydrology_backend}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Contenido de Procedencia */}
                        <div className="p-5 flex-1 min-h-0 flex flex-col gap-4 overflow-y-auto">
                          {/* Tarjetas de Transferencia de Escala */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Sprout className="w-3.5 h-3.5 text-emerald-600" />
                                Micro a meso: Planta a parcela
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Población: <strong className="text-slate-800 dark:text-slate-200">{runIncludesPlantPopulation(selectedSim) ? `${selectedSim.plant_count?.toLocaleString() ?? "No disponible"} plantas modeladas` : "Sin modelo FSPM en esta línea base"}</strong></div>
                                <div>Índice foliar: <strong className="text-slate-800 dark:text-slate-200">{meanLai != null ? `${Number(meanLai).toFixed(3)} m²/m²` : "No disponible"}</strong></div>
                                <div>Profundidad raíz: <strong className="text-slate-800 dark:text-slate-200">{meanRootDepth}</strong></div>
                              </div>
                            </div>

                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Droplets className="w-3.5 h-3.5 text-blue-600" />
                                Meso a macro: Parcela a HRU
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Unidades HRU: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.hru_aggregates?.count != null ? `${selectedSim.hru_aggregates.count} HRUs` : "No disponible"}</strong></div>
                                <div>Fracción área: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.hru_aggregates?.area_fraction_sum != null ? Number(selectedSim.hru_aggregates.area_fraction_sum).toFixed(2) : "No disponible"}</strong></div>
                                <div>Curva SCS: <strong className="text-slate-800 dark:text-slate-200">{curveNumber != null ? `CN = ${curveNumber}` : "No disponible"}</strong></div>
                              </div>
                            </div>

                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Waves className="w-3.5 h-3.5 text-teal-600" />
                                Macro a aforo: Contraste USGS
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Estación: <strong className="text-slate-800 dark:text-slate-200">{selectedGauge ? `USGS ${selectedGauge}` : "No registrada"}</strong></div>
                                <div>Meses aforo: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.aligned_months != null ? `${selectedSim.validation.aligned_months} meses` : "No disponible"}</strong></div>
                                <div>Reducción RMSE: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.improvement_percent?.value != null ? `${selectedSim.validation.improvement_percent.value.toFixed(2)}%` : "No disponible"}</strong></div>
                              </div>
                            </div>
                          </div>

                          {/* Parámetros Criptográficos y Datos de Entrada */}
                          <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-3 text-xs">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                              <span className="font-semibold text-slate-900 dark:text-slate-100">
                                Auditoría de parámetros y semillas
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                Semilla estocástica: {selectedSim.seed}
                              </span>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                              <div>
                                <span className="text-slate-400 block text-[10px]">Semilla</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">seed = {selectedSim.seed}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Motor físico</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.hydrology_backend}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Datos de clima</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{climateSourceLabel(selectedSim.climate_source)}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Duración</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.duration_days} días</span>
                              </div>
                            </div>

                            {/* Detalle JSON de Procedencia */}
                            <details className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-slate-500" open>
                              <summary className="cursor-pointer font-medium hover:text-slate-800 dark:hover:text-slate-300">
                                Registro completo de procedencia criptográfica (JSON)
                              </summary>
                              <pre className="mt-2 p-3 bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto max-h-64">
                                {JSON.stringify(selectedSim.provenance, null, 2)}
                              </pre>
                            </details>
                          </div>
                        </div>
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

      {activeTab !== "RUNS" && (
        <section className="mb-4 flex flex-col gap-2 border-l-2 border-l-emerald-700 bg-white px-4 py-3 dark:border-l-emerald-400 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Informe científico vigente del estudio</h2>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Estas vistas resumen el contrato publicado por el backend; no cambian al seleccionar otra corrida en el catálogo.
            </p>
          </div>
          <div className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
            {finalReport ? (
              <span>{finalReport.current_contract.contract_version} · {finalReport.current_contract.current_execution_status === "EXECUTED" ? "Ejecutado" : "Sin ejecución vigente"}</span>
            ) : (
              <span>{isLoadingFinalReport ? "Consultando informe…" : "Informe no disponible"}</span>
            )}
          </div>
        </section>
      )}

      {activeTab !== "RUNS" && !finalReport && (
        <div role={finalReportError ? "alert" : "status"} className="flex flex-col gap-3 border border-slate-300 bg-white p-5 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 sm:flex-row sm:items-center sm:justify-between">
          <p>
            {isLoadingFinalReport
              ? "Consultando el informe científico vigente…"
              : finalReportError ?? "El backend no tiene un informe científico vigente disponible."}
          </p>
          {!isLoadingFinalReport && (
            <button type="button" onClick={loadInitialData} className="w-fit border border-slate-300 px-3 py-1.5 font-medium hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:border-slate-700 dark:hover:bg-slate-800">
              Volver a consultar
            </button>
          )}
        </div>
      )}

      {activeTab === "VALIDATION" && finalReport && <HypothesisValidationPanel report={finalReport} />}
      {activeTab === "SCENARIOS" && finalReport && <ClimateScenariosPanel report={finalReport} />}
      {activeTab === "STATISTICS" && finalReport && <StatisticalBatteryPanel report={finalReport} />}

      {/* Modal Interactivo de Telemetría e Inspección Detallada */}
      {expandedChartModal && selectedSim && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
          <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
            {/* Cabecera del Modal de Gráfico */}
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                  {expandedChartModal === "MONTHLY" ? "Series mensuales" : expandedChartModal === "STREAMFLOW" ? "Escala Macro" : expandedChartModal === "PLANT" ? "Escala Micro" : "Escala Meso"}
                </span>
                <div>
                  <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                    {expandedChartModal === "MONTHLY" && "Series mensuales de caudal"}
                    {expandedChartModal === "STREAMFLOW" && "Hidrograma de cuenca: Caudal en exutorio y precipitación diaria"}
                    {expandedChartModal === "PLANT" && "Variables de planta: transpiración modelada, ET0 y flujo de savia"}
                    {expandedChartModal === "SOIL" && "Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés hídrico CWSI"}
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    {selectedSim.name} · {selectedPeriodLabel}
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
                {isLoadingResults ? (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                    <Loader2 className="w-5 h-5 animate-spin mr-2" /> Cargando telemetría en alta resolución...
                  </div>
                ) : resultsError ? (
                  <div role="alert" className="flex h-full items-center justify-center px-6 text-center text-xs text-amber-800 dark:text-amber-200">
                    {resultsError}
                  </div>
                ) : expandedChartModal === "MONTHLY" ? (
                  <MonthlyComparisonChart rows={monthlyComparisonData} stationId={selectedGauge} />
                ) : chartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center px-6 text-center text-xs text-slate-500">
                    No hay registros diarios disponibles para esta corrida.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    {expandedChartModal === "STREAMFLOW" ? (
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
                        <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración modelada (mm/d)" stroke="#059669" strokeWidth={2.5} dot={false} />
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
                    <div><span className="text-slate-400 block text-[10px]">Meses evaluados:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.aligned_months != null ? `${selectedSim.validation.aligned_months} meses` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Reducción RMSE:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.improvement_percent?.value != null ? `${selectedSim.validation.improvement_percent.value.toFixed(2)}%` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Criterio H1:</span><strong className="text-slate-800 dark:text-slate-200">{typeof criterionMet === "boolean" ? criterionMet ? "Cumple" : "No cumple" : "No evaluado"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Estación:</span><strong className="text-slate-800 dark:text-slate-200">{selectedGauge ? `USGS ${selectedGauge}` : "No registrada"}</strong></div>
                  </>
                ) : expandedChartModal === "STREAMFLOW" ? (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Caudal pico:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.peak_streamflow_m3s != null ? `${Number(selectedSim.summary_metrics.peak_streamflow_m3s).toFixed(2)} m³/s` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Volumen descargado:</span><strong className="text-blue-700 dark:text-blue-400">{selectedSim.summary_metrics?.total_discharge_hm3 != null ? `${Number(selectedSim.summary_metrics.total_discharge_hm3).toFixed(1)} hm³` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Precipitación total:</span><strong className="text-slate-800 dark:text-slate-200">{(selectedSim.summary_metrics?.total_precip_mm ?? selectedSim.summary_metrics?.total_precipitation_mm) != null ? `${Number(selectedSim.summary_metrics?.total_precip_mm ?? selectedSim.summary_metrics?.total_precipitation_mm).toFixed(0)} mm` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Duración:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.duration_days} días</strong></div>
                  </>
                ) : expandedChartModal === "PLANT" ? (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Población modelada:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.plant_count?.toLocaleString()} plantas</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Evapotranspiración:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.total_actual_et_mm != null ? `${Number(selectedSim.summary_metrics.total_actual_et_mm).toFixed(1)} mm` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Índice foliar LAI:</span><strong className="text-emerald-700 dark:text-emerald-400">{meanLai != null ? `${Number(meanLai).toFixed(2)} m²/m²` : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Rendimiento estimado:</span><strong className="text-slate-800 dark:text-slate-200">{selectedSim.summary_metrics?.seasonal_crop_yield_proxy_t_ha != null ? `${Number(selectedSim.summary_metrics.seasonal_crop_yield_proxy_t_ha).toFixed(2)} t/ha` : "No disponible"}</strong></div>
                  </>
                ) : (
                  <>
                    <div><span className="text-slate-400 block text-[10px]">Estrés medio CWSI:</span><strong className="text-amber-700 dark:text-amber-400">{selectedSim.summary_metrics?.mean_cwsi != null ? Number(selectedSim.summary_metrics.mean_cwsi).toFixed(3) : "No disponible"}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Umbral estrés crítico:</span><strong className="text-rose-700 dark:text-rose-400">CWSI &gt; 0.50</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Profundidad raíz:</span><strong className="text-slate-800 dark:text-slate-200">{meanRootDepth}</strong></div>
                    <div><span className="text-slate-400 block text-[10px]">Número de curva SCS:</span><strong className="text-slate-800 dark:text-slate-200">{curveNumber != null ? `CN = ${curveNumber}` : "No disponible"}</strong></div>
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
                  Revisa qué datos y motor usará el backend antes de crear la corrida.
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
                  1. Estudio y periodo
                </span>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                    Nombre del experimento *
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={150}
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="p. ej., Efecto de siembra directa en South Fork"
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
                        setFormOutletUnit("");
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
                </div>
                <p className="border-l-2 border-l-slate-300 pl-3 text-[11px] text-slate-600 dark:border-l-slate-700 dark:text-slate-400">
                  {formStationId
                    ? `Estación de aforo asociada: USGS ${formStationId}`
                    : "No hay una estación de aforo asociada a esta cuenca."}
                </p>

                {/* Presets de Periodo */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <label className="block text-slate-600 dark:text-slate-400 font-medium text-[11px]">
                    Periodo de interés
                  </label>
                  <select
                    aria-label="Periodo sugerido"
                    value={selectedPeriodPreset}
                    onChange={(event) => {
                      const preset = SIMULATION_PERIOD_PRESETS.find((item) => item.id === event.target.value);
                      if (preset) handleSelectPeriodPreset(preset);
                    }}
                    className="w-full border border-slate-200 bg-white px-2.5 py-2 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                  >
                    {SIMULATION_PERIOD_PRESETS.map((preset) => (
                      <option key={preset.id} value={preset.id}>{preset.label} · {preset.durationBadge}</option>
                    ))}
                  </select>
                  {currentPeriodPreset && <p className="text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{currentPeriodPreset.shortDesc}</p>}
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
                      max={maxSimulationEndDate}
                      value={formEndDate}
                      onChange={(e) => handleEndDateChange(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                </div>
              </div>

              {/* Sección 2: Motor Hidrológico y Clima */}
              <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-col gap-3">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  2. Método y datos de clima
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
                       <option value="SIMPLIFIED">Modelo simplificado</option>
                       <option value="SWAT_PLUS" disabled={capabilities.swat_plus?.status !== "ACTIVE"}>
                         SWAT+ {capabilities.swat_plus?.status === "ACTIVE" ? "(disponible)" : "(no disponible en este servidor)"}
                       </option>
                    </select>
                    <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
                      {usesSimplifiedModel
                        ? "Para explorar escenarios con una representación simplificada de planta y cuenca. No ejecuta SWAT+."
                        : "Ejecuta el proyecto SWAT+ configurado en este servidor."}
                    </p>
                  </div>

                  {formHydrologyBackend === "SIMPLIFIED" && formClimateSource === "SYNTHETIC" ? (
                    <div>
                      <label className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                        Cambio climático
                      </label>
                      <select
                        value={formScenarioId}
                        onChange={(event) => setFormScenarioId(event.target.value)}
                        className="w-full border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                      >
                        {scenarios.map((scenario) => (
                          <option key={scenario.id} value={scenario.id}>{scenario.name}</option>
                        ))}
                      </select>
                      <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                        {scenarios.find((scenario) => scenario.id === formScenarioId)?.description ?? "Elige un cambio climático para esta corrida."}
                      </p>
                    </div>
                  ) : (
                    <div className="flex items-center border-l-2 border-l-slate-300 pl-3 text-[11px] leading-relaxed text-slate-600 dark:border-l-slate-700 dark:text-slate-400">
                      {formHydrologyBackend === "SWAT_PLUS"
                        ? "El proyecto SWAT+ aporta el clima; no se aplican cambios del catálogo de escenarios."
                        : "El dataset aporta el clima; se usa un escenario neutro para no duplicar sus cambios."}
                    </div>
                  )}
                </div>

                {formHydrologyBackend === "SWAT_PLUS" ? (
                  <div className="p-3 rounded-none border border-purple-200 dark:border-purple-900/60 bg-purple-50/50 dark:bg-purple-950/20 text-xs text-purple-900 dark:text-purple-200">
                    <span className="font-semibold block mb-1">Tipo de ejecución</span>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <select
                        aria-label="Modalidad SWAT+"
                        value={formSwatRunType}
                        onChange={(e) => setFormSwatRunType(e.target.value as SwatRunType)}
                        className="w-full rounded-none border border-purple-300 bg-white px-2 py-1 text-xs text-slate-900 dark:border-purple-800 dark:bg-slate-950 dark:text-slate-100"
                      >
                        <option value="SWAT_MULTISCALE_COUPLED">SWAT+ con acoplamiento de cultivo</option>
                        <option value="SWAT_STANDARD_BASELINE">SWAT+ sin acoplamiento</option>
                      </select>
                      <label className="flex items-center justify-between gap-2 text-[11px]">
                        <span>Años previos para estabilizar el modelo</span>
                        <input
                          type="number"
                          min={0}
                          max={36500}
                          value={formWarmupYears}
                          onChange={(event) => setFormWarmupYears(Number(event.target.value))}
                          className="w-24 border border-purple-300 bg-white px-2 py-1 font-mono text-xs text-slate-900 dark:border-purple-800 dark:bg-slate-950 dark:text-slate-100"
                        />
                      </label>
                    </div>
                    <p className="mt-2 text-[11px] leading-relaxed text-purple-800 dark:text-purple-200">
                      SWAT+ empieza antes del periodo elegido. Estos años ayudan a estabilizar el modelo y no se incluyen en los resultados mostrados.
                    </p>
                  </div>
                ) : (
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Datos meteorológicos
                    </label>
                    <select
                      value={formClimateSource}
                      onChange={(e) => changeClimateSource(e.target.value as "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "SWAT_PROJECT")}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value="SYNTHETIC">Clima sintético (generado para explorar)</option>
                      <option value="OBSERVED" disabled={!hasObservedForcing}>
                        Datos observados {!hasObservedForcing && "(no disponibles)"}
                      </option>
                      <option value="CMIP6_FILE" disabled={!hasCmip6Forcing}>
                        Proyección climática {!hasCmip6Forcing && "(no disponible)"}
                      </option>
                    </select>
                  </div>
                )}

                {formHydrologyBackend === "SIMPLIFIED" && ["OBSERVED", "CMIP6_FILE"].includes(formClimateSource) && (
                  <div>
                    <label htmlFor="forcing-dataset" className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                      Datos climáticos
                    </label>
                    <select
                      id="forcing-dataset"
                      required
                      value={formForcingDatasetId}
                      onChange={(event) => selectForcingDataset(event.target.value)}
                      className="w-full border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
                    >
                      <option value="">Elige un conjunto de datos</option>
                      {availableForcingDatasets.map((dataset) => (
                        <option key={dataset.id} value={dataset.id}>
                          {dataset.dataset_name}{dataset.version ? ` · versión ${dataset.version}` : ""}
                        </option>
                      ))}
                    </select>
                    {availableForcingDatasets.length === 0 && (
                      <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-300">
                        No hay un conjunto de datos preparado para esta fuente. Revísalo en el <Link href="/datasets" className="font-semibold underline">Catálogo de datos</Link>.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Sección 3: Fisiología de Cultivo y Parámetros */}
              <div className="p-3.5 rounded-none border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex flex-col gap-3">
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  3. Cultivo y manejo
                </span>

                {(usesSimplifiedModel || formSwatRunType === "SWAT_MULTISCALE_COUPLED") && (
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Plantas representadas en el cultivo
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10000}
                      value={formPlantCount}
                      onChange={(e) => setFormPlantCount(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                    />
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Representantes usados por el modelo de cultivo; no son un conteo observado en campo.
                    </p>
                  </div>
                )}

                {usesSimplifiedModel && (
                  <div>
                    <label className="block text-slate-600 dark:text-slate-400 mb-1 font-medium text-[11px]">
                      Práctica de manejo
                    </label>
                    <select
                      value={formManagement}
                      onChange={(e) => setFormManagement(e.target.value as "BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM")}
                      className="w-full px-2.5 py-1.5 text-xs rounded-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value="BASELINE">Manejo base de maíz</option>
                      <option value="NO_TILL">Siembra directa (aproximación simplificada)</option>
                      <option value="MAIZE_TO_SORGHUM">Sorgo en lugar de maíz (aproximación)</option>
                    </select>
                  </div>
                )}
              </div>

              <details className="border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
                <summary className="cursor-pointer px-3.5 py-3 text-xs font-semibold text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600 dark:text-slate-200">
                  Opciones avanzadas y reproducibilidad
                </summary>
                <div className="grid grid-cols-1 gap-4 border-t border-slate-200 p-3.5 dark:border-slate-800 md:grid-cols-2">
                  {(usesSimplifiedModel || formSwatRunType === "SWAT_MULTISCALE_COUPLED") && (
                    <div>
                      <label htmlFor="simulation-seed" className="mb-1 block text-[11px] font-medium text-slate-600 dark:text-slate-400">
                        Semilla para repetir la misma corrida
                      </label>
                      <input
                        id="simulation-seed"
                        type="number"
                        min={0}
                        max={4294967295}
                        value={formSeed}
                        onChange={(event) => setFormSeed(Number(event.target.value))}
                        className="w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100"
                      />
                    </div>
                  )}

                  {usesSimplifiedModel && (
                    <>
                      <p className="text-[11px] leading-relaxed text-slate-500 dark:text-slate-400 md:col-span-2">
                        Parámetros del modelo simplificado. Déjalos como están si no necesitas modificar la configuración científica.
                      </p>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Coeficiente de cultivo (Kc)
                        <input type="number" required min={0.1} max={2} step={0.01} value={formParameters.base_kc}
                          onChange={(event) => setFormParameters((current) => ({ ...current, base_kc: event.target.value }))}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Profundidad máxima de raíces (cm)
                        <input type="number" required min={1} max={500} step={1} value={formParameters.max_root_depth_cm}
                          onChange={(event) => setFormParameters((current) => ({ ...current, max_root_depth_cm: event.target.value }))}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Número de curva SCS
                        <input type="number" required min={30} max={98} step={1} value={formParameters.curve_number}
                          onChange={(event) => setFormParameters((current) => ({ ...current, curve_number: event.target.value }))}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Humedad inicial del suelo (%)
                        <input type="number" required min={0} max={44} step={0.1} value={formParameters.initial_soil_moisture_vol}
                          onChange={(event) => setFormParameters((current) => ({ ...current, initial_soil_moisture_vol: event.target.value }))}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Riego diario (mm/día)
                        <input type="number" required min={0} max={100} step={0.1} value={formParameters.irrigation_mm_per_day}
                          onChange={(event) => setFormParameters((current) => ({ ...current, irrigation_mm_per_day: event.target.value }))}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                    </>
                  )}

                  {formHydrologyBackend === "SWAT_PLUS" && (
                    <>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Frecuencia de resultados SWAT+
                        <select value={formOutputFrequency} onChange={(event) => setFormOutputFrequency(event.target.value as "DAILY" | "MONTHLY" | "ANNUAL")}
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100">
                          <option value="DAILY">Diaria</option>
                          <option value="MONTHLY">Mensual</option>
                          <option value="ANNUAL">Anual</option>
                        </select>
                      </label>
                      <label className="text-[11px] text-slate-600 dark:text-slate-400">
                        Unidad de salida (opcional)
                        <input value={formOutletUnit} onChange={(event) => setFormOutletUnit(event.target.value)} placeholder="Automática según cuenca"
                          className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                      </label>
                    </>
                  )}

                  {formHydrologyBackend === "SIMPLIFIED" && (
                    <label className="text-[11px] text-slate-600 dark:text-slate-400">
                      Estación USGS (opcional)
                        <input value={formStationId} onChange={(event) => setFormStationId(event.target.value)} minLength={8} maxLength={15} pattern="\d{8,15}" placeholder="Usar estación asociada a la cuenca"
                        className="mt-1 w-full border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100" />
                    </label>
                  )}
                </div>
              </details>

              {preflightMatchesCurrentForm && preflight && (
                <section
                  role={preflight.status === "READY" ? "status" : "alert"}
                  className={`border-l-2 p-3.5 text-xs ${preflight.status === "READY"
                    ? "border-emerald-700 bg-emerald-50 text-emerald-950 dark:border-emerald-400 dark:bg-emerald-950/30 dark:text-emerald-100"
                    : "border-amber-600 bg-amber-50 text-amber-950 dark:border-amber-400 dark:bg-amber-950/30 dark:text-amber-100"
                  }`}
                >
                  <h4 className="font-semibold">
                    {preflight.status === "READY" ? "Configuración lista" : "Hay requisitos pendientes"}
                  </h4>
                  {preflight.blockers && preflight.blockers.length > 0 && (
                    <ul className="mt-2 list-disc space-y-1 pl-4">
                      {preflight.blockers.map((blocker, index) => (
                        <li key={`${index}-${typeof blocker === "string" ? blocker : blocker.code ?? blocker.message ?? index}`}>
                          {preflightBlockerLabel(blocker)}
                        </li>
                      ))}
                    </ul>
                  )}
                  {preflight.status === "BLOCKED" && (!preflight.blockers || preflight.blockers.length === 0) && (
                    <p className="mt-2">El servidor no pudo validar esta configuración. Revisa los datos y vuelve a intentarlo.</p>
                  )}
                  {preflight.status === "READY" && (
                    <div className="mt-2 space-y-1">
                      {preflight.estimated_executions != null && preflight.estimated_executions > 1 && (
                        <p>Para preparar esta corrida, SWAT+ hará {preflight.estimated_executions} ejecuciones internas.</p>
                      )}
                      {preflight.will_consume && preflight.will_consume.length > 0 && (
                        <p><span className="font-semibold">El modelo usará:</span> {preflight.will_consume.map(preflightInputLabel).join(", ")}.</p>
                      )}
                      {preflight.provenance_only && preflight.provenance_only.length > 0 && (
                        <p><span className="font-semibold">Solo como referencia:</span> {preflight.provenance_only.join(", ")}.</p>
                      )}
                    </div>
                  )}
                </section>
              )}
            </form>

            {/* Pie Fijo del Modal */}
            <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 shrink-0 bg-slate-50 dark:bg-slate-950/60 flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 font-mono">
                {formHydrologyBackend === "SWAT_PLUS" ? "Método: SWAT+" : `Método: modelo simplificado; ${climateSourceLabel(formClimateSource)}`}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false);
                    setPreflight(null);
                    setPreflightSignature("");
                  }}
                  className="px-3.5 py-1.5 rounded-none border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  form="simulation-form"
                  disabled={isSubmitting || isPreflighting}
                  className="px-4 py-1.5 rounded-none bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-medium transition cursor-pointer disabled:cursor-wait disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                >
                  {isPreflighting ? "Comprobando…" : isSubmitting ? "Ejecutando corrida…" : preflightReady ? "Ejecutar corrida" : "Revisar antes de ejecutar"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

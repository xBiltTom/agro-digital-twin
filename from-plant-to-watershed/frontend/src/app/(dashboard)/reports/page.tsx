"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { api } from "../../../lib/api";
import { classifySimulationEvidence, simulationEvidenceLabel } from "../../../lib/simulation-evidence";
import type {
  CurrentFinalScientificReportResponse,
  GeneratedReportHistoryEntry,
  SimulationRun,
} from "../../../types/simulation";

type ExportFormat = "pdf" | "docx" | "xlsx";
type PageMessage = { type: "success" | "error"; text: string };

const EXPORTS: Array<{
  format: ExportFormat;
  label: string;
  description: string;
  icon: typeof FileText;
}> = [
  {
    format: "pdf",
    label: "PDF",
    description: "Informe técnico para consulta",
    icon: FileText,
  },
  {
    format: "docx",
    label: "Word",
    description: "Documento editable",
    icon: FileText,
  },
  {
    format: "xlsx",
    label: "Excel",
    description: "Indicadores y registros guardados",
    icon: FileSpreadsheet,
  },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function firstNumber(...values: unknown[]): number | null {
  return values.find(
    (value): value is number => typeof value === "number" && Number.isFinite(value),
  ) ?? null;
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "No disponible";
  return new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatDate(value?: string | null): string {
  if (!value) return "Fecha no registrada";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no registrada";
  return new Intl.DateTimeFormat("es-PE", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function formatRunPeriod(run: SimulationRun): string {
  if (run.start_date && run.end_date) return `${run.start_date} a ${run.end_date}`;
  return `${run.duration_days} días · fechas no registradas`;
}

function climateSourceLabel(source?: SimulationRun["climate_source"]): string {
  switch (source) {
    case "SYNTHETIC": return "Clima sintético";
    case "OBSERVED": return "Clima observado";
    case "CMIP6_FILE": return "Archivo CMIP6";
    case "OBSERVED_HYBRID": return "Clima observado híbrido";
    case "SWAT_PROJECT": return "Proyecto SWAT+";
    default: return "Origen climático no registrado";
  }
}

function runStatusLabel(status: SimulationRun["status"]): string {
  switch (status) {
    case "COMPLETED": return "Completada";
    case "RUNNING": return "En ejecución";
    case "FAILED": return "Fallida";
    default: return "Pendiente";
  }
}

function runStatusTone(status: SimulationRun["status"]): string {
  switch (status) {
    case "COMPLETED": return "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200";
    case "FAILED": return "border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-200";
    case "RUNNING": return "border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200";
    default: return "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300";
  }
}

function runMetrics(run: SimulationRun) {
  const metrics = asRecord(run.summary_metrics);
  const waterBalance = asRecord(metrics.water_balance);
  const totals = asRecord(waterBalance.totals_mm);

  return [
    {
      label: "Precipitación acumulada",
      value: firstNumber(metrics.total_precip_mm, totals.precip_mm),
      unit: "mm",
    },
    {
      label: "Evapotranspiración",
      value: firstNumber(metrics.total_actual_et_mm, metrics.total_evapotranspiration_mm, totals.evapotranspiration_mm),
      unit: "mm",
    },
    {
      label: "Escorrentía",
      value: firstNumber(metrics.total_surface_runoff_mm, metrics.total_runoff_mm, totals.runoff_mm),
      unit: "mm",
    },
    {
      label: "Caudal medio",
      value: firstNumber(metrics.mean_streamflow_m3s, waterBalance.mean_streamflow_m3s),
      unit: "m³/s",
    },
  ];
}

function conclusionLabel(value?: string): string {
  if (value === "H1_NOT_SUPPORTED") return "La hipótesis H1 no está respaldada";
  if (value === "H1_SUPPORTED") return "La hipótesis H1 está respaldada";
  if (value === "INSUFFICIENT_EVIDENCE") return "La evidencia todavía es insuficiente";
  return value?.replaceAll("_", " ") ?? "Conclusión no disponible";
}

function hypothesisCopy(value: string): string {
  if (value.toLowerCase().includes("reduces monthly rmse by at least 15%")) {
    return "H1 plantea reducir al menos 15 % el RMSE mensual.";
  }
  return value;
}

function couplingEffectLabel(value: string): string {
  if (value === "ZERO_WITH_CURRENT_PARAMETERIZATION") return "sin cambio con la parametrización actual";
  return value.replaceAll("_", " ").toLowerCase();
}

function hypothesisTone(value?: string): string {
  if (value === "H1_SUPPORTED") return "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200";
  if (value === "H1_NOT_SUPPORTED" || value === "INSUFFICIENT_EVIDENCE") {
    return "border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100";
  }
  return "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200";
}

function imputationLabel(value?: string): string {
  if (value === "NONE") return "sin imputación";
  if (!value) return "imputación no registrada";
  return value.replaceAll("_", " ").toLowerCase();
}

function scenarioLabel(value: string): string {
  const labels: Record<string, string> = {
    MAIZE_TO_SORGHUM: "Maíz por sorgo",
    NO_TILL: "Labranza cero",
    PRECIPITATION_MINUS_15PCT: "Precipitación −15 %",
    TEMPERATURE_PLUS_2C: "Temperatura +2 °C",
  };
  return labels[value] ?? value.replaceAll("_", " ").toLowerCase();
}

function reportFormatLabel(format: string): string {
  switch (format.toLowerCase()) {
    case "pdf": return "PDF";
    case "docx": return "Word";
    case "xlsx": return "Excel";
    default: return format.toUpperCase();
  }
}

export default function ReportsPage() {
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSimId, setSelectedSimId] = useState("");
  const [history, setHistory] = useState<GeneratedReportHistoryEntry[]>([]);
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [simulationsError, setSimulationsError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [finalReportError, setFinalReportError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<ExportFormat | null>(null);
  const [pageMessage, setPageMessage] = useState<PageMessage | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setSimulations([]);
    setHistory([]);
    setFinalReport(null);
    setSimulationsError(null);
    setHistoryError(null);
    setFinalReportError(null);

    const [simulationsResult, historyResult, reportResult] = await Promise.allSettled([
      api.getSimulations(),
      api.getReportsHistory(),
      api.getFinalScientificReport(),
    ]);

    if (simulationsResult.status === "fulfilled") {
      setSimulations(simulationsResult.value);
      setSelectedSimId((current) =>
        simulationsResult.value.some((run) => run.id === current)
          ? current
          : simulationsResult.value[0]?.id ?? "",
      );
    } else {
      setSimulationsError(simulationsResult.reason instanceof Error ? simulationsResult.reason.message : "No se pudieron cargar las corridas.");
    }

    if (historyResult.status === "fulfilled") {
      setHistory(historyResult.value);
    } else {
      setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "No se pudo cargar el historial.");
    }

    if (reportResult.status === "fulfilled") {
      setFinalReport(reportResult.value);
    } else {
      setFinalReportError(reportResult.reason instanceof Error ? reportResult.reason.message : "No se pudo consultar el informe científico vigente.");
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadData(), 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  const selectedSim = useMemo(
    () => simulations.find((run) => run.id === selectedSimId) ?? null,
    [selectedSimId, simulations],
  );
  const currentResult = finalReport?.current_result ?? null;
  const contractWasExecuted =
    finalReport?.current_contract.current_execution_status === "EXECUTED" && currentResult !== null;
  const canExport = selectedSim?.status === "COMPLETED" && selectedSim.hydrology_backend === "SIMPLIFIED";

  const handleDownload = async (format: ExportFormat) => {
    if (!selectedSim || !canExport) return;
    setDownloadingFormat(format);
    setPageMessage(null);

    try {
      await api.downloadReport(selectedSim.id, format);
      setPageMessage({ type: "success", text: `El archivo ${format.toUpperCase()} se descargó.` });
      try {
        setHistory(await api.getReportsHistory());
        setHistoryError(null);
      } catch (error) {
        setHistoryError(error instanceof Error ? error.message : "No se pudo actualizar el historial.");
      }
    } catch (error) {
      setPageMessage({
        type: "error",
        text: error instanceof Error ? error.message : `No se pudo generar el archivo ${format.toUpperCase()}.`,
      });
    } finally {
      setDownloadingFormat(null);
    }
  };

  const exportAvailability = !selectedSim
    ? "Selecciona una corrida completada para revisar sus opciones de exportación."
    : selectedSim.status !== "COMPLETED"
      ? `La corrida está ${runStatusLabel(selectedSim.status).toLowerCase()}; los archivos estarán disponibles al completarse.`
      : selectedSim.hydrology_backend !== "SIMPLIFIED"
        ? "El exportador multiformato aún no representa resultados SWAT+. La corrida conserva sus resultados en Simulaciones."
        : "El exportador incluye los indicadores y los registros diarios guardados para esta corrida.";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-7 pb-12">
      <header className="flex flex-col justify-between gap-4 border-b border-slate-300 pb-5 sm:flex-row sm:items-end dark:border-slate-800">
        <div>
          <h1 className="font-serif text-2xl tracking-tight text-slate-900 sm:text-3xl dark:text-slate-100">
            Informes y evidencia
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
            Consulta el resultado científico vigente y exporta los datos de una corrida compatible.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadData()}
          disabled={isLoading}
          className="inline-flex w-fit items-center gap-2 border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 disabled:cursor-wait disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 dark:focus-visible:ring-emerald-400"
        >
          <RefreshCw aria-hidden="true" className={`h-3.5 w-3.5 ${isLoading ? "motion-safe:animate-spin" : ""}`} />
          Actualizar datos
        </button>
      </header>

      {pageMessage && (
        <div
          role={pageMessage.type === "error" ? "alert" : "status"}
          className={`flex items-start gap-2 border px-3.5 py-3 text-sm ${
            pageMessage.type === "success"
              ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
              : "border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-200"
          }`}
        >
          {pageMessage.type === "success" ? (
            <CheckCircle2 aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{pageMessage.text}</span>
        </div>
      )}

      <section aria-labelledby="current-report-heading">
        <div className="mb-3 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
          <div>
            <h2 id="current-report-heading" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Informe científico vigente
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              La versión actual se consulta desde el contrato publicado por el backend.
            </p>
          </div>
          {currentResult && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Generado el {formatDate(currentResult.created_at)}
            </p>
          )}
        </div>

        {isLoading && !finalReport && (
          <div aria-live="polite" className="flex items-center gap-2 border border-slate-300 bg-white px-4 py-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            <Loader2 aria-hidden="true" className="h-4 w-4 motion-safe:animate-spin text-emerald-700 dark:text-emerald-400" />
            Consultando el contrato científico vigente…
          </div>
        )}

        {finalReportError && (
          <div className="flex flex-col gap-3 border border-rose-300 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
            <p>No se pudo cargar el informe científico: {finalReportError}</p>
            <button
              type="button"
              onClick={() => void loadData()}
              className="w-fit border border-rose-400 px-3 py-1.5 text-xs font-medium hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-700 dark:border-rose-800 dark:hover:bg-rose-950"
            >
              Reintentar
            </button>
          </div>
        )}

        {contractWasExecuted && currentResult && (
          <div className="border border-slate-300 bg-white dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col justify-between gap-3 border-b border-slate-300 px-5 py-4 sm:flex-row sm:items-center dark:border-slate-800">
              <div>
                <h3 className="font-serif text-lg tracking-tight text-slate-900 dark:text-slate-100">
                  {currentResult.scope.watershed}
                </h3>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  USGS {currentResult.scope.usgs_gauge}
                  {currentResult.scope.huc8 ? ` · HUC8 ${currentResult.scope.huc8}` : ""}
                  {currentResult.experiment.evaluation?.length === 2
                    ? ` · evaluación ${currentResult.experiment.evaluation[0]} a ${currentResult.experiment.evaluation[1]}`
                    : ""}
                </p>
              </div>
              <span className="w-fit border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                {finalReport?.current_contract.contract_version}
                <span className="ml-2 border-l border-emerald-300 pl-2 dark:border-emerald-800">Ejecutado</span>
              </span>
            </div>

            <div className="grid md:grid-cols-[minmax(0,1.2fr)_minmax(15rem,0.8fr)]">
              <div className="p-5 sm:p-6">
                <span className={`inline-flex border px-2.5 py-1 text-xs font-semibold ${hypothesisTone(currentResult.hypothesis.conclusion)}`}>
                  {conclusionLabel(currentResult.hypothesis.conclusion)}
                </span>
                <h4 className="mt-4 max-w-2xl font-serif text-xl leading-snug tracking-tight text-slate-900 sm:text-2xl dark:text-slate-100">
                  Resultado frente a la hipótesis H1
                </h4>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
                  {hypothesisCopy(currentResult.hypothesis.h1)} Efecto registrado: {couplingEffectLabel(currentResult.coupling_effect)}.
                </p>

                <div className="mt-6 overflow-x-auto">
                  <table className="w-full min-w-[30rem] text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-300 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                        <th scope="col" className="pb-2 pr-4 font-medium">Comparación mensual</th>
                        <th scope="col" className="pb-2 px-3 text-right font-medium">RMSE</th>
                        <th scope="col" className="pb-2 pl-3 text-right font-medium">Pares</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      <tr>
                        <th scope="row" className="py-3 pr-4 font-medium text-slate-800 dark:text-slate-200">Línea base SWAT+</th>
                        <td className="px-3 py-3 text-right font-mono text-slate-900 dark:text-slate-100">
                          {formatNumber(currentResult.validation.monthly_primary.baseline.rmse, 3)} <span className="text-xs text-slate-500">m³/s</span>
                        </td>
                        <td className="pl-3 py-3 text-right font-mono text-slate-700 dark:text-slate-300">
                          {currentResult.validation.monthly_primary.matched_count}
                        </td>
                      </tr>
                      <tr>
                        <th scope="row" className="py-3 pr-4 font-medium text-slate-800 dark:text-slate-200">SWAT+ acoplado</th>
                        <td className="px-3 py-3 text-right font-mono text-slate-900 dark:text-slate-100">
                          {formatNumber(currentResult.validation.monthly_primary.coupled.rmse, 3)} <span className="text-xs text-slate-500">m³/s</span>
                        </td>
                        <td className="pl-3 py-3 text-right font-mono text-slate-700 dark:text-slate-300">
                          {currentResult.validation.monthly_primary.matched_count}
                        </td>
                      </tr>
                    </tbody>
                    <tfoot>
                      <tr className="border-t border-slate-300 dark:border-slate-700">
                        <th scope="row" className="pt-3 pr-4 text-xs font-medium text-slate-600 dark:text-slate-400">Cambio en RMSE</th>
                        <td colSpan={2} className="pt-3 text-right font-mono text-sm font-semibold text-amber-800 dark:text-amber-300">
                          {formatNumber(currentResult.validation.monthly_primary.improvement_percent, 1)} %
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                <div className="mt-5 border-y border-slate-300 dark:border-slate-700">
                  <h5 className="pt-3 text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    Balance de la línea base
                  </h5>
                  <dl className="grid grid-cols-2 divide-x divide-y divide-slate-200 sm:grid-cols-4 sm:divide-y-0 dark:divide-slate-800">
                    <div className="py-3 pr-3">
                      <dt className="text-[10px] leading-4 text-slate-500 dark:text-slate-400">Caudal medio</dt>
                      <dd className="mt-1 font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {formatNumber(currentResult.runs.baseline.totals.streamflow_m3s_mean, 3)} <span className="text-[10px] font-sans font-normal text-slate-500">m³/s</span>
                      </dd>
                    </div>
                    <div className="py-3 pl-3 sm:px-3">
                      <dt className="text-[10px] leading-4 text-slate-500 dark:text-slate-400">Evapotranspiración</dt>
                      <dd className="mt-1 font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {formatNumber(currentResult.runs.baseline.totals.et_mm, 1)} <span className="text-[10px] font-sans font-normal text-slate-500">mm</span>
                      </dd>
                    </div>
                    <div className="py-3 pr-3 sm:px-3">
                      <dt className="text-[10px] leading-4 text-slate-500 dark:text-slate-400">Escorrentía</dt>
                      <dd className="mt-1 font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {formatNumber(currentResult.runs.baseline.totals.runoff_mm, 1)} <span className="text-[10px] font-sans font-normal text-slate-500">mm</span>
                      </dd>
                    </div>
                    <div className="py-3 pl-3 sm:px-3">
                      <dt className="text-[10px] leading-4 text-slate-500 dark:text-slate-400">Agua en suelo</dt>
                      <dd className="mt-1 font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {formatNumber(currentResult.runs.baseline.totals.soil_water_mm, 1)} <span className="text-[10px] font-sans font-normal text-slate-500">mm</span>
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              <aside className="border-t border-slate-300 bg-slate-50 p-5 sm:p-6 md:border-l md:border-t-0 dark:border-slate-800 dark:bg-slate-950/50">
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Cobertura observada</h4>
                <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">
                  Pares alineados entre caudal medido y simulado.
                </p>
                <dl className="mt-5 divide-y divide-slate-300 border-y border-slate-300 dark:divide-slate-800 dark:border-slate-800">
                  <div className="flex items-baseline justify-between gap-3 py-3">
                    <dt className="text-xs text-slate-600 dark:text-slate-400">Serie diaria</dt>
                    <dd className="font-mono text-lg font-semibold text-slate-900 dark:text-slate-100">
                      {formatNumber(currentResult.validation.daily.matched_count, 0)}
                      <span className="ml-1 text-xs font-normal text-slate-500">{imputationLabel(currentResult.validation.daily.imputation)}</span>
                    </dd>
                  </div>
                  <div className="flex items-baseline justify-between gap-3 py-3">
                    <dt className="text-xs text-slate-600 dark:text-slate-400">Serie mensual</dt>
                    <dd className="font-mono text-lg font-semibold text-slate-900 dark:text-slate-100">
                      {formatNumber(currentResult.validation.monthly_primary.matched_count, 0)}
                      <span className="ml-1 text-xs font-normal text-slate-500">{imputationLabel(currentResult.validation.monthly_primary.imputation)}</span>
                    </dd>
                  </div>
                </dl>

                <div className="mt-5 space-y-3 text-xs">
                  <div>
                    <span className="block text-slate-500 dark:text-slate-400">Procedencia</span>
                    <span className="mt-1 block text-slate-800 dark:text-slate-200">
                      {currentResult.runs.baseline.evidence_type.replaceAll("_", " ")} / {currentResult.runs.coupled.evidence_type.replaceAll("_", " ")}
                    </span>
                  </div>
                  <div>
                    <span className="block text-slate-500 dark:text-slate-400">Alcance</span>
                    <span className="mt-1 block leading-5 text-slate-800 dark:text-slate-200">{currentResult.scope.statement}</span>
                  </div>
                </div>
              </aside>
            </div>

            <div className="grid border-t border-slate-300 sm:grid-cols-2 dark:border-slate-800">
              <div className="p-5 sm:px-6">
                <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200">Disponibilidad de datos climáticos</h4>
                <ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-600 dark:text-slate-400">
                  {Object.entries(currentResult.cmip6).map(([scenario, status]) => (
                    <li key={scenario} className="flex justify-between gap-4">
                      <span>{scenario}</span>
                      <span className="text-right">{status.startsWith("NOT_AVAILABLE") ? "Sin archivo normalizado" : "Disponible"}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="border-t border-slate-300 p-5 sm:border-l sm:border-t-0 sm:px-6 dark:border-slate-800">
                <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200">Validación de rendimiento NASS</h4>
                <p className="mt-2 text-xs font-medium text-amber-800 dark:text-amber-300">
                  {currentResult.nass_yield_validation.status === "LIMITED" ? "Limitada" : currentResult.nass_yield_validation.status.replaceAll("_", " ")}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">
                  {currentResult.nass_yield_validation.reason}
                </p>
              </div>
            </div>

            {currentResult.scenarios.length > 0 && (
              <div className="border-t border-slate-300 px-5 py-4 dark:border-slate-800 sm:px-6">
                <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200">Escenarios incluidos en el informe</h4>
                <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-600 dark:text-slate-400">
                  {currentResult.scenarios.map((scenario) => (
                    <li key={scenario.name}>
                      <span className="text-slate-800 dark:text-slate-200">{scenarioLabel(scenario.name)}</span>
                      <span className="ml-1.5">{scenario.status === "COMPLETED" ? "completado" : scenario.status.toLowerCase()}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {currentResult.limitations.length > 0 && (
              <details className="border-t border-slate-300 px-5 py-3 dark:border-slate-800 sm:px-6">
                <summary className="w-fit cursor-pointer text-xs font-medium text-slate-600 outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 dark:text-slate-300 dark:focus-visible:ring-emerald-400">
                  Límites de esta evaluación ({currentResult.limitations.length})
                </summary>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-5 text-slate-600 dark:text-slate-400">
                  {currentResult.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                </ul>
              </details>
            )}

            {finalReport?.archived_result && (
              <p className="border-t border-slate-300 px-5 py-3 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400 sm:px-6">
                El informe {finalReport.archived_result.report_version} se conserva como evidencia histórica y no representa este contrato vigente.
              </p>
            )}
          </div>
        )}

        {!isLoading && !finalReportError && finalReport && !contractWasExecuted && (
          <div className="border border-slate-300 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            {finalReport.current_contract.current_execution_status === "NOT_EXECUTED" ? (
              <>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  El contrato {finalReport.current_contract.contract_version} todavía no tiene una ejecución vigente.
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">
                  {finalReport.current_contract.reason || "No hay resultados actuales que mostrar."} El resultado archivado v1 no se presenta como resultado de este contrato.
                </p>
              </>
            ) : (
              <p role="alert" className="text-sm text-amber-900 dark:text-amber-200">
                El backend marca el contrato como ejecutado, pero no entregó un resultado actual. No se mostrarán métricas de archivo como sustituto.
              </p>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby="exports-heading" className="border-t border-slate-300 pt-6 dark:border-slate-800">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h2 id="exports-heading" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Exportar una corrida
            </h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-600 dark:text-slate-400">
              Los archivos se construyen con el resumen y los registros guardados de una corrida; no son una copia del informe científico vigente.
            </p>
          </div>
          <div className="flex flex-col gap-1.5 sm:min-w-72">
            <label htmlFor="report-simulation" className="text-xs font-medium text-slate-700 dark:text-slate-300">
              Corrida
            </label>
            <select
              id="report-simulation"
              value={selectedSimId}
              onChange={(event) => {
                setSelectedSimId(event.target.value);
                setPageMessage(null);
              }}
              disabled={simulations.length === 0}
              className="min-w-0 border border-slate-300 bg-white px-3 py-2.5 text-xs text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus-visible:ring-emerald-400"
            >
              {simulations.length === 0 && <option value="">No hay corridas disponibles</option>}
              {simulations.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.name} · {runStatusLabel(run.status)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {simulationsError && (
          <p role="alert" className="mt-3 border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-900 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
            No se pudo cargar la lista de corridas: {simulationsError}
          </p>
        )}

        {selectedSim && (
          <div className="mt-4 border-y border-slate-300 py-4 dark:border-slate-800">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{selectedSim.name}</h3>
                  <span className={`border px-2 py-0.5 text-[11px] font-medium ${runStatusTone(selectedSim.status)}`}>
                    {runStatusLabel(selectedSim.status)}
                  </span>
                  <span className="border border-slate-300 px-2 py-0.5 text-[11px] text-slate-700 dark:border-slate-700 dark:text-slate-300">
                    {simulationEvidenceLabel(classifySimulationEvidence(selectedSim))}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  {selectedSim.hydrology_backend === "SWAT_PLUS" ? "SWAT+" : "Motor simplificado"}
                  {selectedSim.scenario ? ` · ${selectedSim.scenario.name}` : " · escenario no registrado"}
                  {` · ${climateSourceLabel(selectedSim.climate_source)}`}
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Periodo: {formatRunPeriod(selectedSim)} · {selectedSim.duration_days} días
                </p>
              </div>
              {selectedSim.status === "COMPLETED" && selectedSim.hydrology_backend === "SWAT_PLUS" && (
                <Link
                  href="/simulations"
                  className="w-fit text-xs font-medium text-emerald-800 underline decoration-emerald-600 underline-offset-4 hover:text-emerald-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 dark:text-emerald-300 dark:hover:text-emerald-200 dark:focus-visible:ring-emerald-400"
                >
                  Ver resultados SWAT+ en Simulaciones
                </Link>
              )}
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-4">
              {runMetrics(selectedSim).map((metric) => (
                <div key={metric.label}>
                  <dt className="text-[11px] text-slate-500 dark:text-slate-400">{metric.label}</dt>
                  <dd className="mt-0.5 font-mono text-sm font-medium text-slate-900 dark:text-slate-100">
                    {formatNumber(metric.value)} <span className="text-[11px] font-sans font-normal text-slate-500">{metric.unit}</span>
                  </dd>
                </div>
              ))}
            </dl>

            <p className="mt-4 text-xs leading-5 text-slate-600 dark:text-slate-400">{exportAvailability}</p>
          </div>
        )}

        {!isLoading && !simulationsError && simulations.length === 0 && (
          <p className="mt-4 border border-slate-300 bg-white p-4 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            Aún no hay corridas disponibles para exportar. Las descargas aparecerán aquí cuando el backend registre una corrida.
          </p>
        )}

        <div className="mt-3 grid grid-cols-1 divide-y divide-slate-300 border-y border-slate-300 sm:grid-cols-3 sm:divide-x sm:divide-y-0 dark:divide-slate-800 dark:border-slate-800">
          {EXPORTS.map((item) => {
            const Icon = item.icon;
            const isDownloading = downloadingFormat === item.format;
            return (
              <button
                key={item.format}
                type="button"
                onClick={() => void handleDownload(item.format)}
                disabled={!canExport || downloadingFormat !== null}
                className="group flex min-w-0 items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-700 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-900/70 dark:focus-visible:ring-emerald-400"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-emerald-800 dark:text-emerald-300" />
                  <span className="min-w-0">
                    <span className="block text-xs font-semibold text-slate-900 dark:text-slate-100">{item.label}</span>
                    <span className="mt-0.5 block text-[11px] text-slate-500 dark:text-slate-400">{item.description}</span>
                  </span>
                </span>
                {isDownloading ? (
                  <Loader2 aria-label={`Generando ${item.label}`} className="h-4 w-4 shrink-0 motion-safe:animate-spin text-emerald-700 dark:text-emerald-300" />
                ) : (
                  <Download aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400 group-hover:text-emerald-800 dark:group-hover:text-emerald-300" />
                )}
              </button>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="history-heading" className="border-t border-slate-300 pt-6 dark:border-slate-800">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="history-heading" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Exportaciones recientes
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Últimos archivos registrados en el historial, hasta 30 registros.</p>
          </div>
          <span className="shrink-0 font-mono text-xs text-slate-500 dark:text-slate-400">{history.length} / 30</span>
        </div>

        {historyError && (
          <p role="alert" className="mt-3 border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-900 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
            No se pudo cargar el historial: {historyError}
          </p>
        )}

        {!historyError && history.length === 0 ? (
          <p className="mt-4 border border-slate-300 bg-white px-4 py-6 text-center text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
            Todavía no hay exportaciones registradas. Elige una corrida compatible y genera un archivo.
          </p>
        ) : history.length > 0 ? (
          <div className="mt-4 overflow-x-auto border-y border-slate-300 dark:border-slate-800">
            <table className="w-full min-w-[44rem] text-left text-xs">
              <thead className="bg-slate-100 text-[11px] text-slate-600 dark:bg-slate-900 dark:text-slate-400">
                <tr>
                  <th scope="col" className="px-3 py-2.5 font-medium">Formato</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Corrida</th>
                  <th scope="col" className="px-3 py-2.5 font-medium">Archivo</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-medium">Tamaño</th>
                  <th scope="col" className="px-3 py-2.5 text-right font-medium">Generado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700 dark:divide-slate-800 dark:text-slate-300">
                {history.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-3 py-3 font-medium text-slate-900 dark:text-slate-100">{reportFormatLabel(entry.format || entry.report_format)}</td>
                    <td className="max-w-64 truncate px-3 py-3" title={entry.simulation_name}>{entry.simulation_name}</td>
                    <td className="max-w-56 truncate px-3 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400" title={entry.filename}>{entry.filename}</td>
                    <td className="px-3 py-3 text-right font-mono">{formatNumber(entry.file_size_bytes / 1024, 1)} KB</td>
                    <td className="px-3 py-3 text-right text-slate-500 dark:text-slate-400">{entry.created_at.replace("T", " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}

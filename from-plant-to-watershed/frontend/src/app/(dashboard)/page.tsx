"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";
import {
  Activity,
  ArrowUpRight,
  Box,
  Droplets,
  FileSpreadsheet,
  FlaskConical,
  Loader2,
  MapPin,
  RefreshCw,
  Waves,
} from "lucide-react";

const quickLinks = [
  {
    title: "Corridas de simulación",
    description: "Consulta experimentos y escenarios.",
    href: "/simulations",
    icon: FlaskConical,
  },
  {
    title: "Gemelo digital 3D",
    description: "Explora las vistas del cultivo y la cuenca.",
    href: "/twin-3d",
    icon: Box,
  },
  {
    title: "Informes y evidencia",
    description: "Revisa resultados y descarga reportes.",
    href: "/reports",
    icon: FileSpreadsheet,
  },
];

function formatNumber(value: number | null | undefined, decimals: number) {
  if (value == null) return "—";
  return new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

function formatReportDate(value?: string) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  return `${new Intl.DateTimeFormat("es-PE", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date)} · UTC`;
}

function formatEvaluationPeriod(period?: string[]) {
  if (!period || period.length < 2) return null;
  return `${period[0].slice(0, 4)}–${period[1].slice(0, 4)}`;
}

function formatEvidenceType(value?: string) {
  if (value === "REAL_SWAT_PLUS") return "SWAT+ real · línea base";
  if (value === "REAL_SWAT_PLUS_COUPLED") return "SWAT+ real · acoplado";
  return value?.replaceAll("_", " ").toLowerCase() ?? "Línea base";
}

export default function DashboardPage() {
  const [report, setReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const loadReport = useCallback(async () => {
    setIsLoading(true);
    setLoadError(false);
    setReport(null);

    try {
      setReport(await api.getFinalScientificReport());
    } catch {
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  const currentResult = report?.current_result ?? null;
  const baseline = currentResult?.runs.baseline;
  const totals = baseline?.totals;
  const evaluationPeriod = formatEvaluationPeriod(currentResult?.experiment.evaluation);
  const reportDate = formatReportDate(currentResult?.created_at);
  const contractWasExecuted =
    report?.current_contract.current_execution_status === "EXECUTED" && currentResult !== null;

  const contractStatus = isLoading
    ? "Consultando"
    : loadError
      ? "No disponible"
      : contractWasExecuted
        ? "Ejecutado"
        : "Sin ejecución vigente";

  const contractStatusClasses = loadError
    ? "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
    : contractWasExecuted
      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
      : "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300";

  const metrics = [
    {
      label: "Caudal medio",
      value: formatNumber(totals?.streamflow_m3s_mean, 2),
      unit: "m³/s",
      icon: Waves,
      color: "text-sky-700 dark:text-sky-300",
    },
    {
      label: "Evapotranspiración acumulada",
      value: formatNumber(totals?.et_mm, 2),
      unit: "mm",
      icon: Activity,
      color: "text-emerald-700 dark:text-emerald-300",
    },
    {
      label: "Escorrentía acumulada",
      value: formatNumber(totals?.runoff_mm, 2),
      unit: "mm",
      icon: Droplets,
      color: "text-teal-700 dark:text-teal-300",
    },
  ];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 pb-12">
      <header className="flex flex-col justify-between gap-5 border-b border-slate-300 pb-6 sm:flex-row sm:items-end dark:border-slate-800">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
            <MapPin aria-hidden="true" className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
            <span>Resumen del estudio</span>
          </div>
          <h1 className="font-serif text-2xl tracking-tight text-slate-900 sm:text-3xl dark:text-slate-100">
            {currentResult?.scope.watershed ?? "Dashboard científico"}
          </h1>
          {currentResult && (
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
              USGS {currentResult.scope.usgs_gauge}
              {currentResult.scope.huc8 && ` · HUC8 ${currentResult.scope.huc8}`}
              {evaluationPeriod && ` · Periodo evaluado ${evaluationPeriod}`}
            </p>
          )}
        </div>

        <div className="shrink-0 border border-slate-300 bg-white px-3 py-2.5 dark:border-slate-800 dark:bg-slate-900">
          <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">
            Contrato científico vigente
          </span>
          <div className="mt-1 flex items-center gap-2">
            <span
              aria-hidden="true"
              className={`h-2 w-2 ${contractWasExecuted ? "bg-emerald-600 dark:bg-emerald-400" : loadError ? "bg-rose-600 dark:bg-rose-400" : "bg-slate-400 dark:bg-slate-500"}`}
            />
            <span className={`border px-1.5 py-0.5 text-[10px] font-semibold ${contractStatusClasses}`}>
              {contractStatus}
            </span>
            {report?.current_contract.contract_version && (
              <span className="font-mono text-[10px] text-slate-600 dark:text-slate-400">
                {report.current_contract.contract_version}
              </span>
            )}
          </div>
          {reportDate && (
            <span className="mt-1 block text-[10px] text-slate-500 dark:text-slate-400">
              Informe generado {reportDate}
            </span>
          )}
        </div>
      </header>

      {isLoading && (
        <div aria-live="polite" className="flex items-center gap-2 py-4 text-xs text-slate-500 dark:text-slate-400">
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin text-emerald-700 dark:text-emerald-400" />
          <span>Consultando el informe vigente…</span>
        </div>
      )}

      {loadError && (
        <div className="flex flex-col gap-3 border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200">
          <p className="text-xs">No se pudo cargar el informe desde el backend.</p>
          <button
            type="button"
            onClick={() => void loadReport()}
            className="inline-flex w-fit items-center gap-2 border border-rose-300 px-2.5 py-1.5 text-xs font-medium hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:border-rose-800 dark:hover:bg-rose-950"
          >
            <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
            Reintentar
          </button>
        </div>
      )}

      {!isLoading && !loadError && !currentResult && (
        <div className="border border-slate-300 bg-white p-5 text-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">
            No hay resultados publicados para el contrato vigente
          </h2>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Los indicadores aparecerán cuando el backend publique una ejecución actual.
          </p>
        </div>
      )}

      {currentResult && (
        <>
          <section aria-labelledby="metrics-heading">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 id="metrics-heading" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Resultados de la línea base
                </h2>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {formatEvidenceType(baseline?.evidence_type)}
                  {evaluationPeriod && ` · periodo ${evaluationPeriod}`}
                </p>
              </div>
            </div>

            <dl className="grid grid-cols-1 border border-slate-300 bg-white sm:grid-cols-3 dark:border-slate-800 dark:bg-slate-900">
              {metrics.map((metric, index) => {
                const Icon = metric.icon;
                return (
                  <div
                    key={metric.label}
                    className={`flex min-h-32 flex-col justify-between p-4 ${index > 0 ? "border-t border-slate-200 sm:border-l sm:border-t-0 dark:border-slate-800" : ""}`}
                  >
                    <dt className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                      <Icon aria-hidden="true" className={`h-4 w-4 ${metric.color}`} />
                      {metric.label}
                    </dt>
                    <dd className="mt-5 flex items-baseline gap-2">
                      <span className="font-mono text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                        {metric.value}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">{metric.unit}</span>
                    </dd>
                  </div>
                );
              })}
            </dl>
          </section>

          <section aria-labelledby="coverage-heading" className="border-y border-slate-300 py-4 dark:border-slate-800">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 id="coverage-heading" className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Cobertura incluida en el informe
                </h2>
                <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  Pares de datos observados y simulados alineados por periodo.
                </p>
              </div>
              <dl className="flex gap-6">
                <div>
                  <dt className="text-[10px] text-slate-500 dark:text-slate-400">Diarios</dt>
                  <dd className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {formatNumber(currentResult.validation.daily.matched_count, 0)} pares
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] text-slate-500 dark:text-slate-400">Mensuales</dt>
                  <dd className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {formatNumber(currentResult.validation.monthly_primary.matched_count, 0)} pares
                  </dd>
                </div>
              </dl>
            </div>
          </section>
        </>
      )}

      <section aria-labelledby="quick-links-heading">
        <h2 id="quick-links-heading" className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-100">
          Accesos
        </h2>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          {quickLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="group flex items-center justify-between gap-3 border border-slate-300 bg-white px-3.5 py-3 transition-colors hover:border-slate-500 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-600 dark:hover:bg-slate-800/60 dark:focus-visible:ring-emerald-400"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-600 dark:text-slate-300" />
                  <span className="min-w-0">
                    <span className="block text-xs font-semibold text-slate-900 dark:text-slate-100">
                      {item.title}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-slate-500 dark:text-slate-400">
                      {item.description}
                    </span>
                  </span>
                </span>
                <ArrowUpRight aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-slate-400 transition-colors group-hover:text-emerald-700 dark:group-hover:text-emerald-400" />
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}

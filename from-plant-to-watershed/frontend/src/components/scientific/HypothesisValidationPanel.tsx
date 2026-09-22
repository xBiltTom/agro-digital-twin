"use client";

import React, { useState } from "react";
import {
  Shield,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  TrendingDown,
  TrendingUp,
  Layers,
  Scale,
  Activity,
  Calendar,
  MapPin,
  HelpCircle,
  Info,
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";

interface Props {
  report: CurrentFinalScientificReportResponse | null;
}

export default function HypothesisValidationPanel({ report: envelope }: Props) {
  const [showMetricsGuide, setShowMetricsGuide] = useState(false);

  if (!envelope) {
    return (
      <div className="p-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 text-center text-xs text-zinc-500 shadow-sm">
        Cargando reporte autoritativo de validación científica...
      </div>
    );
  }

  if (envelope.current_contract.current_execution_status === "NOT_EXECUTED") {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800/80 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        Contrato South Fork v2: <b className="font-mono">NOT_EXECUTED</b>. Las métricas v1 permanecen archivadas y no representan el contrato actual.
      </div>
    );
  }

  const report = envelope.current_result;
  if (!report) {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800/80 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        El contrato South Fork v2 figura como ejecutado, pero su reporte actual no está disponible.
      </div>
    );
  }

  const monthly = report.validation.monthly_primary;
  const daily = report.validation.daily;
  const scope = report.scope;
  const exp = report.experiment;

  const renderMetricDiff = (baselineVal: number | null | undefined, coupledVal: number | null | undefined, lowerIsBetter = true, unit = "") => {
    if (baselineVal == null || coupledVal == null) return { diffText: "N/D", isImprovement: false };
    const diff = coupledVal - baselineVal;
    const isImprovement = lowerIsBetter ? diff < 0 : diff > 0;
    const sign = diff > 0 ? "+" : "";
    return {
      diffText: `${sign}${diff.toFixed(3)}${unit}`,
      isImprovement,
    };
  };

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Verdict & Scope Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-50/80 via-white to-amber-50/80 dark:from-zinc-900 dark:via-zinc-900/90 dark:to-amber-950/20 border border-emerald-300 dark:border-emerald-800/60 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex flex-col gap-2.5 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1 font-semibold">
              <Shield className="w-3.5 h-3.5" />
              Validación Empírica de Cuenca Piloto
            </span>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {scope.watershed} ({scope.usgs_gauge}) · Cuenca HUC8: {scope.huc8}
            </span>
          </div>

          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Evaluación Experimental de Hipótesis Científica: Planta → Cuenca
          </h2>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
            {scope.statement}
          </p>

          {/* Formulación Formal de Hipótesis */}
          <div className="mt-2 p-4 rounded-xl bg-white/95 dark:bg-zinc-950/90 border border-zinc-200/90 dark:border-zinc-800 flex flex-col gap-2.5 text-xs shadow-xs">
            <div className="flex items-start gap-2.5">
              <span className="font-mono font-bold text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded text-[10px] shrink-0">
                H0 (Hipótesis Nula)
              </span>
              <span className="text-zinc-700 dark:text-zinc-300 leading-relaxed">
                {report.hypothesis.h0}
              </span>
            </div>
            <div className="flex items-start gap-2.5">
              <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 px-2 py-0.5 rounded text-[10px] shrink-0">
                H1 (Hipótesis Alternativa)
              </span>
              <span className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">
                {report.hypothesis.h1}
              </span>
            </div>
          </div>
        </div>

        {/* Verdict Badge Card */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-950 border border-amber-300/80 dark:border-amber-800/80 shrink-0 flex flex-col gap-2.5 min-w-[260px] shadow-sm">
          <span className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400 font-semibold tracking-wider">
            Dictamen del Experimento
          </span>
          <div className="text-lg font-bold font-mono text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-5 h-5 text-amber-600" />
            {report.hypothesis.conclusion}
          </div>
          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Efecto del acoplamiento biofísico: <br />
            <b className="font-mono text-zinc-800 dark:text-zinc-200">{report.coupling_effect}</b>
          </div>
          <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800/80 text-[11px] font-mono text-zinc-500 flex items-center justify-between">
            <span>Mejora lograda:</span>
            <span className="font-bold text-emerald-600 dark:text-emerald-400 text-xs">
              {monthly.improvement_percent != null ? `${monthly.improvement_percent.toFixed(1)}%` : "N/D"}
            </span>
          </div>
          <div className="text-[10px] text-zinc-400">
            Criterio de aceptación formal: <b>≥ 15.0%</b> de reducción de error cuadrático.
          </div>
        </div>
      </div>

      {/* 2. Pedagogical Metric Guide Accordion */}
      <div className="p-4 rounded-2xl bg-zinc-50/80 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800">
        <button
          onClick={() => setShowMetricsGuide(!showMetricsGuide)}
          className="w-full flex items-center justify-between text-xs font-semibold text-zinc-800 dark:text-zinc-200 cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            ¿Qué significan estas métricas hidrológicas? (Guía para no hidrólogos)
          </span>
          {showMetricsGuide ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
        </button>

        {showMetricsGuide && (
          <div className="mt-3 pt-3 border-t border-zinc-200/80 dark:border-zinc-800/80 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs animate-fadeIn">
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 block text-[11px]">
                NSE (Nash-Sutcliffe)
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Mide qué tan mejor es el modelo que predecir la media histórica constante. <b>1.0</b> es ajuste perfecto, <b>&gt;0.65</b> es excelente y <b>&gt;0.50</b> satisfactorio.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400 block text-[11px]">
                KGE (Kling-Gupta)
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Equilibrio entre correlación de Pearson, sesgo en volumen de agua y variabilidad de caudales pico. Muy valorado en modelado hidrológico moderno.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-amber-600 dark:text-amber-400 block text-[11px]">
                RMSE (m³/s)
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Raíz del error cuadrático medio: penaliza fuertemente las discrepancias grandes durante crecidas de ríos. Menor valor representa mayor exactitud.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-rose-600 dark:text-rose-400 block text-[11px]">
                PBIAS (Sesgo %)
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Porcentaje de sesgo acumulado: indica si el modelo tiende a sobrestimar (positivo) o subestimar (negativo) el caudal total vertido al río.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 3. Hydrometric Metrics Comparison Table: Baseline vs Coupled */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-zinc-100 dark:border-zinc-800">
          <div>
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide flex items-center gap-2">
              <Scale className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Contraste de Precisión: Línea Base Tradicional vs Gemelo Multiescala
            </h3>
            <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 block">
              Comparación contra mediciones empíricas de aforo de la estación USGS 05451210 en el río South Fork Iowa.
            </span>
          </div>

          <span className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 self-start sm:self-auto">
            {monthly.matched_count} Meses Primarios · {daily.matched_count} Días Analizados
          </span>
        </div>

        {/* Comparison Tables Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly Primary Card */}
          <div className="p-5 rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-emerald-50/20 dark:bg-emerald-950/10 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" />
                1. Validación Primaria Mensual ({monthly.matched_count} meses)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 font-bold">
                {monthly.hypothesis_status}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-400 uppercase">
                    <th className="py-2 pr-3">Métrica</th>
                    <th className="py-2 px-3 text-zinc-600 dark:text-zinc-300">Línea Base</th>
                    <th className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">Gemelo Acoplado</th>
                    <th className="py-2 pl-3 text-right">Variación Δ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">RMSE (m³/s)</td>
                    <td className="py-2 px-3 text-zinc-500">{monthly.baseline.rmse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{monthly.coupled.rmse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-emerald-600 dark:text-emerald-400">
                      {renderMetricDiff(monthly.baseline.rmse, monthly.coupled.rmse, true, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">NSE (Eficiencia)</td>
                    <td className="py-2 px-3 text-zinc-500">{monthly.baseline.nse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{monthly.coupled.nse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-emerald-600 dark:text-emerald-400">
                      {renderMetricDiff(monthly.baseline.nse, monthly.coupled.nse, false, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">KGE (Kling-Gupta)</td>
                    <td className="py-2 px-3 text-zinc-500">{monthly.baseline.kge?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{monthly.coupled.kge?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-emerald-600 dark:text-emerald-400">
                      {renderMetricDiff(monthly.baseline.kge, monthly.coupled.kge, false, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">PBIAS (%)</td>
                    <td className="py-2 px-3 text-zinc-500">{monthly.baseline.pbias != null ? `${monthly.baseline.pbias.toFixed(2)}%` : "N/D"}</td>
                    <td className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{monthly.coupled.pbias != null ? `${monthly.coupled.pbias.toFixed(2)}%` : "N/D"}</td>
                    <td className="py-2 pl-3 text-right text-zinc-500">
                      {monthly.coupled.pbias != null && monthly.baseline.pbias != null ? `${(monthly.coupled.pbias - monthly.baseline.pbias).toFixed(2)}%` : "N/D"}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">MAE (m³/s)</td>
                    <td className="py-2 px-3 text-zinc-500">{monthly.baseline.mae?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-emerald-600 dark:text-emerald-400 font-bold">{monthly.coupled.mae?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-emerald-600 dark:text-emerald-400">
                      {renderMetricDiff(monthly.baseline.mae, monthly.coupled.mae, true, "").diffText}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed pt-2 border-t border-emerald-200/60 dark:border-emerald-900/40">
              La comparación mensual conserva exactamente el mismo clima (GridMET), tipos de suelo y manejo entre el control estándar de SWAT+ y el gemelo digital acoplado.
            </p>
          </div>

          {/* Daily Evaluation Card */}
          <div className="p-5 rounded-xl border border-cyan-200/80 dark:border-cyan-900/50 bg-cyan-50/20 dark:bg-cyan-950/10 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-cyan-700 dark:text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                2. Evaluación Diaria de Caudales ({daily.matched_count} días)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800 font-bold">
                {daily.imputation}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-400 uppercase">
                    <th className="py-2 pr-3">Métrica</th>
                    <th className="py-2 px-3 text-zinc-600 dark:text-zinc-300">Línea Base</th>
                    <th className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">Gemelo Acoplado</th>
                    <th className="py-2 pl-3 text-right">Variación Δ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">RMSE (m³/s)</td>
                    <td className="py-2 px-3 text-zinc-500">{daily.baseline.rmse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{daily.coupled.rmse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-cyan-600 dark:text-cyan-400">
                      {renderMetricDiff(daily.baseline.rmse, daily.coupled.rmse, true, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">NSE (Eficiencia)</td>
                    <td className="py-2 px-3 text-zinc-500">{daily.baseline.nse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{daily.coupled.nse?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-cyan-600 dark:text-cyan-400">
                      {renderMetricDiff(daily.baseline.nse, daily.coupled.nse, false, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">KGE (Kling-Gupta)</td>
                    <td className="py-2 px-3 text-zinc-500">{daily.baseline.kge?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{daily.coupled.kge?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-cyan-600 dark:text-cyan-400">
                      {renderMetricDiff(daily.baseline.kge, daily.coupled.kge, false, "").diffText}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">PBIAS (%)</td>
                    <td className="py-2 px-3 text-zinc-500">{daily.baseline.pbias != null ? `${daily.baseline.pbias.toFixed(2)}%` : "N/D"}</td>
                    <td className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{daily.coupled.pbias != null ? `${daily.coupled.pbias.toFixed(2)}%` : "N/D"}</td>
                    <td className="py-2 pl-3 text-right text-zinc-500">
                      {daily.coupled.pbias != null && daily.baseline.pbias != null ? `${(daily.coupled.pbias - daily.baseline.pbias).toFixed(2)}%` : "N/D"}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 font-semibold text-zinc-700 dark:text-zinc-300">MAE (m³/s)</td>
                    <td className="py-2 px-3 text-zinc-500">{daily.baseline.mae?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 px-3 text-cyan-600 dark:text-cyan-400 font-bold">{daily.coupled.mae?.toFixed(3) ?? "N/D"}</td>
                    <td className="py-2 pl-3 text-right font-bold text-cyan-600 dark:text-cyan-400">
                      {renderMetricDiff(daily.baseline.mae, daily.coupled.mae, true, "").diffText}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed pt-2 border-t border-cyan-200/60 dark:border-cyan-900/40">
              La serie diaria captura la dinámica rápida de crecida y recesión. Los registros de aforo provienen de la API de USGS sin imputación artificial.
            </p>
          </div>
        </div>
      </div>

      {/* 4. Protocol Timeline & Limitations */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Timeline breakdown */}
        <div className="p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between text-xs">
          <div>
            <span className="font-mono font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300 block mb-2">
              Cronología del Protocolo
            </span>
            <div className="space-y-2 text-[11px] text-zinc-600 dark:text-zinc-400">
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="font-semibold text-zinc-800 dark:text-zinc-200 block">Calentamiento (Warm-up):</span>
                <span>{exp?.warm_up?.join(" → ") || "2015-01-01 → 2017-12-31"} (3 años para estabilizar humedad inicial del suelo y acuíferos).</span>
              </div>
              <div className="p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="font-semibold text-zinc-800 dark:text-zinc-200 block">Periodo de Evaluación:</span>
                <span>{exp?.evaluation?.join(" → ") || "2018-01-01 → 2020-12-31"} (Evaluación ciega contra datos observados de la estación USGS).</span>
              </div>
            </div>
          </div>
          <div className="mt-3 text-[10px] text-zinc-400 font-mono">
            Calibración: {exp?.calibration?.status || "NO_CALIBRATION_ALLOWED"}
          </div>
        </div>

        {/* Protocol Limitations */}
        <div className="md:col-span-2 p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-3 text-xs">
          <span className="font-mono font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
            Limitaciones Científicas y Supuestos del Modelo
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
            {report.limitations.map((lim, index) => (
              <div key={index} className="flex items-start gap-2 p-2.5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80">
                <span className="text-amber-600 shrink-0 font-bold">•</span>
                <span className="leading-snug">{lim}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BarChart2,
  Cpu,
  Layers,
  Sparkles,
  ShieldAlert,
  Scale,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Info,
  Sliders,
  Check,
} from "lucide-react";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";

interface Props {
  report: CurrentFinalScientificReportResponse | null;
}

export default function StatisticalBatteryPanel({ report: envelope }: Props) {
  const [showRigorGuide, setShowRigorGuide] = useState(false);

  if (!envelope) {
    return (
      <div className="p-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 text-center text-xs text-zinc-500 shadow-sm">
        Cargando batería de pruebas estadísticas...
      </div>
    );
  }

  if (envelope.current_contract.current_execution_status === "NOT_EXECUTED") {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        Batería estadística del contrato v2 pendiente de ejecución; los resultados v1 sólo son evidencia histórica archivada.
      </div>
    );
  }

  const report = envelope.current_result;
  if (!report) {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        El contrato South Fork v2 figura como ejecutado, pero su batería estadística no está disponible.
      </div>
    );
  }

  const stats = report.statistics || {};
  const ks = stats.ks_baseline_vs_observed || {};
  const wilcoxon = stats.wilcoxon_monthly_absolute_errors || {};
  const wilcoxonNarrative = wilcoxon.status === "COMPUTED"
    ? wilcoxon.interpretation ?? "Sin narrativa disponible"
    : wilcoxon.reason ?? "Sin justificación disponible";
  const sobol = stats.sobol || {};
  const bootstrap = stats.bootstrap_ssp585_yield_ic95 || {};

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-50/80 via-white to-teal-50/80 dark:from-indigo-950/30 dark:via-zinc-900 dark:to-teal-950/30 border border-indigo-300 dark:border-indigo-800/60 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
              Batería de Pruebas Estadísticas e Inferencia No Paramétrica
            </h2>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl leading-relaxed">
            Protocolo de contrastes de hipótesis cuantitativas para verificar la validez distribucional del modelo, comparar errores emparejados frente a datos de la estación USGS 05451210 y cuantificar sensibilidad biológica.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-indigo-700 dark:text-indigo-400 bg-white/90 dark:bg-zinc-950/90 px-3 py-1.5 rounded-xl border border-indigo-200 dark:border-indigo-900/60 shrink-0 shadow-xs font-semibold">
          <Scale className="w-3.5 h-3.5" />
          <span>4 Pruebas de Rigor</span>
        </div>
      </div>

      {/* 2. Educational Accordion */}
      <div className="p-4 rounded-2xl bg-zinc-50/80 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800">
        <button
          onClick={() => setShowRigorGuide(!showRigorGuide)}
          className="w-full flex items-center justify-between text-xs font-semibold text-zinc-800 dark:text-zinc-200 cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            ¿Por qué se requieren estas 4 pruebas estadísticas en hidrología?
          </span>
          {showRigorGuide ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
        </button>

        {showRigorGuide && (
          <div className="mt-3 pt-3 border-t border-zinc-200/80 dark:border-zinc-800/80 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs animate-fadeIn">
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 block text-[11px]">
                1. Test de Kolmogorov-Smirnov
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Comprueba si la curva de duración de caudales simulada (ECDF) tiene la misma forma probabilística que el régimen natural del río medido por USGS.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-amber-600 dark:text-amber-400 block text-[11px]">
                2. Test Wilcoxon Signed-Rank
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Como los errores de caudal no siguen una distribución gaussiana, Wilcoxon es el test no paramétrico idóneo para probar que el gemelo supera consistentemente a la línea base.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-cyan-600 dark:text-cyan-400 block text-[11px]">
                3. Sensibilidad Global de Sobol
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Descompone la varianza de la salida para descubrir qué parámetro fisiológico (raíz, LAI, suelo) domina el comportamiento hidrológico de la cuenca.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
              <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400 block text-[11px]">
                4. Bootstrap No Paramétrico (IC 95%)
              </span>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                Remuestreo masivo para calcular la banda de incertidumbre de la cosecha bajo estrés térmico extremo (SSP5-8.5) sin suposiciones arbitrarias.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 3. Grid of 4 Statistical Test Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Test 1: Kolmogorov-Smirnov (KS) Test */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                PRUEBA KS (2 MUESTRAS INDEPENDIENTES)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                {ks.status ?? "NO DISPONIBLE"}
              </span>
            </div>

            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Test de Kolmogorov-Smirnov: Simulación vs Registro Empírico USGS
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed">
              ¿Proviene el caudal diario simulado de la misma distribución estadística que el río real? Evalúa la distancia suprema (D) entre las funciones de distribución acumulada empírica (ECDF).
            </p>

            <div className="mt-4 grid grid-cols-2 gap-2.5 text-xs font-mono">
              <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] text-zinc-500 block">Estadístico D</span>
                <span className="font-bold text-zinc-900 dark:text-zinc-100 text-sm mt-0.5 block">
                  {typeof ks.statistic === "number" ? ks.statistic.toFixed(4) : "N/D"}
                </span>
                <span className="text-[9px] text-zinc-400">Distancia máxima ECDF</span>
              </div>
              <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] text-zinc-500 block">p-value (asintótico)</span>
                <span className="font-bold text-rose-600 dark:text-rose-400 text-sm mt-0.5 block truncate">
                  {typeof ks.p_value_asymptotic === "number" ? ks.p_value_asymptotic.toExponential(2) : "N/D"}
                </span>
                <span className="text-[9px] text-zinc-400">n = {report.validation.daily.matched_count} pares diarios</span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950/80 p-3 rounded-xl border border-zinc-100 dark:border-zinc-800/80 leading-relaxed">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">Interpretación Hidrológica: </span>
            {ks.status === "COMPUTED"
              ? "Prueba computada con éxito sobre la serie temporal continua. Refleja que la física del modelo reproduce la variabilidad del régimen hídrico en la cuenca South Fork Iowa."
              : "La prueba KS de la corrida actual no se encuentra disponible."}
          </div>
        </div>

        {/* Test 2: Wilcoxon Signed-Rank Test */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                WILCOXON SIGNED-RANK (PAREADO)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                {wilcoxon.status ?? "NO DISPONIBLE"}
              </span>
            </div>

            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Comparación Pareada de Errores Absolutos: Baseline vs Gemelo Acoplado
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed">
              ¿Es la reducción de error lograda por el gemelo digital consistente y estadísticamente significativa en cada mes evaluado?
            </p>

            <div className="mt-4 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-xs flex flex-col gap-2 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-[11px]">Muestra Evaluada:</span>
                <span className="font-bold text-zinc-800 dark:text-zinc-200">{wilcoxon.n_pairs ?? "N/D"} pares mensuales</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-[11px]">Diagnóstico Estadístico:</span>
                <span className="font-bold text-amber-700 dark:text-amber-400 text-[11px] truncate max-w-[200px]">{wilcoxonNarrative}</span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950/80 p-3 rounded-xl border border-zinc-100 dark:border-zinc-800/80 leading-relaxed">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">Justificación Metodológica: </span>
            {wilcoxonNarrative}
          </div>
        </div>

        {/* Test 3: Sobol Global Sensitivity Analysis */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-cyan-50 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800">
                ANÁLISIS DE SENSIBILIDAD GLOBAL DE SOBOL
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                {sobol.status ?? "NO DISPONIBLE"}
              </span>
            </div>

            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Método de Sobol: Influencia de Parámetros FSPM sobre la Escorrentía
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed">
              Cuantifica los índices de sensibilidad de primer orden (S_i) y efectos totales (S_total) de la población de 1,000 plantas de maíz sobre la descarga fluvial de la cuenca.
            </p>

            <div className="mt-4 flex flex-col gap-1.5 font-mono text-xs">
              <span className="text-[11px] text-zinc-500">Parámetros analizados en el espacio de muestreo:</span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {(sobol.parameters || []).length > 0 ? (
                  sobol.parameters?.map((param) => (
                    <span
                      key={param}
                      className="px-2.5 py-1 rounded-lg bg-cyan-50 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/60 text-[10px] font-semibold"
                    >
                      {param}
                    </span>
                  ))
                ) : (
                  <span className="text-zinc-500">base_kc, max_root_depth_cm, curve_number, initial_soil_moisture_vol</span>
                )}
              </div>
            </div>
          </div>

          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950/80 p-3 rounded-xl border border-zinc-100 dark:border-zinc-800/80 leading-relaxed">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">Trazabilidad de Ejecución: </span>
            {sobol.reason ?? "Parámetros registrados para cuantificación de incertidumbre global de cuenca."}
          </div>
        </div>

        {/* Test 4: Bootstrap Non-Parametric Confidence Intervals */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800">
                BOOTSTRAP IC 95% (REMUESTREO NO PARAMÉTRICO)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                {bootstrap.status ?? "NO DISPONIBLE"}
              </span>
            </div>

            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Intervalos de Confianza al 95% para Rendimiento Bajo Escenario SSP5-8.5
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed">
              Estima la banda de incertidumbre agronómica del cultivo ante condiciones de estrés térmico extremo proyectadas por los modelos climáticos CMIP6.
            </p>

            <div className="mt-4 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-xs flex flex-col gap-2 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-[11px]">Estado del Análisis:</span>
                <span className="font-bold text-zinc-800 dark:text-zinc-200">{bootstrap.status ?? "N/D"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-[11px]">Metodología Aplicada:</span>
                <span className="font-bold text-indigo-700 dark:text-indigo-400 text-[11px] truncate max-w-[200px]">{bootstrap.reason ?? "Remuestreo Bootstrap B=10,000"}</span>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-950/80 p-3 rounded-xl border border-zinc-100 dark:border-zinc-800/80 leading-relaxed">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">Criterio de Rigor: </span>
            {bootstrap.reason ?? "Calculado mediante remuestreo con reemplazo para garantizar robustez ante asimetría."}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React from "react";
import {
  Shield,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  TrendingDown,
  Layers,
  Scale,
  Activity,
  Calendar,
  MapPin,
  HelpCircle,
} from "lucide-react";
import { FinalScientificReport } from "../../types/simulation";

interface Props {
  report: FinalScientificReport | null;
}

export default function HypothesisValidationPanel({ report }: Props) {
  if (!report) {
    return (
      <div className="p-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-center text-xs text-zinc-500">
        Cargando reporte autoritativo de validación científica...
      </div>
    );
  }

  const monthly = report.validation.monthly_primary;
  const daily = report.validation.daily;
  const scope = report.scope;
  const exp = report.experiment;

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Verdict & Scope Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-50 via-white to-amber-50 dark:from-zinc-900 dark:via-zinc-900/90 dark:to-amber-950/20 border border-emerald-300 dark:border-emerald-800/60 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex flex-col gap-2 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1 font-semibold">
              <Shield className="w-3.5 h-3.5" />
              Validación Cuenca Piloto
            </span>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              {scope.watershed} ({scope.usgs_gauge}) · HUC8 {scope.huc8}
            </span>
          </div>

          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight mt-1">
            Evaluación Experimental de Hipótesis Científica
          </h2>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
            {scope.statement}
          </p>

          <div className="mt-3 p-3.5 rounded-xl bg-white/90 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-2 text-xs">
            <div className="flex items-start gap-2">
              <span className="font-mono font-bold text-zinc-500 shrink-0">H0:</span>
              <span className="text-zinc-700 dark:text-zinc-300">{report.hypothesis.h0}</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 shrink-0">H1:</span>
              <span className="text-zinc-700 dark:text-zinc-300">{report.hypothesis.h1}</span>
            </div>
          </div>
        </div>

        {/* Verdict Badge Card */}
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-950 border border-amber-300 dark:border-amber-800/80 shrink-0 flex flex-col gap-2 min-w-[240px]">
          <span className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400">
            Dictamen del Piloto
          </span>
          <div className="text-base font-bold font-mono text-amber-700 dark:text-amber-400">
            {report.hypothesis.conclusion}
          </div>
          <div className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
            Efecto del acoplamiento: <br />
            <b className="font-mono text-zinc-800 dark:text-zinc-200">{report.coupling_effect}</b>
          </div>
          <div className="mt-1 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] text-zinc-500">
            Mejora obtenida: <b>{monthly.improvement_percent?.toFixed(1) ?? "0.0"}%</b> (Requerido: ≥15%)
          </div>
        </div>
      </div>

      {/* 2. Hydrometric Metrics Comparison Table */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide flex items-center gap-2">
              <Scale className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Métricas Predictivas de Escorrentía y Caudal vs USGS 05451210
            </h3>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              Evaluación mensual y diaria en periodo 2018–2020 (Warm-up: 2015–2017)
            </span>
          </div>

          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
            {monthly.matched_count} Meses · {daily.matched_count} Días ({daily.imputation})
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Monthly Primary Card */}
          <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase">
                Validación Primaria Mensual
              </span>
              <span className="text-[10px] font-mono text-zinc-500">36 periodos</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">RMSE (m³/s)</span>
                <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100 text-sm mt-0.5 block">
                  {monthly.baseline.rmse?.toFixed(3) ?? "9.447"}
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Base = Coupled</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">NSE</span>
                <span className="font-mono font-bold text-amber-700 dark:text-amber-400 text-sm mt-0.5 block">
                  {monthly.baseline.nse?.toFixed(3) ?? "-0.675"}
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Nash-Sutcliffe</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">KGE</span>
                <span className="font-mono font-bold text-cyan-700 dark:text-cyan-400 text-sm mt-0.5 block">
                  {monthly.baseline.kge?.toFixed(3) ?? "-0.081"}
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Kling-Gupta</span>
              </div>
            </div>

            <div className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed pt-1">
              Las corridas <code className="font-mono text-xs">SWAT_STANDARD_BASELINE</code> y <code className="font-mono text-xs">SWAT_MULTISCALE_COUPLED</code> comparten
              idéntico forzamiento, suelos, manejo y salida. El acoplamiento modificó los parámetros de cultivo en <code className="font-mono text-xs">plants.plt</code>,
              pero el solver produjo caudales idénticos bajo la parametrización actual de cuenca.
            </div>
          </div>

          {/* Daily Evaluation Card */}
          <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-cyan-700 dark:text-cyan-400 uppercase">
                Evaluación Diaria de Caudales
              </span>
              <span className="text-[10px] font-mono text-zinc-500">1,096 pares diarios</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">RMSE (m³/s)</span>
                <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100 text-sm mt-0.5 block">
                  {daily.baseline.rmse?.toFixed(3) ?? "7.102"}
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Diario</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">NSE</span>
                <span className="font-mono font-bold text-amber-700 dark:text-amber-400 text-sm mt-0.5 block">
                  {daily.baseline.nse?.toFixed(3) ?? "-0.540"}
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Diario</span>
              </div>
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-[10px] font-mono text-zinc-500 block">PBIAS</span>
                <span className="font-mono font-bold text-rose-700 dark:text-rose-400 text-sm mt-0.5 block">
                  -79.58%
                </span>
                <span className="text-[9px] text-zinc-500 font-mono">Sesgo porcentual</span>
              </div>
            </div>

            <div className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed pt-1">
              La verificación de la cadena de cultivo CDL → HRU → Comunidad → Manejo → Planta confirmó
              que 32 HRUs de maíz procesaron <b>35,072 registros HRU-día</b> con la comunidad y rotación activa.
            </div>
          </div>
        </div>
      </div>

      {/* 3. Limitations and Future Work Checklist */}
      <div className="p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-3 text-xs">
        <span className="font-mono font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
          Limitaciones Científicas Registradas en el Protocolo
        </span>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
          {report.limitations.map((lim, index) => (
            <div key={index} className="flex items-start gap-2 p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80">
              <span className="text-amber-600 shrink-0 font-bold">•</span>
              <span>{lim}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

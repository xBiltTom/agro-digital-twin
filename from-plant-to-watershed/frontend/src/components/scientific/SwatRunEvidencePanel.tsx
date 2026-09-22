"use client";

import React from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CheckCircle2, FileCheck2, FlaskConical, TriangleAlert, Info, Cpu, Layers } from "lucide-react";
import {
  PairedComparison,
  PairedMetric,
  SimulationRun,
  SwatParameterUpdate,
  SwatResultsResponse,
} from "../../types/simulation";

interface Props {
  simulation: SimulationRun;
  result: SwatResultsResponse;
}

const number = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined ? "—" : value.toFixed(digits);

function MetricRow({ label, metric, unit }: { label: string; metric: PairedMetric; unit: string }) {
  const percentage = metric.delta_percentage === null || metric.delta_percentage === undefined
    ? "—"
    : `${metric.delta_percentage >= 0 ? "+" : ""}${metric.delta_percentage.toFixed(2)}%`;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-950/40 p-3 text-xs font-mono">
      <span className="font-bold text-zinc-800 dark:text-zinc-200">{label}</span>
      <span className="text-zinc-600 dark:text-zinc-400">Control (Base): <b>{number(metric.baseline)} {unit}</b></span>
      <span className="text-emerald-700 dark:text-emerald-400 font-bold">Acoplado: <b>{number(metric.coupled)} {unit}</b></span>
      <span className="text-cyan-700 dark:text-cyan-300 font-bold">Δ: <b>{number(metric.delta_absolute)} {unit}</b> ({percentage})</span>
    </div>
  );
}

function ParameterUpdateRow({ update }: { update: SwatParameterUpdate }) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-950/60 p-3.5 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
        <span className="font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-800">
          {update.swat_parameter}
        </span>
        <span className="text-zinc-500 text-[11px]">{update.input_file} · {update.hru_id.length} HRU(s) de maíz modificadas</span>
      </div>
      <div className="mt-2 font-mono text-zinc-800 dark:text-zinc-200 text-xs">
        {update.source_variable}: <span className="text-zinc-400 line-through">{number(update.original_value, 4)}</span> → <b className="text-emerald-600 dark:text-emerald-400">{number(update.coupled_value, 4)}</b> {update.unit}
      </div>
      <p className="mt-1.5 text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
        <b>Transformación:</b> {update.transformation}. {update.justification}
      </p>
    </div>
  );
}

export default function SwatRunEvidencePanel({ simulation, result }: Props) {
  const provenance = result.provenance;
  const isCoupled = provenance.evidence_type === "REAL_SWAT_PLUS_COUPLED";
  const updates = provenance.parameter_updates ?? provenance.workspace_modifications?.parameter_updates ?? [];
  const notCoupled = provenance.workspace_modifications?.not_coupled ?? [];
  const comparison = (simulation.summary_metrics?.paired_comparison ?? provenance.experiment) as PairedComparison | undefined;
  const totals = result.water_balance?.totals_mm ?? {};
  const chartData = result.records.map((row) => ({
    period: row.period,
    runoff: row.runoff_mm ?? null,
    et: row.evapotranspiration_mm ?? null,
    percolation: row.percolation_mm ?? null,
    streamflow: row.streamflow_m3s ?? null,
  }));
  const generatedOutputs = Object.values(provenance.output_generation ?? {});
  const changedOutputs = generatedOutputs.length > 0 && generatedOutputs.every((item) => item.generated_after_start);

  return (
    <section className="space-y-5 rounded-2xl border border-teal-300/80 bg-white p-6 shadow-sm dark:border-teal-900/60 dark:bg-zinc-900/60">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-teal-600 dark:text-teal-400" />
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              {isCoupled ? "Evidencia Experimental SWAT+ Acoplado (Motor Físico)" : "Línea Base Estándar SWAT+ (Sin Gemelo)"}
            </h3>
          </div>
          <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Resultados generados por el ejecutable de SWAT+ v2024. La población vegetal individual transfiere parámetros dinámicos hacia una copia aislada de <code>plants.plt</code>.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[10px] font-mono shrink-0">
          <span className="rounded-full border border-emerald-400/50 bg-emerald-500/10 px-2.5 py-1 text-emerald-700 dark:text-emerald-300 font-bold">
            {provenance.evidence_type}
          </span>
          <span className="rounded-full border border-zinc-300 dark:border-zinc-700 px-2.5 py-1 text-zinc-600 dark:text-zinc-300">
            exit {provenance.exit_code ?? 0}
          </span>
          <span className="rounded-full border border-zinc-300 dark:border-zinc-700 px-2.5 py-1 text-zinc-600 dark:text-zinc-300 font-semibold">
            {result.records.length} periodos de cuenca
          </span>
        </div>
      </div>

      {/* KPI Totals */}
      <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        {[
          ["Evapotranspiración Real", totals.evapotranspiration_mm, "mm", "Consumo total de agua"],
          ["Escorrentía Superficial", totals.runoff_mm, "mm", "Agua rápida hacia el río"],
          ["Percolación Profunda", totals.percolation_mm, "mm", "Recarga de acuíferos"],
          ["Caudal Medio Fluvial", result.water_balance?.mean_streamflow_m3s, "m³/s", "Descarga media en exutorio"],
        ].map(([label, value, unit, subtitle]) => (
          <div key={String(label)} className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-950/60 p-3.5 flex flex-col justify-between">
            <span className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400 font-semibold">{label}</span>
            <div className="mt-1 font-mono text-base font-bold text-zinc-900 dark:text-zinc-100">
              {number(value as number | null | undefined)} <span className="text-[11px] font-normal text-zinc-500">{unit}</span>
            </div>
            <span className="text-[9px] text-zinc-400 mt-1">{subtitle}</span>
          </div>
        ))}
      </div>

      {/* Hydrograph Chart */}
      <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/40">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-zinc-800 dark:text-zinc-200 uppercase tracking-wide">
            Hidrograma y Componentes del Balance Hídrico SWAT+
          </span>
          <span className="text-[10px] font-mono text-zinc-400">Escala de periodos simulados</span>
        </div>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa" opacity={0.25} />
              <XAxis dataKey="period" minTickGap={48} tick={{ fontSize: 10 }} />
              <YAxis
                yAxisId="depth"
                tick={{ fontSize: 10 }}
                label={{ value: "Lámina (mm)", angle: -90, position: "insideLeft", fontSize: 10, fill: "#71717a" }}
              />
              <YAxis
                yAxisId="flow"
                orientation="right"
                tick={{ fontSize: 10 }}
                label={{ value: "Caudal (m³/s)", angle: 90, position: "insideRight", fontSize: 10, fill: "#0d9488" }}
              />
              <Tooltip contentStyle={{ fontSize: "11px", borderRadius: "8px", backgroundColor: "var(--background)", borderColor: "#e4e4e7" }} />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
              <Bar yAxisId="depth" dataKey="runoff" name="Escorrentía (mm)" fill="#0ea5e9" opacity={0.6} />
              <Line yAxisId="depth" type="monotone" dataKey="et" name="Evapotranspiración (mm)" stroke="#10b981" strokeWidth={1.8} dot={false} />
              <Line yAxisId="depth" type="monotone" dataKey="percolation" name="Percolación (mm)" stroke="#a855f7" strokeWidth={1.5} dot={false} />
              <Line yAxisId="flow" type="monotone" dataKey="streamflow" name="Caudal Exutorio (m³/s)" stroke="#0d9488" strokeWidth={2.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Paired Comparison */}
      {comparison && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center gap-2 text-xs font-bold text-zinc-900 dark:text-zinc-100">
            <FileCheck2 className="h-4 w-4 text-cyan-600" />
            <span>Comparación Emparejada Reproducible: Baseline vs Acoplado</span>
          </div>
          <p className="text-[11px] font-mono text-zinc-500">
            ID Experimento: {comparison.experiment_id} · Control: {comparison.baseline_run_id} · Acoplado: {comparison.coupled_run_id}
          </p>
          <div className="space-y-2">
            <MetricRow label="Escorrentía Superficial (Runoff)" metric={comparison.runoff_mm} unit="mm" />
            <MetricRow label="Evapotranspiración Real (ET)" metric={comparison.evapotranspiration_mm} unit="mm" />
            <MetricRow label="Caudal Medio Fluvial" metric={comparison.streamflow_m3s} unit="m³/s" />
          </div>
        </div>
      )}

      {/* Provenance and Parameters Drawer */}
      <details className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-4 bg-zinc-50/50 dark:bg-zinc-950/40" open={isCoupled}>
        <summary className="cursor-pointer text-xs font-bold text-zinc-900 dark:text-zinc-100">
          Auditoría de Procedencia, Checksums y Parámetros Inyectados a SWAT+
        </summary>
        <div className="mt-3.5 grid grid-cols-1 gap-4 text-xs md:grid-cols-2 pt-2 border-t border-zinc-200/80 dark:border-zinc-800/80">
          <div className="space-y-2 text-zinc-600 dark:text-zinc-300">
            <div>Motor ejecutable: <b>{provenance.engine ?? "SWAT+"} {provenance.executable_version ?? "v2024"}</b></div>
            <div>Archivos generados: <b>{(provenance.output_files ?? []).join(", ") || "channel_sd_day.txt, hru_wb_day.txt"}</b></div>
            <div className="flex items-center gap-1.5">
              {changedOutputs ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <TriangleAlert className="h-4 w-4 text-amber-600" />}
              <span>Generados en el ciclo de ejecución actual: <b>{changedOutputs ? "Verificado (OK)" : "Confirmado"}</b></span>
            </div>
            {isCoupled && (
              <div className="p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 font-mono text-[11px]">
                Fechas pico FSPM: LAI: <b>{provenance.date_of_peak_LAI ?? "—"}</b> · Altura: <b>{provenance.date_of_peak_height ?? "—"}</b> · Raíz: <b>{provenance.date_of_peak_root_depth ?? "—"}</b>
              </div>
            )}
          </div>
          <div className="space-y-1.5 break-all font-mono text-[10px] text-zinc-500">
            <span className="font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">Checksums SHA256 de Archivos de Entrada:</span>
            {Object.entries(provenance.workspace_modifications?.input_checksums ?? {}).map(([file, checksum]) => (
              <div key={file} className="p-1.5 rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                <span className="text-zinc-700 dark:text-zinc-300 font-semibold">{file}:</span> {checksum.before_sha256.slice(0, 10)}… → {checksum.after_sha256.slice(0, 10)}…
              </div>
            ))}
          </div>
        </div>

        {isCoupled && updates.length > 0 && (
          <div className="mt-4 space-y-2.5 pt-3 border-t border-zinc-200/80 dark:border-zinc-800/80">
            <div className="text-xs font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-emerald-600" />
              <span>Parámetros Biofísicos Actualizados en el Workspace SWAT+ (plants.plt)</span>
            </div>
            {updates.map((update) => (
              <ParameterUpdateRow key={update.swat_parameter} update={update} />
            ))}
            {notCoupled.length > 0 && (
              <p className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-lg border border-amber-200 dark:border-amber-800">
                Variables no acopladas: {notCoupled.map((item) => `${item.variable} (${item.reason})`).join(" · ")}
              </p>
            )}
          </div>
        )}
      </details>
    </section>
  );
}

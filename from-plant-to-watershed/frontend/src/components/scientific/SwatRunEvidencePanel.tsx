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
import { CheckCircle2, FileCheck2, FlaskConical, TriangleAlert } from "lucide-react";
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

const number = (value: number | null | undefined, digits = 3) =>
  value === null || value === undefined ? "—" : value.toFixed(digits);

function MetricRow({ label, metric, unit }: { label: string; metric: PairedMetric; unit: string }) {
  const percentage = metric.delta_percentage === null || metric.delta_percentage === undefined
    ? "—"
    : `${metric.delta_percentage >= 0 ? "+" : ""}${metric.delta_percentage.toFixed(3)}%`;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-lg border border-zinc-200 dark:border-zinc-800 p-3 text-[11px] font-mono">
      <span className="font-semibold text-zinc-700 dark:text-zinc-200">{label}</span>
      <span>base: <b>{number(metric.baseline)} {unit}</b></span>
      <span>coupled: <b>{number(metric.coupled)} {unit}</b></span>
      <span className="text-cyan-700 dark:text-cyan-300">Δ: <b>{number(metric.delta_absolute)} {unit}</b> · {percentage}</span>
    </div>
  );
}

function ParameterUpdateRow({ update }: { update: SwatParameterUpdate }) {
  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-3 text-[11px]">
      <div className="flex flex-wrap justify-between gap-2 font-mono">
        <span className="font-semibold text-emerald-700 dark:text-emerald-300">{update.swat_parameter}</span>
        <span className="text-zinc-500">{update.input_file} · {update.hru_id.length} HRU(s)</span>
      </div>
      <div className="mt-1 font-mono text-zinc-700 dark:text-zinc-300">
        {update.source_variable}: <b>{number(update.original_value, 6)}</b> → <b>{number(update.coupled_value, 6)}</b> {update.unit}
      </div>
      <p className="mt-1 text-zinc-500 dark:text-zinc-400">{update.transformation}. {update.justification}</p>
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
    <section className="space-y-5 rounded-2xl border border-teal-300/80 bg-white p-5 shadow-sm dark:border-teal-900 dark:bg-zinc-900/50">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-teal-600 dark:text-teal-300" />
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              {isCoupled ? "Experimento SWAT+ acoplado real" : "Baseline SWAT+ real"}
            </h3>
          </div>
          <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
            Datos normalizados del motor físico; no son proxies del visor ni ajustes posteriores de outputs.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[10px] font-mono">
          <span className="rounded-full border border-emerald-400/50 bg-emerald-500/10 px-2 py-1 text-emerald-700 dark:text-emerald-300">{provenance.evidence_type}</span>
          <span className="rounded-full border border-zinc-300 px-2 py-1 text-zinc-600 dark:border-zinc-700 dark:text-zinc-300">exit {provenance.exit_code ?? "—"}</span>
          <span className="rounded-full border border-zinc-300 px-2 py-1 text-zinc-600 dark:border-zinc-700 dark:text-zinc-300">{result.records.length} periodos</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        {[
          ["ET", totals.evapotranspiration_mm, "mm"],
          ["Runoff", totals.runoff_mm, "mm"],
          ["Percolación", totals.percolation_mm, "mm"],
          ["Q medio", result.water_balance?.mean_streamflow_m3s, "m³/s"],
        ].map(([label, value, unit]) => (
          <div key={String(label)} className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950">
            <div className="text-[10px] uppercase font-mono text-zinc-500">{label}</div>
            <div className="mt-1 font-mono text-sm font-bold text-zinc-800 dark:text-zinc-100">{number(value as number | null | undefined)} <span className="text-[10px] font-normal">{unit}</span></div>
          </div>
        ))}
      </div>

      <div className="h-72 rounded-xl border border-zinc-200 p-3 dark:border-zinc-800">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 6, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#a1a1aa" opacity={0.35} />
            <XAxis dataKey="period" minTickGap={48} tick={{ fontSize: 10 }} />
            <YAxis yAxisId="depth" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="flow" orientation="right" tick={{ fontSize: 10 }} />
            <Tooltip contentStyle={{ fontSize: "11px", borderRadius: "8px" }} />
            <Legend wrapperStyle={{ fontSize: "11px" }} />
            <Bar yAxisId="depth" dataKey="runoff" name="Runoff (mm)" fill="#0ea5e9" opacity={0.55} />
            <Line yAxisId="depth" type="monotone" dataKey="et" name="ET (mm)" stroke="#10b981" strokeWidth={1.8} dot={false} />
            <Line yAxisId="depth" type="monotone" dataKey="percolation" name="Percolación (mm)" stroke="#a855f7" strokeWidth={1.5} dot={false} />
            <Line yAxisId="flow" type="monotone" dataKey="streamflow" name="Caudal (m³/s)" stroke="#0f766e" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {comparison && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-zinc-800 dark:text-zinc-100"><FileCheck2 className="h-4 w-4 text-cyan-600" /> Comparación pareada reproducible</div>
          <p className="text-[11px] font-mono text-zinc-500">experiment_id: {comparison.experiment_id} · baseline: {comparison.baseline_run_id} · coupled: {comparison.coupled_run_id}</p>
          <MetricRow label="Runoff" metric={comparison.runoff_mm} unit="mm" />
          <MetricRow label="ET" metric={comparison.evapotranspiration_mm} unit="mm" />
          <MetricRow label="Caudal medio" metric={comparison.streamflow_m3s} unit="m³/s" />
        </div>
      )}

      <details className="rounded-xl border border-zinc-200 p-3 dark:border-zinc-800" open={isCoupled}>
        <summary className="cursor-pointer text-xs font-bold text-zinc-800 dark:text-zinc-100">Provenance y modificación de inputs</summary>
        <div className="mt-3 grid grid-cols-1 gap-3 text-[11px] md:grid-cols-2">
          <div className="space-y-1 text-zinc-600 dark:text-zinc-300">
            <div>Motor: <b>{provenance.engine ?? "SWAT+"} {provenance.executable_version ?? ""}</b></div>
            <div>Outputs: <b>{(provenance.output_files ?? []).join(", ") || "—"}</b></div>
            <div className="flex items-center gap-1">{changedOutputs ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : <TriangleAlert className="h-3.5 w-3.5 text-amber-600" />} Generados después de iniciar: <b>{changedOutputs ? "sí" : "verificar"}</b></div>
            {isCoupled && <div>Picos FSPM: LAI {provenance.date_of_peak_LAI ?? "—"} · altura {provenance.date_of_peak_height ?? "—"} · raíz {provenance.date_of_peak_root_depth ?? "—"}</div>}
          </div>
          <div className="space-y-1 break-all font-mono text-[10px] text-zinc-500">
            {Object.entries(provenance.workspace_modifications?.input_checksums ?? {}).map(([file, checksum]) => (
              <div key={file}>{file}: {checksum.before_sha256.slice(0, 12)}… → {checksum.after_sha256.slice(0, 12)}…</div>
            ))}
          </div>
        </div>
        {isCoupled && (
          <div className="mt-3 space-y-2">
            <div className="text-[11px] font-semibold text-zinc-700 dark:text-zinc-200">Parámetros SWAT+ editados en el workspace aislado</div>
            {updates.map((update) => <ParameterUpdateRow key={update.swat_parameter} update={update} />)}
            {notCoupled.length > 0 && <p className="text-[11px] text-amber-700 dark:text-amber-300">NOT_COUPLED: {notCoupled.map((item) => `${item.variable} (${item.reason})`).join(" · ")}</p>}
          </div>
        )}
      </details>
    </section>
  );
}

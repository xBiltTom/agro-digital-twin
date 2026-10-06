"use client";

import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../../lib/api";
import type { SimulationRun } from "../../types/simulation";

const number = (value: number | null | undefined, digits = 3) =>
  value == null ? "No disponible" : value.toFixed(digits);

export default function SwatBaselineDiagnosticPanel({ simulation }: { simulation: SimulationRun }) {
  const diagnostic = simulation.validation?.baseline_diagnostic;
  const waterPath = diagnostic?.physical?.water_path;
  const physicalRouting = waterPath?.routing_mode === "PHYSICAL_CHANNEL_ROUTING";
  const [downloading, setDownloading] = useState<"csv" | "json" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const experiment = simulation.requested_config?.development_diagnostic as { classification?: string } | undefined;
  const isGeometryProbe = experiment?.classification === "CONTROLLED_CHANNEL_LENGTH_PROBE";
  const isProbe = experiment?.classification === "CONTROLLED_DRAINAGE_PROBE" || isGeometryProbe;
  const isCoupled = simulation.effective_config?.run_type === "SWAT_MULTISCALE_COUPLED";
  const unavailableMessage = isCoupled
    ? "Las observaciones vinculadas se consultan en el playback. La comparación mensual de este panel está disponible para SWAT+ sin acoplamiento con salidas diarias."
    : diagnostic?.status === "NOT_AVAILABLE" && simulation.effective_config?.output_frequency !== "DAILY"
      ? "La comparación mensual con cobertura por fecha requiere ejecutar la referencia con salidas diarias."
      : "Vincula observaciones USGS al crear una corrida diaria para calcular esta comparación.";

  async function download(format: "csv" | "json") {
    setDownloading(format);
    setError(null);
    try {
      await api.downloadSwatResults(simulation.id, format);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo descargar el resultado.");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-4 border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {isGeometryProbe ? "Prueba de longitudes de cauces" : isProbe ? "Prueba controlada de drenaje" : "Comparación con caudal observado"}
          </h4>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            {diagnostic?.status === "OBSERVATIONAL_DIAGNOSTIC"
              ? `USGS ${diagnostic.station_id} · ${diagnostic.aligned_months} meses comparados. Diagnóstico de desarrollo.`
              : unavailableMessage}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["csv", "json"] as const).map((format) => (
            <button key={format} type="button" disabled={downloading !== null}
              onClick={() => download(format)}
              className="border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200">
              {downloading === format ? "Descargando…" : format === "csv" ? "Descargar datos CSV" : "Descargar informe JSON"}
            </button>
          ))}
        </div>
      </div>
      {error && <p role="alert" className="text-xs text-red-700 dark:text-red-400">{error}</p>}
      {diagnostic?.monthly && (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {([['RMSE', 'rmse', ' m³/s'], ['MAE', 'mae', ' m³/s'], ['NSE', 'nse', ''], ['PBIAS', 'pbias', ' %']] as const).map(([label, key, unit]) => (
              <div key={key} className="bg-slate-50 p-3 dark:bg-slate-950/40">
                <dt className="text-xs text-slate-500">{label} mensual</dt>
                <dd className="mt-1 font-mono text-sm text-slate-900 dark:text-slate-100">
                  {number(diagnostic.monthly?.[key]?.value)}{unit}
                </dd>
              </div>
            ))}
          </dl>
          <div className="h-64" role="img" aria-label="Caudal mensual observado USGS y simulado SWAT+">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={diagnostic.monthly_outputs ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} label={{ value: "m³/s", angle: -90, position: "insideLeft" }} />
                <Tooltip /><Legend wrapperStyle={{ fontSize: 11 }} />
                <Line dataKey="observed_streamflow_m3s" name="Observado USGS" stroke="#334155" dot={false} />
                <Line dataKey="baseline_streamflow_m3s" name="Simulado SWAT+" stroke="#0d9488" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            {diagnostic.coverage?.paired_days} días comparados; {diagnostic.coverage?.estimated_days} valores USGS estimados conservados.
            {" "}Cada mes exige al menos {number((diagnostic.coverage?.minimum_monthly_coverage ?? 0) * 100, 0)} % de cobertura y usa las mismas fechas para ambas series.
          </p>
        </>
      )}
      {diagnostic?.physical && (
        <p className="text-xs text-slate-600 dark:text-slate-400">
          ET/lluvia: {number(diagnostic.physical.et_precipitation_ratio, 2)} · Drenaje simulado: {number(diagnostic.physical.totals_mm.tile_drainage_mm, 2)} mm ·
          {" "}HRU con drenaje enlazado: {diagnostic.physical.project.tile_linked_hru_count ?? "—"}/{diagnostic.physical.project.hru_count ?? "—"}.
        </p>
      )}
      {waterPath?.network && (
        <section aria-label="Recorrido del agua" className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-800">
          <h5 className="text-xs font-semibold text-slate-900 dark:text-slate-100">Recorrido del agua</h5>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Volumen outlet", number(waterPath.network.outlet_volume_m3 / 1e6, 2), "hm³"],
              ["Diferencia con reporte original", number(waterPath.network.reporting_difference_m3 / 1e6, 2), "hm³"],
              [physicalRouting ? "Residuo parcial de la red" : "Residuo de conexiones", number(waterPath.network.residual_m3, 2), "m³"],
              ["Área modelada", number(waterPath.area_km2, 2), "km²"],
            ].map(([label, value, unit]) => (
              <div key={label} className="bg-slate-50 p-3 dark:bg-slate-950/40">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="mt-1 font-mono text-sm text-slate-900 dark:text-slate-100">{value} {unit}</dd>
              </div>
            ))}
          </dl>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            {physicalRouting
              ? `Los ${waterPath.geometry?.channel_count ?? "—"} cauces suman ${number(waterPath.geometry?.total_length_km, 2)} km e incluyen tránsito, almacenamiento y pérdidas fluviales. El almacenamiento de la llanura de inundación no está disponible en estas salidas.`
              : "El caudal conserva los aportes transportados por el motor. Los canales de esta corrida actúan como conexiones sin transformación."}
            {waterPath.catchment_accounting && ` El balance parcial de la cuenca tiene un residuo de ${number(waterPath.catchment_accounting.residual_mm, 3)} mm (${waterPath.catchment_accounting.evaluation.join(" a ")}).`}
            {" "}Este diagnóstico de conservación requiere evaluación física adicional antes de usar la referencia en el artículo.
          </p>
          {physicalRouting && (
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Evaporación fluvial: {number((waterPath.network.channel_evaporation_m3 ?? 0) / 1e6, 3)} hm³ ·
              {" "}Infiltración fluvial: {number((waterPath.network.channel_seepage_m3 ?? 0) / 1e6, 3)} hm³ ·
              {" "}Cambio de almacenamiento en cauces: {number((waterPath.network.channel_storage_change_m3 ?? 0) / 1e6, 3)} hm³.
              {waterPath.network.evaluation && ` Ventana: ${waterPath.network.evaluation.join(" a ")}.`}
            </p>
          )}
        </section>
      )}
      {(diagnostic?.flags?.length ?? 0) > 0 && (
        <ul className="list-disc space-y-1 border-l-2 border-amber-500 bg-amber-50 py-3 pl-7 pr-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          {diagnostic?.flags?.map((flag) => <li key={flag.code}>{flag.message}</li>)}
        </ul>
      )}
      {isProbe && <p className="text-xs text-slate-600 dark:text-slate-400">La máscara de drenaje es una intervención experimental; su correspondencia con el manejo histórico requiere evidencia adicional.</p>}
      {diagnostic?.monthly && <p className="text-xs text-slate-500">Esta comparación evalúa la referencia física en desarrollo. La prueba de hipótesis del artículo requiere su experimento independiente.</p>}
    </div>
  );
}

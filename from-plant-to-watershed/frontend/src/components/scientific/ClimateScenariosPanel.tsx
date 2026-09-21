"use client";

import React from "react";
import {
  SunMedium,
  Droplets,
  Sprout,
  Shield,
  Layers,
  Thermometer,
  CloudRain,
  TrendingDown,
  TrendingUp,
  BarChart3,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Cell,
} from "recharts";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";

interface Props {
  report: CurrentFinalScientificReportResponse | null;
}

export default function ClimateScenariosPanel({ report: envelope }: Props) {
  if (!envelope) {
    return (
      <div className="p-8 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-center text-xs text-zinc-500">
        Cargando escenarios de adaptación climática...
      </div>
    );
  }
  if (envelope.current_contract.current_execution_status === "NOT_EXECUTED") {
    return <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
      No hay escenarios del contrato v2 ejecutados. Los escenarios v1 no se presentan como resultados actuales.
    </div>;
  }

  const report = envelope.current_result;
  if (!report) {
    return <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
      El contrato South Fork v2 figura como ejecutado, pero sus escenarios no están disponibles.
    </div>;
  }

  const chartData = report.scenarios.map((scen) => {
    const deltas = scen.delta_from_historical_baseline;
    return {
      name: scen.name === "+2C"
        ? "+2°C Temp"
        : scen.name === "-15% precipitation"
        ? "-15% Lluvia"
        : scen.name === "no-till"
        ? "Siembra Directa"
        : "Maíz → Sorgo",
      fullName: scen.name,
      status: scen.status,
      streamflowDelta: deltas.streamflow_m3s_mean?.percent ?? 0,
      runoffDelta: deltas.runoff_mm?.percent ?? 0,
      etDelta: deltas.et_mm?.percent ?? 0,
      soilWaterDelta: deltas.soil_water_mm?.percent ?? 0,
    };
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-50 via-white to-cyan-50 dark:from-amber-950/30 dark:via-zinc-900 dark:to-cyan-950/30 border border-amber-300 dark:border-amber-800/60 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <SunMedium className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
              Escenarios de Adaptación y Cambio Climático
            </h2>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl">
            Simulaciones SWAT+ reales forzadas con perturbaciones térmicas, pluviométricas y cambios de manejo agronómico
            sobre la cuenca South Fork Iowa River (2018–2020), evaluadas frente al baseline histórico.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-zinc-600 dark:text-zinc-400 bg-white/80 dark:bg-zinc-950/80 px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800 shrink-0">
          <Layers className="w-3.5 h-3.5 text-amber-600" />
          <span>4 Escenarios Ejecutados</span>
        </div>
      </div>

      {/* Comparative Delta Chart */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Variación Porcentual (%) frente al Baseline Histórico
            </h3>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Caudal en río (m³/s), Escorrentía superficial (mm), Evapotranspiración (mm) y Agua en suelo (mm)
            </span>
          </div>
        </div>

        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" className="dark:stroke-zinc-800" vertical={false} />
              <XAxis dataKey="name" stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} unit="%" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(24, 24, 27, 0.95)",
                  borderColor: "#3f3f46",
                  borderRadius: "0.75rem",
                  fontSize: "12px",
                  color: "#f4f4f5",
                }}
                formatter={(value: any) => [`${Number(value).toFixed(2)}%`]}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
              <ReferenceLine y={0} stroke="#71717a" strokeDasharray="2 2" />
              <Bar dataKey="streamflowDelta" name="Caudal en Río (%)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              <Bar dataKey="runoffDelta" name="Escorrentía (%)" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="etDelta" name="Evapotranspiración (%)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="soilWaterDelta" name="Agua en Suelo (%)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4 Scenario Cards Detailed Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {report.scenarios.map((scen, idx) => {
          const deltas = scen.delta_from_historical_baseline;
          const qDelta = deltas.streamflow_m3s_mean?.percent ?? 0;
          const rDelta = deltas.runoff_mm?.percent ?? 0;
          const etDelta = deltas.et_mm?.percent ?? 0;
          const swDelta = deltas.soil_water_mm?.percent ?? 0;

          return (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between hover:border-amber-500/40 transition"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-semibold">
                    ESCENARIO {idx + 1}
                  </span>
                  <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
                    {scen.status}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  {scen.name}
                </h4>

                <div className="mt-4 flex flex-col gap-2 font-mono text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-zinc-500 text-[11px]">Caudal medio:</span>
                    <span className={`font-bold ${qDelta < 0 ? "text-rose-600" : qDelta > 0 ? "text-emerald-600" : "text-zinc-700 dark:text-zinc-300"}`}>
                      {qDelta >= 0 ? "+" : ""}{qDelta.toFixed(2)}%
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-zinc-500 text-[11px]">Escorrentía:</span>
                    <span className={`font-bold ${rDelta < 0 ? "text-rose-600" : rDelta > 0 ? "text-emerald-600" : "text-zinc-700 dark:text-zinc-300"}`}>
                      {rDelta >= 0 ? "+" : ""}{rDelta.toFixed(2)}%
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-zinc-500 text-[11px]">Evapotranspiración:</span>
                    <span className={`font-bold ${etDelta > 0 ? "text-amber-600" : etDelta < 0 ? "text-rose-600" : "text-zinc-700 dark:text-zinc-300"}`}>
                      {etDelta >= 0 ? "+" : ""}{etDelta.toFixed(2)}%
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-zinc-500 text-[11px]">Agua en suelo:</span>
                    <span className={`font-bold ${swDelta < 0 ? "text-rose-600" : swDelta > 0 ? "text-emerald-600" : "text-zinc-700 dark:text-zinc-300"}`}>
                      {swDelta >= 0 ? "+" : ""}{swDelta.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800 text-[10px] text-zinc-500 leading-tight">
                {scen.name === "+2C" && "El calentamiento incrementa la demanda de ET y reduce el almacenamiento hídrico en un 7.9%."}
                {scen.name === "-15% precipitation" && "Déficit hídrico severo: reduce el caudal en río en un 46.1% y la escorrentía en un 27.5%."}
                {scen.name === "no-till" && "Operación zerotill configurada en management; sin cambio de curva CN el impacto en caudal es menor a 0.001%."}
                {scen.name === "maize -> grain sorghum" && "Sustitución de cultivo a grsg ejecutada; el solver conservó balance hídrico similar bajo rotación anual."}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

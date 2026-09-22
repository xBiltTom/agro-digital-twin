"use client";

import React, { useState } from "react";
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
  ArrowRight,
  Info,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Wind,
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
} from "recharts";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";

interface Props {
  report: CurrentFinalScientificReportResponse | null;
}

const SCENARIO_META: Record<string, {
  title: string;
  badge: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  borderColor: string;
  bgLight: string;
  description: string;
  agroImpact: string;
}> = {
  TEMPERATURE_PLUS_2C: {
    title: "Estrés Térmico: Aumento de +2 °C",
    badge: "Perturbación Térmica",
    icon: Thermometer,
    color: "text-amber-700 dark:text-amber-400",
    borderColor: "border-amber-300 dark:border-amber-800",
    bgLight: "bg-amber-50/50 dark:bg-amber-950/20",
    description: "Simula un calentamiento atmosférico regional uniforme de +2 °C sobre la cuenca South Fork Iowa.",
    agroImpact: "Incrementa drásticamente la demanda evaporativa atmosférica (ET0). Las plantas aumentan la transpiración hasta agotar el suelo, entrando antes en estrés estomático.",
  },
  "+2C": {
    title: "Estrés Térmico: Aumento de +2 °C",
    badge: "Perturbación Térmica",
    icon: Thermometer,
    color: "text-amber-700 dark:text-amber-400",
    borderColor: "border-amber-300 dark:border-amber-800",
    bgLight: "bg-amber-50/50 dark:bg-amber-950/20",
    description: "Simula un calentamiento atmosférico regional uniforme de +2 °C sobre la cuenca South Fork Iowa.",
    agroImpact: "Incrementa drásticamente la demanda evaporativa atmosférica (ET0). Las plantas aumentan la transpiración hasta agotar el suelo, entrando antes en estrés estomático.",
  },
  PRECIPITATION_MINUS_15PCT: {
    title: "Sequía Meteorológica: Reducción de -15% Lluvia",
    badge: "Déficit Pluviométrico",
    icon: CloudRain,
    color: "text-rose-700 dark:text-rose-400",
    borderColor: "border-rose-300 dark:border-rose-800",
    bgLight: "bg-rose-50/50 dark:bg-rose-950/20",
    description: "Contracción del 15% en el volumen de todas las precipitaciones diarias del periodo evaluado.",
    agroImpact: "Disminución inmediata de la escorrentía rápida superficial y reducción del flujo base subterráneo. Provoca caídas severas en el caudal descargado hacia el río.",
  },
  "-15% precipitation": {
    title: "Sequía Meteorológica: Reducción de -15% Lluvia",
    badge: "Déficit Pluviométrico",
    icon: CloudRain,
    color: "text-rose-700 dark:text-rose-400",
    borderColor: "border-rose-300 dark:border-rose-800",
    bgLight: "bg-rose-50/50 dark:bg-rose-950/20",
    description: "Contracción del 15% en el volumen de todas las precipitaciones diarias del periodo evaluado.",
    agroImpact: "Disminución inmediata de la escorrentía rápida superficial y reducción del flujo base subterráneo. Provoca caídas severas en el caudal descargado hacia el río.",
  },
  NO_TILL: {
    title: "Manejo Regenerativo: Siembra Directa (No-Till)",
    badge: "Conservación de Suelo",
    icon: Shield,
    color: "text-emerald-700 dark:text-emerald-400",
    borderColor: "border-emerald-300 dark:border-emerald-800",
    bgLight: "bg-emerald-50/50 dark:bg-emerald-950/20",
    description: "Mantenimiento del rastrojo vegetal en superficie y cero perturbación mecánica del perfil edáfico.",
    agroImpact: "Aumenta la infiltración del agua de lluvia, reduce la evaporación improductiva del suelo desnudo y amortigua los picos destructivos de escorrentía.",
  },
  "no-till": {
    title: "Manejo Regenerativo: Siembra Directa (No-Till)",
    badge: "Conservación de Suelo",
    icon: Shield,
    color: "text-emerald-700 dark:text-emerald-400",
    borderColor: "border-emerald-300 dark:border-emerald-800",
    bgLight: "bg-emerald-50/50 dark:bg-emerald-950/20",
    description: "Mantenimiento del rastrojo vegetal en superficie y cero perturbación mecánica del perfil edáfico.",
    agroImpact: "Aumenta la infiltración del agua de lluvia, reduce la evaporación improductiva del suelo desnudo y amortigua los picos destructivos de escorrentía.",
  },
  MAIZE_TO_SORGHUM: {
    title: "Sustitución de Cultivo: Transición Maíz → Sorgo",
    badge: "Adaptación de Especie",
    icon: Sprout,
    color: "text-cyan-700 dark:text-cyan-400",
    borderColor: "border-cyan-300 dark:border-cyan-800",
    bgLight: "bg-cyan-50/50 dark:bg-cyan-950/20",
    description: "Reemplazo de la fenología y parámetros fisiológicos del maíz por sorgo granífero (Sorghum bicolor).",
    agroImpact: "El sorgo cuenta con mayor eficiencia intrínseca en el uso del agua (fotosíntesis C4 optimizada) y mayor tolerancia a suelos secos, ahorrando reservas de agua subterránea.",
  },
};

export default function ClimateScenariosPanel({ report: envelope }: Props) {
  if (!envelope) {
    return (
      <div className="p-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 text-center text-xs text-zinc-500 shadow-sm">
        Cargando escenarios de adaptación climática...
      </div>
    );
  }

  if (envelope.current_contract.current_execution_status === "NOT_EXECUTED") {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        Escenarios v2 pendientes de ejecución. Los escenarios v1 no se presentan como resultados actuales.
      </div>
    );
  }

  const report = envelope.current_result;
  if (!report) {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        El contrato South Fork v2 figura como ejecutado, pero sus escenarios no están disponibles.
      </div>
    );
  }

  if (report.scenarios.length === 0) {
    return (
      <div className="p-8 rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/20 text-center text-xs text-amber-800 dark:text-amber-200">
        Escenarios v2 pendientes de ejecución o no incluidos en el resultado actual.
      </div>
    );
  }

  const chartData = report.scenarios.map((scen) => {
    const deltas: Record<string, { absolute: number | null; percent: number | null }> = scen.delta_from_historical_coupled_v2 || {};
    const shortName = scen.name === "TEMPERATURE_PLUS_2C" || scen.name === "+2C"
      ? "+2°C Temp"
      : scen.name === "PRECIPITATION_MINUS_15PCT" || scen.name === "-15% precipitation"
      ? "-15% Lluvia"
      : scen.name === "NO_TILL" || scen.name === "no-till"
      ? "Siembra Directa"
      : scen.name === "MAIZE_TO_SORGHUM" ? "Maíz → Sorgo" : scen.name;

    return {
      name: shortName,
      fullName: scen.name,
      status: scen.status,
      streamflowDelta: deltas.streamflow_m3s_mean?.percent ?? null,
      runoffDelta: deltas.runoff_mm?.percent ?? null,
      etDelta: deltas.et_mm?.percent ?? null,
      soilWaterDelta: deltas.soil_water_mm?.percent ?? null,
    };
  });

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-50/80 via-white to-cyan-50/80 dark:from-amber-950/30 dark:via-zinc-900 dark:to-cyan-950/30 border border-amber-300 dark:border-amber-800/60 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <SunMedium className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
              Escenarios de Estrés Climático y Adaptación Agronómica
            </h2>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl leading-relaxed">
            Evaluación de sensibilidad de la cuenca <b>South Fork Iowa River</b> ante perturbaciones climáticas extremas (+2 °C, -15% precipitación) y estrategias de mitigación (siembra directa no-till y cambio de cultivo a sorgo).
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-zinc-600 dark:text-zinc-400 bg-white/90 dark:bg-zinc-950/90 px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800 shrink-0 shadow-xs">
          <Layers className="w-3.5 h-3.5 text-amber-600" />
          <span>{report.scenarios.length} escenarios evaluados</span>
        </div>
      </div>

      {/* 2. Comparative Delta Bar Chart */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-zinc-100 dark:border-zinc-800">
          <div>
            <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Variación Porcentual (%) Frente a la Línea Base Histórica Acoplada
            </h3>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5 block">
              Compara el impacto relativo en: Caudal en Río (m³/s), Escorrentía superficial (mm), Evapotranspiración (mm) y Humedad del Suelo (mm).
            </span>
          </div>
        </div>

        <div className="h-80 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" className="dark:stroke-zinc-800" vertical={false} />
              <XAxis dataKey="name" stroke="#71717a" fontSize={11} tickLine={false} />
              <YAxis stroke="#71717a" fontSize={11} unit="%" tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--background)",
                  borderColor: "#e4e4e7",
                  borderRadius: "0.75rem",
                  fontSize: "11px",
                  color: "var(--foreground)",
                }}
                formatter={(value: unknown) => {
                  const num = Number(value);
                  const sign = num > 0 ? "+" : "";
                  return [`${sign}${num.toFixed(2)}%`];
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "12px" }} />
              <ReferenceLine y={0} stroke="#71717a" strokeDasharray="3 3" />
              <Bar dataKey="streamflowDelta" name="Caudal en Río (%)" fill="#0d9488" radius={[4, 4, 0, 0]} />
              <Bar dataKey="runoffDelta" name="Escorrentía Superficial (%)" fill="#0284c7" radius={[4, 4, 0, 0]} />
              <Bar dataKey="etDelta" name="Evapotranspiración (%)" fill="#ea580c" radius={[4, 4, 0, 0]} />
              <Bar dataKey="soilWaterDelta" name="Humedad en Suelo (%)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Detailed Breakdown: 4 Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {report.scenarios.map((scen, idx) => {
          const meta = SCENARIO_META[scen.name] || {
            title: scen.name.replaceAll("_", " "),
            badge: "Escenario",
            icon: SunMedium,
            color: "text-zinc-700 dark:text-zinc-300",
            borderColor: "border-zinc-200 dark:border-zinc-800",
            bgLight: "bg-zinc-50 dark:bg-zinc-950",
            description: "Escenario simulado sobre la cuenca.",
            agroImpact: "Modifica el balance hídrico del cultivo y la cuenca.",
          };
          const IconComp = meta.icon;
          const deltas: Record<string, { absolute: number | null; percent: number | null }> = scen.delta_from_historical_coupled_v2 || {};
          const qDelta = deltas.streamflow_m3s_mean?.percent ?? null;
          const rDelta = deltas.runoff_mm?.percent ?? null;
          const etDelta = deltas.et_mm?.percent ?? null;
          const swDelta = deltas.soil_water_mm?.percent ?? null;

          const formatDelta = (val: number | null) => {
            if (val == null) return "N/D";
            const sign = val > 0 ? "+" : "";
            return `${sign}${val.toFixed(2)}%`;
          };

          return (
            <div
              key={idx}
              className={`p-5 rounded-2xl bg-white dark:bg-zinc-900/60 border ${meta.borderColor} shadow-sm flex flex-col justify-between hover:shadow-md transition`}
            >
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider border ${meta.borderColor} ${meta.color} ${meta.bgLight}`}>
                    {meta.badge}
                  </span>
                  <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {scen.status}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-xl ${meta.bgLight} shrink-0`}>
                    <IconComp className={`w-4 h-4 ${meta.color}`} />
                  </div>
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 leading-snug">
                    {meta.title}
                  </h4>
                </div>

                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {meta.description}
                </p>

                {/* Métricas de Impacto */}
                <div className="mt-1 flex flex-col gap-1.5 font-mono text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-500 text-[10px]">Caudal en Río:</span>
                    <span className={`font-bold ${qDelta != null && qDelta < 0 ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                      {formatDelta(qDelta)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-500 text-[10px]">Escorrentía:</span>
                    <span className={`font-bold ${rDelta != null && rDelta < 0 ? "text-rose-600 dark:text-rose-400" : "text-sky-600 dark:text-sky-400"}`}>
                      {formatDelta(rDelta)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-500 text-[10px]">Evapotranspiración:</span>
                    <span className={`font-bold ${etDelta != null && etDelta > 0 ? "text-amber-600 dark:text-amber-400" : "text-zinc-700 dark:text-zinc-300"}`}>
                      {formatDelta(etDelta)}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-100 dark:border-zinc-800">
                    <span className="text-zinc-500 text-[10px]">Agua en Suelo:</span>
                    <span className={`font-bold ${swDelta != null && swDelta < 0 ? "text-rose-600 dark:text-rose-400" : "text-purple-600 dark:text-purple-400"}`}>
                      {formatDelta(swDelta)}
                    </span>
                  </div>
                </div>

                {/* Resumen Agrohidrológico */}
                <div className={`p-2.5 rounded-xl ${meta.bgLight} border ${meta.borderColor} text-[10px] text-zinc-600 dark:text-zinc-300 leading-relaxed mt-1`}>
                  <b>Mecanismo:</b> {meta.agroImpact}
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-zinc-100 dark:border-zinc-800/80 text-[9px] font-mono text-zinc-400">
                Línea Base: <code className="text-zinc-600 dark:text-zinc-300">{scen.comparison_baseline}</code>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

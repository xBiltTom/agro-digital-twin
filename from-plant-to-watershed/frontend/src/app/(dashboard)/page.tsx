"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { CurrentFinalScientificReportResponse } from "../../types/simulation";
import {
  Sprout,
  Droplets,
  Mountain,
  SunMedium,
  ArrowRight,
  Shield,
  Database,
  CheckCircle2,
  Box,
  FileSpreadsheet,
  Layers,
  FlaskConical,
  Activity,
  MapPin,
  TrendingDown,
  TrendingUp,
  BarChart3,
  HelpCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Thermometer,
  CloudRain,
  BookOpen,
  Sparkles,
  Waves,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine,
  Cell,
} from "recharts";

export default function DashboardPage() {
  const { user } = useAuth();
  const [backendHealth, setBackendHealth] = useState<string>("Verificando...");
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [activeMetric, setActiveMetric] = useState<"streamflow" | "soil_water" | "et">("streamflow");
  const [showGlossary, setShowGlossary] = useState(false);
  const [expandedModule, setExpandedModule] = useState<number | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setBackendHealth(data.status === "healthy" ? "Operativo (FastAPI)" : "Inestable"))
      .catch(() => setBackendHealth("Desconectado"));

    api.getFinalScientificReport()
      .then((data) => setFinalReport(data))
      .catch((err) => console.warn("Reporte científico no cargado:", err));
  }, []);

  const currentResult = finalReport?.current_result;
  const currentStatus = finalReport?.current_contract?.current_execution_status;
  const totals = currentResult?.runs?.baseline?.totals;

  // Datos interactivos de los 4 escenarios de cambio climático
  const scenarioChartData = [
    {
      id: "TEMP",
      title: "Olas de Calor (+2°C)",
      scenario: "+2°C Temp",
      streamflow: -25.93,
      soil_water: -7.93,
      et: 2.60,
      description: "El calor aumenta la evaporación de agua y hace caer el caudal del río en un 26%.",
    },
    {
      id: "PRECIP",
      title: "Sequía Severa (-15% Lluvia)",
      scenario: "-15% Lluvia",
      streamflow: -46.11,
      soil_water: -39.21,
      et: -7.82,
      description: "La falta de precipitación golpea drásticamente al río (-46%) y deja los suelos secos (-39%).",
    },
    {
      id: "NOTILL",
      title: "Siembra Directa (No-Till)",
      scenario: "Siembra Directa",
      streamflow: -0.01,
      soil_water: -0.02,
      et: -0.03,
      description: "Práctica de labranza cero para conservar la estructura del suelo y reducir la erosión.",
    },
    {
      id: "SORGHUM",
      title: "Cambio de Cultivo (Sorgo)",
      scenario: "Maíz → Sorgo",
      streamflow: 0.0,
      soil_water: 0.0,
      et: 0.0,
      description: "Sustitución de maíz por sorgo granífero, una especie más tolerante a estrés hídrico.",
    },
  ];

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto transition-colors duration-200 pb-16">
      {/* 1. Misión Central: ¿Qué es este gemelo digital? (En lenguaje claro) */}
      <div className="relative rounded-2xl bg-gradient-to-r from-emerald-100/90 via-white to-cyan-100/90 dark:from-emerald-950/80 dark:via-zinc-900 dark:to-cyan-950/80 border border-zinc-200 dark:border-zinc-800/80 p-6 md:p-8 overflow-hidden shadow-sm dark:shadow-xl">
        <div className="relative z-10 flex flex-col gap-5">
          {/* Etiquetas superiores */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 font-medium">
              <MapPin className="w-3.5 h-3.5" />
              Cuenca Piloto: South Fork Iowa River (USGS 05451210)
            </span>
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-800 dark:text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5 font-medium">
              <Sprout className="w-3.5 h-3.5" />
              Cultivo Objetivo: Maíz (Zea mays L.)
            </span>
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-zinc-200/80 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 border border-zinc-300 dark:border-zinc-700 flex items-center gap-1.5 font-medium">
              <Database className="w-3.5 h-3.5" />
              Servidor: {backendHealth}
            </span>
          </div>

          {/* Título y Explicación Intuitiva */}
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">
              De la Planta a la Cuenca Hidrográfica
            </h1>
            <p className="text-sm md:text-base text-zinc-700 dark:text-zinc-300 max-w-4xl mt-2 leading-relaxed">
              <b>¿Qué hace este sistema?</b> Es un <b>Gemelo Digital</b> (una réplica virtual interactiva) que conecta
              lo que le pasa a una <b>planta de maíz individual</b> con el agua de <b>todo un río de 580 km²</b> y las proyecciones
              de <b>cambio climático</b>. Nos permite simular cómo las decisiones de cultivo a nivel de planta afectan la
              disponibilidad de agua de toda una región agrícola.
            </p>
          </div>

          {/* Diagrama Visual de las 4 Escalas Conectadas */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-zinc-950/70 border border-zinc-200 dark:border-zinc-800/80 shadow-xs flex flex-col gap-1">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-700 dark:text-emerald-400">
                <Sprout className="w-4 h-4" />
                <span>1. Planta Individual</span>
              </div>
              <span className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
                Simula raíces, hojas, evapotranspiración y fotosíntesis en 3D.
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-zinc-950/70 border border-zinc-200 dark:border-zinc-800/80 shadow-xs flex flex-col gap-1">
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-700 dark:text-cyan-400">
                <Layers className="w-4 h-4" />
                <span>2. Campo Agrícola</span>
              </div>
              <span className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
                Suma 1,000 plantas con variabilidad natural de suelo y vigor.
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-zinc-950/70 border border-zinc-200 dark:border-zinc-800/80 shadow-xs flex flex-col gap-1">
              <div className="flex items-center gap-2 text-xs font-bold text-teal-700 dark:text-teal-400">
                <Mountain className="w-4 h-4" />
                <span>3. Cuenca del Río</span>
              </div>
              <span className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
                Modelo SWAT+ calculando escorrentía, humedad y caudal fluvial.
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-white/80 dark:bg-zinc-950/70 border border-zinc-200 dark:border-zinc-800/80 shadow-xs flex flex-col gap-1">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
                <SunMedium className="w-4 h-4" />
                <span>4. Clima y Futuro</span>
              </div>
              <span className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-snug">
                Proyecciones CMIP6 con olas de calor (+2°C) y sequías (-15%).
              </span>
            </div>
          </div>

          {/* Veredicto de la Hipótesis en Lenguaje Natural */}
          <div className="p-4 rounded-xl bg-white/90 dark:bg-zinc-950/90 border border-amber-300 dark:border-amber-800/80 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-zinc-900 dark:text-zinc-100 text-xs block">
                  ¿Qué descubrió la prueba científica del gemelo digital?
                </span>
                <p className="text-zinc-600 dark:text-zinc-400 text-[11px] mt-0.5 leading-relaxed">
                  Se evaluó la hipótesis <b>H1</b> (si acoplar 3 parámetros de la planta mejoraba la predicción del río en ≥15%).
                  El resultado arrojó que <b>parámetros estáticos no son suficientes</b> (mejora: 0.0%). Para transformar la
                  hidrología regional, el acoplamiento debe transferir la absorción de agua de forma dinámica día a día.
                </p>
              </div>
            </div>
            <div className="shrink-0 flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-500/30 font-mono text-xs font-bold">
                {currentResult?.hypothesis.conclusion ?? "EVALUADO V2"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Botón de Glosario para No Hidrólogos */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-800 dark:text-zinc-200 font-mono">
            Indicadores Clave de la Cuenca South Fork
          </h2>
        </div>
        <button
          onClick={() => setShowGlossary(!showGlossary)}
          className="flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-300 font-medium px-3 py-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 transition cursor-pointer"
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>{showGlossary ? "Ocultar guía de términos" : "¿Qué significan estos términos? (Glosario)"}</span>
        </button>
      </div>

      {/* Glosario Desplegable Didáctico */}
      {showGlossary && (
        <div className="p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-900/60 border border-emerald-300 dark:border-emerald-800/60 text-xs grid grid-cols-1 md:grid-cols-3 gap-4 animate-fadeIn">
          <div className="space-y-1">
            <span className="font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
              <Waves className="w-3.5 h-3.5" /> Caudal Fluvial (Q en m³/s)
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Es el volumen de agua que pasa por el río cada segundo. <b>1 m³/s equivale a 1,000 litros de agua por segundo</b> (unas 4 piscinas olímpicas por hora).
            </p>
          </div>
          <div className="space-y-1">
            <span className="font-bold text-cyan-800 dark:text-cyan-300 flex items-center gap-1.5">
              <Droplets className="w-3.5 h-3.5" /> Evapotranspiración (ET)
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              El agua total que vuelve a las nubes: una parte se evapora directamente del suelo húmedo y otra es "sudada" (transpirada) por las hojas del maíz.
            </p>
          </div>
          <div className="space-y-1">
            <span className="font-bold text-teal-800 dark:text-teal-300 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" /> HRU (Unidades de Respuesta)
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Zonas del mapa que comparten el mismo tipo de suelo, pendiente y cultivo. South Fork tiene 32 HRUs dedicadas a maíz.
            </p>
          </div>
          <div className="space-y-1">
            <span className="font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
              <Mountain className="w-3.5 h-3.5" /> Cuenca Hidrográfica
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Todo el territorio cuyas lluvias van a parar al mismo río principal. Si cae una gota dentro de los 580 km², terminará fluyendo hacia la estación de aforo.
            </p>
          </div>
          <div className="space-y-1">
            <span className="font-bold text-indigo-800 dark:text-indigo-300 flex items-center gap-1.5">
              <FlaskConical className="w-3.5 h-3.5" /> FSPM (Modelo 3D de Planta)
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              <b>Functional-Structural Plant Model</b>: Simula matemáticamente cómo crece la planta, cómo sus raíces buscan agua y cómo sus hojas interceptan el sol.
            </p>
          </div>
          <div className="space-y-1">
            <span className="font-bold text-rose-800 dark:text-rose-300 flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5" /> Calidad de Predicción (RMSE)
            </span>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Mide el error promedio entre lo que calculó la computadora y lo que midió el sensor del río. Cuanto más bajo sea el número, más exacto es el gemelo.
            </p>
          </div>
        </div>
      )}

      {/* 3. Rejilla de 6 KPIs con Explicación Intuitiva */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Ubicación Real</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">South Fork, Iowa</span>
          </div>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono mt-2">EE.UU. (Corn Belt)</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Tamaño Cuenca</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">580.16 km²</span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono mt-2">~81,000 estadios</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Uso Agrícola</span>
            <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400 mt-1 block">85% Cultivado</span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono mt-2">61% maíz / 24% soja</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Caudal Promedio</span>
            <span className="text-sm font-bold text-cyan-700 dark:text-cyan-400 mt-1 block">
              {totals?.streamflow_m3s_mean ? `${totals.streamflow_m3s_mean.toFixed(2)} m³/s` : "1.61 m³/s"}
            </span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono mt-2">1,610 litros/seg</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Días Evaluados</span>
            <span className="text-sm font-bold text-teal-700 dark:text-teal-400 mt-1 block">
              {currentResult?.validation?.daily?.matched_count ?? 1096} días
            </span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono mt-2">3 años continuos</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Evaporación Total</span>
            <span className="text-sm font-bold text-amber-700 dark:text-amber-400 mt-1 block">
              {totals?.et_mm ? `${totals.et_mm.toFixed(0)} mm` : "2,481 mm"}
            </span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono mt-2">Agua a la atmósfera</span>
        </div>
      </div>

      {/* 4. SECCIÓN VISUAL: Gráfico Interactivo de los 4 Escenarios de Cambio Climático */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <SunMedium className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                ¿Qué le pasaría a la cuenca si cambia el clima? (Simulación de Escenarios)
              </h3>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Compara el impacto porcentual (%) de olas de calor, sequías y prácticas de manejo sobre el agua regional.
            </p>
          </div>

          {/* Selector de variable para el gráfico */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-xs">
            <button
              onClick={() => setActiveMetric("streamflow")}
              className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                activeMetric === "streamflow"
                  ? "bg-white dark:bg-zinc-800 text-teal-700 dark:text-teal-300 shadow-xs font-bold"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              🌊 Caudal del Río
            </button>
            <button
              onClick={() => setActiveMetric("soil_water")}
              className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                activeMetric === "soil_water"
                  ? "bg-white dark:bg-zinc-800 text-cyan-700 dark:text-cyan-300 shadow-xs font-bold"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              💧 Humedad en Suelo
            </button>
            <button
              onClick={() => setActiveMetric("et")}
              className={`px-3 py-1.5 rounded-lg font-medium transition cursor-pointer ${
                activeMetric === "et"
                  ? "bg-white dark:bg-zinc-800 text-amber-700 dark:text-amber-300 shadow-xs font-bold"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              ☁️ Evaporación (ET)
            </button>
          </div>
        </div>

        {/* Gráfico de Barras Recharts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
          <div className="lg:col-span-2 h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scenarioChartData} margin={{ top: 20, right: 20, left: -10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#71717a" opacity={0.2} vertical={false} />
                <XAxis dataKey="scenario" stroke="#71717a" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#71717a"
                  fontSize={11}
                  tickLine={false}
                  unit="%"
                  domain={[-55, 10]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    borderRadius: "10px",
                    fontSize: "12px",
                    color: "#f4f4f5",
                  }}
                  formatter={(val: any) => [`${Number(val).toFixed(2)}%`, activeMetric === "streamflow" ? "Variación Caudal" : activeMetric === "soil_water" ? "Variación Agua Suelo" : "Variación Evaporación"]}
                />
                <ReferenceLine y={0} stroke="#71717a" strokeWidth={1.5} />
                <Bar dataKey={activeMetric} radius={[6, 6, 6, 6]}>
                  {scenarioChartData.map((entry, index) => {
                    const val = entry[activeMetric];
                    const color = val < -20 ? "#ef4444" : val < 0 ? "#f97316" : "#10b981";
                    return <Cell key={`cell-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Tarjeta explicativa del gráfico */}
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-3 text-xs">
            <div className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>Interpretación para toma de decisiones:</span>
            </div>
            <ul className="space-y-2 text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              <li className="flex items-start gap-1.5">
                <span className="text-rose-500 font-bold shrink-0">⚠️ Sequía (-15% lluvia):</span>
                <span>Es el impacto más destructivo. Provoca que el río pierda <b>casi la mitad de su agua (-46%)</b> y el suelo quede seco (-39%).</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-amber-500 font-bold shrink-0">☀️ Calor (+2°C):</span>
                <span>Al hacer más calor, las plantas y el suelo evaporan más agua (+2.6%), lo que reduce el caudal del río en un <b>-26%</b>.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="text-emerald-500 font-bold shrink-0">🌱 Siembra Directa y Sorgo:</span>
                <span>Alternativas de adaptación agrícola para retener humedad en el perfil y mitigar el estrés térmico.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 5. Los 5 Módulos Científicos Explicados Paso a Paso */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-800 dark:text-zinc-200 font-mono flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Metodología Científica: Los 5 Módulos de la Investigación
          </h2>
          <span className="text-xs text-zinc-500 font-mono">Paso a Paso</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {/* Módulo 1 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-xs hover:border-emerald-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-emerald-700 dark:text-emerald-400">MÓDULO 1</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Datos y Forzamientos</h3>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                ¿Qué datos alimentan el gemelo? Sensores diarios del río (USGS), mapas de satélite de cultivo de maíz y clima meteorológico.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Datos oficiales limpios
            </div>
          </div>

          {/* Módulo 2 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-xs hover:border-cyan-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-cyan-700 dark:text-cyan-400">MÓDULO 2</span>
                <span className="w-2 h-2 rounded-full bg-cyan-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Acoplamiento Multiescala</h3>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                ¿Cómo viaja la información? De una planta de maíz individual $\rightarrow$ a un campo de 1,000 plantas $\rightarrow$ a toda la cuenca del río con SWAT+.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Conexión 3D funcional
            </div>
          </div>

          {/* Módulo 3 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-xs hover:border-teal-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-teal-700 dark:text-teal-400">MÓDULO 3</span>
                <span className="w-2 h-2 rounded-full bg-teal-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Validación con Sensores</h3>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                ¿Qué tan exacto es? Se comparan día a día los cálculos de la computadora contra las mediciones de caudal reales del río tomadas en campo.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> 1,096 días contrastados
            </div>
          </div>

          {/* Módulo 4 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-xs hover:border-amber-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-amber-700 dark:text-amber-400">MÓDULO 4</span>
                <span className="w-2 h-2 rounded-full bg-amber-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Escenarios de Adaptación</h3>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                ¿Qué pasará si el clima empeora? Simulación de +2°C de calor, sequía severa del 15% y cambio de maíz a sorgo.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> 4 escenarios evaluados
            </div>
          </div>

          {/* Módulo 5 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-xs hover:border-indigo-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-indigo-700 dark:text-indigo-400">MÓDULO 5</span>
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Impacto y Estadística</h3>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                Pruebas matemáticas rigurosas (KS, Wilcoxon, sensibilidad de Sobol) que garantizan que los resultados no son producto del azar.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Batería estadística v2
            </div>
          </div>
        </div>
      </div>

      {/* 6. Tarjetas de Acceso a las Secciones Interactivas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/simulations"
          className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-emerald-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
        >
          <div>
            <div className="w-11 h-11 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-4 group-hover:scale-110 transition">
              <FlaskConical className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition">
              1. Simulador y Experimentos SWAT+
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Crea nuevas simulaciones, pon a prueba distintos escenarios climáticos y revisa gráficos detallados de caudal y transpiración vegetal.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <span>Abrir Simulador</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/twin-3d"
          className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-cyan-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
        >
          <div>
            <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-4 group-hover:scale-110 transition">
              <Box className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition">
              2. Gemelo Digital 3D Interactivo
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Explora visualmente el gemelo en 3 dimensiones. Haz zoom a la planta individual para ver su savia y raíces, o aléjate para ver todo el valle y el río.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-cyan-600 dark:text-cyan-400">
            <span>Ver Gemelo 3D</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/reports"
          className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-indigo-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
        >
          <div>
            <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-4 group-hover:scale-110 transition">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition">
              3. Centro de Reportes Formales
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Exporta los resultados y balances de agua en documentos formales: <b>PDF</b> para presentaciones ejecutivas, <b>Word (.docx)</b> y <b>Excel (.xlsx)</b>.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-indigo-600 dark:text-indigo-400">
            <span>Descargar Reportes</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>
      </div>

      {/* 7. Pie de Trazabilidad y Stack Técnico */}
      <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm text-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-zinc-900 dark:text-zinc-100 block">Trazabilidad y Calidad de Software</span>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Datos verificados contra observaciones del USGS con control de calidad SHA-256 y arquitectura reproducible.
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
          <span className="px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
            SWAT+ 61.0.2.61
          </span>
          <span className="px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
            FSPM 1,000 Plantas
          </span>
          <span className="px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
            USGS 05451210
          </span>
          <span className="px-2.5 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
            FastAPI + Next.js
          </span>
        </div>
      </div>
    </div>
  );
}

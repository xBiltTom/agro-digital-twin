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
  Thermometer,
  CloudRain,
  BookOpen,
  Sparkles,
  Waves,
  AlertTriangle,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
} from "recharts";

export default function DashboardPage() {
  const { user } = useAuth();
  const [backendHealth, setBackendHealth] = useState<string>("Verificando...");
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [showGlossary, setShowGlossary] = useState(false);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("TEMP");
  const [chartMode, setChartMode] = useState<"compare" | "all">("compare");

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
  const totals = currentResult?.runs?.baseline?.totals;

  // Datos intuitivos de los escenarios con simulación SWAT+ real (2018-2020)
  const waterLitersData = [
    {
      id: "NORMAL",
      name: "Situación Normal",
      shortName: "Normal",
      liters: 100,
      soilPct: 100,
      etPct: 100,
      runoffPct: 100,
      status: "Base Histórica",
      color: "#10b981", // Verde esmeralda
      tag: "100 L habituales",
      deltaText: "Línea Base (100%)",
      summary: "Condiciones de lluvia y temperatura normales medidas en Iowa.",
      why: "Punto de referencia contra el que se evalúan todas las crisis.",
      rawMetrics: {
        streamflow: "1.61 m³/s",
        soilWater: "302 mm",
        et: "2,481 mm",
        runoff: "300 mm",
      },
    },
    {
      id: "TEMP",
      name: "Calor (+2°C)",
      shortName: "+2°C Calor",
      liters: 74,
      soilPct: 92,
      etPct: 103,
      runoffPct: 84,
      status: "Pérdida moderada",
      color: "#f59e0b", // Ámbar
      tag: "Quedan 74 L (-26%)",
      deltaText: "El río pierde 26 de cada 100 L",
      summary: "Una ola de calor calienta el suelo y hace que el agua se evapore más rápido hacia la atmósfera.",
      why: "El sol calienta las hojas del maíz y la tierra. La evaporación aumenta (+2.6%) y queda menos agua para que escurra hacia el río.",
      rawMetrics: {
        streamflow: "1.19 m³/s (-26%)",
        soilWater: "278 mm (-8%)",
        et: "2,546 mm (+3%)",
        runoff: "251 mm (-16%)",
      },
    },
    {
      id: "PRECIP",
      name: "Sequía (-15% Lluvia)",
      shortName: "-15% Sequía",
      liters: 54,
      soilPct: 61,
      etPct: 92,
      runoffPct: 73,
      status: "Impacto Severo",
      color: "#ef4444", // Rojo alerta
      tag: "Quedan 54 L (-46%)",
      deltaText: "El río pierde casi la mitad (-46%)",
      summary: "Una pequeña caída del 15% en lluvia provoca un colapso dramático en el caudal del río.",
      why: "El suelo seco funciona como una esponja sedienta: absorbe toda la lluvia que cae y casi nada llega a los arroyos.",
      rawMetrics: {
        streamflow: "0.87 m³/s (-46%)",
        soilWater: "184 mm (-39%)",
        et: "2,287 mm (-8%)",
        runoff: "218 mm (-27%)",
      },
    },
    {
      id: "NOTILL",
      name: "Siembra Directa",
      shortName: "Siembra Directa",
      liters: 100,
      soilPct: 100,
      etPct: 100,
      runoffPct: 100,
      status: "Caudal Estable",
      color: "#06b6d4", // Cyan
      tag: "Quedan 100 L (Estable)",
      deltaText: "Caudal idéntico (100%)",
      summary: "Los agricultores siembran sin meter tractores a arar la tierra, dejando rastrojos protectores.",
      why: "¿Por qué no cambia el río? Porque esta práctica no altera el clima ni la lluvia; su objetivo es proteger el suelo para que no se erosione.",
      rawMetrics: {
        streamflow: "1.61 m³/s (0%)",
        soilWater: "302 mm (0%)",
        et: "2,481 mm (0%)",
        runoff: "300 mm (0%)",
      },
    },
    {
      id: "SORGHUM",
      name: "Maíz → Sorgo",
      shortName: "Sorgo",
      liters: 100,
      soilPct: 100,
      etPct: 100,
      runoffPct: 100,
      status: "Caudal Estable",
      color: "#8b5cf6", // Púrpura
      tag: "Quedan 100 L (Estable)",
      deltaText: "Caudal idéntico (100%)",
      summary: "Cambiar maíz por sorgo granífero, una planta prima mucho más resistente a la escasez de agua.",
      why: "¿Por qué no cambia el río? Porque el sorgo gasta el agua de forma más eficiente para sobrevivir en sequías, manteniendo la cosecha.",
      rawMetrics: {
        streamflow: "1.61 m³/s (0%)",
        soilWater: "302 mm (0%)",
        et: "2,481 mm (0%)",
        runoff: "300 mm (0%)",
      },
    },
  ];

  const activeScenario = waterLitersData.find((s) => s.id === selectedScenarioId) || waterLitersData[1];

  // Datos comparativos interactivos Cara a Cara (Normal vs Seleccionado)
  const comparisonData = [
    {
      metric: "Caudal Río",
      normal: 100,
      scenario: activeScenario.liters,
      unit: "L",
      normalRaw: "1.61 m³/s",
      scenarioRaw: activeScenario.rawMetrics.streamflow,
      desc: "Agua que llega al cauce del río",
    },
    {
      metric: "Humedad Suelo",
      normal: 100,
      scenario: activeScenario.soilPct,
      unit: "%",
      normalRaw: "302 mm",
      scenarioRaw: activeScenario.rawMetrics.soilWater,
      desc: "Agua almacenada en la tierra",
    },
    {
      metric: "Evaporación (ET)",
      normal: 100,
      scenario: activeScenario.etPct,
      unit: "%",
      normalRaw: "2,481 mm",
      scenarioRaw: activeScenario.rawMetrics.et,
      desc: "Agua que sube a la atmósfera",
    },
    {
      metric: "Escorrentía",
      normal: 100,
      scenario: activeScenario.runoffPct,
      unit: "%",
      normalRaw: "300 mm",
      scenarioRaw: activeScenario.rawMetrics.runoff,
      desc: "Agua que corre sobre el suelo",
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

      {/* 2. Glosario Didáctico para No Hidrólogos */}
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
              El agua total que vuelve a las nubes: una parte se evapora directamente del suelo húmedo y otra es transpirada por las hojas del maíz.
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
        </div>
      )}

      {/* 3. Rejilla de 6 KPIs con Metáforas Claras */}
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

      {/* ========================================================================= */}
      {/* PENDIENTE DE REVISIÓN: Simulación de Escenarios en Dashboard Principal   */}
      {/* Deshabilitado temporalmente para destriparlo y simplificarlo a futuro.     */}
      {/* ========================================================================= */}
      {false && (
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-6">
        {/* Cabecera y controles superiores */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Waves className="w-5 h-5 text-teal-600 dark:text-teal-400" />
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                ¿Cuánta agua queda en el río si cambia el clima? (Simulador Interactivo)
              </h3>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Haz clic en cualquier escenario para ver cómo <b>cambia y se transforma el gráfico</b> en tiempo real comparado con las condiciones normales.
            </p>
          </div>

          {/* Selector de Modo: Cara a Cara vs Panorama Completo */}
          <div className="flex items-center gap-1 p-1 bg-zinc-100 dark:bg-zinc-800/80 rounded-xl border border-zinc-200 dark:border-zinc-700/60 shrink-0 self-start md:self-auto">
            <button
              onClick={() => setChartMode("compare")}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                chartMode === "compare"
                  ? "bg-white dark:bg-zinc-900 text-teal-700 dark:text-teal-300 shadow-xs"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Cara a Cara (Normal vs {activeScenario.shortName})
            </button>
            <button
              onClick={() => setChartMode("all")}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                chartMode === "all"
                  ? "bg-white dark:bg-zinc-900 text-teal-700 dark:text-teal-300 shadow-xs"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white"
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Panorama (Los 5 Juntos)
            </button>
          </div>
        </div>

        {/* Píldoras interactivas de selección rápida de escenarios */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-zinc-100 dark:border-zinc-800/60">
          <span className="text-[11px] font-mono uppercase text-zinc-400 font-semibold mr-1">
            Seleccionar Escenario:
          </span>
          {waterLitersData.map((s) => {
            const isSelected = selectedScenarioId === s.id;
            return (
              <button
                key={s.id}
                onClick={() => {
                  setSelectedScenarioId(s.id);
                  setChartMode("compare"); // Cambia de inmediato el gráfico
                }}
                className={`text-xs font-medium px-3 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-2 border ${
                  isSelected
                    ? "border-teal-500 bg-teal-50 dark:bg-teal-950/40 text-teal-800 dark:text-teal-200 font-bold shadow-xs scale-102"
                    : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
                }`}
              >
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
                <span>{s.name}</span>
                {isSelected && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-teal-500 text-white font-mono">
                    Activo
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Gráfico y Ficha Explicativa */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Contenedor del Gráfico Dinámico */}
          <div className="lg:col-span-7 h-80 w-full bg-zinc-50/50 dark:bg-zinc-950/40 rounded-2xl p-4 border border-zinc-100 dark:border-zinc-800/60">
            {chartMode === "compare" ? (
              // Vista Cara a Cara: Normal vs Escenario Seleccionado
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-between text-xs px-2 mb-1">
                  <span className="font-bold text-zinc-700 dark:text-zinc-300">
                    Comparativa Directa: Situación Normal vs. {activeScenario.name}
                  </span>
                  <span className="text-[11px] text-zinc-500 font-mono">Valores relativos (Base = 100%)</span>
                </div>
                <div className="h-68 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={comparisonData}
                      margin={{ top: 20, right: 10, left: -20, bottom: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#71717a" opacity={0.2} vertical={false} />
                      <XAxis
                        dataKey="metric"
                        stroke="#71717a"
                        fontSize={11}
                        tickLine={false}
                      />
                      <YAxis
                        stroke="#71717a"
                        fontSize={11}
                        tickLine={false}
                        domain={[0, 115]}
                        unit="%"
                      />
                      <Tooltip
                        cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const item = payload[0].payload;
                            const diff = item.scenario - item.normal;
                            return (
                              <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white shadow-xl space-y-2">
                                <div className="font-bold border-b border-zinc-800 pb-1 flex items-center justify-between gap-4">
                                  <span>{item.metric}</span>
                                  <span className="text-[10px] text-zinc-400 font-normal">{item.desc}</span>
                                </div>
                                <div className="grid grid-cols-2 gap-3 text-[11px]">
                                  <div>
                                    <span className="text-zinc-400 block text-[10px]">Situación Normal</span>
                                    <span className="font-bold text-emerald-400">{item.normal}%</span>
                                    <span className="text-[10px] text-zinc-500 block font-mono">({item.normalRaw})</span>
                                  </div>
                                  <div>
                                    <span className="text-zinc-400 block text-[10px]">{activeScenario.shortName}</span>
                                    <span className="font-bold" style={{ color: activeScenario.color }}>
                                      {item.scenario}%
                                    </span>
                                    <span className="text-[10px] text-zinc-500 block font-mono">({item.scenarioRaw})</span>
                                  </div>
                                </div>
                                <div className="text-[10px] font-bold pt-1 border-t border-zinc-800 flex items-center gap-1">
                                  {diff < 0 && (
                                    <span className="text-rose-400 flex items-center gap-1">
                                      <TrendingDown className="w-3 h-3" /> Caída de {Math.abs(diff)}%
                                    </span>
                                  )}
                                  {diff > 0 && (
                                    <span className="text-amber-400 flex items-center gap-1">
                                      <TrendingUp className="w-3 h-3" /> Aumento de +{diff}%
                                    </span>
                                  )}
                                  {diff === 0 && (
                                    <span className="text-cyan-400">
                                      = 100% Idéntico (Sin impacto macro en caudal)
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align="right"
                        iconType="circle"
                        wrapperStyle={{ paddingBottom: 6, fontSize: 11 }}
                      />
                      <Bar
                        dataKey="normal"
                        name="Situación Normal (100%)"
                        fill="#10b981"
                        radius={[6, 6, 0, 0]}
                        animationDuration={500}
                      >
                        <LabelList
                          dataKey="normal"
                          position="top"
                          formatter={(v: any) => `${v}%`}
                          fill="#10b981"
                          fontSize={10}
                          fontWeight="bold"
                        />
                      </Bar>
                      <Bar
                        dataKey="scenario"
                        name={activeScenario.name}
                        fill={activeScenario.color}
                        radius={[6, 6, 0, 0]}
                        animationDuration={500}
                      >
                        <LabelList
                          dataKey="scenario"
                          position="top"
                          formatter={(v: any) => `${v}%`}
                          fill={activeScenario.color}
                          fontSize={10}
                          fontWeight="bold"
                        />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              // Vista Panorama: Los 5 escenarios de río juntos
              <div className="h-full flex flex-col justify-between">
                <div className="flex items-center justify-between text-xs px-2 mb-1">
                  <span className="font-bold text-zinc-700 dark:text-zinc-300">
                    Panorama General: ¿Cuántos Litros de Río Quedan en Cada Crisis?
                  </span>
                  <span className="text-[11px] text-zinc-500 font-mono">Normal = 100 Litros</span>
                </div>
                <div className="h-68 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={waterLitersData}
                      margin={{ top: 20, right: 10, left: -20, bottom: 20 }}
                      onClick={(data: any) => {
                        if (data && data.activePayload && data.activePayload.length > 0) {
                          setSelectedScenarioId(data.activePayload[0].payload.id);
                          setChartMode("compare");
                        }
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#71717a" opacity={0.2} vertical={false} />
                      <XAxis
                        dataKey="name"
                        stroke="#71717a"
                        fontSize={11}
                        tickLine={false}
                        interval={0}
                        angle={-12}
                        textAnchor="end"
                      />
                      <YAxis
                        stroke="#71717a"
                        fontSize={11}
                        tickLine={false}
                        domain={[0, 110]}
                        unit=" L"
                      />
                      <Tooltip
                        cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const item = payload[0].payload;
                            return (
                              <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-white shadow-xl space-y-1">
                                <div className="font-bold flex items-center justify-between gap-3">
                                  <span>{item.name}</span>
                                  <span className="font-mono text-emerald-400">{item.liters} L</span>
                                </div>
                                <div className="text-[11px] text-zinc-400">{item.deltaText}</div>
                                <div className="text-[10px] text-teal-400 pt-1 border-t border-zinc-800 font-semibold">
                                  Haz clic para ver comparativa Cara a Cara
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar
                        dataKey="liters"
                        radius={[8, 8, 0, 0]}
                        className="cursor-pointer transition hover:opacity-80"
                      >
                        <LabelList
                          dataKey="liters"
                          position="top"
                          formatter={(val: any) => `${val} L`}
                          fill="#a1a1aa"
                          fontSize={11}
                          fontWeight="bold"
                        />
                        {waterLitersData.map((entry) => (
                          <Cell
                            key={entry.id}
                            fill={entry.color}
                            stroke={selectedScenarioId === entry.id ? "#ffffff" : "transparent"}
                            strokeWidth={2}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {/* Tarjeta Explicativa Dinámica del Escenario Seleccionado */}
          <div className="lg:col-span-5 p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between gap-4">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                  {activeScenario.status}
                </span>
                <span className="text-base font-bold font-mono text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: activeScenario.color }} />
                  {activeScenario.liters} de 100 Litros
                </span>
              </div>

              <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-2">
                {activeScenario.name}: {activeScenario.tag}
              </h4>
              <p className="text-xs text-zinc-600 dark:text-zinc-300 mt-1.5 leading-relaxed">
                {activeScenario.summary}
              </p>

              {/* Indicadores numéricos reales medidos por SWAT+ */}
              <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 text-xs">
                <div className="p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                  <span className="text-[10px] text-zinc-400 block">Caudal del Río</span>
                  <span className="font-bold font-mono text-zinc-800 dark:text-zinc-200">
                    {activeScenario.rawMetrics.streamflow}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                  <span className="text-[10px] text-zinc-400 block">Humedad en Suelo</span>
                  <span className="font-bold font-mono text-zinc-800 dark:text-zinc-200">
                    {activeScenario.rawMetrics.soilWater}
                  </span>
                </div>
              </div>

              {/* Explicación física */}
              <div className="mt-3 p-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs">
                <span className="font-bold text-zinc-800 dark:text-zinc-200 block text-[11px]">
                  💡 ¿Por qué ocurre esto físicamente?
                </span>
                <p className="text-zinc-500 dark:text-zinc-400 text-[11px] mt-1 leading-relaxed">
                  {activeScenario.why}
                </p>
              </div>
            </div>

            {/* Mensaje al pie */}
            <div className="text-[11px] text-zinc-500 dark:text-zinc-400 pt-2 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <span>{activeScenario.deltaText}</span>
              <button
                onClick={() => setChartMode(chartMode === "compare" ? "all" : "compare")}
                className="text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
              >
                {chartMode === "compare" ? "Ver panorama general →" : "Ver cara a cara →"}
              </button>
            </div>
          </div>
        </div>

        {/* Explicación destacada: ¿Por qué Siembra Directa y Sorgo están en 100 L? */}
        <div className="p-4 rounded-xl bg-cyan-50/60 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-800/60 text-xs flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-cyan-950 dark:text-cyan-200">
              ¿Por qué solo hay caídas en Calor y Lluvia, mientras que Siembra Directa y Sorgo están en 100 L?
            </span>
            <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
              Porque el <b>calor y las sequías</b> son perturbaciones del clima que alteran toda la lluvia y la evaporación de la atmósfera.
              En cambio, la <b>Siembra Directa</b> y el <b>Sorgo</b> son prácticas de los agricultores: su función en este modelo no es "crear más agua" en el río,
              sino <b>proteger la tierra fértil</b> y asegurar que la planta sobreviva con menos agua para no perder la cosecha.
            </p>
          </div>
        </div>
      </div>
      )}

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

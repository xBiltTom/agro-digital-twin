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
  Users,
  Layers,
  FlaskConical,
  Activity,
  MapPin,
  TrendingDown,
  TrendingUp,
  BarChart3,
  FileCheck2,
  ExternalLink,
} from "lucide-react";

export default function DashboardPage() {
  const { user, hasAnyRole } = useAuth();
  const [backendHealth, setBackendHealth] = useState<string>("Verificando...");
  const [finalReport, setFinalReport] = useState<CurrentFinalScientificReportResponse | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, { status: string; evidence_type?: string }>>({});

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setBackendHealth(data.status === "healthy" ? "Operativo (FastAPI)" : "Inestable"))
      .catch(() => setBackendHealth("Desconectado"));

    api.getFinalScientificReport()
      .then((data) => setFinalReport(data))
      .catch((err) => console.warn("Reporte científico no cargado:", err));

    api.getCapabilities()
      .then((data) => setCapabilities(data))
      .catch((err) => console.warn("Capabilities no cargadas:", err));
  }, []);

  const primaryRole = user?.roles?.[0]?.name || "INVESTIGADOR";
  const currentResult = finalReport?.current_result;
  const currentStatus = finalReport?.current_contract?.current_execution_status;

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto transition-colors duration-200 pb-12">
      {/* 1. Scientific Mission Banner */}
      <div className="relative rounded-2xl bg-gradient-to-r from-emerald-100/80 via-white to-cyan-100/80 dark:from-emerald-950/70 dark:via-zinc-900 dark:to-cyan-950/70 border border-zinc-200 dark:border-zinc-800/80 p-6 md:p-8 overflow-hidden shadow-sm dark:shadow-xl">
        <div className="absolute right-0 top-0 w-96 h-full bg-radial from-emerald-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5 font-medium">
                <MapPin className="w-3.5 h-3.5" />
                Cuenca Piloto: South Fork Iowa River (USGS 05451210)
              </span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-500/20 flex items-center gap-1.5 font-medium">
                <FlaskConical className="w-3.5 h-3.5" />
                SWAT+ 61.0.2 & FSPM Acoplados
              </span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-zinc-200/70 dark:bg-zinc-800/70 text-zinc-700 dark:text-zinc-300 border border-zinc-300 dark:border-zinc-700 flex items-center gap-1.5 font-medium">
                <Database className="w-3.5 h-3.5" />
                Backend: {backendHealth}
              </span>
            </div>

            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">
                From Plant to Watershed: Gemelo Digital Multiescala
              </h1>
              <p className="text-xs md:text-sm text-zinc-600 dark:text-zinc-400 max-w-3xl mt-1.5 leading-relaxed">
                Framework ecohidrológico que conecta el modelo funcional-estructural de maíz individual (FSPM) con la
                hidrología de cuenca SWAT+ y proyecciones de cambio climático. Permite simular el efecto de prácticas de manejo
                a nivel de cultivo sobre el balance hídrico regional.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
              <span className="text-zinc-500 dark:text-zinc-400 font-mono">Hipótesis evaluada:</span>
              <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-800 dark:text-amber-300 border border-amber-500/30 font-mono text-[11px] font-semibold">
                {currentStatus === "NOT_EXECUTED" ? "SOUTH_FORK_V2: NOT_EXECUTED" : currentResult?.hypothesis.conclusion ?? "REPORTE_V2_NO_DISPONIBLE"}
              </span>
              <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                {currentStatus === "NOT_EXECUTED" ? "Las métricas v1 son históricas; el contrato v2 aún no tiene resultados." : <>Mejora RMSE mensual: <b>{currentResult?.validation?.monthly_primary?.improvement_percent ?? "N/D"}%</b></>}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            <div className="p-3.5 rounded-xl bg-white/90 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-xs shadow-sm">
              <div className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400 mb-1">
                Investigador Activo
              </div>
              <div className="flex items-center gap-2 font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                <Shield className="w-4 h-4" />
                <span>{primaryRole}</span>
              </div>
              <div className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 mt-1">
                {user?.full_name}
              </div>
              <div className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate max-w-[210px]">
                {user?.profile?.institution || user?.email}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Watershed & Pilot Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Cuenca Piloto</span>
          <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">South Fork, IA</span>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">HUC8 07080207</span>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Área Drenaje</span>
          <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">580.16 km²</span>
          <span className="text-[10px] text-zinc-500 font-mono">224 mi² oficiales</span>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Uso Agrícola</span>
          <span className="text-sm font-bold text-emerald-700 dark:text-emerald-400 mt-1 block">84.9% Cultivo</span>
          <span className="text-[10px] text-zinc-500 font-mono">61% maíz / 23% soja</span>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">HRUs Mapeadas</span>
          <span className="text-sm font-bold text-cyan-700 dark:text-cyan-400 mt-1 block">32 HRUs Maíz</span>
          <span className="text-[10px] text-zinc-500 font-mono">USDA CDL 2019</span>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">Pares v2 evaluados</span>
          <span className="text-sm font-bold text-teal-700 dark:text-teal-400 mt-1 block">{currentResult?.validation?.daily?.matched_count ?? "N/D"}</span>
          <span className="text-[10px] text-zinc-500 font-mono">{currentStatus === "NOT_EXECUTED" ? "Contrato v2 pendiente" : "USGS real"}</span>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 shadow-sm">
          <span className="text-[10px] font-mono uppercase text-zinc-500 dark:text-zinc-400 block">RMSE Mensual</span>
          <span className="text-sm font-bold text-amber-700 dark:text-amber-400 mt-1 block">
            {currentResult?.validation?.monthly_primary?.baseline?.rmse?.toFixed(3) ?? "N/D"}{currentResult ? " m³/s" : ""}
          </span>
          <span className="text-[10px] text-zinc-500 font-mono">NSE: {currentResult?.validation?.monthly_primary?.baseline?.nse?.toFixed(3) ?? "N/D"}</span>
        </div>
      </div>

      {/* 3. The 5 Scientific Modules Status */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-800 dark:text-zinc-200 font-mono flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Metodología Científica: Estado de los 5 Módulos
          </h2>
          <span className="text-xs text-zinc-500 font-mono">Pipeline de Investigación</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {/* Módulo 1 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-sm hover:border-emerald-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-emerald-700 dark:text-emerald-400">MÓDULO 1</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Datos & Forzamientos</h3>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                USGS 05451210 diario verificado, CDL 2019, SoilGrids 2.0 y GridMET. Preparado para NEX-GDDP-CMIP6.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
              ✓ SHA-256 & QC Activos
            </div>
          </div>

          {/* Módulo 2 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-sm hover:border-cyan-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-cyan-700 dark:text-cyan-400">MÓDULO 2</span>
                <span className="w-2 h-2 rounded-full bg-cyan-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Arquitectura Multiescala</h3>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                N1 Planta (FSPM GDD) → N2 Campo (1000 plantas BARC) → N3 Cuenca (SWAT+ 61.0.2) → N4 Clima.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-cyan-600 dark:text-cyan-400">
              ✓ Acoplamiento plants.plt
            </div>
          </div>

          {/* Módulo 3 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-sm hover:border-teal-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-teal-700 dark:text-teal-400">MÓDULO 3</span>
                <span className="w-2 h-2 rounded-full bg-teal-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Validación Hidrológica</h3>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                {currentStatus === "NOT_EXECUTED" ? "El contrato South Fork v2 aún no tiene evaluación hidrológica." : <>Evaluación pareada contra USGS. RMSE: {currentResult?.validation?.monthly_primary?.baseline?.rmse?.toFixed(3) ?? "N/D"} m³/s; NSE: {currentResult?.validation?.monthly_primary?.baseline?.nse?.toFixed(3) ?? "N/D"}.</>}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-amber-600 dark:text-amber-400">
              {currentStatus === "NOT_EXECUTED" ? "NOT_EXECUTED" : currentResult?.hypothesis.conclusion ?? "REPORTE_V2_NO_DISPONIBLE"}
            </div>
          </div>

          {/* Módulo 4 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-sm hover:border-amber-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-amber-700 dark:text-amber-400">MÓDULO 4</span>
                <span className="w-2 h-2 rounded-full bg-amber-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Escenarios Climáticos</h3>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                4 corridas ejecutadas: +2°C (-25.9% Q), -15% P (-46.1% Q), siembra directa y cambio a sorgo.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-amber-600 dark:text-amber-400">
              ✓ 4 Escenarios Listos
            </div>
          </div>

          {/* Módulo 5 */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col justify-between shadow-sm hover:border-indigo-500/40 transition">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-indigo-700 dark:text-indigo-400">MÓDULO 5</span>
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
              </div>
              <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 mt-1">Impacto & Estadística</h3>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                KS-test (D=0.547, p=4.4e-143), Wilcoxon signed-rank, análisis Sobol y Bootstrap 95%.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-indigo-600 dark:text-indigo-400">
              ✓ Batería KS / Wilcoxon
            </div>
          </div>
        </div>
      </div>

      {/* 4. Action Cards for Direct Navigation */}
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
              Simulación y Acoplamiento FSPM → SWAT+
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Ejecuta corridas pareadas (control vs acoplado), inspecciona el mapeo de parámetros fisiológicos
              (<code className="font-mono text-emerald-600 dark:text-emerald-400">corn.lai_pot</code>, <code className="font-mono text-emerald-600 dark:text-emerald-400">can_ht_max</code>)
              y revisa los balances diarios de masa.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <span>Abrir Simulador y Acoplamiento</span>
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
              Gemelo Digital 3D Multiescala
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Explorador espacial tridimensional con tres niveles de detalle: arquitectura de planta individual (FSPM),
              parcela de 1,000 plantas con variabilidad BARC y relieve topográfico con la red hidrográfica de South Fork.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-cyan-600 dark:text-cyan-400">
            <span>Iniciar Visor 3D</span>
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
              Centro de Reportes y Evidencia Científica
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 leading-relaxed">
              Descarga informes ejecutivos en <b>PDF</b>, memorias técnicas en <b>Word (.docx)</b> y matrices de datos
              en <b>Excel (.xlsx)</b>. Consulta la evidencia congelada del reporte final y los 4 escenarios ejecutados.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-indigo-600 dark:text-indigo-400">
            <span>Ver Reportes y Evidencia</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>
      </div>

      {/* 5. System Technical Stack & Provenance */}
      <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm text-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-zinc-900 dark:text-zinc-100 block">Trazabilidad y Reproducibilidad Experimental</span>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
              Ejecuciones inmutables con semillas registradas, hashes SHA-256 de binarios SWAT+ y manifiestos de corrida.
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

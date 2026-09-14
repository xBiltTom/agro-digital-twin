"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
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
  Users
} from "lucide-react";

export default function DashboardPage() {
  const { user, hasAnyRole } = useAuth();
  const [backendHealth, setBackendHealth] = useState<string>("Verificando...");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setBackendHealth(data.status === "healthy" ? "Operativo (FastAPI)" : "Inestable"))
      .catch(() => setBackendHealth("Desconectado"));
  }, []);

  const primaryRole = user?.roles?.[0]?.name || "USUARIO";

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto transition-colors duration-200">
      {/* Welcome Banner */}
      <div className="relative rounded-2xl bg-gradient-to-r from-emerald-100/70 via-white to-cyan-100/70 dark:from-emerald-950/70 dark:via-zinc-900 dark:to-cyan-950/70 border border-zinc-200 dark:border-zinc-800/80 p-6 md:p-8 overflow-hidden shadow-sm dark:shadow-xl">
        <div className="absolute right-0 top-0 w-96 h-full bg-radial from-emerald-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Módulo 1: RBAC & Core Activo
              </span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-500/20 flex items-center gap-1.5 font-medium">
                <Database className="w-3.5 h-3.5" />
                Backend: {backendHealth}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">
              Bienvenido, {user?.full_name}
            </h1>
            <p className="text-xs md:text-sm text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              El piloto científico congelado es South Fork Iowa River (USGS 05451210, HUC8 07080207):
              baseline/coupled real, USGS y cuatro escenarios están registrados en el reporte final. Este visor conserva
              resultados persistidos y geometrías ilustrativas, que no sustituyen ese artefacto científico.
            </p>
          </div>

          <div className="flex flex-col gap-2 shrink-0">
            <div className="p-3 rounded-xl bg-white/90 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 text-xs shadow-sm">
              <div className="text-[10px] uppercase font-mono text-zinc-500 dark:text-zinc-400 mb-1">
                Rol Activo en Sistema
              </div>
              <div className="flex items-center gap-2 font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                <Shield className="w-4 h-4" />
                <span>{primaryRole}</span>
              </div>
              <div className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 truncate max-w-[200px]">
                {user?.profile?.institution || "Centro de Investigación"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Multiscale Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Micro: Planta */}
        <div className="rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between hover:border-emerald-500/40 transition group shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400">Escala Micro</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <Sprout className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">FSPM de maíz determinista</div>
            <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100 mt-0.5">ACTIVO</div>
            <div className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1 font-mono font-medium">
              <span>GDD, fenología, LAI, raíces, ET y estrés</span>
            </div>
          </div>
        </div>

        {/* Meso: Parcela */}
        <div className="rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between hover:border-cyan-500/40 transition group shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400">Escala Meso</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
              <Droplets className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">Población y Campo → HRU</div>
            <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100 mt-0.5">ACTIVO</div>
            <div className="text-[11px] text-cyan-600 dark:text-cyan-400 mt-1 flex items-center gap-1 font-mono font-medium">
              <span>PlantPopulation → FieldAggregate → HRU</span>
            </div>
          </div>
        </div>

        {/* Macro: motor hidrológico declarado por corrida */}
        <div className="rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between hover:border-teal-500/40 transition group shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400">Escala Macro</span>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-600 dark:text-teal-400">
              <Mountain className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">Motor hidrológico por corrida</div>
            <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100 mt-0.5">SWAT+ / PROXY</div>
            <div className="text-[11px] text-teal-600 dark:text-teal-400 mt-1 flex items-center gap-1 font-mono font-medium">
              <span>La evidencia y provenance se ven en cada ejecución</span>
            </div>
          </div>
        </div>

        {/* Forzamiento */}
        <div className="rounded-xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 p-5 flex flex-col justify-between hover:border-amber-500/40 transition group shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono uppercase text-zinc-500 dark:text-zinc-400">Forzamiento declarado</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <SunMedium className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">La fuente queda registrada por corrida</div>
            <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100 mt-0.5">TRACEABLE</div>
            <div className="text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1 font-mono font-medium">
              <span>WGN, sintético u otro artefacto declarado</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/twin-3d"
          className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-emerald-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-4 group-hover:scale-110 transition">
              <Box className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition">
              Gemelo Digital 3D Multiescala
            </h2>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
              Explora la cuenca agrícola, la muestra espacial del campo y la arquitectura de una
              planta de maíz derivadas de una corrida persistida.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <span>Iniciar Visor 3D</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <Link
          href="/reports"
          className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-cyan-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
        >
          <div>
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-4 group-hover:scale-110 transition">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition">
              Generador de Reportes Multiformato
            </h2>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
              Exporta informes ejecutivos y científicos automatizados en formatos <b>PDF</b> con gráficos,
              documentos técnicos en <b>Word (.docx)</b> y matrices de datos en <b>Excel (.xlsx)</b>.
            </p>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs font-medium text-cyan-600 dark:text-cyan-400">
            <span>Abrir Centro de Reportes</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        {hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO"]) ? (
          <Link
            href="/users"
            className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-rose-500/50 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
          >
            <div>
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-600 dark:text-rose-400 mb-4 group-hover:scale-110 transition">
                <Users className="w-5 h-5" />
              </div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-rose-600 dark:group-hover:text-rose-400 transition">
                Gestión de Usuarios y Roles (RBAC)
              </h2>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                Controla la matriz de roles y permisos, asigna credenciales a investigadores y
                administra los perfiles científicos habilitados para simulación.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-medium text-rose-600 dark:text-rose-400">
              <span>Administrar Usuarios</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
            </div>
          </Link>
        ) : (
          <Link
            href="/profile"
            className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 hover:border-zinc-400 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-900/70 transition flex flex-col justify-between group shadow-sm dark:shadow-lg"
          >
            <div>
              <div className="w-10 h-10 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center text-zinc-600 dark:text-zinc-300 mb-4 group-hover:scale-110 transition">
                <Shield className="w-5 h-5" />
              </div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 transition">
                Mi Perfil y Credenciales
              </h2>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1.5 leading-relaxed">
                Revisa tus permisos asignados, actualiza tu institución académica, especialidad científica
                y administra tu contraseña.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs font-medium text-zinc-600 dark:text-zinc-300">
              <span>Ver Perfil</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
            </div>
          </Link>
        )}
      </div>
    </div>
  );
}

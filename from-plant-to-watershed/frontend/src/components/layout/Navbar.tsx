"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { LogOut, Shield } from "lucide-react";
import Link from "next/link";
import ThemeToggle from "./ThemeToggle";

const pageTitles: Record<string, string> = {
  "/": "Dashboard Científico",
  "/simulations": "Simulación y Acoplamiento",
  "/twin-3d": "Gemelo Digital 3D",
  "/datasets": "Catálogo de Datos y ML",
  "/reports": "Centro de Reportes",
  "/users": "Gestión de Usuarios (RBAC)",
  "/profile": "Mi Perfil Científico",
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const primaryRole = user?.roles?.[0]?.name || "USUARIO";
  const currentTitle = pageTitles[pathname] || "Gemelo Digital";

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "SUPERADMIN":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30";
      case "ADMIN_CIENTIFICO":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
      case "INVESTIGADOR_HIDROLOGO":
        return "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30";
      case "OPERADOR_AGROPECUARIO":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30";
      default:
        return "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/30";
    }
  };

  const getInitial = (name?: string) => {
    if (!name) return "U";
    const cleaned = name.replace(/^(Dr\.|Dra\.|Ing\.|Lic\.)\s*/i, "").trim();
    return (cleaned.charAt(0) || name.charAt(0)).toUpperCase();
  };

  return (
    <header className="h-16 shrink-0 border-b border-zinc-200 dark:border-zinc-800/80 bg-white/90 dark:bg-zinc-950/80 backdrop-blur-md px-6 flex items-center justify-between z-30 transition-colors duration-200">
      {/* Lado izquierdo: Título de Sección y Estado Activo */}
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 tracking-tight hidden sm:block">
          {currentTitle}
        </h2>
        <span className="text-zinc-300 dark:text-zinc-700 hidden sm:inline">|</span>
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 text-[11px] font-mono font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>En línea</span>
        </div>
      </div>

      {/* Lado derecho: Theme toggle, Perfil de Usuario y Logout */}
      <div className="flex items-center gap-3">
        <ThemeToggle />

        {user && (
          <div className="flex items-center gap-2">
            <Link
              href="/profile"
              className="flex items-center gap-2.5 px-2.5 py-1 rounded-lg bg-zinc-100/80 dark:bg-zinc-900/80 border border-zinc-200/80 dark:border-zinc-800/80 hover:border-zinc-300 dark:hover:border-zinc-700 transition group"
            >
              <div className="w-7 h-7 rounded-full bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-700/50 flex items-center justify-center text-emerald-800 dark:text-emerald-300 font-bold text-xs shadow-xs">
                {getInitial(user.full_name)}
              </div>
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 group-hover:text-zinc-950 dark:group-hover:text-white transition leading-tight">
                  {user.full_name}
                </span>
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate max-w-[150px] leading-tight">
                  {user.profile?.institution || user.email}
                </span>
              </div>
            </Link>

            <span
              className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${getRoleBadgeColor(
                primaryRole
              )} hidden md:inline-flex items-center gap-1`}
            >
              <Shield className="w-2.5 h-2.5" />
              {primaryRole}
            </span>

            <button
              onClick={logout}
              title="Cerrar sesión"
              className="p-1.5 text-zinc-400 hover:text-rose-600 dark:text-zinc-400 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 border border-transparent hover:border-rose-200 dark:hover:border-rose-900/50 rounded-lg transition cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}


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
        return "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900";
      case "ADMIN_CIENTIFICO":
        return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900";
      case "INVESTIGADOR_HIDROLOGO":
        return "bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-900";
      case "OPERADOR_AGROPECUARIO":
        return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900";
      default:
        return "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
    }
  };

  const getInitial = (name?: string) => {
    if (!name) return "U";
    const cleaned = name.replace(/^(Dr\.|Dra\.|Ing\.|Lic\.)\s*/i, "").trim();
    return (cleaned.charAt(0) || name.charAt(0)).toUpperCase();
  };

  return (
    <header className="z-30 flex h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-300 bg-white px-3 transition-colors duration-200 sm:px-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex min-w-0 items-center gap-3">
        <h2 className="hidden truncate text-sm font-semibold tracking-tight text-slate-900 sm:block dark:text-slate-100">
          {currentTitle}
        </h2>
        <span
          aria-hidden="true"
          className="hidden h-4 w-px shrink-0 bg-slate-300 sm:block dark:bg-slate-700"
        />
        <div className="flex shrink-0 items-center gap-1.5 border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
          <span aria-hidden="true" className="h-1.5 w-1.5 bg-emerald-600 dark:bg-emerald-400" />
          <span>En línea</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <ThemeToggle />

        {user && (
          <div className="flex items-center gap-1.5 sm:gap-2">
            <Link
              href="/profile"
              aria-current={pathname === "/profile" ? "page" : undefined}
              className="group flex items-center gap-2 border border-slate-200 bg-slate-50 px-1.5 py-1 transition-colors hover:border-slate-400 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-600 dark:hover:bg-slate-900 dark:focus-visible:ring-emerald-400 dark:focus-visible:ring-offset-slate-900 sm:gap-2.5 sm:px-2.5"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center border border-emerald-300 bg-emerald-100 text-xs font-bold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                {getInitial(user.full_name)}
              </span>
              <span className="hidden min-w-0 flex-col text-left sm:flex">
                <span className="max-w-36 truncate text-xs font-semibold leading-tight text-slate-800 group-hover:text-slate-950 dark:text-slate-200 dark:group-hover:text-white">
                  {user.full_name}
                </span>
                <span className="max-w-36 truncate text-[10px] leading-tight text-slate-500 dark:text-slate-400">
                  {user.profile?.institution || user.email}
                </span>
              </span>
            </Link>

            <span
              className={`hidden items-center gap-1 border px-2 py-1 font-mono text-[9px] font-semibold lg:inline-flex ${getRoleBadgeColor(
                primaryRole
              )}`}
            >
              <Shield aria-hidden="true" className="h-2.5 w-2.5" />
              {primaryRole}
            </span>

            <button
              type="button"
              onClick={logout}
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              className="flex h-9 w-9 items-center justify-center border border-transparent text-slate-500 transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 dark:text-slate-400 dark:hover:border-rose-900 dark:hover:bg-rose-950/40 dark:hover:text-rose-300"
            >
              <LogOut aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

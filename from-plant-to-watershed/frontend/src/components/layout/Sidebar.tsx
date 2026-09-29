"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import {
  LayoutDashboard,
  Box,
  Sliders,
  FileSpreadsheet,
  Users,
  UserCheck,
  Layers,
  Sprout,
  Database,
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { hasAnyRole } = useAuth();

  const navigation = [
    {
      name: "Dashboard Científico",
      href: "/",
      icon: LayoutDashboard,
      roles: ["ALL"],
    },
    {
      name: "Simulación y Acoplamiento",
      href: "/simulations",
      icon: Sliders,
      roles: ["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"],
      badge: "SWAT+",
    },
    {
      name: "Gemelo Digital 3D",
      href: "/twin-3d",
      icon: Box,
      roles: ["ALL"],
      badge: "3D",
    },
    {
      name: "Catálogo de Datos y ML",
      href: "/datasets",
      icon: Database,
      roles: ["ALL"],
    },
    {
      name: "Reportes y Evidencia",
      href: "/reports",
      icon: FileSpreadsheet,
      roles: ["ALL"],
    },
    {
      name: "Usuarios y Roles (RBAC)",
      href: "/users",
      icon: Users,
      roles: ["SUPERADMIN", "ADMIN_CIENTIFICO"],
      badge: "Admin",
    },
    {
      name: "Mi Perfil Científico",
      href: "/profile",
      icon: UserCheck,
      roles: ["ALL"],
    },
  ];

  return (
    <aside className="flex h-full w-64 shrink-0 select-none flex-col justify-between overflow-hidden border-r border-slate-300 bg-white text-slate-900 transition-colors duration-200 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100">
      <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-4">
        <Link
          href="/"
          className="group flex items-center gap-3 border-b border-slate-200 pb-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 dark:border-slate-800 dark:focus-visible:ring-offset-slate-900"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-950">
            <Sprout className="h-5 w-5 text-emerald-700 transition-transform group-hover:scale-105 dark:text-emerald-400" />
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="flex items-center gap-1.5 whitespace-nowrap text-[11px] font-bold tracking-tight text-slate-900 dark:text-slate-100">
              PLANT TO WATERSHED
              <span className="border border-slate-300 bg-white px-1 py-0.5 font-mono text-[9px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
                SWAT+
              </span>
            </span>
            <span className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
              Gemelo Digital Multiescala
            </span>
          </div>
        </Link>

        <nav aria-label="Navegación principal" className="flex flex-col gap-1">
          <span className="mb-1 px-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
            Módulos
          </span>
          {navigation.map((item) => {
            const isAllowed =
              item.roles.includes("ALL") || hasAnyRole(item.roles);
            if (!isAllowed) return null;

            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                title={item.name}
                aria-current={isActive ? "page" : undefined}
                className={`relative flex min-h-10 items-center justify-between gap-2 border px-2.5 py-2 text-xs transition-colors focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:focus-visible:ring-emerald-400 ${
                  isActive
                    ? "border-slate-300 border-l-2 border-l-slate-900 bg-slate-100 font-semibold text-slate-900 dark:border-slate-700 dark:border-l-slate-100 dark:bg-slate-800/80 dark:text-slate-50"
                    : "border-transparent border-l-2 text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:border-slate-800 dark:hover:bg-slate-800/50 dark:hover:text-slate-100"
                }`}
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <Icon
                    aria-hidden="true"
                    className={`h-4 w-4 shrink-0 ${
                      isActive
                        ? "text-slate-900 dark:text-slate-100"
                        : "text-slate-500 dark:text-slate-400"
                    }`}
                  />
                  <span className="truncate">{item.name}</span>
                </span>
                {item.badge && (
                  <span className="shrink-0 border border-slate-300 bg-white px-1.5 py-0.5 font-mono text-[9px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="shrink-0 border-t border-slate-300 p-3 dark:border-slate-800">
        <div className="flex items-start gap-2.5 border border-slate-200 bg-slate-50 p-2.5 dark:border-slate-800 dark:bg-slate-950/70">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
            <Layers className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
          </div>
          <div className="min-w-0">
            <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400">
              Cuenca piloto
            </span>
            <span className="block truncate text-xs font-semibold text-slate-800 dark:text-slate-200">
              South Fork Iowa River
            </span>
            <span className="mt-1 block font-mono text-[9px] leading-relaxed text-slate-500 dark:text-slate-400">
              USGS 05451210 · FSPM ⇄ 1000 plantas ⇄ SWAT+
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}

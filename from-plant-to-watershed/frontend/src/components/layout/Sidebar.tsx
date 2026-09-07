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
  Sprout
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { hasAnyRole } = useAuth();

  const navigation = [
    {
      name: "Dashboard General",
      href: "/",
      icon: LayoutDashboard,
      roles: ["ALL"],
    },
    {
      name: "Gemelo Digital 3D",
      href: "/twin-3d",
      icon: Box,
      roles: ["ALL"],
      badge: "3D",
    },
    {
      name: "Modelado SWAT & Clima",
      href: "/simulations",
      icon: Sliders,
      roles: ["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"],
    },
    {
      name: "Reportes Multiformato",
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
    <aside className="w-64 border-r border-zinc-200 dark:border-zinc-800/80 bg-white dark:bg-zinc-950 flex flex-col justify-between shrink-0 transition-colors duration-200">
      <div className="p-5 flex flex-col gap-6">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-400 p-[1px] shadow-lg shadow-emerald-500/20">
            <div className="w-full h-full bg-white dark:bg-zinc-950 rounded-[11px] flex items-center justify-center transition-colors">
              <Sprout className="w-5 h-5 text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100 tracking-tight flex items-center gap-1.5">
              AP-3 TWIN
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-800/50">
                v1.0
              </span>
            </span>
            <span className="text-[11px] text-zinc-500 dark:text-zinc-400">Plant to Watershed</span>
          </div>
        </Link>

        {/* Navigation list */}
        <nav className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 dark:text-zinc-400 px-3 py-1 font-semibold">
            Módulos del Sistema
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
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                  isActive
                    ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-300/80 dark:border-emerald-500/20 shadow-sm font-semibold"
                    : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-500 dark:text-zinc-400"
                    }`}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      item.badge === "3D"
                        ? "bg-cyan-100 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-300 dark:border-cyan-500/30"
                        : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700/50"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-900 text-[11px] text-zinc-500 dark:text-zinc-400 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-zinc-500 dark:text-zinc-400" />
          <span className="font-mono text-zinc-700 dark:text-zinc-300">Escalas: Micro ⇄ Meso ⇄ Macro</span>
        </div>
        <p className="text-[10px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
          Acoplamiento Fisiológico Vegetal, Hidrología SWAT y CMIP6.
        </p>
      </div>
    </aside>
  );
}

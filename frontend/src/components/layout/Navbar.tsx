"use client";

import React from "react";
import { useAuth } from "../../context/AuthContext";
import { LogOut, User as UserIcon, Shield, Activity } from "lucide-react";
import Link from "next/link";

export default function Navbar() {
  const { user, logout } = useAuth();

  const primaryRole = user?.roles?.[0]?.name || "USUARIO";

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "SUPERADMIN":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "ADMIN_CIENTIFICO":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "INVESTIGADOR_HIDROLOGO":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      case "OPERADOR_AGROPECUARIO":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
    }
  };

  return (
    <header className="h-16 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-mono tracking-wide text-zinc-400 uppercase">
            Plataforma Gemelo Digital Activa
          </span>
        </div>
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-400">
          <Activity className="w-3 h-3 text-cyan-400" />
          <span>Fisiología ⇄ SWAT Hidrología</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <Link
              href="/profile"
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-zinc-800 hover:border-zinc-700 transition group"
            >
              <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-700/50 flex items-center justify-center text-cyan-300 font-semibold text-xs">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col text-left">
                <span className="text-xs font-medium text-zinc-200 group-hover:text-white transition">
                  {user.full_name}
                </span>
                <span className="text-[10px] text-zinc-400 truncate max-w-[140px]">
                  {user.profile?.institution || user.email}
                </span>
              </div>
            </Link>

            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getRoleBadgeColor(
                primaryRole
              )} hidden md:inline-flex items-center gap-1`}
            >
              <Shield className="w-2.5 h-2.5" />
              {primaryRole}
            </span>

            <button
              onClick={logout}
              title="Cerrar sesión"
              className="p-2 text-zinc-400 hover:text-rose-400 hover:bg-rose-950/30 border border-transparent hover:border-rose-900/50 rounded-lg transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

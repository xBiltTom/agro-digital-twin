"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import { Sprout, ShieldCheck, ArrowRight, Loader2, KeyRound } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Error de inicio de sesión");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-zinc-900/80 border border-zinc-800/80 rounded-2xl p-8 backdrop-blur-xl shadow-2xl z-10">
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 p-[1.5px] mb-4 shadow-xl shadow-emerald-950/60">
            <div className="w-full h-full bg-zinc-950 rounded-[14.5px] flex items-center justify-center">
              <Sprout className="w-7 h-7 text-emerald-400" />
            </div>
          </div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
            Gemelo Digital Multiescala (AP-3)
          </h1>
          <p className="text-xs text-zinc-400 mt-1 max-w-xs">
            From Plant to Watershed: Acoplamiento Fisiológico, Hidrología SWAT y CMIP6
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-zinc-400 mb-1.5 font-medium">
              Correo Electrónico
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="cientifico@digitaltwin.org"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-sm focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-zinc-400 mb-1.5 font-medium">
              Contraseña
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-sm focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 w-full py-2.5 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Iniciar Sesión en Plataforma</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Demo Quick Access */}
        <div className="mt-6 pt-6 border-t border-zinc-800/80 flex flex-col gap-2.5">
          <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 font-mono">
            <KeyRound className="w-3.5 h-3.5 text-amber-400" />
            <span>Acceso Rápido de Prueba (Demo Roles):</span>
          </div>

          <div className="grid grid-cols-1 gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => handleQuickLogin("admin@digitaltwin.org", "Admin123!")}
              className="px-2.5 py-1.5 rounded-md bg-zinc-950 hover:bg-zinc-800/90 border border-zinc-800 hover:border-zinc-700 text-zinc-300 flex items-center justify-between text-left transition group"
            >
              <div className="flex flex-col">
                <span className="font-medium group-hover:text-rose-300">Dr. Valdivia (Superadmin)</span>
                <span className="text-[10px] text-zinc-400">Acceso total y gestión RBAC</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                SUPERADMIN
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("investigador@digitaltwin.org", "Investiga123!")}
              className="px-2.5 py-1.5 rounded-md bg-zinc-950 hover:bg-zinc-800/90 border border-zinc-800 hover:border-zinc-700 text-zinc-300 flex items-center justify-between text-left transition group"
            >
              <div className="flex flex-col">
                <span className="font-medium group-hover:text-cyan-300">Dra. Ramos (SWAT & Clima)</span>
                <span className="text-[10px] text-zinc-400">Simulaciones y reportes hidrológicos</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                INVESTIGADOR
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("operador@digitaltwin.org", "Operador123!")}
              className="px-2.5 py-1.5 rounded-md bg-zinc-950 hover:bg-zinc-800/90 border border-zinc-800 hover:border-zinc-700 text-zinc-300 flex items-center justify-between text-left transition group"
            >
              <div className="flex flex-col">
                <span className="font-medium group-hover:text-amber-300">Ing. Morales (Operador)</span>
                <span className="text-[10px] text-zinc-400">Monitoreo de planta y sensores</span>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                OPERADOR
              </span>
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-zinc-400">
          ¿No tienes una cuenta aún?{" "}
          <Link href="/register" className="text-emerald-400 hover:underline">
            Regístrate aquí
          </Link>
        </div>
      </div>
    </div>
  );
}

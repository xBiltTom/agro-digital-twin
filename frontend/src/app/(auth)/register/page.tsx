"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import { Sprout, ArrowRight, Loader2 } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [institution, setInstitution] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register({
        email,
        password,
        full_name: fullName,
        institution,
        scientific_specialty: specialty,
        role_names: ["OPERADOR_AGROPECUARIO"]
      });
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Error durante el registro");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg bg-zinc-900/80 border border-zinc-800/80 rounded-2xl p-8 backdrop-blur-xl shadow-2xl z-10">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 p-[1.5px] mb-3">
            <div className="w-full h-full bg-zinc-950 rounded-[11px] flex items-center justify-center">
              <Sprout className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
            Registro de Investigador / Operador
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Únete a la plataforma del Gemelo Digital AP-3
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
          <div>
            <label className="block text-xs font-mono uppercase text-zinc-400 mb-1 font-medium">
              Nombre Completo
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Dr. Fernando Morales"
              className="w-full px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-mono uppercase text-zinc-400 mb-1 font-medium">
                Correo Institucional
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="investigador@uni.edu.pe"
                className="w-full px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-zinc-400 mb-1 font-medium">
                Contraseña
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-mono uppercase text-zinc-400 mb-1 font-medium">
                Institución / Centro
              </label>
              <input
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="Universidad Nacional de Ingeniería"
                className="w-full px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-zinc-400 mb-1 font-medium">
                Especialidad Científica
              </label>
              <input
                type="text"
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                placeholder="Hidrología / Agronomía"
                className="w-full px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/50 transition placeholder:text-zinc-600"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-3 w-full py-2.5 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Completar Registro</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-zinc-400">
          ¿Ya tienes cuenta?{" "}
          <Link href="/login" className="text-emerald-400 hover:underline">
            Inicia sesión
          </Link>
        </div>
      </div>
    </div>
  );
}

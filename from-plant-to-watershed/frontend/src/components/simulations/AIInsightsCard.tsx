"use client";

import React, { useState } from "react";
import {
  Sparkles,
  RefreshCw,
  Cpu,
  Sprout,
  Layers,
  Waves,
  ShieldCheck,
  FileCheck2,
  AlertTriangle,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { AIInsightsResponse } from "@/types/simulation";
import { api } from "@/lib/api";

interface AIInsightsCardProps {
  simulationId: string;
  initialInsights?: AIInsightsResponse | null;
  onInsightsUpdated?: (insights: AIInsightsResponse) => void;
}

export const AIInsightsCard: React.FC<AIInsightsCardProps> = ({
  simulationId,
  initialInsights,
  onInsightsUpdated
}) => {
  const [insights, setInsights] = useState<AIInsightsResponse | null>(initialInsights || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"plant" | "field" | "watershed">("watershed");
  const [isExpanded, setIsExpanded] = useState(true);

  const fetchInsights = async (forceRegenerate = false) => {
    try {
      setLoading(true);
      setError(null);
      const res = forceRegenerate
        ? await api.generateSimulationAIInsights(simulationId)
        : await api.getSimulationAIInsights(simulationId);
      setInsights(res);
      if (onInsightsUpdated) {
        onInsightsUpdated(res);
      }
    } catch (err: unknown) {
      console.error("Error loading AI insights:", err);
      setError(err instanceof Error ? err.message : "Error al procesar el análisis de IA");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-emerald-500/30 rounded-xl p-5 shadow-xl relative overflow-hidden backdrop-blur-sm">
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-4 relative z-10">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/40 text-emerald-400 shadow-sm">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-white tracking-wide">
                Diagnóstico Científico & Recomendaciones de Política (IA)
              </h3>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-700/50 flex items-center gap-1 font-mono">
                <Cpu className="w-3 h-3 text-emerald-400" />
                LangChain
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Síntesis biofísica multiescala (Planta FSPM ➔ Parcela ➔ Cuenca SWAT+) y sugerencias de manejo
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {insights && (
            <button
              onClick={() => fetchInsights(true)}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
              title="Regenerar análisis con el motor de IA"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-emerald-400" : ""}`} />
              {loading ? "Sintetizando..." : "Regenerar"}
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title={isExpanded ? "Plegar tarjeta" : "Desplegar tarjeta"}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Body */}
      {isExpanded && (
        <div className="space-y-5 relative z-10">
          {error && (
            <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-xs text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!insights && !loading && (
            <div className="text-center py-8 px-4 border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
              <Sparkles className="w-8 h-8 text-emerald-400/60 mx-auto mb-2.5" />
              <h4 className="text-sm font-medium text-slate-200">
                Generar Síntesis Inteligente de la Simulación
              </h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-4">
                El agente de IA analizará los resultados biofísicos de la simulación, el balance de masa hídrico y formulará directrices de política adaptativa.
              </p>
              <button
                onClick={() => fetchInsights(false)}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-lg shadow-emerald-900/30 flex items-center gap-2 mx-auto transition-all"
              >
                <Sparkles className="w-4 h-4" />
                Analizar Simulación con IA
              </button>
            </div>
          )}

          {loading && !insights && (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
              <p className="text-xs text-slate-300 font-mono animate-pulse">
                Sintetizando balance hídrico y evaluando resiliencia multiescala...
              </p>
            </div>
          )}

          {insights && (
            <>
              {/* Provider Badge */}
              <div className="flex items-center justify-between text-xs text-slate-400 bg-slate-950/60 border border-slate-800/80 px-3 py-1.5 rounded-lg">
                <span className="flex items-center gap-1.5 font-mono">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
                  Motor: <strong className="text-slate-200">{insights.provider}</strong>
                </span>
                <span>Generado: {new Date(insights.generated_at).toLocaleString()}</span>
              </div>

              {/* 1. Executive Summary */}
              <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                  <FileCheck2 className="w-4 h-4" />
                  Resumen Ejecutivo del Balance Hídrico
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-sans">
                  {insights.executive_summary}
                </p>
              </div>

              {/* 2. Multiscale Biophysical Diagnosis */}
              <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
                  <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-4 h-4" />
                    Diagnóstico Biofísico Multiescala
                  </span>

                  <div className="flex gap-1">
                    <button
                      onClick={() => setActiveTab("plant")}
                      className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-colors ${
                        activeTab === "plant"
                          ? "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <Sprout className="w-3 h-3" /> Micro (Planta)
                    </button>
                    <button
                      onClick={() => setActiveTab("field")}
                      className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-colors ${
                        activeTab === "field"
                          ? "bg-amber-600/30 text-amber-300 border border-amber-500/40"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <Layers className="w-3 h-3" /> Meso (Parcela)
                    </button>
                    <button
                      onClick={() => setActiveTab("watershed")}
                      className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1 transition-colors ${
                        activeTab === "watershed"
                          ? "bg-blue-600/30 text-blue-300 border border-blue-500/40"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <Waves className="w-3 h-3" /> Macro (Cuenca)
                    </button>
                  </div>
                </div>

                <div className="text-xs text-slate-300 leading-relaxed min-h-[4rem]">
                  {activeTab === "plant" && (
                    <div className="bg-emerald-950/20 border border-emerald-900/30 p-3 rounded-lg">
                      <div className="font-medium text-emerald-300 mb-1 flex items-center gap-1.5">
                        <Sprout className="w-3.5 h-3.5" /> Nivel 1: Fisiología y Dosel de Maíz (1,000 plantas FSPM)
                      </div>
                      <p>{insights.multiscale_biophysical_diagnosis.micro_scale_plant}</p>
                    </div>
                  )}

                  {activeTab === "field" && (
                    <div className="bg-amber-950/20 border border-amber-900/30 p-3 rounded-lg">
                      <div className="font-medium text-amber-300 mb-1 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5" /> Nivel 2: Dinámica de Parcela y Suelo Radicular (0-100 cm)
                      </div>
                      <p>{insights.multiscale_biophysical_diagnosis.meso_scale_field}</p>
                    </div>
                  )}

                  {activeTab === "watershed" && (
                    <div className="bg-blue-950/20 border border-blue-900/30 p-3 rounded-lg">
                      <div className="font-medium text-blue-300 mb-1 flex items-center gap-1.5">
                        <Waves className="w-3.5 h-3.5" /> Nivel 3: Enrutamiento SWAT+ Cuenca South Fork Iowa (USGS 05451210)
                      </div>
                      <p>{insights.multiscale_biophysical_diagnosis.macro_scale_watershed}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* 3. Climate Resilience & Policy Recommendations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Resilience */}
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-orange-400 uppercase tracking-wider">
                      <ShieldCheck className="w-4 h-4" />
                      Evaluación de Resiliencia Climática
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">
                      {insights.climate_resilience_assessment}
                    </p>
                  </div>
                </div>

                {/* Recommendations */}
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2.5 text-xs font-semibold text-teal-400 uppercase tracking-wider">
                    <FileCheck2 className="w-4 h-4" />
                    Recomendaciones de Política y Manejo
                  </div>
                  <ul className="space-y-2">
                    {insights.policy_recommendations.map((rec, idx) => (
                      <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                        <span className="w-4 h-4 rounded-full bg-teal-950 text-teal-300 border border-teal-700/60 flex items-center justify-center text-[10px] shrink-0 mt-0.5 font-mono">
                          {idx + 1}
                        </span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 4. Limitations Footer */}
              <div className="text-[11px] text-slate-400/90 bg-slate-950/40 border border-slate-800/50 rounded-lg p-2.5 flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400/80 shrink-0 mt-0.5" />
                <span>{insights.limitations_and_uncertainty}</span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

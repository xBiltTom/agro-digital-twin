"use client";

import React, { useState } from "react";
import {
  RefreshCw,
  Cpu,
  Sprout,
  Layers,
  Waves,
  ShieldCheck,
  FileText,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Maximize2,
  X,
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
  onInsightsUpdated,
}) => {
  const [insights, setInsights] = useState<AIInsightsResponse | null>(initialInsights || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scaleTab, setScaleTab] = useState<"plant" | "field" | "watershed">("watershed");
  const [isReaderModalOpen, setIsReaderModalOpen] = useState(false);

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
      console.error("Error al cargar diagnóstico de IA:", err);
      setError(err instanceof Error ? err.message : "Error al procesar el análisis de IA");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-none overflow-hidden transition-colors">
      {/* Encabezado del Documento de Diagnóstico */}
      <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-950/40">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-serif font-semibold text-slate-900 dark:text-slate-100">
              Diagnóstico biofísico y recomendaciones de manejo
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-none bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 font-mono">
              LangChain
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Evaluación automatizada del balance hídrico, resiliencia climática y recomendaciones agronómicas.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {insights && (
            <button
              type="button"
              onClick={() => setIsReaderModalOpen(true)}
              className="px-3 py-1.5 rounded-none border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
              title="Abrir en modal de lectura a pantalla completa"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Modo lector / Modal</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => fetchInsights(Boolean(insights))}
            disabled={loading}
            className="px-3 py-1.5 rounded-none bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-medium flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{loading ? "Procesando..." : insights ? "Actualizar" : "Generar"}</span>
          </button>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {error && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-none text-xs text-rose-800 dark:text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!insights && !loading && (
          <div className="text-center py-10 px-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-none bg-slate-50/40 dark:bg-slate-950/20">
            <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2 opacity-70" />
            <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200">
              Sin diagnóstico generado para este experimento
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 mb-4 leading-relaxed">
              El agente de LangChain analiza las series temporales de la simulación, el balance de masa hídrico y evalúa la adaptación agronómica bajo el protocolo de la Ficha Técnica.
            </p>
            <button
              type="button"
              onClick={() => fetchInsights(false)}
              className="px-4 py-2 rounded-none bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-medium transition cursor-pointer shadow-none"
            >
              Generar diagnóstico con LangChain
            </button>
          </div>
        )}

        {loading && !insights && (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="w-6 h-6 rounded-none border-2 border-slate-900 dark:border-slate-100 border-t-transparent animate-spin" />
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              Evaluando tensores biofísicos y formulando directrices de manejo...
            </p>
          </div>
        )}

        {insights && (
          <>
            {/* Metadatos del Informe */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-100 dark:border-slate-800">
              <span className="font-mono text-[11px]">
                Motor: <strong className="text-slate-800 dark:text-slate-200 font-normal">{insights.provider}</strong>
              </span>
              <span className="font-mono text-[11px]">
                Fecha de generación: {new Date(insights.generated_at).toLocaleString()}
              </span>
            </div>

            {/* 1. Resumen Ejecutivo del Balance */}
            <div>
              <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 mb-1.5 flex items-center gap-1.5 uppercase tracking-wide">
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                Resumen ejecutivo del balance hídrico
              </h4>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50/70 dark:bg-slate-950/50 border border-slate-200/80 dark:border-slate-800/80 rounded-none p-3.5">
                {insights.executive_summary}
              </p>
            </div>

            {/* 2. Diagnóstico Multiescala (Planta / Suelo / Cuenca) */}
            <div className="border border-slate-200/80 dark:border-slate-800/80 rounded-none p-3.5 bg-slate-50/40 dark:bg-slate-950/30">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-2 border-b border-slate-200/60 dark:border-slate-800/60">
                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Diagnóstico por nivel de escala
                </span>

                <div className="flex items-center gap-1 bg-white dark:bg-slate-900 p-0.5 rounded-none border border-slate-200 dark:border-slate-800 text-xs">
                  <button
                    type="button"
                    onClick={() => setScaleTab("plant")}
                    className={`px-2.5 py-1 rounded-none text-xs transition cursor-pointer ${
                      scaleTab === "plant"
                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                        : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                  >
                    Micro (Planta)
                  </button>
                  <button
                    type="button"
                    onClick={() => setScaleTab("field")}
                    className={`px-2.5 py-1 rounded-none text-xs transition cursor-pointer ${
                      scaleTab === "field"
                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                        : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                  >
                    Meso (Parcela)
                  </button>
                  <button
                    type="button"
                    onClick={() => setScaleTab("watershed")}
                    className={`px-2.5 py-1 rounded-none text-xs transition cursor-pointer ${
                      scaleTab === "watershed"
                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium shadow-none"
                        : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                  >
                    Macro (Cuenca)
                  </button>
                </div>
              </div>

              <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed min-h-[3.5rem]">
                {scaleTab === "plant" && (
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-1">
                      Fisiología individual y dosel foliar
                    </span>
                    <p>{insights.multiscale_biophysical_diagnosis.micro_scale_plant}</p>
                  </div>
                )}

                {scaleTab === "field" && (
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-1">
                      Perfil edáfico y dinámica de raíces
                    </span>
                    <p>{insights.multiscale_biophysical_diagnosis.meso_scale_field}</p>
                  </div>
                )}

                {scaleTab === "watershed" && (
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-1">
                      Enrutamiento hidrológico y aforo en exutorio
                    </span>
                    <p>{insights.multiscale_biophysical_diagnosis.macro_scale_watershed}</p>
                  </div>
                )}
              </div>
            </div>

            {/* 3. Resiliencia Climática & Recomendaciones de Política */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <div className="p-3.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/40 dark:bg-slate-950/30 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 mb-1.5 flex items-center gap-1.5 uppercase tracking-wide">
                    <ShieldCheck className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                    Evaluación de resiliencia climática
                  </h4>
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    {insights.climate_resilience_assessment}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-none border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/40 dark:bg-slate-950/30">
                <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-1.5 uppercase tracking-wide">
                  <Layers className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  Recomendaciones de manejo y política hídrica
                </h4>
                <ul className="space-y-2">
                  {insights.policy_recommendations.map((rec, idx) => (
                    <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2">
                      <span className="font-mono text-[10px] text-slate-400 mt-0.5 shrink-0">
                        [{idx + 1}]
                      </span>
                      <span className="leading-relaxed">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* 4. Declaración de Incertidumbre y Límites del Modelo */}
            <div className="text-[11px] text-slate-500 dark:text-slate-400 bg-slate-50/70 dark:bg-slate-950/50 border border-slate-200/60 dark:border-slate-800/60 rounded-none p-3 flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-medium text-slate-700 dark:text-slate-300 mr-1">Incertidumbre y límites del modelo:</span>
                {insights.limitations_and_uncertainty}
              </div>
            </div>
          </>
        )}
      </div>
      {/* Modal Lector de Diagnóstico Científico */}
      {isReaderModalOpen && insights && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
          <div className="w-full max-w-4xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
            {/* Cabecera del Modal Lector */}
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-serif font-semibold text-base text-slate-900 dark:text-slate-100">
                    Diagnóstico biofísico y recomendaciones de manejo
                  </h3>
                  <span className="text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                    LangChain Agent
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Generado: {new Date(insights.generated_at).toLocaleString()} · Motor: {insights.provider}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsReaderModalOpen(false)}
                className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                title="Cerrar modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Contenido Completo del Reporte */}
            <div className="p-6 space-y-6 flex-1 min-h-0 overflow-y-auto">
              {/* 1. Resumen Ejecutivo */}
              <div className="space-y-2">
                <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-slate-500" />
                  1. Resumen ejecutivo del balance hídrico
                </h4>
                <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                  {insights.executive_summary}
                </div>
              </div>

              {/* 2. Diagnóstico Multiescala */}
              <div className="space-y-2">
                <div className="flex items-center justify-between pb-1 border-b border-slate-200 dark:border-slate-800">
                  <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                    2. Diagnóstico biofísico multiescala
                  </h4>
                  <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-0.5 text-xs font-mono">
                    <button
                      type="button"
                      onClick={() => setScaleTab("plant")}
                      className={`px-2.5 py-1 ${scaleTab === "plant" ? "bg-white dark:bg-slate-900 font-bold text-slate-900 dark:text-slate-100" : "text-slate-500 hover:text-slate-900"}`}
                    >Micro (Planta)</button>
                    <button
                      type="button"
                      onClick={() => setScaleTab("field")}
                      className={`px-2.5 py-1 ${scaleTab === "field" ? "bg-white dark:bg-slate-900 font-bold text-slate-900 dark:text-slate-100" : "text-slate-500 hover:text-slate-900"}`}
                    >Meso (Parcela)</button>
                    <button
                      type="button"
                      onClick={() => setScaleTab("watershed")}
                      className={`px-2.5 py-1 ${scaleTab === "watershed" ? "bg-white dark:bg-slate-900 font-bold text-slate-900 dark:text-slate-100" : "text-slate-500 hover:text-slate-900"}`}
                    >Macro (Cuenca)</button>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                  {scaleTab === "plant" && insights.multiscale_biophysical_diagnosis.micro_scale_plant}
                  {scaleTab === "field" && insights.multiscale_biophysical_diagnosis.meso_scale_field}
                  {scaleTab === "watershed" && insights.multiscale_biophysical_diagnosis.macro_scale_watershed}
                </div>
              </div>

              {/* 3. Resiliencia y Políticas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-2">
                  <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    3. Resiliencia climática
                  </h4>
                  <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {insights.climate_resilience_assessment}
                  </p>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-2">
                  <h4 className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    4. Recomendaciones de política
                  </h4>
                  <ul className="space-y-2">
                    {insights.policy_recommendations.map((rec, idx) => (
                      <li key={idx} className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 flex items-start gap-2">
                        <span className="font-mono text-[11px] text-slate-400 mt-0.5">[{idx + 1}]</span>
                        <span className="leading-relaxed">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 4. Incertidumbre */}
              <div className="p-3 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-700 dark:text-slate-300 mr-1">Incertidumbre y límites del modelo:</strong>
                  {insights.limitations_and_uncertainty}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

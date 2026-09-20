"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { DatasetInfo, ExternalModelInfo } from "../../../types/simulation";
import {
  Database,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileCheck2,
  Layers,
  MapPin,
  Calendar,
  Search,
  Activity,
  Shield,
  FileCode,
  Tag,
} from "lucide-react";

export default function DatasetsPage() {
  const [activeTab, setActiveTab] = useState<"DATASETS" | "MODELS">("DATASETS");
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [models, setModels] = useState<ExternalModelInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    async function loadCatalog() {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const [dsData, mdData] = await Promise.all([
          api.getDatasets(),
          api.getExternalModels(),
        ]);
        setDatasets(dsData);
        setModels(mdData);
      } catch (err: any) {
        setErrorMsg(err.message || "Error al cargar el catálogo de datos y modelos.");
      } finally {
        setIsLoading(false);
      }
    }
    loadCatalog();
  }, []);

  const filteredDatasets = datasets.filter((ds) =>
    ds.dataset_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ds.provider.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ds.variable.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredModels = models.filter((m) =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.target.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.framework.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto transition-colors duration-200 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              Catálogo de Datos Observacionales y Modelos ML
            </h1>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl">
            Módulo 1 de Datos: Fuentes oficiales con trazabilidad verificada (USGS NWIS, USDA CDL, GridMET) y
            registro de bundles de Machine Learning independientes para emulación y screening ecohidrológico.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="Filtrar catálogo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-800 dark:text-zinc-200 focus:outline-none focus:border-emerald-500 shadow-sm"
            />
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2">
        <button
          onClick={() => setActiveTab("DATASETS")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "DATASETS"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Datasets Observacionales ({datasets.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("MODELS")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer flex items-center gap-2 ${
            activeTab === "MODELS"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/80"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>Modelos Externos de ML ({models.length})</span>
        </button>
      </div>

      {isLoading ? (
        <div className="p-16 flex flex-col items-center justify-center gap-3 text-zinc-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
          <span>Consultando catálogo de datos y modelos del runtime...</span>
        </div>
      ) : activeTab === "DATASETS" ? (
        /* Datasets View */
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDatasets.map((ds) => (
              <div
                key={ds.id}
                className="p-5 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between hover:border-emerald-500/40 transition gap-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 font-semibold">
                      {ds.provider}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      {ds.evidence_type}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    {ds.dataset_name}
                  </h3>
                  <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 block font-mono">
                    Variable: {ds.variable} ({ds.unit})
                  </span>

                  <div className="mt-3 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80 flex flex-col gap-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 text-[11px]">Resolución Temporal:</span>
                      <span className="font-bold text-zinc-800 dark:text-zinc-200">{ds.temporal_resolution}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 text-[11px]">Soporte Espacial:</span>
                      <span className="font-bold text-zinc-800 dark:text-zinc-200">{ds.spatial_support}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 text-[11px]">Artefactos Registrados:</span>
                      <span className="font-bold text-emerald-600 dark:text-emerald-400">{ds.normalized_artifact_count}</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-zinc-400 flex items-center justify-between">
                  <span>ID: {ds.id.slice(0, 12)}...</span>
                  <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Verificado
                  </span>
                </div>
              </div>
            ))}
          </div>

          {filteredDatasets.length === 0 && (
            <div className="p-12 text-center text-xs text-zinc-500 rounded-2xl border border-zinc-200 dark:border-zinc-800">
              No se encontraron datasets que coincidan con la búsqueda.
            </div>
          )}
        </div>
      ) : (
        /* Machine Learning Models View */
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredModels.map((m) => (
              <div
                key={m.id}
                className="p-5 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between hover:border-cyan-500/40 transition gap-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border border-cyan-500/30 font-semibold">
                      {m.framework}
                    </span>
                    <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                      {m.status}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    {m.name}
                  </h3>
                  <span className="text-xs text-cyan-700 dark:text-cyan-400 font-mono mt-0.5 block">
                    Objetivo: {m.target}
                  </span>

                  <div className="mt-3 p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800/80 flex flex-col gap-1.5 text-xs font-mono">
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 text-[11px]">Tipo Entrenamiento:</span>
                      <span className="font-bold text-zinc-800 dark:text-zinc-200">{m.training_data_type ?? "SYNTHETIC_SCREENING"}</span>
                    </div>
                    {Object.entries(m.metrics || {}).map(([metricKey, val]) => (
                      <div key={metricKey} className="flex items-center justify-between">
                        <span className="text-zinc-500 text-[11px]">{metricKey}:</span>
                        <span className="font-bold text-emerald-600 dark:text-emerald-400">
                          {typeof val === "number" ? val.toFixed(4) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 text-[10px] font-mono text-zinc-400 flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span>Artifact SHA-256:</span>
                    <span className="text-zinc-500 dark:text-zinc-400">{m.checksum ? `${m.checksum.slice(0, 10)}...` : "—"}</span>
                  </div>
                  <div className="text-[9px] text-zinc-500 truncate">
                    {m.artifact_path ?? "Runtime local"}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredModels.length === 0 && (
            <div className="p-12 text-center text-xs text-zinc-500 rounded-2xl border border-zinc-200 dark:border-zinc-800">
              No se encontraron modelos de Machine Learning registrados en el runtime actual.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

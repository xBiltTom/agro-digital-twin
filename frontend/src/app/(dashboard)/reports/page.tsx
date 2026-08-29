"use client";

import React, { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { SimulationRun } from "../../../types/simulation";
import {
  FileSpreadsheet,
  FileText,
  FileCode2,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Calendar,
  Layers,
  History,
  Shield,
  Sparkles
} from "lucide-react";

export default function ReportsPage() {
  const [simulations, setSimulations] = useState<SimulationRun[]>([]);
  const [selectedSimId, setSelectedSimId] = useState<string>("");
  const [history, setHistory] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [sims, hist] = await Promise.all([
        api.getSimulations(),
        api.getReportsHistory(),
      ]);
      setSimulations(sims);
      setHistory(hist);
      if (sims.length > 0 && !selectedSimId) {
        setSelectedSimId(sims[0].id);
      }
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Error cargando reportes" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDownload = async (format: "pdf" | "docx" | "xlsx") => {
    if (!selectedSimId) return;
    setDownloadingFormat(format);
    setStatusMsg(null);

    try {
      await api.downloadReport(selectedSimId, format);
      setStatusMsg({
        type: "success",
        text: `Reporte en formato ${format.toUpperCase()} generado y descargado exitosamente.`,
      });
      // Refrescar historial
      const updatedHistory = await api.getReportsHistory();
      setHistory(updatedHistory);
    } catch (err: any) {
      setStatusMsg({
        type: "error",
        text: err.message || `Error al generar el reporte ${format.toUpperCase()}`,
      });
    } finally {
      setDownloadingFormat(null);
    }
  };

  const selectedSim = simulations.find((s) => s.id === selectedSimId);

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-6 h-6 text-emerald-400" />
            <h1 className="text-xl font-bold text-zinc-100">
              Centro de Reportes Multiformato (PDF, Word, Excel)
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Exportación automatizada de balances hidrológicos SWAT, dinámica biofísica de planta y forzamientos climáticos CMIP6.
          </p>
        </div>

        {/* Simulation Selector Dropdown */}
        {simulations.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-400">Simulación:</span>
            <select
              value={selectedSimId}
              onChange={(e) => setSelectedSimId(e.target.value)}
              className="px-3.5 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 font-medium"
            >
              {simulations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.scenario?.code})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {statusMsg && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 ${
            statusMsg.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-300"
          }`}
        >
          {statusMsg.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Selected Simulation Summary Card */}
      {selectedSim && (
        <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono uppercase text-zinc-400">Experimento Seleccionado</span>
            <h3 className="text-sm font-bold text-zinc-100">{selectedSim.name}</h3>
            <span className="text-xs text-zinc-400 mt-0.5">
              Escenario: {selectedSim.scenario?.name} • Duración: {selectedSim.duration_days} días
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
            <div className="flex flex-col">
              <span className="text-[10px] text-zinc-400">Lluvia Total</span>
              <span className="text-zinc-200 font-bold">{selectedSim.summary_metrics?.total_precip_mm ?? "-"} mm</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-zinc-400">Volumen Río</span>
              <span className="text-teal-400 font-bold">{selectedSim.summary_metrics?.total_discharge_hm3 ?? "-"} hm³</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-zinc-400">Estrés CWSI</span>
              <span className="text-emerald-400 font-bold">{selectedSim.summary_metrics?.mean_cwsi ?? "-"}</span>
            </div>
          </div>
        </div>
      )}

      {/* 3 Format Download Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: PDF */}
        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-rose-500/50 transition flex flex-col justify-between shadow-xl group">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 group-hover:scale-110 transition">
                <FileText className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                PDF FORMAL
              </span>
            </div>

            <h3 className="text-base font-bold text-zinc-100 group-hover:text-rose-300 transition">
              Informe Técnico Ejecutivo (PDF)
            </h3>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Documento formal de ingeniería con membrete institucional, tablas estilizadas de balance hídrico SWAT,
              resumen de indicadores biofísicos y recomendaciones de gestión de cuenca para tomadores de decisiones.
            </p>

            <div className="mt-4 pt-4 border-t border-zinc-800/80 text-[11px] text-zinc-500 flex flex-col gap-1">
              <span>• Portada con metadatos del CMIP6</span>
              <span>• Tablas de balance de masa en suelo</span>
              <span>• Muestra diaria de los 10 primeros días</span>
            </div>
          </div>

          <button
            onClick={() => handleDownload("pdf")}
            disabled={downloadingFormat === "pdf"}
            className="mt-6 w-full py-2.5 px-4 rounded-xl bg-rose-500 hover:bg-rose-400 text-zinc-950 font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-rose-500/20 cursor-pointer disabled:opacity-50"
          >
            {downloadingFormat === "pdf" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Descargar Reporte PDF</span>
          </button>
        </div>

        {/* Card 2: Word (DOCX) */}
        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-sky-500/50 transition flex flex-col justify-between shadow-xl group">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 group-hover:scale-110 transition">
                <FileCode2 className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30">
                WORD (.DOCX)
              </span>
            </div>

            <h3 className="text-base font-bold text-zinc-100 group-hover:text-sky-300 transition">
              Documento Técnico Editable (Word)
            </h3>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Informe editable estructurado con títulos jerárquicos, tablas con formato de cuadrícula formal,
              narrativa detallada del comportamiento hidrológico bajo escenarios de cambio climático y conclusiones científicas.
            </p>

            <div className="mt-4 pt-4 border-t border-zinc-800/80 text-[11px] text-zinc-500 flex flex-col gap-1">
              <span>• Compatible con Microsoft Word y LibreOffice</span>
              <span>• Tablas con estilos y sombreados formales</span>
              <span>• Texto completamente editable</span>
            </div>
          </div>

          <button
            onClick={() => handleDownload("docx")}
            disabled={downloadingFormat === "docx"}
            className="mt-6 w-full py-2.5 px-4 rounded-xl bg-sky-500 hover:bg-sky-400 text-zinc-950 font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-sky-500/20 cursor-pointer disabled:opacity-50"
          >
            {downloadingFormat === "docx" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Descargar Documento Word</span>
          </button>
        </div>

        {/* Card 3: Excel (XLSX) */}
        <div className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-emerald-500/50 transition flex flex-col justify-between shadow-xl group">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                EXCEL (.XLSX)
              </span>
            </div>

            <h3 className="text-base font-bold text-zinc-100 group-hover:text-emerald-300 transition">
              Libro Analítico Completo (Excel)
            </h3>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Libro de cálculo multi-hoja con series temporales diarias completas (365 días), componentes
              separados para el balance SWAT, parámetros de absorción radicular de Feddes y forzamiento climático.
            </p>

            <div className="mt-4 pt-4 border-t border-zinc-800/80 text-[11px] text-zinc-500 flex flex-col gap-1">
              <span>• Pestaña 1: Resumen Ejecutivo y Metadatos</span>
              <span>• Pestaña 2: Series Diarias SWAT (Precip, Q, ET)</span>
              <span>• Pestaña 3: Fisiología de Planta (Tr, CWSI, Savia)</span>
            </div>
          </div>

          <button
            onClick={() => handleDownload("xlsx")}
            disabled={downloadingFormat === "xlsx"}
            className="mt-6 w-full py-2.5 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
          >
            {downloadingFormat === "xlsx" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            <span>Descargar Hoja de Cálculo Excel</span>
          </button>
        </div>
      </div>

      {/* Reports Audit / History Table */}
      <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800 shadow-xl flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-zinc-400" />
            <h3 className="text-xs font-semibold text-zinc-200 uppercase tracking-wide">
              Historial de Reportes Generados
            </h3>
          </div>
          <span className="text-[11px] font-mono text-zinc-500">
            {history.length} reportes registrados
          </span>
        </div>

        {history.length === 0 ? (
          <div className="py-8 text-center text-zinc-500 text-xs">
            Aún no has generado ningún reporte. Selecciona una simulación y descarga cualquiera de los 3 formatos.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-950/80 border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-3">Archivo</th>
                  <th className="py-2.5 px-3">Formato</th>
                  <th className="py-2.5 px-3">Simulación Asociada</th>
                  <th className="py-2.5 px-3">Tamaño</th>
                  <th className="py-2.5 px-3">Fecha y Hora</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {history.map((h, idx) => (
                  <tr key={h.id || idx} className="hover:bg-zinc-800/30 transition text-[11px]">
                    <td className="py-2.5 px-3 font-semibold text-zinc-200">{h.filename}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] ${
                          h.report_format === "pdf"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : h.report_format === "docx"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        }`}
                      >
                        {h.report_format?.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-zinc-400 font-sans">{h.simulation_name}</td>
                    <td className="py-2.5 px-3 text-zinc-400">
                      {h.file_size_bytes ? `${(h.file_size_bytes / 1024).toFixed(1)} KB` : "-"}
                    </td>
                    <td className="py-2.5 px-3 text-zinc-500">{h.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

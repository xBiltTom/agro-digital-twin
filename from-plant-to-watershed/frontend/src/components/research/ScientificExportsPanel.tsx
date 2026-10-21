"use client";

import { useEffect, useId, useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import type { ScientificExportCatalog, ScientificFormat, ScientificVariant } from "../../types/scientific-exports";

type Scope = "all" | "simulation" | "partitions";
const control = "min-h-10 border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";
const groupLabels = { results: "Resultados TEST", partitions: "Protocolo temporal", configuration: "Configuración experimental" };

export default function ScientificExportsPanel({ scope = "all" }: { scope?: Scope }) {
  const id = useId();
  const [open, setOpen] = useState(scope === "all");
  const [catalog, setCatalog] = useState<ScientificExportCatalog | null>(null);
  const [selected, setSelected] = useState("");
  const [variant, setVariant] = useState<ScientificVariant>("PRIMARY");
  const [preview, setPreview] = useState<{ key: string; url: string } | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);
  const [downloading, setDownloading] = useState<ScientificFormat | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!open) return;
    let disposed = false;
    api.getScientificExports().then(value => {
      if (!disposed) { setCatalog(value); setCatalogError(null); }
    }).catch((error: unknown) => {
      if (!disposed) setCatalogError(error instanceof Error ? error.message : "No se pudo cargar el catálogo de exportaciones.");
    });
    return () => { disposed = true; };
  }, [open, revision]);

  const entries = catalog?.entries.filter(entry => scope === "all" || (
    scope === "partitions" ? entry.group === "partitions" : entry.group !== "partitions")) ?? [];
  const entry = entries.find(item => item.id === selected) ?? entries[0];
  const identifier = entry?.id;
  const effectiveVariant = entry?.supports_sensitivity ? variant : "PRIMARY";
  const previewKey = `${identifier}:${effectiveVariant}:${revision}`;
  const previewUrl = preview?.key === previewKey ? preview.url : null;

  useEffect(() => {
    if (!open || !identifier) return;
    const controller = new AbortController();
    let url: string | null = null;
    api.getScientificPreview(identifier, effectiveVariant, controller.signal).then(blob => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setPreview({ key: previewKey, url });
      setPreviewError(null);
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setPreviewError(error instanceof Error ? error.message : "No se pudo generar la vista previa.");
    });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [open, identifier, effectiveVariant, previewKey]);

  const download = async (format: ScientificFormat) => {
    if (!entry) return;
    setDownloading(format);
    setMessage(null);
    try {
      await api.downloadScientificExport(entry.id, format, effectiveVariant);
      setMessage({ error: false, text: `${entry.title} se descargó en ${format.toUpperCase()}.` });
    } catch (error) {
      setMessage({ error: true, text: error instanceof Error ? error.message : "No se pudo descargar el archivo." });
    } finally { setDownloading(null); }
  };

  return <details open={open} onToggle={event => {
    const nextOpen = event.currentTarget.open;
    setOpen(nextOpen);
    if (!nextOpen) { setPreview(null); setPreviewError(null); }
  }} className="border-y border-slate-300 bg-white dark:border-slate-800 dark:bg-slate-900">
    <summary className="cursor-pointer px-4 py-4 text-sm font-semibold text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 dark:text-slate-100">
      {scope === "partitions" ? "Figuras y tablas del protocolo temporal" : "Figuras y tablas científicas"}
    </summary>
    {open && <div className="space-y-4 px-4 pb-5">
      <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-400">
        Exportaciones del experimento publicado South Fork{catalog ? ` (${catalog.experiment_id})` : ""} con el formato de las referencias del artículo.
        {scope === "simulation" && " Estos resultados corresponden al experimento publicado completo, independientemente de la corrida seleccionada."}
      </p>
      {catalogError && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{catalogError}</p>}
      {!catalog && !catalogError && <p role="status" className="text-sm text-slate-500">Cargando exportaciones…</p>}
      {entry && <>
        <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
          <div className="grid min-w-0 flex-1 gap-1 text-sm text-slate-700 dark:text-slate-300">
            <label htmlFor={`${id}-figure`}>Figura o tabla</label>
            <select id={`${id}-figure`} className={`${control} w-full`} value={entry.id} onChange={event => { setSelected(event.target.value); setPreviewError(null); setMessage(null); }}>
              {Object.entries(groupLabels).map(([group, label]) => <optgroup key={group} label={label}>
                {entries.filter(item => item.group === group).map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
              </optgroup>)}
            </select>
          </div>
          {entry.supports_sensitivity && <div className="grid min-w-0 gap-1 text-sm text-slate-700 dark:text-slate-300">
            <label htmlFor={`${id}-variant`}>Observaciones</label>
            <select id={`${id}-variant`} className={`${control} w-full`} value={variant} onChange={event => { setVariant(event.target.value as ScientificVariant); setPreviewError(null); setMessage(null); }}>
              <option value="PRIMARY">Evaluación principal</option>
              <option value="EXCLUDE_ESTIMATED">Excluir observaciones estimadas</option>
            </select>
          </div>}
        </div>
        <div className="min-h-32 overflow-x-auto border border-slate-300 bg-white p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700" role="region" aria-label="Vista previa desplazable" tabIndex={0} aria-busy={!previewUrl && !previewError}>
          {previewError ? <p role="alert" className="p-4 text-sm text-rose-700">{previewError}</p> : previewUrl ? (
            // Authenticated PNG blob; keep the publication canvas white in both themes.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt={`Vista previa de ${entry.title}`} className="h-auto w-full min-w-[720px] sm:min-w-0" />
          ) : <p role="status" className="flex items-center gap-2 p-4 text-sm text-slate-600"><Loader2 aria-hidden="true" className="h-4 w-4 motion-safe:animate-spin" />Generando vista previa…</p>}
        </div>
        <p className="text-xs text-slate-500 sm:hidden dark:text-slate-400">Desliza la vista previa horizontalmente para ver toda la figura o tabla.</p>
        <div className="flex flex-wrap items-center gap-2">
          {entry.formats.map(format => <button key={format} type="button" className={`${control} inline-flex items-center gap-2`} disabled={downloading !== null} onClick={() => void download(format)}>
            {downloading === format ? <Loader2 aria-hidden="true" className="h-4 w-4 motion-safe:animate-spin" /> : <Download aria-hidden="true" className="h-4 w-4" />}
            Descargar {format.toUpperCase()}
          </button>)}
        </div>
        <p className="max-w-3xl text-xs leading-5 text-slate-500 dark:text-slate-400">
          PNG a 300 dpi. SVG y PDF vectoriales. Las tablas incluyen CSV.
          {entry.group === "results" && " ΔRMSE = RMSE de referencia − RMSE del candidato: un valor positivo indica mejora. Los contrastes secundarios son descriptivos, sin ajuste por multiplicidad. KGE modificado y PBIAS simulado − observado."}
          {entry.group === "configuration" && entry.id === "plant-mapping" && " Contrato vegetal derivado en 2010 y congelado para este experimento; ext_co y bm_e son parámetros base sin calibrar."}
          {entry.group === "partitions" && " Las fechas y los meses corresponden al protocolo registrado, incluida la calibración física."}
        </p>
      </>}
      <button type="button" className="text-sm text-emerald-800 underline underline-offset-4 focus-visible:ring-2 focus-visible:ring-emerald-700 dark:text-emerald-300" onClick={() => { setCatalogError(null); setPreviewError(null); setRevision(value => value + 1); }}>Actualizar exportaciones</button>
      {message && <p role={message.error ? "alert" : "status"} className={`text-sm ${message.error ? "text-rose-700 dark:text-rose-300" : "text-emerald-800 dark:text-emerald-300"}`}>{message.text}</p>}
    </div>}
  </details>;
}

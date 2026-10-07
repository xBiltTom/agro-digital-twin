"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import type { ResearchReport, MonthlyPrediction } from "../../types/research";
import type { SimulationRun } from "../../types/simulation";

const labels: Record<string, string> = { A: "A · SWAT+", B: "B · SWAT+ y FSPM", C: "C · A + ML", D: "D · B + ML", AFFINE_A: "Afín A", AFFINE_B: "Afín B", CLIMATOLOGY: "Climatología" };
const colors: Record<string, string> = { A: "#64748b", B: "#059669", C: "#0284c7", D: "#e11d48", AFFINE_A: "#a16207", AFFINE_B: "#7c3aed", CLIMATOLOGY: "#6b7280" };
const control = "border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-emerald-600";
const number = (value: number | null | undefined) => value == null ? "—" : value.toFixed(3);

export default function SouthForkResearchPanel({ allowCreate = false }: { allowCreate?: boolean }) {
  const { hasAnyRole, user } = useAuth();
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sensitivity, setSensitivity] = useState(false);
  const [series, setSeries] = useState(["A", "B", "C", "D"]);
  const [year, setYear] = useState(2025);
  const [arm, setArm] = useState<"A" | "B">("B");
  const [monthlyML, setMonthlyML] = useState(true);
  const [run, setRun] = useState<SimulationRun | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [download, setDownload] = useState(false);
  const [refreshRun, setRefreshRun] = useState(0);

  const load = () => { setError(null); setRefreshRun(n => n + 1); api.getSouthForkResearch().then(setReport).catch((e: Error) => setError(e.message)); };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (allowCreate && user) { setRun(null); setRunId(localStorage.getItem(`south-fork-user-run-${user.id}`)); }
  }, [allowCreate, user]);
  useEffect(() => {
    if (!runId) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const value = await api.getSimulation(runId);
        if (disposed) return;
        setRun(value);
        if (["PENDING", "RUNNING"].includes(value.status) || (value.status === "COMPLETED" && !value.ml_result)) timer = setTimeout(poll, 10000);
      } catch (e) { if (!disposed) setError(e instanceof Error ? e.message : "No se pudo consultar la ejecución"); }
    };
    void poll();
    return () => { disposed = true; clearTimeout(timer); };
  }, [runId, refreshRun]);

  const create = async () => {
    setBusy(true); setError(null);
    try {
      const value = await api.createSouthForkRun({ year, arm, monthly_ml: monthlyML });
      setRun(value); setRunId(value.id); if (user) localStorage.setItem(`south-fork-user-run-${user.id}`, value.id);
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo iniciar la ejecución"); }
    finally { setBusy(false); }
  };
  const save = async (action: () => Promise<void>) => {
    setDownload(true); setError(null);
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "Descarga fallida"); }
    finally { setDownload(false); }
  };
  const evaluation = sensitivity ? report?.sensitivity : report?.primary;
  const contrast = evaluation?.contrasts.D_vs_A;
  const chart = new Map<string, Record<string, string | number | null>>();
  for (const row of report?.predictions ?? []) {
    if (row.variant !== (sensitivity ? "EXCLUDE_ESTIMATED" : "PRIMARY")) continue;
    const point = chart.get(row.month) ?? { month: row.month, Observado: row.observed };
    point[row.series] = row.eligible ? row.predicted : null;
    chart.set(row.month, point);
  }
  const ml = run?.ml_result as { status?: string; message?: string; predictions?: MonthlyPrediction[] } | null | undefined;
  const running = !!run && (["PENDING", "RUNNING"].includes(run.status) || (run.status === "COMPLETED" && !ml));
  return <section className="space-y-5 border-b border-slate-300 bg-white p-5 text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100" aria-label="Experimento actual South Fork">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-xs uppercase tracking-widest text-emerald-700 dark:text-emerald-400">Experimento actual · South Fork</p>
        <h2 className="mt-1 font-serif text-2xl">Caudal mensual · evaluación 2021–2025</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-600 dark:text-slate-400">Comparación reservada de SWAT+, acoplamiento FSPM y corrección ML. El visor reproduce estados físicos diarios; la corrección mensual es retrospectiva.</p></div>
      <button className={control} onClick={load}>Actualizar</button>
    </header>
    {error && <p role="alert" className="border-l-4 border-rose-700 px-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
    {!report && !error && <p role="status">Cargando evidencia…</p>}
    {report && <>
      <div className="border-l-4 border-amber-600 pl-4">
        <h3 className="font-semibold">H1 no respaldada en el contraste principal D frente a A</h3>
        <p className="mt-1 text-sm">Reducción de RMSE: {number(contrast?.rmse_reduction_m3s)} m³/s · IC 95% [{number(contrast?.ci95_reduction_m3s[0])}, {number(contrast?.ci95_reduction_m3s[1])}]. Un valor positivo favorece D. El intervalo incluye cero.</p>
        <p className="mt-1 text-xs text-slate-500">Referencia física exploratoria: no superó el criterio de sesgo de calibración. No se ha validado la fisiología ni la conservación del balance por ML.</p>
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={sensitivity} onChange={e => setSensitivity(e.target.checked)} />Excluir observaciones estimadas aprobadas (sensibilidad)</label>
      <p className="text-xs text-slate-500">{evaluation?.eligible_months} de {evaluation?.calendar_months} meses elegibles. Principal: {report.observation_qc.accepted_days} días aprobados, {report.observation_qc.approved_estimated_days} estimados. La sensibilidad conserva los huecos y cambia la composición estacional.</p>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Métricas mensuales del experimento</caption><thead><tr className="border-b border-slate-300"><th className="py-2">Variante</th>{["RMSE (m³/s)", "MAE (m³/s)", "NSE", "KGE", "PBIAS (%)"].map(x => <th key={x} className="px-3 py-2">{x}</th>)}</tr></thead><tbody>{Object.entries(evaluation?.metrics ?? {}).map(([key, metrics]) => <tr key={key} className="border-b border-slate-200 dark:border-slate-800"><th className="py-2 font-normal">{labels[key] ?? key}</th>{["rmse", "mae", "nse", "kge", "pbias"].map(x => <td key={x} className="px-3 py-2 font-mono">{number(metrics[x]?.value)}</td>)}</tr>)}</tbody></table></div>
      <fieldset className="flex flex-wrap gap-4 text-xs"><legend className="mb-2 text-sm">Series del gráfico · m³/s</legend>{Object.keys(labels).map(key => <label key={key} className="flex items-center gap-1"><input type="checkbox" checked={series.includes(key)} onChange={() => setSeries(s => s.includes(key) ? s.filter(x => x !== key) : [...s, key])} />{labels[key]}</label>)}</fieldset>
      <div className="h-72 w-full" role="img" aria-label="Comparación mensual de caudal observado y variantes seleccionadas"><ResponsiveContainer width="100%" height="100%"><LineChart data={[...chart.values()]}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month" minTickGap={45} /><YAxis width={45} /><Tooltip /><Legend /><Line dataKey="Observado" stroke="#d97706" strokeWidth={2} dot={false} connectNulls={false} />{series.map(key => <Line key={key} dataKey={key} name={labels[key]} stroke={colors[key]} dot={false} connectNulls={false} />)}</LineChart></ResponsiveContainer></div>
      <div className="flex flex-wrap gap-2">{(["report", "predictions", "manuscript", "paper"] as const).map(key => <button key={key} className={control} disabled={download || ((key === "paper" || key === "manuscript") && !report.paper_available)} onClick={() => void save(() => api.downloadResearch(key))}>{ { report: "Informe JSON", predictions: "Comparación CSV", manuscript: "Borrador del paper", paper: "Paquete del paper" }[key]}</button>)}</div>
      <div className="flex flex-wrap items-center gap-3 text-sm"><span>Corridas físicas disponibles:</span>{report.publications.map(pair => <span key={pair.year} className="flex gap-2">{pair.year}{(["A", "B"] as const).map(key => pair[key] && <Link className="underline underline-offset-4" key={key} href={`/twin-3d?simId=${encodeURIComponent(pair[key]!)}`}>Visor {key}</Link>)}</span>)}{report.publications.every(x => !x.A && !x.B) && <span className="text-slate-500">La evidencia agregada está disponible. Inicia una corrida propia para acceder a su visor.</span>}</div>
    </>}
    {allowCreate && hasAnyRole(["SUPERADMIN", "ADMIN_CIENTIFICO", "INVESTIGADOR_HIDROLOGO"]) && <div className="space-y-3 border-t border-slate-300 pt-5 dark:border-slate-700">
      <h3 className="font-serif text-xl">Ejecutar una reproducción propia</h3><p className="text-sm text-slate-500">South Fork con parámetros congelados, clima histórico y calentamiento desde 2000. Puede tardar varios minutos; puedes salir y volver a esta página. Esta ejecución no cambia la decisión de H1.</p>
      <div className="flex flex-wrap items-end gap-4"><label className="grid gap-1 text-sm">Año<select className={control} value={year} onChange={e => setYear(Number(e.target.value))}>{[2021, 2022, 2023, 2024, 2025].map(x => <option key={x}>{x}</option>)}</select></label><label className="grid gap-1 text-sm">Sistema<select className={control} value={arm} onChange={e => setArm(e.target.value as "A" | "B")}><option value="A">A · SWAT+</option><option value="B">B · SWAT+ y FSPM</option></select></label><label className="flex items-center gap-2 py-2 text-sm"><input type="checkbox" checked={monthlyML} onChange={e => setMonthlyML(e.target.checked)} />Añadir ML mensual {arm === "A" ? "C" : "D"}</label><button className={`${control} bg-emerald-700 text-white dark:bg-emerald-700`} disabled={busy || running} onClick={() => void create()}>{busy ? "Iniciando…" : "Ejecutar"}</button></div>
      {run && <div aria-live="polite" className="space-y-2 text-sm"><p>{run.name} · {running ? "En proceso" : run.status === "COMPLETED" ? "Física completada" : run.status === "FAILED" ? "Ejecución fallida" : run.status}</p>{run.status === "FAILED" && <p role="alert">{JSON.stringify(run.error ?? "Consulta la ejecución para ver el detalle")}</p>}{ml?.status === "FAILED" && <p role="alert">La física está disponible; falló el cálculo mensual: {ml.message}</p>}{run.status === "COMPLETED" && <div className="flex flex-wrap gap-3"><Link className="underline" href={`/twin-3d?simId=${run.id}`}>Abrir visor diario</Link><button className={control} disabled={download} onClick={() => void save(() => api.downloadSwatResults(run.id, "csv"))}>Física diaria CSV</button>{!!ml?.predictions?.length && <button className={control} disabled={download} onClick={() => void save(() => api.downloadMonthlyResearch(run.id))}>ML mensual CSV</button>}</div>}{ml?.predictions && <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="py-2 text-left">Caudal mensual de la reproducción (m³/s)</caption><thead><tr><th>Mes</th><th>Observado</th><th>Físico</th><th>ML</th></tr></thead><tbody>{ml.predictions.map(row => <tr key={row.month} className="border-t border-slate-200 dark:border-slate-800"><th className="py-1 font-normal">{row.month}</th><td>{number(row.observed_streamflow_m3s)}</td><td>{number(row.physical_streamflow_m3s)}</td><td>{number(row.predicted_streamflow_m3s)}</td></tr>)}</tbody></table></div>}</div>}
    </div>}
  </section>;
}

"use client";

import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Sprout, Waves } from "lucide-react";
import type { HistoricalChartPoint } from "../../lib/historical-charts";

interface Props {
  points: HistoricalChartPoint[];
  kind: "SWAT_PLUS" | "SIMPLIFIED";
  frequency: string | null;
  truncated: boolean;
}

export default function HistoricalTwinCharts({ points, kind, frequency, truncated }: Props) {
  const swat = kind === "SWAT_PLUS";
  if (!points.length) return <div className="rounded-xl border border-zinc-700 p-5 text-sm text-zinc-500">
    Esta corrida no tiene resultados históricos graficables.
  </div>;

  return <section className="space-y-4" aria-label="Gráficos históricos sin contrato temporal">
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
      <strong>Gráficos históricos · sin artefacto twin-playback-v1.</strong> Se muestran los resultados persistidos de esta corrida.
      No se usan para reconstruir estados meteorológicos o vegetales del visor 3D.
      {swat && " SWAT+ no proporciona aquí una serie de precipitación recuperable ni una trayectoria FSPM diaria."}
      {!swat && " Las variables FSPM históricas conservan su semántica original; este visor no reinterpreta ni corrige sus valores."}
      {truncated && " La API histórica permite consultar solo los primeros 1000 resultados; esta serie está truncada."}
      <span className="block mt-1">{frequency ? `Frecuencia declarada: ${frequency}.` : "Frecuencia histórica no declarada."} Registros mostrados: {points.length}.</span>
    </div>
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900/60">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Waves className="h-4 w-4 text-cyan-500" /> Caudal y {swat ? "escorrentía SWAT+" : "forcing almacenado"}</h2>
        <div className="h-64"><ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points}><CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis yAxisId="flow" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="water" orientation="right" tick={{ fontSize: 10 }} /><Tooltip /><Legend />
            <Line yAxisId="flow" dataKey="streamflow" name="Caudal modelado (m³/s)" stroke="#14b8a6" dot={false} connectNulls={false} />
            {swat ? <Bar yAxisId="water" dataKey="runoff" name="Escorrentía SWAT+ (mm/periodo)" fill="#38bdf8" /> :
              <Bar yAxisId="water" dataKey="precipitation" name="Precipitación almacenada (mm/día)" fill="#38bdf8" />}
          </ComposedChart>
        </ResponsiveContainer></div>
      </div>
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900/60">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Sprout className="h-4 w-4 text-emerald-500" /> {swat ? "Balance hídrico SWAT+" : "Fisiología histórica simplificada"}</h2>
        <div className="h-64"><ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points}><CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="period" tick={{ fontSize: 10 }} /><YAxis yAxisId="left" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} /><Tooltip /><Legend />
            {swat ? <>
              <Line yAxisId="left" dataKey="evapotranspiration" name="ET SWAT+ (mm/periodo)" stroke="#22c55e" dot={false} connectNulls={false} />
              <Line yAxisId="left" dataKey="percolation" name="Percolación SWAT+ (mm/periodo)" stroke="#a855f7" dot={false} connectNulls={false} />
              <Line yAxisId="right" dataKey="soilWater" name="Agua almacenada (mm)" stroke="#f59e0b" dot={false} connectNulls={false} />
            </> : <>
              <Line yAxisId="left" dataKey="stress" name="Estrés FSPM histórico (fracción)" stroke="#f59e0b" dot={false} connectNulls={false} />
              <Line yAxisId="right" dataKey="transpiration" name="Transpiración FSPM histórica (mm/día)" stroke="#06b6d4" dot={false} connectNulls={false} />
            </>}
          </ComposedChart>
        </ResponsiveContainer></div>
      </div>
    </div>
  </section>;
}

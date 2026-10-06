"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SimulationRun } from "../../types/simulation";

export default function SwatMeteorologyDiagnosticPanel({ simulation }: { simulation: SimulationRun }) {
  const audit = simulation.validation?.meteorology_diagnostic;
  if (!audit) return null;
  const coverage = audit.weather_source.coverage;
  const verified = ["VERIFIED_ARCHIVED_GRIDMET_CONVERSIONS", "VERIFIED_GRIDMET_WITH_INTERPOLATED_YEAR_END_DAYS"].includes(audit.weather_source.status);
  const interpolatedDates = audit.weather_source.runtime_coverage.interpolated_dates;
  const cacheConflicts = audit.weather_source.source_cache_consistency;

  return (
    <section aria-label="Meteorología y evapotranspiración" className="space-y-4 border border-slate-200 p-4 dark:border-slate-800">
      <div>
        <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Meteorología y evapotranspiración</h4>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
          {verified ? "Procedencia gridMET documentada mediante reconstrucción de archivos y conversiones." : "El archivo gridMET presenta diferencias que requieren revisión antes de calibrar."}
          {" "}{coverage.stations} puntos · {audit.forcing_aggregation.hru_count} HRU · archivos {coverage.start} a {coverage.end}.
          {" "}Comparación de {audit.period.join(" a ")}.
        </p>
      </div>
      {interpolatedDates.length > 0 && <p className="border-l-2 border-amber-500 bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
        El warm-up usa {interpolatedDates.length} fechas interpoladas: {interpolatedDates.join(", ")}.
        {" "}Corresponden al 31 de diciembre de años bisiestos ausente en las descargas originales. La auditoría conserva esos inputs y compara sus valores con nuevas descargas de gridMET.
      </p>}
      {cacheConflicts.status === "CONFLICTS_FOUND" && <p className="border-l-2 border-amber-500 bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
        Hay {cacheConflicts.conflicting_station_variable_years} comparaciones de punto, variable y año con valores distintos entre descargas originales que cubren la misma celda.
        {" "}El informe JSON incluye los archivos implicados y nuevas descargas de precipitación de 2011 y viento de 2015.
      </p>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-700 dark:text-slate-300">
          <caption className="mb-2 text-left font-medium">Totales anuales · mm</caption>
          <thead><tr className="border-b border-slate-200 dark:border-slate-800">
            <th className="py-2">Magnitud</th><th className="px-3">SWAT+</th><th className="px-3">gridMET</th><th className="px-3">TerraClimate v1.1</th>
          </tr></thead>
          <tbody>
            <tr><th className="py-2 font-normal">ET real modelada</th><td className="px-3">{audit.annual_mm.swat_et_mm.toFixed(1)}</td><td className="px-3">—</td><td className="px-3">{audit.annual_mm.terraclimate_aet_mm.toFixed(1)}</td></tr>
            <tr><th className="py-2 font-normal">PET / ET de referencia</th><td className="px-3">{audit.annual_mm.swat_pet_mm.toFixed(1)}</td><td className="px-3">{audit.annual_mm.gridmet_etr_mm.toFixed(1)} (alfalfa)</td><td className="px-3">{audit.annual_mm.terraclimate_pet_mm.toFixed(1)}</td></tr>
          </tbody>
        </table>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {([
          { title: "ET real modelada · mm/mes", model: "swat_et_mm", reference: "terraclimate_aet_mm" },
          { title: "PET / ET de referencia · mm/mes", model: "swat_pet_mm", reference: "terraclimate_pet_mm" },
        ] as const).map((chart) => (
          <div key={chart.model}>
            <h5 className="mb-2 text-xs font-medium text-slate-700 dark:text-slate-300">{chart.title}</h5>
            <div className="h-56" role="img" aria-label={chart.title}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={audit.monthly}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line dataKey={chart.model} name="SWAT+" stroke="#0d9488" dot={false} />
                  <Line dataKey={chart.reference} name="TerraClimate modelado" stroke="#475569" dot={false} />
                  {chart.model === "swat_pet_mm" && <Line dataKey="gridmet_etr_mm" name="gridMET ETr" stroke="#b45309" dot={false} />}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        TerraClimate es una comparación con otro modelo; su ET no es una medición. gridMET ETr comparte el proveedor meteorológico de esta corrida.
        {" "}Los productos se muestrean en los puntos del forcing y se ponderan por área de HRU. Las diferencias de referencia vegetal y método limitan la comparación de PET.
      </p>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        Lluvia ponderada por HRU: {audit.forcing_aggregation.area_weighted_annual_precip_mm.toFixed(2)} mm.
        {" "}El promedio antiguo de estaciones difiere en {audit.forcing_aggregation.equal_minus_area_weighted_precip_mm.toFixed(2)} mm.
        {" "}El playback histórico conserva su agregado original. Puedes descargar la auditoría completa en el informe JSON de esta corrida.
      </p>
    </section>
  );
}

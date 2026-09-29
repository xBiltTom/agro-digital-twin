"use client";

import { Grid, Maximize2, Mountain, Sprout } from "lucide-react";
import MultiScaleViewer3D, { type ScaleMode } from "./MultiScaleViewer3D";
import type { SimulationRun } from "../../types/simulation";

/** Historical exploration has the original 3D navigation, but no fabricated time state. */
export default function HistoricalContext3D({ simulation, scaleMode, onChangeScale, onToggleFullscreen }: {
  simulation: SimulationRun;
  scaleMode: ScaleMode;
  onChangeScale: (mode: ScaleMode) => void;
  onToggleFullscreen: () => void;
}) {
  const configuredBasin = simulation.effective_config?.watershed_id;
  const stationId = simulation.station_id === "05451210" ||
    (typeof configuredBasin === "string" && /05451210|south.?fork/i.test(configuredBasin))
      ? "05451210" : simulation.station_id;
  const scales: [ScaleMode, string, typeof Mountain][] = [
    ["MACRO", "Cuenca", Mountain], ["MESO", "Campo", Grid], ["MICRO", "Planta", Sprout],
  ];
  return <div className="relative h-full w-full bg-zinc-950">
    <MultiScaleViewer3D scaleMode={scaleMode} onChangeScale={onChangeScale} scene={null}
      stationId={stationId} showHydrologyFlow={false} showScientificLabels={true} />
    <div className="pointer-events-none absolute left-4 right-4 top-4 z-20 flex flex-wrap justify-between gap-3">
      <div className="pointer-events-auto max-w-lg rounded-xl border border-amber-500/40 bg-zinc-950/90 p-3 text-xs text-zinc-200 shadow-xl">
        <strong className="text-amber-300">Exploración 3D histórica · representación ilustrativa</strong>
        <p className="mt-1">Esta corrida no tiene trayectoria twin-playback-v1. La cuenca, parcela y planta son referencias visuales; no muestran crecimiento, lluvia, estrés ni caudal de una fecha. Los gráficos históricos se conservan debajo.</p>
      </div>
      <button onClick={onToggleFullscreen} className="pointer-events-auto h-fit rounded-lg border border-zinc-600 bg-zinc-950/90 px-3 py-2 text-xs text-zinc-100">
        <Maximize2 className="inline h-3.5 w-3.5" /> Pantalla completa
      </button>
    </div>
    <div className="pointer-events-auto absolute bottom-4 left-4 z-20 flex gap-1 rounded-xl border border-zinc-700 bg-zinc-950/90 p-1 text-xs shadow-xl">
      {scales.map(([mode, label, Icon]) => <button key={mode} onClick={() => onChangeScale(mode)}
        className={`flex items-center gap-1 rounded-lg px-3 py-2 ${scaleMode === mode ? "bg-cyan-600/40 text-cyan-200" : "text-zinc-400 hover:text-white"}`}>
        <Icon className="h-4 w-4" />{label}</button>)}
    </div>
  </div>;
}

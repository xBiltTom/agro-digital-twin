"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sky } from "@react-three/drei";
import WatershedMesh3D from "./WatershedMesh3D";
import type { SimulationRun } from "../../types/simulation";

export default function HistoricalContext3D({ simulation, onToggleFullscreen }: {
  simulation: SimulationRun;
  onToggleFullscreen: () => void;
}) {
  const configuredBasin = simulation.effective_config?.watershed_id;
  const southFork = simulation.station_id === "05451210" ||
    (typeof configuredBasin === "string" && /05451210|south.?fork/i.test(configuredBasin));

  return <div className="relative h-full w-full bg-zinc-950">
    <Canvas shadows camera={{ position: [0, 36, 42], fov: 44 }}>
      <Sky distance={450000} sunPosition={[55, 45, 50]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[40, 50, 30]} intensity={2} castShadow />
      <OrbitControls enableDamping minDistance={8} maxDistance={85} maxPolarAngle={Math.PI / 2.02} />
      {southFork ? <WatershedMesh3D
        streamflowM3s={null} precipMm={null} rainEffectMm={null}
        precipitationUnit="mm" periodLabel="Sin reproducción temporal"
        stationId={simulation.station_id} evidenceType="NOT_AVAILABLE"
        showHydrologyFlow={false} showScientificLabels={false} /> : <mesh receiveShadow rotation-x={-Math.PI / 2}>
        <planeGeometry args={[45, 35]} />
        <meshStandardMaterial color="#294335" roughness={0.95} />
      </mesh>}
    </Canvas>
    <div className="pointer-events-none absolute left-4 right-4 top-4 flex justify-between gap-3">
      <div className="max-w-lg rounded-xl border border-amber-500/40 bg-zinc-950/90 p-3 text-xs text-zinc-200 shadow-xl">
        <strong className="text-amber-300">Contexto 3D estático · sin reproducción científica</strong>
        <p className="mt-1">Esta corrida no tiene trayectoria twin-playback-v1. El relieve es ilustrativo; no se muestran lluvia, cultivo ni caudal como estados de la simulación. Sus gráficos históricos están debajo.</p>
      </div>
      <button onClick={onToggleFullscreen} className="pointer-events-auto h-fit rounded-lg border border-zinc-600 bg-zinc-950/90 px-3 py-2 text-xs text-zinc-100">
        Pantalla completa
      </button>
    </div>
  </div>;
}

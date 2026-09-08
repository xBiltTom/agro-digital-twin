"use client";

import React, { useMemo } from "react";
import { Html } from "@react-three/drei";

export interface PlantSample3D { plant_id: number; x_m: number; y_m: number; lai: number; stress: number; root_depth_cm?: number; }
interface FieldPlotMesh3DProps { soilMoistureVol: number; cwsiStress: number; plantSample: PlantSample3D[]; plantCount?: number; onSelectPlant: () => void; }

function MaizeStand({ plant }: { plant: PlantSample3D }) {
  const height = 0.75 + Math.min(0.45, plant.lai * 0.11);
  const leaf = plant.stress < 0.45 ? "#5a9e45" : "#b69142";
  return <group position={[plant.x_m, 0, plant.y_m]}><mesh castShadow position={[0, height / 2, 0]}><cylinderGeometry args={[0.018, 0.026, height, 7]} /><meshStandardMaterial color="#547c31" /></mesh>{[0.28, 0.48, 0.67].map((y, i) => <group key={i} position={[0, height * y, 0]} rotation-y={plant.plant_id * 0.7 + i * 2.1}><mesh position={[0.22, 0.025, 0]} rotation-z={-0.35} castShadow><planeGeometry args={[0.52 - i * 0.05, 0.09]} /><meshStandardMaterial color={leaf} side={2} /></mesh></group>)}</group>;
}

export default function FieldPlotMesh3D({ soilMoistureVol, cwsiStress, plantSample, plantCount = 1000, onSelectPlant }: FieldPlotMesh3DProps) {
  const plants = useMemo(() => {
    if (!plantSample.length) return [];
    const maxX = Math.max(...plantSample.map((p) => p.x_m), 1);
    const maxY = Math.max(...plantSample.map((p) => p.y_m), 1);
    return plantSample.map((p) => ({ ...p, x_m: p.x_m / maxX * 20 - 10, y_m: p.y_m / maxY * 15 - 7.5 }));
  }, [plantSample]);
  const soil = soilMoistureVol > 0.25 ? "#765536" : "#8c5937";
  return <group position={[0, -0.1, 0]} onClick={onSelectPlant}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}><planeGeometry args={[24, 19, 20, 20]} /><meshStandardMaterial color={soil} roughness={0.98} /></mesh>
    {[...Array(9)].map((_, i) => <mesh key={i} rotation-x={-Math.PI / 2} position={[0, 0.008, -7.7 + i * 1.9]}><planeGeometry args={[23, 0.12]} /><meshStandardMaterial color="#4b3327" roughness={1} /></mesh>)}
    {plants.map((plant) => <MaizeStand key={plant.plant_id} plant={plant} />)}
    {!plants.length && <Html position={[0, 1.4, 0]} center><div className="rounded-md border border-amber-300/30 bg-slate-950/85 px-3 py-2 font-mono text-[10px] text-amber-200">La corrida elegida no contiene una muestra de plantas.</div></Html>}
    <Html position={[-10.5, 1.8, -7.5]} distanceFactor={13}><div className="w-60 rounded-lg border border-emerald-300/35 bg-slate-950/85 p-3 font-mono text-[10px] text-slate-200 shadow-xl backdrop-blur"><div className="font-bold text-emerald-300">Campo de maíz · escala meso</div><div className="mt-1">Muestra visual: {plants.length} de n={plantCount.toLocaleString()} plantas simuladas</div><div className="text-slate-400">Humedad {soilMoistureVol.toFixed(3)} · estrés medio {cwsiStress.toFixed(2)}</div><div className="mt-1 text-cyan-300">Clic para inspeccionar una planta</div></div></Html>
  </group>;
}

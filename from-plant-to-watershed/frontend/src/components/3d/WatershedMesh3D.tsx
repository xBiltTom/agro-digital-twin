"use client";

import React from "react";
import { Html, Line } from "@react-three/drei";

interface HruSummary { hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string; }
interface WatershedMesh3DProps { streamflowM3s: number; precipMm: number; soilMoistureVol: number; hruAggregates?: { hrus?: HruSummary[] }; onSelectSubbasin: () => void; }
const tileColors = ["#6f9c4d", "#c2a558", "#88a85c"];

export default function WatershedMesh3D({ streamflowM3s, precipMm, soilMoistureVol, hruAggregates, onSelectSubbasin }: WatershedMesh3DProps) {
  const hrus = hruAggregates?.hrus?.slice(0, 3) ?? [];
  return <group position={[0, -0.3, 0]} onClick={onSelectSubbasin}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}><planeGeometry args={[48, 34]} /><meshStandardMaterial color="#466143" roughness={0.95} /></mesh>
    {[-12, 0, 12].map((x, i) => <group key={x} position={[x, 0.02, 0]}><mesh rotation-x={-Math.PI / 2} receiveShadow><planeGeometry args={[11.4, 29.5]} /><meshStandardMaterial color={tileColors[i]} roughness={0.9} /></mesh>{[...Array(7)].map((_, row) => <mesh key={row} rotation-x={-Math.PI / 2} position={[0, 0.012, -11 + row * 3.65]}><planeGeometry args={[10.8, 0.1]} /><meshStandardMaterial color="#526c36" /></mesh>)}</group>)}
    <Line points={[[-22, 0.08, 9], [-12, 0.09, 5], [-5, 0.1, 2], [4, 0.12, -3], [14, 0.11, -8], [22, 0.1, -12]]} color="#46a8d7" lineWidth={3.2} />
    <mesh position={[20.5, 0.35, -11.5]}><cylinderGeometry args={[0.35, 0.35, 0.65, 16]} /><meshStandardMaterial color="#dce9ee" metalness={0.35} roughness={0.4} /></mesh>
    <Html position={[-21, 2.3, 12]} distanceFactor={17}><div className="w-72 rounded-lg border border-cyan-300/35 bg-slate-950/85 p-3 font-mono text-[10px] text-slate-100 shadow-xl backdrop-blur"><div className="font-bold text-cyan-300">Cuenca agrícola del Corn Belt · escala macro</div><div className="mt-1">Forzantes: precipitación {precipMm.toFixed(1)} mm · humedad {soilMoistureVol.toFixed(3)}</div><div>Caudal simulado: {streamflowM3s.toFixed(2)} m³/s · referencia USGS</div><div className="mt-1 text-amber-200">HRU: proxy de acoplamiento, no una ejecución SWAT+</div></div></Html>
    {hrus.map((hru, index) => <Html key={hru.hru_id ?? index} position={[-12 + index * 12, 1.2, 1]} center distanceFactor={18}><div className="rounded border border-white/20 bg-slate-950/75 px-2 py-1 font-mono text-[9px] text-white">HRU {hru.hru_number ?? index + 1} · {((hru.area_fraction ?? 0) * 100).toFixed(0)}% · {hru.crop ?? "proxy"}</div></Html>)}
    <Html position={[20.5, 1.1, -11.5]} center distanceFactor={17}><div className="font-mono text-[9px] text-cyan-100">USGS gauge</div></Html>
  </group>;
}

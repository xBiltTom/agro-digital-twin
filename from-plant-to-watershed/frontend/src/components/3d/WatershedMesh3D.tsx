"use client";

import React, { useMemo } from "react";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

interface HruSummary { hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string; }
interface WatershedMesh3DProps { streamflowM3s: number; precipMm: number; soilMoistureVol: number; hruAggregates?: { hrus?: HruSummary[] }; onSelectSubbasin: () => void; }

function RollingTerrain() {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(52, 38, 70, 50);
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i); const y = pos.getY(i);
      const elevation = .32 * Math.sin(x * .24) * Math.cos(y * .20) + .15 * Math.sin(x * .57 + y * .16) - .12 * Math.exp(-(x * x + y * y) / 130);
      pos.setZ(i, elevation);
    }
    geo.computeVertexNormals();
    return geo;
  }, []);
  return <mesh geometry={geometry} rotation-x={-Math.PI / 2} receiveShadow><meshStandardMaterial color="#405f38" roughness={.98} /></mesh>;
}

function FieldPatch({ position, size, color, rotation = 0 }: { position: [number, number, number]; size: [number, number]; color: string; rotation?: number }) {
  const rows = Math.max(3, Math.round(size[1] / 1.3));
  return <group position={position} rotation-y={rotation}><mesh rotation-x={-Math.PI / 2} receiveShadow><planeGeometry args={size} /><meshStandardMaterial color={color} roughness={.92} /></mesh>{Array.from({ length: rows }, (_, row) => <mesh key={row} rotation-x={-Math.PI / 2} position={[0, .018, -size[1] / 2 + .55 + row * (size[1] - 1.1) / Math.max(1, rows - 1)]}><planeGeometry args={[size[0] * .96, .075]} /><meshStandardMaterial color="#314e2e" /></mesh>)}</group>;
}

function Shelterbelt({ x, z, length, rotation = 0 }: { x: number; z: number; length: number; rotation?: number }) {
  return <group position={[x, .18, z]} rotation-y={rotation}>{Array.from({ length }, (_, tree) => <group key={tree} position={[tree * .62 - length * .31, 0, 0]}><mesh castShadow position={[0, .27, 0]}><cylinderGeometry args={[.035, .055, .54, 7]} /><meshStandardMaterial color="#5e4127" /></mesh><mesh castShadow position={[0, .65, 0]}><coneGeometry args={[.27, .62, 8]} /><meshStandardMaterial color="#274f2e" /></mesh></group>)}</group>;
}

export default function WatershedMesh3D({ streamflowM3s, precipMm, soilMoistureVol, hruAggregates, onSelectSubbasin }: WatershedMesh3DProps) {
  const hrus = hruAggregates?.hrus?.slice(0, 3) ?? [];
  const riverWidth = Math.min(.42, .12 + streamflowM3s / 70);
  return <group position={[0, -.36, 0]} onClick={onSelectSubbasin}>
    <RollingTerrain />
    {/* Deliberately low-relief Midwestern catchment: land-cover mosaic above, not fabricated high mountains. */}
    <FieldPatch position={[-12, .14, 4]} size={[13, 15]} color="#688f3f" rotation={-.12} />
    <FieldPatch position={[1, .16, 7]} size={[11, 12]} color="#a49a4f" rotation={.08} />
    <FieldPatch position={[13, .13, 3]} size={[12, 16]} color="#567d3b" rotation={-.18} />
    <FieldPatch position={[-10, .13, -10]} size={[15, 11]} color="#7e8e46" rotation={.14} />
    <FieldPatch position={[7, .15, -10]} size={[16, 10]} color="#638d47" rotation={-.09} />
    <Shelterbelt x={-17} z={9} length={16} rotation={-.12} /><Shelterbelt x={11} z={11} length={12} rotation={.08} /><Shelterbelt x={-3} z={-14} length={15} rotation={-.09} />
    <Line points={[[-23, .33, 12], [-17, .26, 8], [-11, .18, 5], [-5, .12, 2], [2, .08, -2], [8, .04, -6], [15, -.03, -9], [23, -.08, -13]]} color="#4fc3e8" lineWidth={riverWidth * 10} transparent opacity={.94} />
    <Line points={[[-18, .25, -13], [-13, .20, -7], [-8, .15, -3], [-5, .12, 2]]} color="#67c6e8" lineWidth={1.3} transparent opacity={.75} />
    <Line points={[[10, .16, 14], [7, .12, 9], [3, .10, 5], [2, .08, -2]]} color="#67c6e8" lineWidth={1.1} transparent opacity={.7} />
    <mesh rotation-x={-Math.PI / 2} position={[20.2, -.01, -12.1]}><circleGeometry args={[.46, 24]} /><meshStandardMaterial color="#f44d59" emissive="#5f121d" emissiveIntensity={.6} /></mesh>
    <mesh position={[20.2, .35, -12.1]}><cylinderGeometry args={[.22, .22, .67, 14]} /><meshStandardMaterial color="#d8e4e8" metalness={.42} roughness={.35} /></mesh>
    <Html position={[-21, 2.4, 13]} distanceFactor={17}><div className="w-72 rounded-xl border border-cyan-300/35 bg-slate-950/84 p-3 font-mono text-[10px] text-slate-100 shadow-2xl backdrop-blur"><div className="font-bold text-cyan-300">Corn Belt watershed · escala macro</div><div className="mt-1">P {precipMm.toFixed(1)} mm · θ {soilMoistureVol.toFixed(3)} · Q {streamflowM3s.toFixed(2)} m³/s</div><div className="mt-1 text-slate-400">Mosaico agrícola y drenaje representados para explorar agregados persistidos.</div><div className="mt-1 text-amber-200">HRU proxy: no una ejecución SWAT+.</div></div></Html>
    {hrus.map((hru, index) => <Html key={hru.hru_id ?? index} position={[[-12, 1, 13][index], 1.1, [4, 7, 3][index]]} center distanceFactor={18}><div className="rounded border border-white/25 bg-slate-950/76 px-2 py-1 font-mono text-[9px] text-white">HRU {hru.hru_number ?? index + 1} · {((hru.area_fraction ?? 0) * 100).toFixed(0)}% · {hru.crop ?? "proxy"}</div></Html>)}
    <Html position={[20.2, 1.2, -12.1]} center distanceFactor={17}><div className="rounded bg-slate-950/75 px-1.5 py-1 font-mono text-[9px] text-cyan-100">USGS gauge</div></Html>
  </group>;
}

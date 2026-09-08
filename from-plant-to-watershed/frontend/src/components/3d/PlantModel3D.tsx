"use client";

import React, { useMemo } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";

interface PlantModel3DProps {
  transpirationMm: number;
  cwsiStress: number;
  sapFlowVelocityCmh: number;
  soilMoistureVol: number;
  lai?: number;
  rootDepthCm?: number;
}

/** Botanical maize rendering driven by the persisted simplified plant state. */
export default function PlantModel3D({ transpirationMm, cwsiStress, sapFlowVelocityCmh, soilMoistureVol, lai = 3.4, rootDepthCm = 105 }: PlantModel3DProps) {
  const healthy = cwsiStress < 0.45;
  const leafColor = healthy ? "#4d9b4a" : "#b4943c";
  const height = 2.25 + Math.min(1.1, lai * 0.22);
  const nodes = useMemo(() => Array.from({ length: 10 }, (_, i) => i), []);
  const roots = useMemo(() => Array.from({ length: 18 }, (_, i) => i), []);
  const soilColor = soilMoistureVol > 0.25 ? "#5e4430" : "#7a5132";

  return (
    <group position={[0, -1.9, 0]}>
      <mesh receiveShadow rotation-x={-Math.PI / 2}><circleGeometry args={[3.7, 64]} /><meshStandardMaterial color={soilColor} roughness={0.95} /></mesh>
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, -0.025, 0]}><ringGeometry args={[0.8, 3.65, 64]} /><meshStandardMaterial color="#2f241d" roughness={1} /></mesh>
      <mesh castShadow position={[0, height / 2, 0]}><cylinderGeometry args={[0.055, 0.075, height, 12]} /><meshStandardMaterial color="#527b31" roughness={0.75} /></mesh>
      {nodes.map((node) => {
        const y = 0.45 + node * (height - 0.7) / 10;
        const angle = node * 2.38;
        const length = 0.8 + (node % 3) * 0.18;
        return <group key={node} position={[0, y, 0]} rotation-y={angle}><mesh castShadow position={[length * 0.36, 0.06, 0]} rotation-z={-0.32 + (node % 2) * 0.16}><planeGeometry args={[length, 0.22, 5, 1]} /><meshStandardMaterial color={leafColor} side={THREE.DoubleSide} roughness={0.62} /></mesh></group>;
      })}
      <group position={[0.1, height * 0.59, 0.06]} rotation-z={0.8}><mesh castShadow><cylinderGeometry args={[0.11, 0.13, 0.42, 12]} /><meshStandardMaterial color="#d5a83e" roughness={0.68} /></mesh><mesh position={[0, 0.24, 0]}><coneGeometry args={[0.17, 0.36, 10]} /><meshStandardMaterial color="#527b31" /></mesh></group>
      <mesh position={[0, height + 0.18, 0]} castShadow><coneGeometry args={[0.17, 0.55, 9]} /><meshStandardMaterial color="#c4a47a" roughness={0.8} /></mesh>
      {roots.map((root) => {
        const angle = root * (Math.PI * 2 / roots.length);
        const length = 0.45 + (root % 5) * 0.12;
        const depth = Math.min(1.45, rootDepthCm / 100) * (0.65 + (root % 4) * 0.08);
        return <mesh key={root} position={[Math.cos(angle) * length / 2, -depth / 2, Math.sin(angle) * length / 2]} rotation-z={Math.cos(angle) * 0.75} rotation-x={Math.sin(angle) * 0.55}><cylinderGeometry args={[0.012, 0.02, Math.sqrt(length * length + depth * depth), 6]} /><meshStandardMaterial color="#c38a52" roughness={1} /></mesh>;
      })}
      <Html position={[0, height + 0.85, 0]} center distanceFactor={9}><div className="w-56 rounded-lg border border-emerald-300/40 bg-slate-950/85 px-3 py-2 text-center font-mono text-[10px] text-emerald-100 shadow-xl backdrop-blur"><div className="font-bold text-emerald-300">Zea mays L. · planta simulada</div><div className="mt-1 text-slate-300">LAI {lai.toFixed(2)} · raíz {rootDepthCm.toFixed(0)} cm</div><div className="text-slate-400">ET {transpirationMm.toFixed(2)} mm · estrés {cwsiStress.toFixed(2)} · flujo {sapFlowVelocityCmh.toFixed(1)} cm/h</div></div></Html>
    </group>
  );
}

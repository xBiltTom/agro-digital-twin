"use client";

import React, { useMemo } from "react";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

interface PlantModel3DProps { transpirationMm: number; cwsiStress: number; sapFlowVelocityCmh: number; soilMoistureVol: number; lai?: number; rootDepthCm?: number; }

/** A tapered, arched blade following a natural maize phyllotaxis. */
function LeafBlade({ angle, length, rise, droop, width, color }: { angle: number; length: number; rise: number; droop: number; width: number; color: string }) {
  const geometry = useMemo(() => {
    const segments = 14;
    const vertices: number[] = [];
    const indices: number[] = [];
    const direction = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle));
    const side = new THREE.Vector3(-Math.sin(angle), 0, Math.cos(angle));
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const center = direction.clone().multiplyScalar(length * t);
      center.y = rise * Math.sin(Math.PI * t) - droop * t * t;
      const halfWidth = width * Math.sin(Math.PI * Math.pow(t, 0.82)) * (1 - t * 0.35);
      const left = center.clone().addScaledVector(side, halfWidth);
      const right = center.clone().addScaledVector(side, -halfWidth);
      vertices.push(left.x, left.y, left.z, right.x, right.y, right.z);
      if (i < segments) {
        const a = i * 2;
        indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    }
    const result = new THREE.BufferGeometry();
    result.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    result.setIndex(indices);
    result.computeVertexNormals();
    return result;
  }, [angle, length, rise, droop, width]);
  const midrib = useMemo(() => Array.from({ length: 10 }, (_, i) => {
    const t = i / 9;
    return [Math.cos(angle) * length * t, rise * Math.sin(Math.PI * t) - droop * t * t, Math.sin(angle) * length * t] as [number, number, number];
  }), [angle, length, rise, droop]);
  return <group><mesh geometry={geometry} castShadow receiveShadow><meshPhysicalMaterial color={color} side={THREE.DoubleSide} roughness={0.5} clearcoat={0.12} /></mesh><Line points={midrib} color="#294f2a" lineWidth={0.55} transparent opacity={0.58} /></group>;
}

function RootSystem({ rootDepthCm }: { rootDepthCm: number }) {
  const roots = useMemo(() => Array.from({ length: 26 }, (_, i) => i), []);
  const depthScale = Math.min(1.62, rootDepthCm / 100);
  return <group>{roots.map((root) => {
    const angle = root * 2.39996;
    const spread = 0.45 + (root % 7) * 0.13;
    const depth = depthScale * (0.46 + (root % 5) * 0.1);
    const points: [number, number, number][] = [[0, -0.04, 0], [Math.cos(angle) * spread * .38, -depth * .28, Math.sin(angle) * spread * .38], [Math.cos(angle) * spread, -depth, Math.sin(angle) * spread]];
    return <Line key={root} points={points} color={root % 4 === 0 ? "#e0a55e" : "#b87544"} lineWidth={root % 4 === 0 ? 1.1 : 0.55} transparent opacity={0.9} />;
  })}</group>;
}

export default function PlantModel3D({ transpirationMm, cwsiStress, sapFlowVelocityCmh, soilMoistureVol, lai = 3.4, rootDepthCm = 105 }: PlantModel3DProps) {
  const stress = Math.min(1, Math.max(0, cwsiStress));
  const canopy = new THREE.Color().lerpColors(new THREE.Color("#bd9440"), new THREE.Color("#3f8f3d"), 1 - stress * .85).getStyle();
  const height = 2.48 + Math.min(1.25, lai * .22);
  const leaves = useMemo(() => Array.from({ length: 13 }, (_, i) => i), []);
  const soilColor = soilMoistureVol > 0.25 ? "#513a27" : "#7d4c2e";

  return <group position={[0, -1.82, 0]}>
    {/* Translucent soil profile preserves the depth relationship between canopy and roots. */}
    <mesh receiveShadow rotation-x={-Math.PI / 2}><circleGeometry args={[3.85, 72]} /><meshStandardMaterial color={soilColor} roughness={1} /></mesh>
    <mesh position={[0, -0.62, 0]}><cylinderGeometry args={[3.82, 3.82, 1.22, 64, 1, true]} /><meshPhysicalMaterial color="#5b3e2c" transparent opacity={0.20} side={THREE.DoubleSide} roughness={.95} /></mesh>
    <mesh position={[0, -1.27, 0]}><cylinderGeometry args={[3.8, 3.8, 0.1, 64]} /><meshStandardMaterial color="#8d6243" transparent opacity={.27} /></mesh>
    <RootSystem rootDepthCm={rootDepthCm} />

    {/* Stem segments and collars make the individual scale read as maize, never a woody plant. */}
    <mesh castShadow position={[0, height / 2, 0]}><cylinderGeometry args={[.047, .076, height, 16]} /><meshPhysicalMaterial color="#557d2f" roughness={.62} clearcoat={.08} /></mesh>
    {Array.from({ length: 11 }, (_, node) => <mesh key={node} castShadow position={[0, .38 + node * (height - .5) / 11, 0]}><torusGeometry args={[.073 - node * .0015, .014, 7, 18]} /><meshStandardMaterial color="#6f943e" roughness={.65} /></mesh>)}
    {leaves.map((leaf) => {
      const t = leaf / (leaves.length - 1);
      const length = .86 + Math.sin(t * Math.PI) * (1.14 + lai * .08);
      const bladeColor = leaf < 2 ? "#527d37" : canopy;
      return <group key={leaf} position={[0, .42 + t * (height - .75), 0]} rotation-y={leaf * 2.39996}><LeafBlade angle={leaf % 2 ? .15 : -.12} length={length} rise={length * (.20 - t * .045)} droop={length * (.20 + stress * .20 + t * .06)} width={.11 + Math.sin(t * Math.PI) * .13} color={bladeColor} /></group>;
    })}
    <group position={[.1, height * .58, .04]} rotation-z={.55}><mesh castShadow><cylinderGeometry args={[.105, .135, .46, 14]} /><meshStandardMaterial color="#d9ae3b" roughness={.72} /></mesh><mesh position={[0, .22, 0]}><coneGeometry args={[.18, .40, 12]} /><meshStandardMaterial color="#4e7c36" /></mesh></group>
    <group position={[0, height + .18, 0]}>{Array.from({ length: 9 }, (_, i) => <mesh key={i} rotation-z={(i - 4) * .20} rotation-y={i * .7}><cylinderGeometry args={[.011, .017, .52, 6]} /><meshStandardMaterial color="#d5bd83" /></mesh>)}</group>
    <Html position={[0, height + 1.02, 0]} center distanceFactor={9}><div className="w-60 rounded-xl border border-emerald-300/45 bg-slate-950/82 px-3 py-2 text-center font-mono text-[10px] text-emerald-100 shadow-2xl backdrop-blur"><div className="font-bold text-emerald-300">Zea mays L. · escala individual</div><div className="mt-1 text-slate-300">LAI {lai.toFixed(2)} · profundidad radicular {rootDepthCm.toFixed(0)} cm</div><div className="text-slate-400">ET {transpirationMm.toFixed(2)} mm · estrés {cwsiStress.toFixed(2)} · xilema {sapFlowVelocityCmh.toFixed(1)} cm/h</div></div></Html>
  </group>;
}

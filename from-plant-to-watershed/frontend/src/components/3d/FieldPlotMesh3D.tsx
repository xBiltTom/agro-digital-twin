"use client";

import React, { useEffect, useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";

export interface PlantSample3D { plant_id: number; x_m: number; y_m: number; lai: number; stress: number; root_depth_cm?: number; }
interface FieldPlotMesh3DProps { soilMoistureVol: number; cwsiStress: number; plantSample: PlantSample3D[]; plantCount?: number; onSelectPlant: () => void; }

function DenseCanopy({ stress }: { stress: number }) {
  const stems = useRef<THREE.InstancedMesh>(null);
  const bladesA = useRef<THREE.InstancedMesh>(null);
  const bladesB = useRef<THREE.InstancedMesh>(null);
  const positions = useMemo(() => Array.from({ length: 560 }, (_, i) => {
    const row = Math.floor(i / 28);
    const column = i % 28;
    const jitter = ((i * 9301 + 49297) % 233280) / 233280 - .5;
    return { x: -10.3 + column * .76 + jitter * .11, z: -7.4 + row * .76 + Math.sin(i * 7.3) * .06, h: .82 + ((i * 37) % 100) / 340 };
  }), []);
  useEffect(() => {
    const matrix = new THREE.Matrix4(); const position = new THREE.Vector3(); const rotation = new THREE.Euler(); const scale = new THREE.Vector3();
    positions.forEach((plant, i) => {
      position.set(plant.x, plant.h / 2, plant.z); rotation.set(0, i * .41, 0); scale.set(1, 1, 1); matrix.compose(position, new THREE.Quaternion().setFromEuler(rotation), scale); stems.current?.setMatrixAt(i, matrix);
      position.set(plant.x, plant.h * .53, plant.z); rotation.set(0, i * .41, (i % 2 ? -.35 : .34)); scale.set(.7 + (i % 4) * .06, 1, 1); matrix.compose(position, new THREE.Quaternion().setFromEuler(rotation), scale); bladesA.current?.setMatrixAt(i, matrix);
      rotation.set(0, i * .41 + 1.65, (i % 3 ? .26 : -.29)); matrix.compose(position, new THREE.Quaternion().setFromEuler(rotation), scale); bladesB.current?.setMatrixAt(i, matrix);
    });
    [stems, bladesA, bladesB].forEach(ref => { if (ref.current) ref.current.instanceMatrix.needsUpdate = true; });
  }, [positions]);
  const leaf = stress < .45 ? "#477f37" : "#a8843c";
  return <group>
    <instancedMesh ref={stems} args={[undefined, undefined, positions.length]} castShadow><cylinderGeometry args={[.013, .022, 1, 6]} /><meshStandardMaterial color="#4e7130" roughness={.7} /></instancedMesh>
    <instancedMesh ref={bladesA} args={[undefined, undefined, positions.length]} castShadow><planeGeometry args={[.5, .095]} /><meshStandardMaterial color={leaf} side={THREE.DoubleSide} roughness={.62} /></instancedMesh>
    <instancedMesh ref={bladesB} args={[undefined, undefined, positions.length]} castShadow><planeGeometry args={[.5, .095]} /><meshStandardMaterial color="#5a9444" side={THREE.DoubleSide} roughness={.62} /></instancedMesh>
  </group>;
}

function SamplePlant({ plant }: { plant: PlantSample3D }) {
  const height = 1.08 + Math.min(.45, plant.lai * .08);
  const color = plant.stress < .45 ? "#6ab34e" : "#d0a745";
  return <group position={[plant.x_m, 0, plant.y_m]}><mesh castShadow position={[0, height / 2, 0]}><cylinderGeometry args={[.025, .038, height, 8]} /><meshStandardMaterial color="#4d7a2e" /></mesh>{Array.from({ length: 5 }, (_, leaf) => <group key={leaf} position={[0, height * (.25 + leaf * .13), 0]} rotation-y={plant.plant_id * .7 + leaf * 2.4}><mesh position={[.31, .035, 0]} rotation-z={leaf % 2 ? -.28 : .32} castShadow><planeGeometry args={[.72 - leaf * .055, .12]} /><meshStandardMaterial color={color} side={THREE.DoubleSide} /></mesh></group>)}</group>;
}

export default function FieldPlotMesh3D({ soilMoistureVol, cwsiStress, plantSample, plantCount = 1000, onSelectPlant }: FieldPlotMesh3DProps) {
  const plants = useMemo(() => {
    if (!plantSample.length) return [];
    const maxX = Math.max(...plantSample.map(p => p.x_m), 1); const maxY = Math.max(...plantSample.map(p => p.y_m), 1);
    return plantSample.map(p => ({ ...p, x_m: p.x_m / maxX * 20 - 10, y_m: p.y_m / maxY * 15 - 7.5 }));
  }, [plantSample]);
  const soil = soilMoistureVol > .25 ? "#60402a" : "#8c5634";
  return <group position={[0, -.12, 0]} onClick={onSelectPlant}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}><planeGeometry args={[24, 19, 30, 30]} /><meshStandardMaterial color={soil} roughness={1} /></mesh>
    {[...Array(20)].map((_, row) => <mesh key={row} rotation-x={-Math.PI / 2} position={[0, .012, -7.45 + row * .76]}><planeGeometry args={[22.2, .07]} /><meshStandardMaterial color="#38271f" roughness={1} /></mesh>)}
    <DenseCanopy stress={cwsiStress} />
    {plants.map(plant => <SamplePlant key={plant.plant_id} plant={plant} />)}
    <mesh rotation-x={-Math.PI / 2} position={[0, .02, 0]}><ringGeometry args={[10.65, 10.9, 64]} /><meshBasicMaterial color="#d6bd7e" transparent opacity={.55} /></mesh>
    {!plants.length && <Html position={[0, 1.4, 0]} center><div className="rounded-md border border-amber-300/30 bg-slate-950/85 px-3 py-2 font-mono text-[10px] text-amber-200">La corrida elegida no contiene una muestra de plantas.</div></Html>}
    <Html position={[-10.5, 2.0, -7.6]} distanceFactor={13}><div className="w-64 rounded-xl border border-emerald-300/35 bg-slate-950/85 p-3 font-mono text-[10px] text-slate-200 shadow-2xl backdrop-blur"><div className="font-bold text-emerald-300">Campo de maíz · escala meso</div><div className="mt-1">Población: n={plantCount.toLocaleString()} · muestra resaltada: {plants.length}</div><div className="text-slate-400">Canopeo denso representado sobre hileras de 0.76 m</div><div className="mt-1 text-cyan-300">Clic para entrar a la planta individual</div></div></Html>
  </group>;
}

"use client";

import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { numeric, type SceneState } from "../../lib/playback-scene";

interface Props {
  scene: SceneState;
  showSoilHorizons?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

function MicroRain({ intensity }: { intensity: number }) {
  const group = useRef<THREE.Group>(null);
  const count = Math.max(4, Math.floor(intensity * 150));
  const points = useMemo(() => Array.from({ length: count }, (_, i) => [
    (((i * 31) % 151) / 151 - 0.5) * 6,
    ((i * 47) % 113) / 113 * 5,
    (((i * 67) % 157) / 157 - 0.5) * 6,
  ] as const), [count]);
  useFrame((_, delta) => { if (group.current) group.current.position.y = (group.current.position.y - delta * 5 + 5) % 5; });
  return <group ref={group}>{points.map(([x, y, z], i) =>
    <mesh key={i} position={[x, y, z]}><boxGeometry args={[0.01, 0.18, 0.01]} /><meshBasicMaterial color="#a6e9fb" transparent opacity={0.6} /></mesh>
  )}</group>;
}

/** Schematic maize architecture. Stem height maps 1 m to 1 scene unit; leaf count is graphic only. */
export default function PlantModel3D({ scene, showSoilHorizons = true, showScientificLabels = true,
  showHydrologyFlow = true }: Props) {
  const sample = scene.sample;
  const height = sample ? numeric(sample.variables.height_m) : null;
  const lai = sample ? numeric(sample.variables.lai) : null;
  const rootDepth = sample ? numeric(sample.variables.root_depth_m) : null;
  const stress = sample ? numeric(sample.variables.water_stress) : null;
  const stage = sample?.variables.phenological_stage?.availability === "AVAILABLE"
    ? String(sample.variables.phenological_stage.value) : scene.record.crop?.phenological_stage;
  const visualHeight = height === null ? null : Math.min(3.2, Math.max(0.03, height));
  const leafCount = lai === null ? 0 : Math.max(1, Math.min(14, Math.round(lai * 2.5)));
  const leafColor = new THREE.Color("#2e8d39").lerp(new THREE.Color("#a0a238"),
    stress === null ? 0 : Math.max(0, Math.min(1, stress)));

  return <group position={[0, -0.18, 0]}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}>
      <planeGeometry args={[6, 6]} />
      <meshStandardMaterial color="#594537" roughness={0.93} />
    </mesh>
    {showSoilHorizons && <mesh position={[0, -0.25, 0]}>
      <boxGeometry args={[3.2, 0.5, 3.2]} />
      <meshStandardMaterial color="#6b4934" roughness={1} />
    </mesh>}
    {visualHeight !== null && <group>
      <mesh castShadow position={[0, visualHeight / 2, 0]}>
        <cylinderGeometry args={[0.03, 0.065, visualHeight, 9]} />
        <meshStandardMaterial color="#6a9a37" roughness={0.72} />
      </mesh>
      {Array.from({ length: leafCount }, (_, i) => {
        const fraction = (i + 1) / (leafCount + 1);
        const angle = i * 2.39996;
        const length = Math.min(0.9, 0.18 + (lai ?? 0) * 0.14) * Math.sin(Math.PI * fraction);
        return <group key={i} position={[0, visualHeight * fraction, 0]} rotation-y={angle}>
          <mesh castShadow position={[length / 2, 0.02, 0]} rotation-z={-0.14} scale={[Math.max(0.08, length), 0.025, Math.max(0.025, length * 0.12)]}>
            <sphereGeometry args={[1, 8, 5]} />
            <meshStandardMaterial color={leafColor} side={THREE.DoubleSide} roughness={0.55} />
          </mesh>
        </group>;
      })}
      {rootDepth !== null && Array.from({ length: 8 }, (_, i) =>
        <mesh key={i} position={[Math.cos(i * Math.PI / 4) * 0.1, -Math.min(0.45, rootDepth) / 2, Math.sin(i * Math.PI / 4) * 0.1]}
          rotation-z={Math.cos(i * Math.PI / 4) * 0.2}>
          <cylinderGeometry args={[0.003, 0.012, Math.min(0.9, rootDepth), 5]} />
          <meshStandardMaterial color="#d4b884" />
        </mesh>)}
    </group>}
    {showHydrologyFlow && scene.rainIntensity !== null && scene.rainIntensity > 0 && <MicroRain intensity={scene.rainIntensity} />}
    {showScientificLabels && <Html position={[1.7, 2.7, 0]} distanceFactor={7}>
      <div className="w-64 rounded-xl border border-emerald-500/40 bg-zinc-950/95 p-3 text-xs text-zinc-100 shadow-2xl">
        <b className="text-emerald-300">Muestra FSPM {sample?.plant_id ?? "no disponible"}</b>
        <p className="mt-1">{scene.record.date} · {stage ?? "Etapa no disponible"}</p>
        <p>Altura: {height === null ? "No disponible" : `${height.toFixed(2)} m`}</p>
        <p>LAI: {lai === null ? "No disponible" : lai.toFixed(2)}</p>
        <p>Raíz: {rootDepth === null ? "No disponible" : `${rootDepth.toFixed(2)} m`}</p>
        <p>Estrés: {stress === null ? "No disponible" : stress.toFixed(2)}</p>
        <p className="mt-1 text-zinc-400">Geometría ilustrativa; dimensiones foliares y raíces no son una reconstrucción 3D validada.</p>
      </div>
    </Html>}
  </group>;
}

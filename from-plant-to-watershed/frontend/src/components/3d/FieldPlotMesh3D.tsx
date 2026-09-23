"use client";

import { useEffect, useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneState } from "../../lib/playback-scene";

interface Props {
  scene: SceneState;
  onSelectPlant: () => void;
  showSensors?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

/** Instances represent field means; they are not independent simulated plants. */
function AggregateCanopy({ heightM, lai, cover, stress }: {
  heightM: number; lai: number; cover: number | null; stress: number | null;
}) {
  const stems = useRef<THREE.InstancedMesh>(null);
  const leaves = useRef<THREE.InstancedMesh>(null);
  const columns = 22;
  const rows = 18;
  const count = columns * rows;
  const canopyRadius = Math.max(0.08, Math.min(0.48, 0.12 + lai * 0.055)) *
    (cover === null ? 1 : Math.max(0.35, Math.min(1, cover * 1.4)));
  const visualHeight = Math.max(0.03, Math.min(3.2, heightM)); // 1 scene unit/m, bounded.
  const color = useMemo(() => stress === null ? new THREE.Color("#63885a") :
    new THREE.Color("#258a3d").lerp(new THREE.Color("#a6a33c"), Math.max(0, Math.min(1, stress))), [stress]);

  useEffect(() => {
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const rotation = new THREE.Quaternion();
    const scale = new THREE.Vector3();
    for (let i = 0; i < count; i++) {
      const x = (i % columns - (columns - 1) / 2) * 0.85;
      const z = (Math.floor(i / columns) - (rows - 1) / 2) * 0.9;
      position.set(x, visualHeight / 2, z);
      scale.set(1, visualHeight, 1);
      matrix.compose(position, rotation, scale);
      stems.current?.setMatrixAt(i, matrix);
      position.set(x, visualHeight * 0.67, z);
      scale.set(canopyRadius, Math.max(0.05, visualHeight * 0.62), canopyRadius);
      matrix.compose(position, rotation, scale);
      leaves.current?.setMatrixAt(i, matrix);
    }
    if (stems.current) stems.current.instanceMatrix.needsUpdate = true;
    if (leaves.current) leaves.current.instanceMatrix.needsUpdate = true;
  }, [count, visualHeight, canopyRadius]);

  return <group>
    <instancedMesh ref={stems} args={[undefined, undefined, count]} castShadow>
      <cylinderGeometry args={[0.035, 0.055, 1, 6]} />
      <meshStandardMaterial color="#5d8d36" roughness={0.85} />
    </instancedMesh>
    <instancedMesh ref={leaves} args={[undefined, undefined, count]} castShadow>
      <coneGeometry args={[1, 1, 5]} />
      <meshStandardMaterial color={color} roughness={0.65} side={THREE.DoubleSide} />
    </instancedMesh>
  </group>;
}

function FieldRain({ intensity }: { intensity: number }) {
  const group = useRef<THREE.Group>(null);
  const count = Math.max(8, Math.floor(intensity * 400));
  const points = useMemo(() => Array.from({ length: count }, (_, i) => {
    const x = (((i * 73) % 397) / 397 - 0.5) * 22;
    const z = (((i * 163) % 401) / 401 - 0.5) * 20;
    const y = ((i * 47) % 101) / 101 * 10;
    return [x, y, z] as const;
  }), [count]);
  useFrame((_, delta) => { if (group.current) group.current.position.y = (group.current.position.y - delta * 7 + 10) % 10; });
  return <group ref={group}>{points.map(([x, y, z], i) =>
    <mesh key={i} position={[x, y, z]}><boxGeometry args={[0.015, 0.32, 0.015]} /><meshBasicMaterial color="#9de5fa" transparent opacity={0.55} /></mesh>
  )}</group>;
}

export default function FieldPlotMesh3D({ scene, onSelectPlant, showSensors = true,
  showScientificLabels = true, showHydrologyFlow = true }: Props) {
  const showCrop = scene.cropActive && scene.cropSupported && scene.fieldHeightM !== null && scene.fieldLai !== null;
  return <group position={[0, -0.18, 0]}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}>
      <planeGeometry args={[23, 21]} />
      <meshStandardMaterial color="#584434" roughness={0.95} />
    </mesh>
    <gridHelper args={[22, 22, "#765e48", "#574532"]} position={[0, 0.005, 0]} />
    {showCrop && <group onClick={() => { if (scene.sample) onSelectPlant(); }}>
      <AggregateCanopy heightM={scene.fieldHeightM!} lai={scene.fieldLai!}
        cover={scene.canopyCover} stress={scene.stress} />
    </group>}
    {showSensors && <mesh position={[-10, 1, -9]}><cylinderGeometry args={[0.035, 0.035, 2, 8]} /><meshStandardMaterial color="#94a3b8" /></mesh>}
    {showHydrologyFlow && scene.rainIntensity !== null && scene.rainIntensity > 0 &&
      <FieldRain intensity={scene.rainIntensity} />}
    {showScientificLabels && <Html position={[-10, 4, 0]} distanceFactor={12}>
      <div className="w-64 rounded-xl border border-emerald-500/40 bg-zinc-950/95 p-3 text-xs text-zinc-100 shadow-2xl">
        <b className="text-emerald-300">Campo FSPM · {scene.record.date}</b>
        <p className="mt-1">{scene.cropActive ? `${scene.record.crop?.crop ?? "Cultivo"} · ${scene.record.crop?.phenological_stage ?? "Etapa no disponible"}` : "Sin cultivo activo"}</p>
        {scene.cropActive && !scene.cropSupported && <p className="text-amber-300">Geometría de este cultivo no disponible.</p>}
        {scene.cropActive && scene.cropSupported && !showCrop && <p className="text-amber-300">Altura o LAI no disponibles para dibujar el dosel.</p>}
        <p>LAI: {scene.fieldLai === null ? "No disponible" : scene.fieldLai.toFixed(2)}</p>
        <p>Altura: {scene.fieldHeightM === null ? "No disponible" : `${scene.fieldHeightM.toFixed(2)} m`}</p>
        <p className="mt-1 text-zinc-400">Geometría decorativa basada en promedios; {scene.record.plant_samples.length} muestras individuales registradas.</p>
        {scene.record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" && <p className="text-amber-300">Ventana agrícola aproximada por PHU</p>}
        {scene.sample && <button className="mt-2 text-emerald-300 underline" onClick={onSelectPlant}>Ver muestra {scene.sample.plant_id}</button>}
      </div>
    </Html>}
  </group>;
}

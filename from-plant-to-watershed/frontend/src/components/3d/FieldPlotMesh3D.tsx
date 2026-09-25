"use client";

import { useEffect, useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { SceneState } from "../../lib/playback-scene";
import { fieldCanopyAvailable, maizeReproductive } from "../../lib/visual-state";
import { createCurvedMaizeLeafGeometry, EddyCovarianceTower, MesoRainSystem, SoilMoistureProbeStation } from "./FieldVisuals3D";

interface Props {
  scene: SceneState | null;
  onSelectPlant: (plantId?: string) => void;
  showSensors?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

/** 26 × 39 decorative maize meshes, driven by the field mean. They are not persisted individual trajectories. */
function RichCanopy({ heightM, lai, cover, stress, stage }: {
  heightM: number; lai: number; cover: number | null; stress: number | null; stage: string | null;
}) {
  const stems = useRef<THREE.InstancedMesh>(null);
  const lower = useRef<THREE.InstancedMesh>(null);
  const middle = useRef<THREE.InstancedMesh>(null);
  const upper = useRef<THREE.InstancedMesh>(null);
  const tassels = useRef<THREE.InstancedMesh>(null);
  const rows = 26, columns = 39, count = rows * columns;
  const leafGeoA = useMemo(() => createCurvedMaizeLeafGeometry(0.88, 0.17, 0.35), []);
  const leafGeoB = useMemo(() => createCurvedMaizeLeafGeometry(0.82, 0.15, 0.28), []);
  const leafGeoC = useMemo(() => createCurvedMaizeLeafGeometry(0.68, 0.13, 0.20), []);
  useEffect(() => () => { leafGeoA.dispose(); leafGeoB.dispose(); leafGeoC.dispose(); }, [leafGeoA, leafGeoB, leafGeoC]);

  useEffect(() => {
    const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), scale = new THREE.Vector3();
    const rotation = new THREE.Euler(), quaternion = new THREE.Quaternion();
    const height = Math.max(0.005, Math.min(3.2, heightM)); // metre for metre
    const leafScale = Math.max(0, Math.min(1.2, lai / 3.8)) *
      (cover === null ? 1 : Math.max(0, Math.min(1, cover)));
    const color = stress === null ? new THREE.Color("#467938") :
      new THREE.Color("#22631a").lerp(new THREE.Color("#989e30"), Math.max(0, Math.min(1, stress)));
    for (let i = 0; i < count; i++) {
      const x = (i % columns - (columns - 1) / 2) * 0.54;
      const z = (Math.floor(i / columns) - (rows - 1) / 2) * 0.82;
      const turn = i * 0.73;
      position.set(x, height / 2, z); rotation.set(0, turn, 0); scale.set(1, height, 1);
      matrix.compose(position, quaternion.setFromEuler(rotation), scale);
      stems.current?.setMatrixAt(i, matrix);
      stems.current?.setColorAt(i, new THREE.Color("#416a24"));
      [lower, middle, upper].forEach((ref, layer) => {
        position.set(x, height * (0.34 + layer * 0.24), z);
        rotation.set(0, turn + layer * Math.PI / 2, (stress ?? 0) * 0.25);
        const horizontal = leafScale * (layer === 2 ? 0.72 : 1);
        scale.set(horizontal, horizontal, horizontal * (0.5 + height * 0.3));
        matrix.compose(position, quaternion.setFromEuler(rotation), scale);
        ref.current?.setMatrixAt(i, matrix);
        ref.current?.setColorAt(i, color);
      });
      position.set(x, height - (maizeReproductive(stage) ? 0.10 : 0), z);
      rotation.set(0, turn, 0);
      const tasselSize = maizeReproductive(stage) ? 0.7 : 0.001;
      scale.set(tasselSize, tasselSize, tasselSize);
      matrix.compose(position, quaternion.setFromEuler(rotation), scale);
      tassels.current?.setMatrixAt(i, matrix);
    }
    [stems, lower, middle, upper, tassels].forEach((ref) => {
      if (ref.current) {
        ref.current.instanceMatrix.needsUpdate = true;
        if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      }
    });
  }, [heightM, lai, cover, stress, stage, count]);

  return <group data-testid="rich-field-canopy">
    <instancedMesh ref={stems} args={[undefined, undefined, count]} castShadow>
      <cylinderGeometry args={[0.022, 0.038, 1, 8]} /><meshPhysicalMaterial roughness={0.4} clearcoat={0.35} />
    </instancedMesh>
    {[ [lower, leafGeoA], [middle, leafGeoB], [upper, leafGeoC] ].map(([ref, geometry], index) =>
      <instancedMesh key={index} ref={ref as React.RefObject<THREE.InstancedMesh>}
        args={[geometry as THREE.BufferGeometry, undefined, count]} castShadow receiveShadow>
        <meshPhysicalMaterial side={THREE.DoubleSide} roughness={0.28} clearcoat={0.72} clearcoatRoughness={0.18} />
      </instancedMesh>)}
    <instancedMesh ref={tassels} args={[undefined, undefined, count]} castShadow>
      <coneGeometry args={[0.08, 0.32, 6]} /><meshStandardMaterial color="#e5ce79" roughness={0.55} />
    </instancedMesh>
  </group>;
}

export default function FieldPlotMesh3D({ scene, onSelectPlant, showSensors = true,
  showScientificLabels = true, showHydrologyFlow = true }: Props) {
  const reference = scene === null;
  const showCrop = fieldCanopyAvailable(scene);
  const height = reference ? 2.1 : scene?.fieldHeightM ?? null;
  const lai = reference ? 3.5 : scene?.fieldLai ?? null;
  const soilColor = scene?.soilMoisturePercent === null || !scene ? "#422b18" :
    new THREE.Color("#53351c").lerp(new THREE.Color("#22140a"), Math.max(0, Math.min(1, scene.soilMoisturePercent / 45)));
  const sampleMarkers = scene?.cropActive && scene.cropSupported ? scene.record.plant_samples : [];
  return <group position={[0, -0.12, 0]}>
    <mesh receiveShadow rotation-x={-Math.PI / 2}>
      <planeGeometry args={[24, 24, 32, 32]} /><meshStandardMaterial color={soilColor} roughness={0.85} />
    </mesh>
    {Array.from({ length: 26 }, (_, row) => <group key={row} position={[0, 0.012, (row - 12.5) * 0.82]}>
      <mesh rotation-x={-Math.PI / 2}><planeGeometry args={[22.5, 0.16]} />
        <meshStandardMaterial color="#170c06" roughness={0.8} /></mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0.38]}>
        <planeGeometry args={[22, 0.32]} /><meshStandardMaterial color="#8a7650" transparent opacity={0.82} roughness={0.88} /></mesh>
    </group>)}
    {showCrop && height !== null && lai !== null && <RichCanopy heightM={height} lai={lai}
      cover={reference ? null : scene!.canopyCover} stress={reference ? null : scene!.stress}
      stage={reference ? "REPRODUCTIVE" : scene!.record.crop?.phenological_stage ?? null} />}
    {showSensors && <>
      <EddyCovarianceTower position={[-9.5, 0, -8.5]} />
      <SoilMoistureProbeStation position={[8.2, 0, 7.5]} label="Sonda contextual"
        valuePercent={null} />
      <SoilMoistureProbeStation position={[-7.5, 0, 8.2]} label="Sonda contextual"
        valuePercent={null} />
    </>}
    {sampleMarkers.map((sample) => Number.isFinite(sample.x_m) && Number.isFinite(sample.y_m) ?
      <group key={sample.plant_id} position={[sample.x_m - 11.6, 0.035, sample.y_m - 3.1]}>
        <mesh rotation-x={-Math.PI / 2} onClick={(event) => { event.stopPropagation(); onSelectPlant(sample.plant_id); }}>
          <ringGeometry args={[0.18, 0.28, 24]} /><meshBasicMaterial color="#00f5b2" side={THREE.DoubleSide} />
        </mesh>
        {showScientificLabels && <Html position={[0, 0.35, 0]} center distanceFactor={12}>
          <button className="rounded border border-emerald-400/50 bg-zinc-950/90 px-1.5 py-0.5 text-[9px] text-emerald-200"
            onClick={() => onSelectPlant(sample.plant_id)}>{sample.plant_id}</button>
        </Html>}
      </group> : null)}
    {showHydrologyFlow && scene?.rainMm !== null && scene?.rainMm !== undefined && scene.rainIntensity !== null && scene.rainMm > 0 &&
      <MesoRainSystem precipMm={scene.rainMm} />}
    {showScientificLabels && <Html position={[-10.8, 4.2, -9.5]} distanceFactor={18}>
      <div className="w-64 rounded-xl border border-teal-400/50 bg-zinc-950/95 p-3 text-xs text-zinc-100 shadow-2xl">
        <b className="text-teal-300">{reference ? "Parcela de referencia · ilustrativa" : `Campo FSPM · ${scene.record.date}`}</b>
        <p className="mt-1">{reference ? "Vegetación y surcos contextuales" : scene.cropActive ?
          `${scene.record.crop?.crop ?? "Cultivo"} · ${scene.record.crop?.phenological_stage ?? "Etapa no disponible"}` : "Sin cultivo activo"}</p>
        {!reference && scene.cropActive && !scene.cropSupported && <p className="text-amber-300">Geometría de este cultivo no disponible.</p>}
        {!reference && scene.cropActive && scene.cropSupported && !showCrop && <p className="text-amber-300">Altura o LAI no disponibles.</p>}
        <p>LAI: {reference ? "Referencia visual" : lai === null ? "No disponible" : lai.toFixed(2)}</p>
        <p>Altura: {reference ? "Referencia visual" : height === null ? "No disponible" : `${height.toFixed(2)} m`}</p>
        <p className="mt-1 text-zinc-400">Las instancias son vegetación decorativa; {sampleMarkers.length} muestras FSPM persistidas con ID propio.</p>
        {scene?.record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" && <p className="text-amber-300">Ventana agrícola aproximada por PHU.</p>}
        {scene?.sample && <button className="mt-2 text-emerald-300 underline" onClick={() => onSelectPlant(scene.sample!.plant_id)}>
          Ver muestra {scene.sample.plant_id}</button>}
        {reference && <button className="mt-2 text-emerald-300 underline" onClick={() => onSelectPlant()}>
          Explorar planta de referencia</button>}
      </div>
    </Html>}
  </group>;
}

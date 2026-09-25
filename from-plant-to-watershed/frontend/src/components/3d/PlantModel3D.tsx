"use client";

import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { SceneState } from "../../lib/playback-scene";
import { maizeFromScene, maizeReproductive } from "../../lib/visual-state";
import { MicroRainSystem, RealisticBraceRoots, RealisticMaizeEar, RealisticMaizeLeaf, RealisticMaizeTassel } from "./MaizeVisuals3D";

interface Props {
  scene: SceneState | null;
  showSoilHorizons?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

/** The sample's measured/modelled height maps directly to scene metres; leaf anatomy is illustrative. */
export default function PlantModel3D({ scene, showSoilHorizons = true, showScientificLabels = true,
  showHydrologyFlow = true }: Props) {
  const plant = maizeFromScene(scene);
  const height = plant.heightM === null ? null : Math.max(0, Math.min(3.2, plant.heightM));
  const lai = plant.lai;
  const stress = plant.stress;
  const leafCount = lai === null || lai <= 0 ? 0 : Math.max(2, Math.min(18, Math.round(lai * 2.7 + 2)));
  const soilColor = plant.soilMoisturePercent === null ? "#382618" :
    new THREE.Color("#53351c").lerp(new THREE.Color("#21160e"),
      Math.max(0, Math.min(1, plant.soilMoisturePercent / 45)));
  const leaves = height === null ? [] : Array.from({ length: leafCount }, (_, i) => {
    const t = (i + 1) / (leafCount + 1);
    const spread = Math.min(1, Math.max(0.08, (lai ?? 0) / 4));
    const length = (0.28 + 1.14 * Math.sin(Math.PI * t)) * spread;
    return {
      angle: i * Math.PI * 0.94 + (i % 2 === 0 ? 0.08 : -0.06),
      nodeHeight: height * t,
      length,
      width: (0.045 + 0.14 * Math.sin(Math.PI * t)) * spread,
      rise: length * (0.23 - t * 0.06),
      droop: length * (0.16 + (stress ?? 0) * 0.46 + t * 0.1),
    };
  });
  const reproductive = maizeReproductive(plant.stage);
  const showRain = Boolean(scene && showHydrologyFlow && scene.rainIntensity !== null && scene.rainMm !== null && scene.rainMm > 0);

  return <group position={[0, -0.18, 0]}>
    {/* Contextual soil layers; their depths and stratigraphy are illustrative. */}
    <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, 0.003, 0]}>
      <circleGeometry args={[2.9, 64]} /><meshStandardMaterial color={soilColor} roughness={0.82} />
    </mesh>
    {showSoilHorizons && <group>
      <mesh position={[0, -0.16, 0]}><cylinderGeometry args={[2.88, 2.88, 0.32, 48, 1, true]} />
        <meshPhysicalMaterial color="#56371e" transparent opacity={0.55} side={THREE.DoubleSide} /></mesh>
      <mesh position={[0, -0.49, 0]}><cylinderGeometry args={[2.86, 2.86, 0.34, 48, 1, true]} />
        <meshPhysicalMaterial color="#704524" transparent opacity={0.46} side={THREE.DoubleSide} /></mesh>
      <mesh position={[0, -0.94, 0]}><cylinderGeometry args={[2.84, 2.84, 0.56, 48, 1, true]} />
        <meshPhysicalMaterial color="#8b603b" transparent opacity={0.37} side={THREE.DoubleSide} /></mesh>
      {[-0.32, -0.66].map((y) => <mesh key={y} position={[0, y, 0]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[2.82, 2.88, 48]} /><meshBasicMaterial color="#c7a574" transparent opacity={0.6} />
      </mesh>)}
    </group>}
    {height !== null && height > 0 && <group data-testid="detailed-maize-plant">
      {/* One scene unit is one metre; no additional calendar growth multiplier. */}
      <mesh castShadow position={[0, height / 2, 0]}>
        <cylinderGeometry args={[0.03, 0.07, height, 20]} />
        <meshPhysicalMaterial color={stress !== null && stress > 0.5 ? "#717a2f" : "#4f7d2c"}
          roughness={0.38} clearcoat={0.35} clearcoatRoughness={0.22} />
      </mesh>
      {leaves.map((leaf, i) => <group key={i}>
        <mesh position={[0, leaf.nodeHeight, 0]} rotation-x={Math.PI / 2} castShadow>
          <torusGeometry args={[0.044, 0.011, 8, 20]} /><meshStandardMaterial color="#6a9537" /></mesh>
        <RealisticMaizeLeaf {...leaf} stress={stress ?? 0} />
      </group>)}
      {plant.rootDepthM !== null && plant.rootDepthM > 0 && <RealisticBraceRoots rootDepthCm={plant.rootDepthM * 100} />}
      {reproductive && <>
        <RealisticMaizeEar nodeY={height * 0.48} angle={Math.PI * 0.42} />
        <RealisticMaizeTassel apexY={Math.max(0, height - 0.76)} />
      </>}
    </group>}
    {showRain && <MicroRainSystem precipMm={scene!.rainMm!} />}
    {showScientificLabels && <Html position={[1.5, 2.4, 0]} distanceFactor={1.8}>
      <div className="w-64 rounded-xl border border-emerald-500/40 bg-zinc-950/95 p-3 text-xs text-zinc-100 shadow-2xl">
        <b className="text-emerald-300">{plant.reference ? "Maíz de referencia · ilustrativo" : `Muestra FSPM ${plant.sampleId ?? "no disponible"}`}</b>
        <p className="mt-1">{scene?.record.date ?? "Sin fecha científica"} · {plant.reference ? "Anatomía reproductiva ilustrativa" : plant.stage ?? "Etapa no disponible"}</p>
        <p>Altura: {plant.reference ? "Referencia visual" : height === null ? "No disponible" : `${height.toFixed(2)} m`}</p>
        <p>LAI: {plant.reference ? "Referencia visual" : lai === null ? "No disponible" : lai.toFixed(2)}</p>
        <p>Raíz: {plant.reference ? "Referencia visual" : plant.rootDepthM === null ? "No disponible" : `${plant.rootDepthM.toFixed(2)} m`}</p>
        <p>Estrés: {stress === null ? "No disponible" : stress.toFixed(2)}</p>
        <p>Transpiración: {plant.transpirationMmDay === null ? "No disponible" : `${plant.transpirationMmDay.toFixed(2)} mm/día`}</p>
        {scene?.sample && <p className="text-cyan-300">{scene.sample.variables.height_m?.evidence ?? "NOT_AVAILABLE"} · {scene.sample.variables.height_m?.source ?? "Sin fuente"}</p>}
        <p className="mt-1 text-zinc-400">Hojas, mazorca, raíces laterales y perfil del suelo son ilustrativos.</p>
        {!scene && <p className="text-amber-300">Sin trayectoria individual persistida.</p>}
        {scene && !scene.sample && <p className="text-amber-300">Esta corrida/fecha no contiene muestra FSPM activa.</p>}
      </div>
    </Html>}
  </group>;
}

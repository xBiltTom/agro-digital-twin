"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

export interface PlantSample3D {
  plant_id: number | string;
  x_m: number;
  y_m: number;
  lai: number;
  stress: number;
  root_depth_cm?: number;
}

interface FieldPlotMesh3DProps {
  soilMoistureVol: number;
  cwsiStress: number;
  plantSample: PlantSample3D[];
  plantCount?: number;
  onSelectPlant: () => void;
  showSensors?: boolean;
  showScientificLabels?: boolean;
}

interface SimulatedPlant {
  id: number;
  x: number;
  z: number;
  height: number;
  lai: number;
  stress: number;
  isHighlighted: boolean;
  color: THREE.Color;
}

/**
 * Eddy Covariance Micrometeorological Flux Tower (USDA BARC)
 * Measures sensible heat, latent heat (ET), and CO2 exchange
 */
function EddyCovarianceTower({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Concrete foundation pad */}
      <mesh position={[0, 0.05, 0]} receiveShadow>
        <boxGeometry args={[0.9, 0.1, 0.9]} />
        <meshStandardMaterial color="#64748b" roughness={0.85} />
      </mesh>
      {/* Triangular lattice tower mast */}
      <mesh position={[0, 2.4, 0]} castShadow>
        <cylinderGeometry args={[0.045, 0.09, 4.7, 4]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Cross-arms for sensors */}
      <mesh position={[0, 4.3, 0]} rotation-y={Math.PI / 4}>
        <boxGeometry args={[1.2, 0.03, 0.03]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} />
      </mesh>
      {/* 3D Sonic Anemometer */}
      <mesh position={[0.55, 4.45, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 0.22, 8]} />
        <meshStandardMaterial color="#f8fafc" metalness={0.5} roughness={0.2} />
      </mesh>
      {/* Net Radiometer */}
      <mesh position={[-0.55, 4.4, 0]}>
        <sphereGeometry args={[0.055, 8, 8]} />
        <meshStandardMaterial color="#38bdf8" metalness={0.4} roughness={0.3} />
      </mesh>
      {/* Solar Panel Power Supply */}
      <mesh position={[0.2, 3.2, 0.25]} rotation-x={-0.6} rotation-y={0.3}>
        <boxGeometry args={[0.55, 0.75, 0.02]} />
        <meshStandardMaterial color="#1e3a8a" roughness={0.2} metalness={0.9} />
      </mesh>
      {/* Data Logger Enclosure box */}
      <mesh position={[-0.15, 1.3, 0]}>
        <boxGeometry args={[0.32, 0.42, 0.22]} />
        <meshStandardMaterial color="#f1f5f9" roughness={0.4} />
      </mesh>
      {/* Pulsing Telemetry LED */}
      <mesh position={[-0.15, 1.55, 0.12]}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshBasicMaterial color="#10b981" />
      </mesh>
    </group>
  );
}

/**
 * Soil Moisture Probe Stations (SoilGrids TDR / In-situ Telemetry)
 */
function SoilMoistureProbeStation({
  position,
  label,
  valuePercent,
}: {
  position: [number, number, number];
  label: string;
  valuePercent: number;
}) {
  return (
    <group position={position}>
      {/* In-ground sensor probe housing */}
      <mesh position={[0, 0.22, 0]} castShadow>
        <cylinderGeometry args={[0.03, 0.04, 0.44, 8]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.6} />
      </mesh>
      {/* Telemetry blinking beacon */}
      <mesh position={[0, 0.46, 0]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshBasicMaterial color="#06b6d4" />
      </mesh>
      {/* Ground ring marker */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.15, 0.22, 16]} />
        <meshBasicMaterial color="#06b6d4" transparent opacity={0.6} />
      </mesh>
      <Html position={[0, 0.7, 0]} center distanceFactor={14}>
        <div className="whitespace-nowrap rounded bg-slate-950/85 px-1.5 py-0.5 font-mono text-[8px] text-cyan-300 border border-cyan-500/30 backdrop-blur">
          {label}: {valuePercent.toFixed(1)}%
        </div>
      </Html>
    </group>
  );
}

export default function FieldPlotMesh3D({
  soilMoistureVol,
  cwsiStress,
  plantSample,
  plantCount = 1000,
  onSelectPlant,
  showSensors = true,
  showScientificLabels = true,
}: FieldPlotMesh3DProps) {
  const stemsRef = useRef<THREE.InstancedMesh>(null);
  const leavesARef = useRef<THREE.InstancedMesh>(null);
  const leavesBRef = useRef<THREE.InstancedMesh>(null);
  const tasselsRef = useRef<THREE.InstancedMesh>(null);

  const [selectedPlantId, setSelectedPlantId] = useState<number | null>(null);

  // Field agronomic layout: 28 rows, 36 plants per row = 1008 plants (~1000 n)
  // Row spacing: 0.76 m (standard 30" Corn Belt rows), plant spacing in row: ~0.20 m
  const totalPlants = 1008;
  const numRows = 28;
  const plantsPerRow = 36;
  const rowSpacing = 0.76;
  const inRowSpacing = 0.45; // Spacing scaled for 3D view visibility

  const plantsData: SimulatedPlant[] = useMemo(() => {
    const list: SimulatedPlant[] = [];
    const sampleMap = new Map<number, PlantSample3D>();
    plantSample.forEach((p, idx) => {
      const pId = typeof p.plant_id === "number" ? p.plant_id : idx;
      sampleMap.set(pId % totalPlants, p);
    });

    const fieldWidth = (plantsPerRow - 1) * inRowSpacing;
    const fieldLength = (numRows - 1) * rowSpacing;

    for (let r = 0; r < numRows; r++) {
      for (let c = 0; c < plantsPerRow; c++) {
        const idx = r * plantsPerRow + c;
        // Position relative to field center
        const baseX = c * inRowSpacing - fieldWidth / 2;
        const baseZ = r * rowSpacing - fieldLength / 2;

        // Natural planting jitter
        const jitterX = ((idx * 7919) % 100) / 1000 - 0.05;
        const jitterZ = ((idx * 6271) % 100) / 1000 - 0.05;
        const posX = baseX + jitterX;
        const posZ = baseZ + jitterZ;

        // Spatial variability gradient (USDA BARC field):
        // Swale / high OM depression at (x < 0, z > 0), knoll / shallow soil at (x > 0, z < 0)
        const spatialMoistureGradient =
          Math.sin(posX * 0.18) * 0.4 - Math.cos(posZ * 0.14) * 0.4;
        const localMoisture = Math.max(
          10,
          Math.min(45, soilMoistureVol + spatialMoistureGradient * 6)
        );

        const sample = sampleMap.get(idx);
        const localStress =
          sample?.stress ??
          Math.min(
            1,
            Math.max(
              0,
              cwsiStress - spatialMoistureGradient * 0.25 + (((idx * 31) % 20) - 10) / 100
            )
          );

        const localLai =
          sample?.lai ??
          Math.max(
            1.6,
            Math.min(4.8, 3.8 + spatialMoistureGradient * 0.9 - localStress * 1.2)
          );

        // Plant height scales with LAI and stress
        const height = 1.35 + (localLai / 4.8) * 0.95;

        // Leaf color reflecting local vigor and CWSI stress
        const healthyColor = new THREE.Color("#4a8536");
        const stressedColor = new THREE.Color("#a39942");
        const plantColor = healthyColor.clone().lerp(stressedColor, localStress);

        list.push({
          id: idx + 1,
          x: posX,
          z: posZ,
          height,
          lai: localLai,
          stress: localStress,
          isHighlighted: sample !== undefined || idx === 504,
          color: plantColor,
        });
      }
    }
    return list;
  }, [totalPlants, numRows, plantsPerRow, inRowSpacing, rowSpacing, plantSample, soilMoistureVol, cwsiStress]);

  // Set initial instance matrices
  useEffect(() => {
    if (!stemsRef.current || !leavesARef.current || !leavesBRef.current || !tasselsRef.current)
      return;

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    plantsData.forEach((plant, i) => {
      // 1. Stem
      pos.set(plant.x, plant.height / 2, plant.z);
      rot.set(0, (i * 0.61) % (Math.PI * 2), 0);
      scl.set(1, plant.height, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      stemsRef.current?.setMatrixAt(i, matrix);
      stemsRef.current?.setColorAt(i, new THREE.Color("#4b7830"));

      // 2. Arching Leaves A
      pos.set(plant.x, plant.height * 0.58, plant.z);
      rot.set(0, (i * 0.61) % (Math.PI * 2), i % 2 === 0 ? 0.35 : -0.35);
      scl.set(0.85 + (plant.lai / 5.0) * 0.35, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesARef.current?.setMatrixAt(i, matrix);
      leavesARef.current?.setColorAt(i, plant.color);

      // 3. Arching Leaves B (orthogonal orientation)
      rot.set(0, ((i * 0.61) % (Math.PI * 2)) + Math.PI / 2, i % 3 === 0 ? -0.32 : 0.32);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesBRef.current?.setMatrixAt(i, matrix);
      leavesBRef.current?.setColorAt(i, plant.color);

      // 4. Apical Tassel
      pos.set(plant.x, plant.height + 0.12, plant.z);
      rot.set(0, i * 0.4, 0);
      scl.set(1, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      tasselsRef.current?.setMatrixAt(i, matrix);
      tasselsRef.current?.setColorAt(i, new THREE.Color("#d8c57b"));
    });

    [stemsRef, leavesARef, leavesBRef, tasselsRef].forEach((ref) => {
      if (ref.current) {
        ref.current.instanceMatrix.needsUpdate = true;
        if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      }
    });
  }, [plantsData]);

  // Wind sway wave simulation in useFrame
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    if (!leavesARef.current || !leavesBRef.current) return;

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    // Sample wave across subset for smooth performance
    for (let i = 0; i < plantsData.length; i += 4) {
      const plant = plantsData[i];
      // Wind wave moving diagonally across the field
      const windWave =
        Math.sin(plant.x * 0.4 + plant.z * 0.3 - time * 2.4) * 0.08;

      leavesARef.current.getMatrixAt(i, matrix);
      matrix.decompose(pos, q, scl);
      rot.setFromQuaternion(q);
      rot.z += windWave * 0.02;
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesARef.current.setMatrixAt(i, matrix);
    }
    leavesARef.current.instanceMatrix.needsUpdate = true;
  });

  // Highlighted central plant for detail inspection
  const centralPlant = plantsData[504] || plantsData[0];
  const activePlant = selectedPlantId
    ? plantsData.find((p) => p.id === selectedPlantId) || centralPlant
    : centralPlant;

  // Agricultural soil color (dark Midwestern Mollisol / silt loam)
  const soilBaseColor = soilMoistureVol > 28 ? "#3d291a" : "#5a3d28";

  return (
    <group position={[0, -0.1, 0]}>
      {/* 1. Agricultural Soil Bed Ground with Furrows */}
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, 0, 0]}>
        <planeGeometry args={[26, 26, 32, 32]} />
        <meshStandardMaterial
          color={soilBaseColor}
          roughness={0.96}
          metalness={0.02}
        />
      </mesh>

      {/* 2. Realistic Agricultural Crop Bed Furrows & Residue Rows */}
      {Array.from({ length: numRows }, (_, r) => {
        const rowZ = r * rowSpacing - ((numRows - 1) * rowSpacing) / 2;
        return (
          <group key={`row-bed-${r}`} position={[0, 0.012, rowZ]}>
            {/* Darker moist furrow groove */}
            <mesh rotation-x={-Math.PI / 2}>
              <planeGeometry args={[22.5, 0.12]} />
              <meshStandardMaterial color="#2c1d12" roughness={1} />
            </mesh>
            {/* Conservation Agriculture Mulch / Crop Residue Strip (Siembra Directa) */}
            <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0.38]}>
              <planeGeometry args={[22.2, 0.28]} />
              <meshStandardMaterial
                color="#8c7853"
                roughness={0.88}
                transparent
                opacity={0.85}
              />
            </mesh>
          </group>
        );
      })}

      {/* 3. Instanced 1000 Maize Plants (Stems, Leaves, Tassels) */}
      <instancedMesh
        ref={stemsRef}
        args={[undefined, undefined, totalPlants]}
        castShadow
      >
        <cylinderGeometry args={[0.018, 0.03, 1, 6]} />
        <meshStandardMaterial roughness={0.65} />
      </instancedMesh>

      <instancedMesh
        ref={leavesARef}
        args={[undefined, undefined, totalPlants]}
        castShadow
        receiveShadow
      >
        <planeGeometry args={[0.72, 0.14]} />
        <meshStandardMaterial side={THREE.DoubleSide} roughness={0.55} />
      </instancedMesh>

      <instancedMesh
        ref={leavesBRef}
        args={[undefined, undefined, totalPlants]}
        castShadow
        receiveShadow
      >
        <planeGeometry args={[0.72, 0.14]} />
        <meshStandardMaterial side={THREE.DoubleSide} roughness={0.55} />
      </instancedMesh>

      <instancedMesh
        ref={tasselsRef}
        args={[undefined, undefined, totalPlants]}
        castShadow
      >
        <coneGeometry args={[0.065, 0.26, 6]} />
        <meshStandardMaterial roughness={0.7} />
      </instancedMesh>

      {/* 4. Highlight Ring around Active Plant */}
      <group position={[activePlant.x, 0.02, activePlant.z]}>
        <mesh rotation-x={-Math.PI / 2}>
          <ringGeometry args={[0.32, 0.38, 32]} />
          <meshBasicMaterial color="#10b981" />
        </mesh>
        <Line
          points={[
            [0, 0, 0],
            [0, activePlant.height + 0.35, 0],
          ]}
          color="#34d399"
          lineWidth={1.5}
          dashed
          dashSize={0.1}
          gapSize={0.05}
        />
      </group>

      {/* 5. Field Instrumentation (Eddy Covariance Tower & Soil Sensors) */}
      {showSensors && (
        <>
          <EddyCovarianceTower position={[-8.5, 0, -6.5]} />
          <SoilMoistureProbeStation
            position={[6.5, 0, 5.5]}
            label="Sonda-A (Depresión)"
            valuePercent={soilMoistureVol + 3.2}
          />
          <SoilMoistureProbeStation
            position={[-5.5, 0, 7.0]}
            label="Sonda-B (Loma)"
            valuePercent={soilMoistureVol - 2.8}
          />
        </>
      )}

      {/* 6. Scientific 3D Callouts */}
      {showScientificLabels && (
        <>
          {/* Meso Field HUD */}
          <Html position={[-10.8, 3.2, -8.0]} distanceFactor={14}>
            <div className="w-68 rounded-xl border border-teal-400/40 bg-zinc-950/90 p-3 font-mono text-[10px] text-zinc-200 shadow-2xl backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-teal-500/30 pb-1">
                <span className="font-bold text-teal-300">Parcela Agrícola (Meso Nivel 2)</span>
                <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[9px] text-teal-300">
                  n=1000
                </span>
              </div>
              <div className="mt-1.5 space-y-1 text-[9px]">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Población total:</span>
                  <span className="font-bold text-zinc-100">{plantCount.toLocaleString()} plantas</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Marco de siembra:</span>
                  <span className="font-bold text-teal-200">0.76 m (30") × 0.20 m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Manejo de suelo:</span>
                  <span className="font-bold text-emerald-300">Siembra Directa (Mulch)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Torre Eddy Covariance:</span>
                  <span className="font-bold text-cyan-300">Activa (Flujo H, LE)</span>
                </div>
              </div>
            </div>
          </Html>

          {/* Active Selected Plant Card with Drilldown Button */}
          <Html
            position={[activePlant.x, activePlant.height + 0.6, activePlant.z]}
            center
            distanceFactor={11}
          >
            <div className="flex flex-col items-center gap-1.5 rounded-xl border border-emerald-400/50 bg-slate-950/92 p-2.5 font-mono text-[10px] text-emerald-100 shadow-2xl backdrop-blur-md">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="font-bold text-emerald-300">Planta #{activePlant.id}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[9px] text-zinc-300">
                <span>LAI: {activePlant.lai.toFixed(2)}</span>
                <span>Estrés: {activePlant.stress.toFixed(2)}</span>
                <span>Altura: {activePlant.height.toFixed(2)}m</span>
                <span>θ: {soilMoistureVol.toFixed(1)}%</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectPlant();
                }}
                className="mt-1 cursor-pointer rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-2.5 py-1 text-[9px] font-bold text-white shadow-md hover:from-emerald-500 hover:to-teal-500 transition active:scale-95"
              >
                Analizar FSPM Individual (Micro) →
              </button>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

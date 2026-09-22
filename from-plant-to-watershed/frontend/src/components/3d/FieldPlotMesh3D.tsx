"use client";

import React, { useEffect, useMemo, useRef } from "react";
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
  plant_height_m?: number;
  leaf_count?: number;
  leaf_area_m2?: number;
  phenological_stage?: string;
}

interface FieldPlotMesh3DProps {
  soilMoistureVol: number;
  cwsiStress: number;
  plantSample: PlantSample3D[];
  plantCount?: number;
  fieldAggregate?: Record<string, unknown>;
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
 * Torre micrometeorológica esquemática.
 * Mástil reticulado con anemómetro sónico 3D, radiómetro neto, panel solar y datalogger.
 */
function EddyCovarianceTower({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Plinto de concreto */}
      <mesh position={[0, 0.08, 0]} receiveShadow>
        <boxGeometry args={[1.1, 0.16, 1.1]} />
        <meshStandardMaterial color="#64748b" roughness={0.8} />
      </mesh>
      {/* Mástil reticulado triangular */}
      <mesh position={[0, 2.5, 0]} castShadow>
        <cylinderGeometry args={[0.05, 0.1, 4.8, 4]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.85} roughness={0.25} />
      </mesh>
      {/* Brazos transversales de instrumentación */}
      <mesh position={[0, 4.4, 0]} rotation-y={Math.PI / 4}>
        <boxGeometry args={[1.3, 0.035, 0.035]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} />
      </mesh>
      {/* Anemómetro sónico 3D */}
      <mesh position={[0.6, 4.58, 0]}>
        <cylinderGeometry args={[0.035, 0.035, 0.24, 8]} />
        <meshStandardMaterial color="#ffffff" metalness={0.4} roughness={0.2} />
      </mesh>
      {/* Radiómetro neto */}
      <mesh position={[-0.6, 4.52, 0]}>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshStandardMaterial color="#38bdf8" metalness={0.5} roughness={0.3} />
      </mesh>
      {/* Panel solar fotovoltaico */}
      <mesh position={[0.22, 3.3, 0.28]} rotation-x={-0.65} rotation-y={0.25}>
        <boxGeometry args={[0.6, 0.8, 0.025]} />
        <meshStandardMaterial color="#1e3a8a" roughness={0.15} metalness={0.92} />
      </mesh>
      {/* Gabinete del registrador de datos (Datalogger) */}
      <mesh position={[-0.18, 1.4, 0]}>
        <boxGeometry args={[0.35, 0.46, 0.25]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.35} />
      </mesh>
      {/* Baliza LED de telemetría activa */}
      <mesh position={[-0.18, 1.68, 0.14]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshBasicMaterial color="#10b981" />
      </mesh>
    </group>
  );
}

/**
 * Marcador de sonda de suelo esquemático.
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
      <mesh position={[0, 0.25, 0]} castShadow>
        <cylinderGeometry args={[0.035, 0.045, 0.5, 8]} />
        <meshStandardMaterial color="#f1f5f9" metalness={0.7} />
      </mesh>
      <mesh position={[0, 0.52, 0]}>
        <sphereGeometry args={[0.03, 8, 8]} />
        <meshBasicMaterial color="#06b6d4" />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.18, 0.26, 16]} />
        <meshBasicMaterial color="#06b6d4" transparent opacity={0.65} />
      </mesh>
      <Html position={[0, 0.8, 0]} center distanceFactor={11}>
        <div className="rounded-lg bg-zinc-950/92 px-2.5 py-1 font-mono text-[11px] text-cyan-300 border border-cyan-500/40 shadow-xl backdrop-blur whitespace-nowrap">
          {label}: <b>{valuePercent.toFixed(1)}%</b>
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
  fieldAggregate,
  onSelectPlant,
  showSensors = true,
  showScientificLabels = true,
}: FieldPlotMesh3DProps) {
  const stemsRef = useRef<THREE.InstancedMesh>(null);
  const leavesARef = useRef<THREE.InstancedMesh>(null);
  const leavesBRef = useRef<THREE.InstancedMesh>(null);
  const leavesCRef = useRef<THREE.InstancedMesh>(null);
  const tasselsRef = useRef<THREE.InstancedMesh>(null);

  // The mesh count deliberately matches the persisted population count.  Exact
  // states are available for the stored sample; the remaining instances use the
  // persisted field aggregate rather than invented spatial variability.
  const totalPlants = Math.max(1, plantCount);
  const numRows = Math.ceil(Math.sqrt(totalPlants));
  const plantsPerRow = Math.ceil(totalPlants / numRows);
  const rowSpacing = 0.76;
  const inRowSpacing = 0.20;

  const plantsData: SimulatedPlant[] = useMemo(() => {
    const list: SimulatedPlant[] = [];
    const sampleMap = new Map<number, PlantSample3D>();
    plantSample.forEach((p, idx) => {
      const pId = typeof p.plant_id === "number" ? p.plant_id : idx;
      sampleMap.set(pId % totalPlants, p);
    });

    const fieldWidth = (plantsPerRow - 1) * inRowSpacing;
    const fieldLength = (numRows - 1) * rowSpacing;
    const aggregateNumber = (name: string, fallback: number) => {
      const value = fieldAggregate?.[name];
      return typeof value === "number" && Number.isFinite(value) ? value : fallback;
    };
    const aggregateLai = aggregateNumber("mean_LAI", aggregateNumber("mean_lai", 0));
    const aggregateStress = aggregateNumber("water_stress", aggregateNumber("mean_stress", cwsiStress));
    const aggregateHeight = aggregateNumber("plant_height_mean_m", aggregateLai > 0 ? 1.45 + (aggregateLai / 4.8) * 0.95 : 0.45);

    for (let r = 0; r < numRows; r++) {
      for (let c = 0; c < plantsPerRow; c++) {
        const idx = r * plantsPerRow + c;
        if (idx >= totalPlants) break;
        const baseX = c * inRowSpacing - fieldWidth / 2;
        const baseZ = r * rowSpacing - fieldLength / 2;
        const posX = baseX;
        const posZ = baseZ;

        const sample = sampleMap.get(idx);
        const localStress = Math.min(1, Math.max(0, sample?.stress ?? aggregateStress));
        const localLai = Math.max(0, sample?.lai ?? aggregateLai);
        const height = Math.max(0.15, sample?.plant_height_m ?? aggregateHeight);

        // Tonalidad del follaje según vigor y estrés CWSI
        const healthy = new THREE.Color("#2f6e22");
        const stressed = new THREE.Color("#9ca338");
        const plantColor = healthy.clone().lerp(stressed, localStress);

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
  }, [totalPlants, numRows, plantsPerRow, inRowSpacing, rowSpacing, plantSample, cwsiStress, fieldAggregate]);

  // Inicialización de matrices de instanciación
  useEffect(() => {
    if (
      !stemsRef.current ||
      !leavesARef.current ||
      !leavesBRef.current ||
      !leavesCRef.current ||
      !tasselsRef.current
    )
      return;

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    plantsData.forEach((plant, i) => {
      // 1. Tallo
      pos.set(plant.x, plant.height / 2, plant.z);
      rot.set(0, (i * 0.61) % (Math.PI * 2), 0);
      scl.set(1, plant.height, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      stemsRef.current?.setMatrixAt(i, matrix);
      stemsRef.current?.setColorAt(i, new THREE.Color("#4a752a"));

      // 2. Hojas Nivel A (inferiores arqueadas)
      pos.set(plant.x, plant.height * 0.42, plant.z);
      rot.set(0, (i * 0.61) % (Math.PI * 2), i % 2 === 0 ? 0.38 : -0.38);
      scl.set(0.9 + (plant.lai / 5.0) * 0.35, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesARef.current?.setMatrixAt(i, matrix);
      leavesARef.current?.setColorAt(i, plant.color);

      // 3. Hojas Nivel B (medias en cruz)
      pos.set(plant.x, plant.height * 0.65, plant.z);
      rot.set(0, ((i * 0.61) % (Math.PI * 2)) + Math.PI / 2, i % 3 === 0 ? -0.34 : 0.34);
      scl.set(1.0 + (plant.lai / 5.0) * 0.3, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesBRef.current?.setMatrixAt(i, matrix);
      leavesBRef.current?.setColorAt(i, plant.color);

      // 4. Hojas Nivel C (superiores erectas hacia el sol)
      pos.set(plant.x, plant.height * 0.82, plant.z);
      rot.set(0, ((i * 0.61) % (Math.PI * 2)) + Math.PI / 4, i % 2 === 0 ? 0.22 : -0.22);
      scl.set(0.8 + (plant.lai / 5.0) * 0.25, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesCRef.current?.setMatrixAt(i, matrix);
      leavesCRef.current?.setColorAt(i, plant.color);

      // 5. Panoja apical
      pos.set(plant.x, plant.height + 0.14, plant.z);
      rot.set(0, i * 0.4, 0);
      scl.set(1, 1, 1);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      tasselsRef.current?.setMatrixAt(i, matrix);
      tasselsRef.current?.setColorAt(i, new THREE.Color("#d4be6e"));
    });

    [stemsRef, leavesARef, leavesBRef, leavesCRef, tasselsRef].forEach((ref) => {
      if (ref.current) {
        ref.current.instanceMatrix.needsUpdate = true;
        if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      }
    });
  }, [plantsData]);

  // Oleaje de viento procedural en tiempo real (efecto Honami sobre las 1,000 plantas)
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    if (!leavesBRef.current || !leavesCRef.current) return;

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    // Propagación de onda de viento diagonal a través de la parcela
    for (let i = 0; i < plantsData.length; i += 2) {
      const plant = plantsData[i];
      const wavePhase = (plant.x * 0.38 + plant.z * 0.52) - time * 2.4;
      const windWave = Math.sin(wavePhase) * 0.09;
      const microFlutter = Math.sin(wavePhase * 2.2) * 0.03;

      // Nivel B
      leavesBRef.current.getMatrixAt(i, matrix);
      matrix.decompose(pos, q, scl);
      rot.setFromQuaternion(q);
      rot.z += windWave * 0.04;
      rot.x += windWave * 0.02;
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesBRef.current.setMatrixAt(i, matrix);

      // Nivel C (superior, mayor deflexión)
      leavesCRef.current.getMatrixAt(i, matrix);
      matrix.decompose(pos, q, scl);
      rot.setFromQuaternion(q);
      rot.z += (windWave + microFlutter) * 0.06;
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesCRef.current.setMatrixAt(i, matrix);
    }
    leavesBRef.current.instanceMatrix.needsUpdate = true;
    leavesCRef.current.instanceMatrix.needsUpdate = true;
  });

  const activePlant = plantsData[504] || plantsData[0];
  const soilMoistureFactor = Math.min(1, Math.max(0, soilMoistureVol / 45));
  const soilBaseColor = soilMoistureFactor > 0.5 ? "#24160d" : "#452d1b";
  const soilRoughness = Math.max(0.42, 0.95 - soilMoistureFactor * 0.48);
  const soilMetalness = soilMoistureFactor * 0.12;

  return (
    <group position={[0, -0.12, 0]}>
      {/* 1. Suelo Agrícola con Textura de Labranza y Brillo de Humedad */}
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, 0, 0]}>
        <planeGeometry args={[27, 27, 32, 32]} />
        <meshStandardMaterial
          color={soilBaseColor}
          roughness={soilRoughness}
          metalness={soilMetalness}
        />
      </mesh>

      {/* 2. Surcos Agrícolas y Colchón de Rastrojo (Siembra Directa) */}
      {Array.from({ length: numRows }, (_, r) => {
        const rowZ = r * rowSpacing - ((numRows - 1) * rowSpacing) / 2;
        return (
          <group key={`row-bed-${r}`} position={[0, 0.012, rowZ]}>
            {/* Surco oscuro húmedo */}
            <mesh rotation-x={-Math.PI / 2}>
              <planeGeometry args={[23.2, 0.14]} />
              <meshStandardMaterial
                color="#1b0f08"
                roughness={soilRoughness * 0.8}
                metalness={soilMetalness}
              />
            </mesh>
            {/* Banda de rastrojo / mulch protector */}
            <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0.38]}>
              <planeGeometry args={[22.8, 0.3]} />
              <meshStandardMaterial color="#8a7650" roughness={0.88} transparent opacity={0.85} />
            </mesh>
          </group>
        );
      })}

      {/* 3. Población de maíz instanciada: 1,000 plantas con brillo físico PBR */}
      <instancedMesh ref={stemsRef} args={[undefined, undefined, totalPlants]} castShadow>
        <cylinderGeometry args={[0.02, 0.034, 1, 8]} />
        <meshPhysicalMaterial roughness={0.42} clearcoat={0.3} />
      </instancedMesh>

      <instancedMesh ref={leavesARef} args={[undefined, undefined, totalPlants]} castShadow receiveShadow>
        <planeGeometry args={[0.76, 0.16]} />
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.65}
          clearcoatRoughness={0.2}
        />
      </instancedMesh>

      <instancedMesh ref={leavesBRef} args={[undefined, undefined, totalPlants]} castShadow receiveShadow>
        <planeGeometry args={[0.78, 0.15]} />
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.68}
          clearcoatRoughness={0.2}
        />
      </instancedMesh>

      <instancedMesh ref={leavesCRef} args={[undefined, undefined, totalPlants]} castShadow receiveShadow>
        <planeGeometry args={[0.65, 0.13]} />
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.72}
          clearcoatRoughness={0.2}
        />
      </instancedMesh>

      <instancedMesh ref={tasselsRef} args={[undefined, undefined, totalPlants]} castShadow>
        <coneGeometry args={[0.07, 0.28, 6]} />
        <meshStandardMaterial roughness={0.55} color="#e5ce79" />
      </instancedMesh>

      {/* 4. Retículo de Selección de Planta de Muestra */}
      <group position={[activePlant.x, 0.02, activePlant.z]}>
        <mesh rotation-x={-Math.PI / 2}>
          <ringGeometry args={[0.35, 0.42, 32]} />
          <meshBasicMaterial color="#10b981" />
        </mesh>
        <Line
          points={[
            [0, 0, 0],
            [0, activePlant.height + 0.4, 0],
          ]}
          color="#34d399"
          lineWidth={1.8}
        />
      </group>

      {/* 5. Instrumentación Micrometeorológica */}
      {showSensors && (
        <>
          <EddyCovarianceTower position={[-8.8, 0, -6.8]} />
          <SoilMoistureProbeStation
            position={[7.0, 0, 5.8]}
            label="Sonda Hondonada"
            valuePercent={soilMoistureVol + 3.2}
          />
          <SoilMoistureProbeStation
            position={[-5.8, 0, 7.2]}
            label="Sonda Loma"
            valuePercent={soilMoistureVol - 2.8}
          />
        </>
      )}

      {/* 6. Tarjetas 3D Claras y Legibles */}
      {showScientificLabels && (
        <>
          <Html position={[-11.2, 3.5, -8.2]} distanceFactor={11}>
            <div
              className="rounded-xl border border-teal-400/50 bg-zinc-950/92 p-3 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "240px" }}
            >
              <div className="flex items-center justify-between border-b border-teal-500/30 pb-1.5">
                <span className="font-bold text-teal-300">Campo FSPM agregado</span>
                <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[10px] font-mono text-teal-300">
                  n={plantCount}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Marco de siembra:</span>
                  <span className="font-bold text-teal-200">0.76 m × 0.20 m (visual)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Estados individuales:</span>
                  <span className="font-bold text-emerald-300">muestra persistida + agregado</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Geometría de parcela:</span>
                  <span className="font-bold text-cyan-300">esquemática; no GIS</span>
                </div>
              </div>
            </div>
          </Html>

          <Html position={[activePlant.x, activePlant.height + 0.65, activePlant.z]} center distanceFactor={9}>
            <div
              className="flex flex-col items-center gap-1.5 rounded-xl border border-emerald-400/60 bg-zinc-950/94 p-3 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "200px" }}
            >
              <div className="flex items-center gap-1.5 font-bold text-emerald-300">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
                <span>Planta Muestreada #{activePlant.id}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono text-zinc-300">
                <span>LAI: <b>{activePlant.lai.toFixed(2)}</b></span>
                <span>Estrés: <b>{activePlant.stress.toFixed(2)}</b></span>
                <span>Altura: <b>{activePlant.height.toFixed(2)}m</b></span>
                <span>θ: <b>{soilMoistureVol.toFixed(1)}%</b></span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectPlant();
                }}
                className="mt-1.5 w-full cursor-pointer rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-3 py-1.5 text-[11px] font-bold text-white shadow-md hover:from-emerald-500 hover:to-teal-500 transition active:scale-95 text-center"
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

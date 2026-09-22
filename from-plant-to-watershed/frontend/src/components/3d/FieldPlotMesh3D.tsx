"use client";

import React, { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

const deterministicUnit = (index: number, salt = 0) => {
  const value = Math.sin((index + 1) * 12.9898 + (salt + 1) * 78.233) * 43758.5453;
  return value - Math.floor(value);
};

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
  currentDay?: number;
  totalDays?: number;
  precipMm?: number;
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
 * Lluvia volumétrica cinemática sobre la parcela meso (estelas reflectivas)
 */
function MesoRainSystem({ precipMm }: { precipMm: number }) {
  const streakCount = Math.min(1400, Math.floor(precipMm * 70) + 400);
  const linesRef = useRef<THREE.LineSegments>(null);

  const initialPositions = useMemo(() => {
    const pos = new Float32Array(streakCount * 6);
    for (let i = 0; i < streakCount; i++) {
      const x = (deterministicUnit(i, 1) - 0.5) * 24;
      const y = 0.5 + deterministicUnit(i, 2) * 16;
      const z = (deterministicUnit(i, 3) - 0.5) * 24;
      const streakLen = 0.65 + deterministicUnit(i, 4) * 0.45;

      pos[i * 6] = x;
      pos[i * 6 + 1] = y;
      pos[i * 6 + 2] = z;

      pos[i * 6 + 3] = x - 0.05;
      pos[i * 6 + 4] = y - streakLen;
      pos[i * 6 + 5] = z + 0.02;
    }
    return pos;
  }, [streakCount]);

  useFrame((_, delta) => {
    if (!linesRef.current || streakCount === 0) return;
    const pos = linesRef.current.geometry.attributes.position.array as Float32Array;
    const fallSpeed = 32.0;
    for (let i = 0; i < streakCount; i++) {
      const y1Idx = i * 6 + 1;
      const y2Idx = i * 6 + 4;
      const streakLen = pos[y1Idx] - pos[y2Idx];

      pos[y1Idx] -= fallSpeed * delta;
      pos[y2Idx] -= fallSpeed * delta;

      if (pos[y2Idx] < 0.05) {
        const newY = 15.0 + deterministicUnit(i, 5) * 2.5;
        pos[y1Idx] = newY;
        pos[y2Idx] = newY - streakLen;
      }
    }
    linesRef.current.geometry.attributes.position.needsUpdate = true;
  });

  if (precipMm < 0.25) return null;

  return (
    <lineSegments ref={linesRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[initialPositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color="#a5f3fc"
        transparent
        opacity={Math.min(0.85, 0.4 + (precipMm / 40) * 0.4)}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  );
}

/**
 * Geometría de hoja de maíz curvada en arco 3D (no un plano plano)
 */
function createCurvedMaizeLeafGeometry(length = 0.82, width = 0.16, droop = 0.28) {
  const segments = 10;
  const vertices: number[] = [];
  const indices: number[] = [];
  const uvs: number[] = [];

  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const r = length * t;
    const y = Math.sin(t * Math.PI * 0.72) * 0.18 - droop * Math.pow(t, 2.1);
    const halfW = width * Math.sin(t * Math.PI * 0.8) * Math.pow(1 - t, 0.35);

    vertices.push(-halfW, y, r);
    vertices.push(halfW, y, r);

    uvs.push(0, t);
    uvs.push(1, t);

    if (i < segments) {
      const row = i * 2;
      indices.push(row, row + 1, row + 2);
      indices.push(row + 1, row + 3, row + 2);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

/**
 * Torre micrometeorológica de covarianza de torbellinos (Eddy Covariance Tower)
 */
function EddyCovarianceTower({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      {/* Plinto de concreto */}
      <mesh position={[0, 0.08, 0]} receiveShadow>
        <boxGeometry args={[1.2, 0.16, 1.2]} />
        <meshStandardMaterial color="#64748b" roughness={0.8} />
      </mesh>
      {/* Mástil reticulado triangular */}
      <mesh position={[0, 2.5, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.11, 4.8, 4]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.85} roughness={0.25} />
      </mesh>
      {/* Brazos transversales de instrumentación */}
      <mesh position={[0, 4.4, 0]} rotation-y={Math.PI / 4}>
        <boxGeometry args={[1.4, 0.04, 0.04]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.7} />
      </mesh>
      {/* Anemómetro sónico 3D */}
      <mesh position={[0.65, 4.6, 0]}>
        <cylinderGeometry args={[0.035, 0.035, 0.26, 8]} />
        <meshStandardMaterial color="#ffffff" metalness={0.4} roughness={0.2} />
      </mesh>
      {/* Radiómetro neto */}
      <mesh position={[-0.65, 4.54, 0]}>
        <sphereGeometry args={[0.07, 8, 8]} />
        <meshStandardMaterial color="#38bdf8" metalness={0.5} roughness={0.3} />
      </mesh>
      {/* Panel solar fotovoltaico */}
      <mesh position={[0.24, 3.3, 0.3]} rotation-x={-0.65} rotation-y={0.25}>
        <boxGeometry args={[0.7, 0.9, 0.03]} />
        <meshStandardMaterial color="#1e3a8a" roughness={0.15} metalness={0.92} />
      </mesh>
      {/* Gabinete del datalogger */}
      <mesh position={[-0.2, 1.4, 0]}>
        <boxGeometry args={[0.38, 0.5, 0.28]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.35} />
      </mesh>
      {/* Baliza LED de telemetría activa con bloom */}
      <mesh position={[-0.2, 1.7, 0.15]}>
        <sphereGeometry args={[0.03, 8, 8]} />
        <meshBasicMaterial color="#10b981" />
      </mesh>
    </group>
  );
}

/**
 * Estación de sonda de humedad del suelo TDR con anillo de detección
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
        <sphereGeometry args={[0.035, 8, 8]} />
        <meshBasicMaterial color="#06b6d4" />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.015, 0]}>
        <ringGeometry args={[0.22, 0.32, 24]} />
        <meshBasicMaterial color="#06b6d4" transparent opacity={0.75} />
      </mesh>
      <Html position={[0, 0.85, 0]} center distanceFactor={11}>
        <div className="rounded-lg bg-zinc-950/94 px-2.5 py-1 font-mono text-[11px] text-cyan-300 border border-cyan-500/40 shadow-xl backdrop-blur whitespace-nowrap">
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
  currentDay = 1,
  totalDays = 365,
  precipMm = 0,
}: FieldPlotMesh3DProps) {
  const stemsRef = useRef<THREE.InstancedMesh>(null);
  const leavesARef = useRef<THREE.InstancedMesh>(null);
  const leavesBRef = useRef<THREE.InstancedMesh>(null);
  const leavesCRef = useRef<THREE.InstancedMesh>(null);
  const tasselsRef = useRef<THREE.InstancedMesh>(null);

  // Curvas de geometría de hoja en arco
  const leafGeoA = useMemo(() => createCurvedMaizeLeafGeometry(0.88, 0.17, 0.35), []);
  const leafGeoB = useMemo(() => createCurvedMaizeLeafGeometry(0.82, 0.15, 0.28), []);
  const leafGeoC = useMemo(() => createCurvedMaizeLeafGeometry(0.68, 0.13, 0.20), []);

  // Distribución balanceada que LLENA toda la parcela agrícola de 22m x 22m:
  // 26 surcos (en Z) x 39 plantas por surco (en X) = 1,014 plantas
  const numRows = 26;
  const plantsPerRow = 39;
  const totalPlants = Math.min(1014, Math.max(1, plantCount));

  const rowSpacing = 0.82; // Espacio entre surcos (m)
  const inRowSpacing = 0.54; // Espacio entre plantas en el surco (m)

  // Factor de crecimiento fenológico dependiente del día del año (Día 1 a N)
  const dayProgress = useMemo(() => {
    if (totalDays >= 300) {
      // Ciclo anual: siembra en mayo (~día 115) hasta cosecha en octubre (~día 280)
      if (currentDay < 115) return 0.08;
      if (currentDay > 280) return 1.0;
      return 0.08 + ((currentDay - 115) / 165) * 0.92;
    }
    // Temporada de 90-120 días: progresión directa completa
    return Math.min(1.0, Math.max(0.08, currentDay / Math.max(1, totalDays)));
  }, [currentDay, totalDays]);

  // Estrés biofísico acoplado a la humedad volumétrica del suelo y CWSI atmosférico
  const soilStressDeficit = Math.max(0, Math.min(1, (32 - soilMoistureVol) / 15));
  const baseStress = Math.max(cwsiStress, soilStressDeficit);

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
    const baseLai = aggregateNumber("mean_LAI", aggregateNumber("mean_lai", 3.8));
    const dynamicLai = baseLai * dayProgress;
    const dynamicHeight = (0.35 + dayProgress * 2.15) * (1 - baseStress * 0.15);

    for (let r = 0; r < numRows; r++) {
      for (let c = 0; c < plantsPerRow; c++) {
        const idx = r * plantsPerRow + c;
        if (idx >= totalPlants) break;

        const posX = c * inRowSpacing - fieldWidth / 2;
        const posZ = r * rowSpacing - fieldLength / 2;

        const sample = sampleMap.get(idx);
        // Variación espacial individual por microtopografía y microclima
        const spatialNoise = (deterministicUnit(idx, 11) - 0.5) * 0.16;
        const localStress = Math.max(0, Math.min(1, baseStress + spatialNoise));
        const localLai = Math.max(0.1, (sample?.lai ? sample.lai * dayProgress : dynamicLai));
        const plantH = Math.max(0.2, (sample?.plant_height_m ? sample.plant_height_m * dayProgress : dynamicHeight));

        // Tonalidad del follaje: verde esmeralda con turgor -> amarillo clorótico con sequía
        const healthy = new THREE.Color("#22631a");
        const stressed = new THREE.Color("#989e30");
        const plantColor = healthy.clone().lerp(stressed, localStress);

        list.push({
          id: idx + 1,
          x: posX,
          z: posZ,
          height: plantH,
          lai: localLai,
          stress: localStress,
          isHighlighted: idx === 507,
          color: plantColor,
        });
      }
    }
    return list;
  }, [totalPlants, numRows, plantsPerRow, inRowSpacing, rowSpacing, plantSample, baseStress, fieldAggregate, dayProgress]);

  // Actualización de matrices de instanciación con turgor y crecimiento
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
      // 1. Tallo botánico
      pos.set(plant.x, plant.height / 2, plant.z);
      rot.set(0, (i * 0.73) % (Math.PI * 2), 0);
      scl.set(0.8 + (plant.height / 2.5) * 0.3, plant.height, 0.8 + (plant.height / 2.5) * 0.3);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      stemsRef.current?.setMatrixAt(i, matrix);
      stemsRef.current?.setColorAt(i, new THREE.Color("#416a24"));

      // 2. Hojas Nivel A (inferiores en arco abierto)
      pos.set(plant.x, plant.height * 0.38, plant.z);
      rot.set(0, (i * 0.73) % (Math.PI * 2), plant.stress * 0.35);
      scl.set(1, 1, 0.6 + plant.height * 0.3);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesARef.current?.setMatrixAt(i, matrix);
      leavesARef.current?.setColorAt(i, plant.color);

      // 3. Hojas Nivel B (medias en cruz angular)
      pos.set(plant.x, plant.height * 0.62, plant.z);
      rot.set(0, ((i * 0.73) % (Math.PI * 2)) + Math.PI / 2, plant.stress * 0.4);
      scl.set(1, 1, 0.6 + plant.height * 0.35);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesBRef.current?.setMatrixAt(i, matrix);
      leavesBRef.current?.setColorAt(i, plant.color);

      // 4. Hojas Nivel C (superiores)
      pos.set(plant.x, plant.height * 0.82, plant.z);
      rot.set(0, ((i * 0.73) % (Math.PI * 2)) + Math.PI / 4, plant.stress * 0.3);
      scl.set(0.9, 0.9, 0.5 + plant.height * 0.28);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesCRef.current?.setMatrixAt(i, matrix);
      leavesCRef.current?.setColorAt(i, plant.color);

      // 5. Panoja apical (solo visible si la planta superó el 50% de desarrollo)
      const tasselScale = dayProgress > 0.45 ? 1 : 0.001;
      pos.set(plant.x, plant.height + 0.12, plant.z);
      rot.set(0, i * 0.4, 0);
      scl.set(tasselScale, tasselScale * 1.2, tasselScale);
      matrix.compose(pos, q.setFromEuler(rot), scl);
      tasselsRef.current?.setMatrixAt(i, matrix);
      tasselsRef.current?.setColorAt(i, new THREE.Color("#e5ce79"));
    });

    [stemsRef, leavesARef, leavesBRef, leavesCRef, tasselsRef].forEach((ref) => {
      if (ref.current) {
        ref.current.instanceMatrix.needsUpdate = true;
        if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      }
    });
  }, [plantsData, dayProgress]);

  // Oleaje de viento continuo tipo Honami
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    if (!leavesBRef.current || !leavesCRef.current) return;

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    for (let i = 0; i < plantsData.length; i += 2) {
      const plant = plantsData[i];
      const wavePhase = (plant.x * 0.36 + plant.z * 0.48) - time * 2.5;
      const windWave = Math.sin(wavePhase) * 0.085;

      leavesBRef.current.getMatrixAt(i, matrix);
      matrix.decompose(pos, q, scl);
      rot.setFromQuaternion(q);
      rot.z += windWave * 0.04;
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesBRef.current.setMatrixAt(i, matrix);

      leavesCRef.current.getMatrixAt(i, matrix);
      matrix.decompose(pos, q, scl);
      rot.setFromQuaternion(q);
      rot.z += windWave * 0.07;
      matrix.compose(pos, q.setFromEuler(rot), scl);
      leavesCRef.current.setMatrixAt(i, matrix);
    }
    leavesBRef.current.instanceMatrix.needsUpdate = true;
    leavesCRef.current.instanceMatrix.needsUpdate = true;
  });

  const activePlant = plantsData[507] || plantsData[0];
  const soilMoistureFactor = Math.min(1, Math.max(0, soilMoistureVol / 45));
  const soilBaseColor = soilMoistureFactor > 0.5 ? "#22140a" : "#422b18";
  const soilRoughness = Math.max(0.42, 0.95 - soilMoistureFactor * 0.48);
  const soilMetalness = soilMoistureFactor * 0.12;

  return (
    <group position={[0, -0.12, 0]}>
      {/* 1. Suelo Agrícola que cubre completamente el área bajo las plantas */}
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, 0, 0]}>
        <planeGeometry args={[24, 24, 32, 32]} />
        <meshStandardMaterial
          color={soilBaseColor}
          roughness={soilRoughness}
          metalness={soilMetalness}
        />
      </mesh>

      {/* 2. Surcos Agrícolas Continuos (Siembra Directa con Mulch Protector) */}
      {Array.from({ length: numRows }, (_, r) => {
        const rowZ = r * rowSpacing - ((numRows - 1) * rowSpacing) / 2;
        return (
          <group key={`row-bed-${r}`} position={[0, 0.012, rowZ]}>
            {/* Surco húmedo enriquecido */}
            <mesh rotation-x={-Math.PI / 2}>
              <planeGeometry args={[22.5, 0.16]} />
              <meshStandardMaterial
                color="#170c06"
                roughness={soilRoughness * 0.75}
                metalness={soilMetalness}
              />
            </mesh>
            {/* Franja de rastrojo protector */}
            <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0.38]}>
              <planeGeometry args={[22.0, 0.32]} />
              <meshStandardMaterial color="#8a7650" roughness={0.88} transparent opacity={0.82} />
            </mesh>
          </group>
        );
      })}

      {/* 3. Población de maíz instanciada: 1,000 plantas con geometría en arco y PBR */}
      <instancedMesh ref={stemsRef} args={[undefined, undefined, totalPlants]} castShadow>
        <cylinderGeometry args={[0.022, 0.038, 1, 8]} />
        <meshPhysicalMaterial roughness={0.4} clearcoat={0.35} />
      </instancedMesh>

      <instancedMesh ref={leavesARef} args={[leafGeoA, undefined, totalPlants]} castShadow receiveShadow>
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.7}
          clearcoatRoughness={0.18}
        />
      </instancedMesh>

      <instancedMesh ref={leavesBRef} args={[leafGeoB, undefined, totalPlants]} castShadow receiveShadow>
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.72}
          clearcoatRoughness={0.18}
        />
      </instancedMesh>

      <instancedMesh ref={leavesCRef} args={[leafGeoC, undefined, totalPlants]} castShadow receiveShadow>
        <meshPhysicalMaterial
          side={THREE.DoubleSide}
          roughness={0.28}
          clearcoat={0.75}
          clearcoatRoughness={0.18}
        />
      </instancedMesh>

      <instancedMesh ref={tasselsRef} args={[undefined, undefined, totalPlants]} castShadow>
        <coneGeometry args={[0.08, 0.32, 6]} />
        <meshStandardMaterial roughness={0.55} color="#e5ce79" />
      </instancedMesh>

      {/* 4. Retículo de Selección de Planta de Muestra */}
      <group position={[activePlant.x, 0.02, activePlant.z]}>
        <mesh rotation-x={-Math.PI / 2}>
          <ringGeometry args={[0.35, 0.44, 32]} />
          <meshBasicMaterial color="#10b981" />
        </mesh>
        <Line
          points={[
            [0, 0, 0],
            [0, activePlant.height + 0.45, 0],
          ]}
          color="#34d399"
          lineWidth={2.0}
        />
      </group>

      {/* 5. Instrumentación Micrometeorológica */}
      {showSensors && (
        <>
          <EddyCovarianceTower position={[-9.5, 0, -8.5]} />
          <SoilMoistureProbeStation
            position={[8.2, 0, 7.5]}
            label="Sonda Hondonada"
            valuePercent={soilMoistureVol + 2.8}
          />
          <SoilMoistureProbeStation
            position={[-7.5, 0, 8.2]}
            label="Sonda Loma"
            valuePercent={soilMoistureVol - 2.5}
          />
        </>
      )}

      {/* 6. Rótulos Científicos */}
      {showScientificLabels && (
        <>
          <Html position={[-10.8, 3.8, -9.5]} distanceFactor={11}>
            <div
              className="rounded-xl border border-teal-400/50 bg-zinc-950/92 p-3 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "240px" }}
            >
              <div className="flex items-center justify-between border-b border-teal-500/30 pb-1.5">
                <span className="font-bold text-teal-300">Población de Campo Meso</span>
                <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[10px] font-mono text-teal-300">
                  n=1,000 plantas
                </span>
              </div>
              <div className="mt-2 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Marco de siembra:</span>
                  <span className="font-bold text-teal-200">0.82 m × 0.54 m (completo)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Desarrollo fenológico:</span>
                  <span className="font-bold text-emerald-300">{(dayProgress * 100).toFixed(0)}% (Día {currentDay})</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Estrés hídrico CWSI:</span>
                  <span className={`font-bold ${cwsiStress > 0.3 ? "text-amber-400" : "text-emerald-300"}`}>
                    {cwsiStress.toFixed(2)} {cwsiStress > 0.3 ? "⚠️ Sequía" : "✓ Óptimo"}
                  </span>
                </div>
              </div>
            </div>
          </Html>

          <Html position={[activePlant.x, activePlant.height + 0.65, activePlant.z]} center distanceFactor={9}>
            <div
              className="flex flex-col items-center gap-1.5 rounded-xl border border-emerald-400/60 bg-zinc-950/94 p-3 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "205px" }}
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

      {/* 7. Lluvia volumétrica activa sobre el cultivo */}
      <MesoRainSystem precipMm={precipMm} />
    </group>
  );
}

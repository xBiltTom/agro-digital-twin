"use client";

// Surcos e instrumentación contextual recuperados de 6c1477f; la sonda no representa una observación.
import { Html } from "@react-three/drei";
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export function createCurvedMaizeLeafGeometry(length = 0.82, width = 0.16, droop = 0.28) {
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
export function EddyCovarianceTower({ position }: { position: [number, number, number] }) {
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
export function SoilMoistureProbeStation({
  position,
  label,
  valuePercent,
}: {
  position: [number, number, number];
  label: string;
  valuePercent: number | null;
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
          {label}: <b>{valuePercent === null ? "Sin dato" : `${valuePercent.toFixed(1)}% vol`}</b>
        </div>
      </Html>
    </group>
  );
}

const deterministicUnit = (index: number, salt = 0) => {
  const value = Math.sin((index + 1) * 12.9898 + (salt + 1) * 78.233) * 43758.5453;
  return value - Math.floor(value);
};

export function MesoRainSystem({ precipMm }: { precipMm: number }) {
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

  if (precipMm <= 0) return null;

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

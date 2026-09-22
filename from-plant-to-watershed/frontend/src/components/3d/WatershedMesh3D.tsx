"use client";

import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

const deterministicUnit = (index: number, salt = 0) => {
  const value = Math.sin((index + 1) * 12.9898 + (salt + 1) * 78.233) * 43758.5453;
  return value - Math.floor(value);
};

export interface HruSummary {
  hru_id?: string;
  hru_number?: number;
  area_fraction?: number;
  crop?: string;
  soil_type?: string;
}

interface WatershedMesh3DProps {
  streamflowM3s: number;
  precipMm: number;
  soilMoistureVol: number;
  hruAggregates?: { hrus?: HruSummary[]; results?: HruSummary[] };
  watershedName?: string;
  stationId?: string | null;
  evidenceType?: string;
  onSelectSubbasin: () => void;
  showHruBorders?: boolean;
  showHydrologyFlow?: boolean;
  showScientificLabels?: boolean;
}

/**
 * Schematic watershed context. The app currently does not persist SWAT+ GIS
 * polygons for the viewer, so this is intentionally never presented as a DEM.
 */
function WatershedCatchmentTerrain() {
  const geometry = useMemo(() => {
    const width = 58;
    const height = 46;
    const segX = 120;
    const segY = 96;
    const geo = new THREE.PlaneGeometry(width, height, segX, segY);
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    const valleyCol = new THREE.Color("#1f381c");
    const ridgeCol = new THREE.Color("#5a7433");
    const cropCol = new THREE.Color("#375b24");
    const cropCol2 = new THREE.Color("#4a6a2c");

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);

      // Crestas de divisoria de aguas en los bordes de la cuenca
      const edgeX = Math.abs(x) / (width / 2);
      const edgeY = Math.abs(y) / (height / 2);
      const boundaryRidge =
        Math.pow(edgeX, 2.6) * 4.4 + Math.pow(edgeY, 2.4) * 3.8;

      // Incisión del valle fluvial meándrico principal
      const riverPathX = -18 + (y + height / 2) * 0.74 + Math.sin(y * 0.16) * 3.8;
      const distToRiver = Math.abs(x - riverPathX);
      const valleyCarve = -Math.exp(-Math.pow(distToRiver / 4.6, 2)) * 1.95;

      // Topografía glacial ondulada suave típica de Iowa (Des Moines Lobe)
      const rolling =
        Math.sin(x * 0.19) * Math.cos(y * 0.16) * 1.35 +
        Math.sin(x * 0.4 + y * 0.24) * 0.65 +
        Math.cos(x * 0.09 - y * 0.14) * 0.85;

      const elevation = Math.max(-0.58, boundaryRidge + valleyCarve + rolling);
      pos.setZ(i, elevation);

      const normElev = Math.min(1, Math.max(0, (elevation + 0.58) / 5.8));
      
      // Mosaico de parcelas y fondo de valle
      const parcelPattern = (Math.sin(x * 0.8) * Math.cos(y * 0.8) > 0.1) ? cropCol : cropCol2;
      const vertexColor =
        normElev < 0.32
          ? valleyCol.clone().lerp(parcelPattern, normElev / 0.32)
          : parcelPattern.clone().lerp(ridgeCol, (normElev - 0.32) / 0.68);

      colors[i * 3] = vertexColor.r;
      colors[i * 3 + 1] = vertexColor.g;
      colors[i * 3 + 2] = vertexColor.b;
    }

    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return geo;
  }, []);

  return (
    <mesh geometry={geometry} rotation-x={-Math.PI / 2} receiveShadow>
      <meshStandardMaterial vertexColors roughness={0.88} metalness={0.06} />
    </mesh>
  );
}

/**
 * Superficie Fluvial 3D Fotorrealista con Curvatura Suave, Ondas Viajeras y Reflejos Físicos
 */
function RealisticRiverSurface3D({
  points,
  width,
  streamflowM3s,
}: {
  points: [number, number, number][];
  width: number;
  streamflowM3s: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const flowSpeed = Math.min(3.2, 0.9 + (streamflowM3s / 12) * 0.4);

  const { geometry, foamLineLeft, foamLineRight } = useMemo(() => {
    const vectors = points.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    const curve = new THREE.CatmullRomCurve3(vectors);
    const divisions = 68;
    const curvePoints = curve.getPoints(divisions);

    const vertices: number[] = [];
    const indices: number[] = [];
    const uvs: number[] = [];
    const leftFoam: [number, number, number][] = [];
    const rightFoam: [number, number, number][] = [];
    const up = new THREE.Vector3(0, 1, 0);

    for (let i = 0; i <= divisions; i++) {
      const p = curvePoints[i];
      const t = i / divisions;
      const tangent = curve.getTangent(t).normalize();
      const binormal = new THREE.Vector3().crossVectors(tangent, up).normalize();

      const halfW = (width * 0.5) * (0.88 + Math.sin(t * Math.PI * 3.5) * 0.12);

      const left = new THREE.Vector3().copy(p).addScaledVector(binormal, halfW);
      const right = new THREE.Vector3().copy(p).addScaledVector(binormal, -halfW);

      vertices.push(left.x, left.y + 0.05, left.z);
      vertices.push(right.x, right.y + 0.05, right.z);

      uvs.push(0, t * 8);
      uvs.push(1, t * 8);

      leftFoam.push([left.x, left.y + 0.055, left.z]);
      rightFoam.push([right.x, right.y + 0.055, right.z]);

      if (i < divisions) {
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

    return { geometry: geo, foamLineLeft: leftFoam, foamLineRight: rightFoam };
  }, [points, width]);

  // Física de oleaje y corriente en tiempo real
  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const time = clock.getElapsedTime() * flowSpeed;
    const pos = meshRef.current.geometry.attributes.position;

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const wave = Math.sin(x * 0.7 + z * 0.5 - time * 2.5) * 0.025;
      const ripple = Math.sin(x * 2.2 - z * 1.9 + time * 4.0) * 0.012;
      pos.setY(i, pos.getY(i) + (wave + ripple) * 0.006);
    }
    pos.needsUpdate = true;
  });

  return (
    <group>
      {/* Lámina de agua 3D con refracción, Fresnel y reflejos de cielo */}
      <mesh ref={meshRef} geometry={geometry} receiveShadow>
        <meshPhysicalMaterial
          color="#0284c7"
          roughness={0.06}
          metalness={0.05}
          clearcoat={1.0}
          clearcoatRoughness={0.03}
          transmission={0.46}
          ior={1.333}
          specularIntensity={1.0}
          transparent
          opacity={0.93}
        />
      </mesh>

      {/* Líneas de espuma en las orillas ribereñas */}
      <Line points={foamLineLeft} color="#bae6fd" lineWidth={1.8} transparent opacity={0.7} />
      <Line points={foamLineRight} color="#bae6fd" lineWidth={1.8} transparent opacity={0.7} />
    </group>
  );
}

/**
 * Parcela HRU con textura de surcos agrícolas y contorno luminoso
 */
function AgriculturalHruParcel({
  position,
  size,
  color,
  rotation = 0,
  onClick,
}: {
  position: [number, number, number];
  size: [number, number];
  color: string;
  rotation?: number;
  onClick?: () => void;
}) {
  const rows = Math.max(4, Math.round(size[1] / 1.1));

  return (
    <group
      position={position}
      rotation-y={rotation}
      onClick={(e) => {
        if (onClick) {
          e.stopPropagation();
          onClick();
        }
      }}
    >
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={size} />
        <meshStandardMaterial color={color} roughness={0.88} />
      </mesh>

      {/* Surcos agrícolas texturizados */}
      {Array.from({ length: rows }, (_, r) => (
        <mesh
          key={r}
          rotation-x={-Math.PI / 2}
          position={[0, 0.02, -size[1] / 2 + 0.6 + r * (size[1] - 1.2) / (rows - 1)]}
        >
          <planeGeometry args={[size[0] * 0.96, 0.08]} />
          <meshStandardMaterial color="#273f1f" roughness={0.9} />
        </mesh>
      ))}

      {/* Borde perimetral de la unidad HRU */}
      <Line
        points={[
          [-size[0] / 2, 0.04, -size[1] / 2],
          [size[0] / 2, 0.04, -size[1] / 2],
          [size[0] / 2, 0.04, size[1] / 2],
          [-size[0] / 2, 0.04, size[1] / 2],
          [-size[0] / 2, 0.04, -size[1] / 2],
        ]}
        color="#86efac"
        lineWidth={1.3}
        transparent
        opacity={0.7}
      />
    </group>
  );
}

/**
 * Bosque de Galería Ribereño (Riparian Buffer) protegiendo el río
 */
function RiparianTreeBelt({
  curvePoints,
  treeCount = 26,
}: {
  curvePoints: [number, number, number][];
  treeCount?: number;
}) {
  const treePositions = useMemo(() => {
    const list: Array<[number, number, number]> = [];
    for (let i = 0; i < treeCount; i++) {
      const t = i / (treeCount - 1);
      const ptIdx = Math.min(curvePoints.length - 2, Math.floor(t * (curvePoints.length - 1)));
      const p1 = curvePoints[ptIdx];
      const p2 = curvePoints[ptIdx + 1];
      const localT = t * (curvePoints.length - 1) - ptIdx;

      const x = p1[0] + (p2[0] - p1[0]) * localT + (i % 2 === 0 ? 0.8 : -0.8);
      const y = p1[1] + (p2[1] - p1[1]) * localT + 0.15;
      const z = p1[2] + (p2[2] - p1[2]) * localT + (i % 3 === 0 ? 0.45 : -0.45);
      list.push([x, y, z]);
    }
    return list;
  }, [curvePoints, treeCount]);

  return (
    <group>
      {treePositions.map((pos, idx) => (
        <group key={`tree-${idx}`} position={pos}>
          <mesh position={[0, 0.32, 0]} castShadow>
            <cylinderGeometry args={[0.045, 0.07, 0.65, 6]} />
            <meshStandardMaterial color="#423124" roughness={0.8} />
          </mesh>
          <mesh position={[0, 0.82, 0]} castShadow>
            <sphereGeometry args={[0.36 + (idx % 3) * 0.06, 8, 8]} />
            <meshStandardMaterial color="#1a4a24" roughness={0.65} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/**
 * Estación de Aforo Fluvial USGS (#05451210) en Desagüe
 */
function UsgsGaugingStation({
  position,
  streamflowM3s,
  stationId,
  evidenceType,
}: {
  position: [number, number, number];
  streamflowM3s: number;
  stationId?: string | null;
  evidenceType?: string;
}) {
  return (
    <group position={position}>
      {/* Vertedero de concreto */}
      <mesh position={[0, 0.28, 0]} receiveShadow>
        <boxGeometry args={[2.4, 0.55, 1.5]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.8} />
      </mesh>
      {/* Caseta de aforo USGS */}
      <mesh position={[-0.75, 1.05, -0.25]} castShadow>
        <boxGeometry args={[0.7, 0.95, 0.7]} />
        <meshStandardMaterial color="#e2e8f0" roughness={0.4} />
      </mesh>
      {/* Panel solar */}
      <mesh position={[-0.75, 1.58, -0.25]} rotation-x={-0.55}>
        <boxGeometry args={[0.6, 0.6, 0.025]} />
        <meshStandardMaterial color="#1e3a8a" metalness={0.9} roughness={0.2} />
      </mesh>
      {/* Mástil y antena */}
      <mesh position={[-0.75, 2.05, -0.25]}>
        <cylinderGeometry args={[0.015, 0.015, 0.95, 6]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} />
      </mesh>

      {/* Cartel USGS Nítido y Proporcionado */}
      <Html position={[0, 2.1, 0]} center distanceFactor={14}>
        <div
          className="flex flex-col items-center rounded-xl border border-cyan-400/60 bg-zinc-950/94 p-3 font-sans text-xs text-cyan-200 shadow-2xl backdrop-blur-md whitespace-nowrap"
          style={{ minWidth: "190px" }}
        >
          <div className="flex items-center gap-1.5 font-bold text-cyan-300">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span>{stationId ? `USGS Gage #${stationId}` : "Outlet de simulación"}</span>
          </div>
          <div className="mt-1 text-zinc-200 font-mono text-[11px]">
            Caudal Q: <b className="text-teal-300 text-xs">{streamflowM3s.toFixed(2)} m³/s</b>
          </div>
          <div className="text-zinc-400 font-mono text-[10px] mt-0.5">
            {evidenceType ? `${evidenceType} · caudal simulado` : "caudal del modelo"}
          </div>
        </div>
      </Html>
    </group>
  );
}

/**
 * Lluvia 3D Volumétrica
 */
function PrecipitationRainSystem({ precipMm }: { precipMm: number }) {
  const count = Math.min(500, Math.floor(precipMm * 30));
  const pointsRef = useRef<THREE.Points>(null);

  const initialPositions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (deterministicUnit(i, 1) - 0.5) * 50;
      pos[i * 3 + 1] = deterministicUnit(i, 2) * 24;
      pos[i * 3 + 2] = (deterministicUnit(i, 3) - 0.5) * 40;
    }
    return pos;
  }, [count]);

  useFrame((_, delta) => {
    if (!pointsRef.current || count === 0) return;
    const pos = pointsRef.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < count; i++) {
      const yIdx = i * 3 + 1;
      pos[yIdx] -= 28 * delta;
      if (pos[yIdx] < 0.1) {
        pos[yIdx] = 20 + deterministicUnit(i, 4) * 4;
      }
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  if (precipMm < 0.5) return null;

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[initialPositions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.065}
        color="#7dd3fc"
        transparent
        opacity={0.7}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export default function WatershedMesh3D({
  streamflowM3s,
  precipMm,
  soilMoistureVol,
  hruAggregates,
  watershedName,
  stationId,
  evidenceType,
  onSelectSubbasin,
  showHruBorders = true,
  showHydrologyFlow = true,
  showScientificLabels = true,
}: WatershedMesh3DProps) {
  const hruCount = hruAggregates?.results?.length ?? hruAggregates?.hrus?.length ?? 0;
  const riverPoints: [number, number, number][] = useMemo(
    () => [
      [-22, 1.45, 16],
      [-16, 0.95, 12],
      [-10, 0.58, 7],
      [-4, 0.35, 3],
      [3, 0.18, -1],
      [10, 0.08, -6],
      [17, -0.02, -10],
      [22, -0.12, -13.5],
    ],
    []
  );

  const tributaryPoints: [number, number, number][] = useMemo(
    () => [
      [-16, 1.65, -14],
      [-11, 0.98, -8],
      [-6, 0.58, -3],
      [3, 0.18, -1],
    ],
    []
  );

  const riverWidth = Math.min(1.25, 0.3 + (streamflowM3s / 35) * 0.65);

  return (
    <group position={[0, -0.38, 0]}>
      {/* 1. Contexto visual esquemático; no es un DEM ni polígonos SWAT+ */}
      <WatershedCatchmentTerrain />

      {/* 2. Parcelas esquemáticas: la geometría HRU no está persistida en la API */}
      <AgriculturalHruParcel
        position={[-9, 0.58, 6]}
        size={[14.5, 12.5]}
        color="#548238"
        rotation={-0.12}
        onClick={onSelectSubbasin}
      />

      <AgriculturalHruParcel
        position={[8, 0.48, 7]}
        size={[12.5, 11.5]}
        color="#8c8442"
        rotation={0.14}
      />

      <AgriculturalHruParcel
        position={[-12, 1.2, -9]}
        size={[13.5, 10.5]}
        color="#6b8244"
        rotation={0.18}
      />

      <AgriculturalHruParcel
        position={[11, 0.25, -8]}
        size={[11.5, 9.5]}
        color="#467034"
        rotation={-0.15}
      />

      {/* 3. Bosque Ribereño */}
      <RiparianTreeBelt curvePoints={riverPoints} treeCount={26} />

      {/* 4. Red Fluvial 3D Físico con Shader de Ondas y Reflejos */}
      <RealisticRiverSurface3D points={riverPoints} width={riverWidth * 2.2} streamflowM3s={streamflowM3s} />
      <RealisticRiverSurface3D points={tributaryPoints} width={riverWidth * 1.3} streamflowM3s={streamflowM3s * 0.4} />

      {/* 5. Aforo USGS */}
      <UsgsGaugingStation position={[22, -0.12, -13.5]} streamflowM3s={streamflowM3s} stationId={stationId} evidenceType={evidenceType} />

      {/* 6. Lluvia 3D */}
      {showHydrologyFlow && <PrecipitationRainSystem precipMm={precipMm} />}

      {/* 7. Tarjetas 3D Claras y Visibles */}
      {showScientificLabels && (
        <>
          <Html position={[-20, 4.2, 14]} distanceFactor={15}>
            <div
              className="rounded-xl border border-cyan-400/50 bg-zinc-950/94 p-3.5 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "260px" }}
            >
              <div className="flex items-center justify-between border-b border-cyan-500/30 pb-1.5">
                <span className="font-bold text-cyan-300">{watershedName ?? "Cuenca"} · contexto macro</span>
                <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] font-mono text-cyan-300">
                  Nivel 3
                </span>
              </div>
              <div className="mt-2 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Precipitación:</span>
                  <span className="font-bold text-sky-300">{precipMm.toFixed(1)} mm/d</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Humedad media θ:</span>
                  <span className="font-bold text-teal-300">{soilMoistureVol.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Caudal modelado (Q):</span>
                  <span className="font-bold text-cyan-300 text-xs">{streamflowM3s.toFixed(2)} m³/s</span>
                </div>
                <div className="mt-1.5 border-t border-zinc-800 pt-1 text-emerald-300 font-sans text-[11px]">
                  Vista esquemática: {hruCount ? `${hruCount} resultados HRU disponibles` : "geometrías HRU no disponibles en API"}.
                </div>
              </div>
            </div>
          </Html>

          <Html position={[-9, 1.8, 6]} center distanceFactor={14}>
            <div
              onClick={(e) => {
                e.stopPropagation();
                onSelectSubbasin();
              }}
              className="cursor-pointer rounded-xl border border-emerald-400/60 bg-zinc-950/94 px-3 py-2 font-sans text-xs text-emerald-300 shadow-xl backdrop-blur transition hover:scale-105 hover:border-emerald-300 text-center"
              style={{ minWidth: "170px" }}
            >
              <div className="font-bold flex items-center justify-center gap-1">
                <span>{hruCount ? `${hruCount} HRUs SWAT+` : "HRUs esquemáticos"}</span>
                <span>→</span>
              </div>
              <div className="text-[10px] text-zinc-300 font-mono mt-0.5">Explorar estado FSPM de campo</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

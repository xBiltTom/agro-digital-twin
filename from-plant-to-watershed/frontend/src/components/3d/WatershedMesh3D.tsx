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
  currentDay?: number;
  totalDays?: number;
}

/**
 * Función analítica de elevación del terreno de la cuenca (South Fork Iowa River basin).
 * Proporciona elevación Y consistente para el terreno, río, parcelas e infraestructura.
 */
export function getTerrainElevation(x: number, z: number): number {
  const width = 58;
  const height = 46;
  const y = -z;

  const edgeX = Math.abs(x) / (width / 2);
  const edgeY = Math.abs(y) / (height / 2);
  // Crestas delimitadoras de cuenca en los extremos
  const boundaryRidge = Math.pow(edgeX, 2.8) * 3.4 + Math.pow(edgeY, 2.6) * 3.0;

  // Meandro del río principal
  const riverPathX = -18 + (y + height / 2) * 0.74 + Math.sin(y * 0.16) * 3.8;
  const distToRiver = Math.abs(x - riverPathX);
  // Incisión natural del cauce fluvial
  const valleyCarve = -Math.exp(-Math.pow(distToRiver / 4.8, 2)) * 1.85;

  // Suaves ondulaciones de relieve glacial (swales and swells)
  const rolling =
    Math.sin(x * 0.18) * Math.cos(y * 0.15) * 0.95 +
    Math.sin(x * 0.38 + y * 0.22) * 0.45 +
    Math.cos(x * 0.08 - y * 0.12) * 0.55;

  return Math.max(-0.52, boundaryRidge + valleyCarve + rolling);
}

/**
 * Trayectoria analítica central del río en función de Z
 */
export function getRiverPathX(z: number): number {
  const y = -z;
  const height = 46;
  return -18 + (y + height / 2) * 0.74 + Math.sin(y * 0.16) * 3.8;
}

/**
 * Terreno de Cuenca Hidrográfica con Relieve Físico Continuo
 */
function WatershedCatchmentTerrain({ soilMoistureVol }: { soilMoistureVol: number }) {
  const moistureFactor = Math.min(1, Math.max(0, soilMoistureVol / 45));

  const geometry = useMemo(() => {
    const width = 58;
    const height = 46;
    const segX = 120;
    const segY = 96;
    const geo = new THREE.PlaneGeometry(width, height, segX, segY);
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    const valleyCol = new THREE.Color("#183214");
    const ridgeCol = new THREE.Color("#556d2e");
    const cropCol = new THREE.Color("#2f521e");
    const cropCol2 = new THREE.Color("#415f25");

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const zWorld = -y;

      const elevation = getTerrainElevation(x, zWorld);
      pos.setZ(i, elevation);

      const normElev = Math.min(1, Math.max(0, (elevation + 0.52) / 5.2));
      const parcelPattern = (Math.sin(x * 0.75) * Math.cos(y * 0.75) > 0.05) ? cropCol : cropCol2;

      const vertexColor =
        normElev < 0.28
          ? valleyCol.clone().lerp(parcelPattern, normElev / 0.28)
          : parcelPattern.clone().lerp(ridgeCol, (normElev - 0.28) / 0.72);

      colors[i * 3] = vertexColor.r;
      colors[i * 3 + 1] = vertexColor.g;
      colors[i * 3 + 2] = vertexColor.b;
    }

    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return geo;
  }, []);

  const terrainRoughness = Math.max(0.48, 0.88 - moistureFactor * 0.35);

  return (
    <mesh geometry={geometry} rotation-x={-Math.PI / 2} receiveShadow>
      <meshStandardMaterial
        vertexColors
        roughness={terrainRoughness}
        metalness={moistureFactor * 0.1}
      />
    </mesh>
  );
}

/**
 * Superficie Fluvial 3D Sólida con Malla Continua Multiseccional, Ondas Físicas y Caudal Q Dinámico
 */
function RealisticRiverSurface3D({
  streamflowM3s,
}: {
  streamflowM3s: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const flowSpeed = Math.min(3.5, 1.0 + Math.sqrt(Math.max(0.1, streamflowM3s)) * 0.4);
  // Ancho y calado dinámicos según el caudal Q modelado en la cuenca
  const riverWidth = Math.min(5.8, 2.2 + Math.pow(Math.max(0.1, streamflowM3s), 0.38) * 0.52);
  const waterStage = 0.32 + Math.min(0.85, Math.pow(Math.max(0.1, streamflowM3s), 0.35) * 0.18);

  const geometry = useMemo(() => {
    const divisions = 90;
    const crossSegs = 4; // 5 vértices transversales para una superficie plana horizontal en cada corte
    const startZ = 18.5;
    const endZ = -18.5;
    const stepZ = (endZ - startZ) / divisions;

    const vertices: number[] = [];
    const indices: number[] = [];
    const uvs: number[] = [];

    const centerPoints: Array<{ x: number; y: number; z: number }> = [];
    for (let i = 0; i <= divisions; i++) {
      const z = startZ + i * stepZ;
      const x = getRiverPathX(z);
      const bedY = getTerrainElevation(x, z);
      // La superficie del agua es horizontal sobre el fondo del lecho
      centerPoints.push({ x, y: bedY + waterStage, z });
    }

    for (let i = 0; i <= divisions; i++) {
      const p = centerPoints[i];
      const prev = centerPoints[Math.max(0, i - 1)];
      const next = centerPoints[Math.min(divisions, i + 1)];

      const tangent = new THREE.Vector3(next.x - prev.x, 0, next.z - prev.z).normalize();
      const binormal = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();

      const halfW = riverWidth * 0.5;

      for (let j = 0; j <= crossSegs; j++) {
        const u = j / crossSegs;
        const offset = (u - 0.5) * riverWidth;
        const vx = p.x + binormal.x * offset;
        const vz = p.z + binormal.z * offset;
        // Superficie nivelada horizontalmente a la cota del agua
        vertices.push(vx, p.y, vz);
        uvs.push(u, (i / divisions) * 12);
      }

      if (i < divisions) {
        for (let j = 0; j < crossSegs; j++) {
          const row1 = i * (crossSegs + 1) + j;
          const row2 = (i + 1) * (crossSegs + 1) + j;
          indices.push(row1, row2, row1 + 1);
          indices.push(row1 + 1, row2, row2 + 1);
        }
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    return geo;
  }, [riverWidth, waterStage]);

  // Animación física de corriente fluvial continua y ondas de flujo
  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const time = clock.getElapsedTime() * flowSpeed;
    const pos = meshRef.current.geometry.attributes.position;
    const count = pos.count;

    for (let i = 0; i < count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const wave = Math.sin(x * 0.75 + z * 0.55 - time * 2.8) * 0.018;
      const ripple = Math.sin(x * 2.2 - z * 1.8 + time * 4.6) * 0.009;
      pos.setY(i, pos.getY(i) + (wave + ripple) * 0.004);
    }
    pos.needsUpdate = true;
  });

  return (
    <group>
      {/* Lámina de agua continua con reflejos especulares físicos y Fresnel */}
      <mesh ref={meshRef} geometry={geometry} receiveShadow>
        <meshStandardMaterial
          color="#0284c7"
          roughness={0.06}
          metalness={0.22}
          transparent
          opacity={0.92}
        />
      </mesh>
    </group>
  );
}

/**
 * Parcela HRU de alta resolución que se adapta (drapes) milimétricamente al relieve
 * y NUNCA queda oculta bajo las colinas.
 */
function AgriculturalHruParcel({
  center,
  size,
  color,
  onClick,
}: {
  center: [number, number];
  size: [number, number];
  color: string;
  onClick?: () => void;
}) {
  const { geometry, outlinePoints } = useMemo(() => {
    // Malla fina densa que sigue fielmente la curvatura continua del terreno
    const segX = 36;
    const segZ = 30;
    const vertices: number[] = [];
    const indices: number[] = [];
    const outline: [number, number, number][] = [];

    const halfW = size[0] / 2;
    const halfL = size[1] / 2;

    for (let iz = 0; iz <= segZ; iz++) {
      for (let ix = 0; ix <= segX; ix++) {
        const u = ix / segX;
        const v = iz / segZ;
        const x = center[0] - halfW + u * size[0];
        const z = center[1] - halfL + v * size[1];
        // Elevado exactamente +0.095m sobre el terreno para garantizar visibilidad total
        const y = getTerrainElevation(x, z) + 0.095;

        vertices.push(x, y, z);

        if (ix < segX && iz < segZ) {
          const row1 = iz * (segX + 1) + ix;
          const row2 = (iz + 1) * (segX + 1) + ix;
          indices.push(row1, row2, row1 + 1);
          indices.push(row1 + 1, row2, row2 + 1);
        }
      }
    }

    // Puntos perimetrales elevados para contorno nítido
    for (let ix = 0; ix <= segX; ix++) {
      const x = center[0] - halfW + (ix / segX) * size[0];
      const z = center[1] - halfL;
      outline.push([x, getTerrainElevation(x, z) + 0.12, z]);
    }
    for (let iz = 0; iz <= segZ; iz++) {
      const x = center[0] + halfW;
      const z = center[1] - halfL + (iz / segZ) * size[1];
      outline.push([x, getTerrainElevation(x, z) + 0.12, z]);
    }
    for (let ix = segX; ix >= 0; ix--) {
      const x = center[0] - halfW + (ix / segX) * size[0];
      const z = center[1] + halfL;
      outline.push([x, getTerrainElevation(x, z) + 0.12, z]);
    }
    for (let iz = segZ; iz >= 0; iz--) {
      const x = center[0] - halfW;
      const z = center[1] - halfL + (iz / segZ) * size[1];
      outline.push([x, getTerrainElevation(x, z) + 0.12, z]);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    return { geometry: geo, outlinePoints: outline };
  }, [center, size]);

  return (
    <group
      onClick={(e) => {
        if (onClick) {
          e.stopPropagation();
          onClick();
        }
      }}
    >
      <mesh geometry={geometry} receiveShadow>
        <meshStandardMaterial color={color} roughness={0.82} />
      </mesh>
      {/* Borde perimetral adaptado a la topografía */}
      <Line
        points={outlinePoints}
        color="#86efac"
        lineWidth={1.8}
        transparent
        opacity={0.85}
      />
    </group>
  );
}

/**
 * Bosque de Galería Ribereño (Riparian Buffer) con árboles que se adaptan a la cota del río
 */
function RiparianTreeBelt({ treeCount = 28 }: { treeCount?: number }) {
  const treePositions = useMemo(() => {
    const list: Array<[number, number, number]> = [];
    for (let i = 0; i < treeCount; i++) {
      const t = i / (treeCount - 1);
      const z = 16 - t * 32;
      const riverX = getRiverPathX(z);
      const sideOffset = (i % 2 === 0 ? 1.8 : -1.8) + (i % 3 === 0 ? 0.5 : -0.5);
      const x = riverX + sideOffset;
      const y = getTerrainElevation(x, z) + 0.05;
      list.push([x, y, z]);
    }
    return list;
  }, [treeCount]);

  return (
    <group>
      {treePositions.map((pos, idx) => (
        <group key={`tree-${idx}`} position={pos}>
          {/* Tronco */}
          <mesh position={[0, 0.35, 0]} castShadow>
            <cylinderGeometry args={[0.06, 0.09, 0.7, 6]} />
            <meshStandardMaterial color="#38281d" roughness={0.8} />
          </mesh>
          {/* Copa foliar densa */}
          <mesh position={[0, 0.95, 0]} castShadow>
            <sphereGeometry args={[0.42 + (idx % 3) * 0.07, 8, 8]} />
            <meshStandardMaterial color={idx % 2 === 0 ? "#1c4a22" : "#265d2c"} roughness={0.6} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/**
 * Estación de Aforo Fluvial USGS (#05451210) sobre el vertedero del río
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
      {/* Vertedero de concreto hidráulico */}
      <mesh position={[0, 0.28, 0]} receiveShadow>
        <boxGeometry args={[3.2, 0.65, 1.8]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.7} />
      </mesh>
      {/* Caseta de aforo USGS */}
      <mesh position={[-1.1, 1.15, -0.3]} castShadow>
        <boxGeometry args={[0.75, 1.05, 0.75]} />
        <meshStandardMaterial color="#f1f5f9" roughness={0.35} />
      </mesh>
      {/* Panel solar */}
      <mesh position={[-1.1, 1.72, -0.3]} rotation-x={-0.55}>
        <boxGeometry args={[0.65, 0.65, 0.03]} />
        <meshStandardMaterial color="#1e3a8a" metalness={0.92} roughness={0.15} />
      </mesh>
      {/* Mástil y antena */}
      <mesh position={[-1.1, 2.2, -0.3]}>
        <cylinderGeometry args={[0.018, 0.018, 1.05, 6]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} />
      </mesh>

      {/* Cartel USGS Nítido */}
      <Html position={[0, 2.3, 0]} center distanceFactor={14}>
        <div
          className="flex flex-col items-center rounded-xl border border-cyan-400/60 bg-zinc-950/94 p-3 font-sans text-xs text-cyan-200 shadow-2xl backdrop-blur-md whitespace-nowrap"
          style={{ minWidth: "200px" }}
        >
          <div className="flex items-center gap-1.5 font-bold text-cyan-300">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span>{stationId ? `USGS Gage #${stationId}` : "Outlet de simulación"}</span>
          </div>
          <div className="mt-1 text-zinc-200 font-mono text-[11px]">
            Caudal Q: <b className="text-teal-300 text-xs">{streamflowM3s.toFixed(2)} m³/s</b>
          </div>
          <div className="text-zinc-400 font-mono text-[10px] mt-0.5">
            {evidenceType ? `${evidenceType} · caudal modelado` : "caudal acoplado"}
          </div>
        </div>
      </Html>
    </group>
  );
}

/**
 * Sistema de Lluvia Cinemática Hiperrealista (Estilo GTA 6)
 * Utiliza 2,400 estelas de lluvia volumétricas (LineSegments) con velocidad terminal e inclinación de viento
 */
function PrecipitationRainSystem({ precipMm }: { precipMm: number }) {
  const streakCount = Math.min(2400, Math.floor(precipMm * 85) + 600);
  const linesRef = useRef<THREE.LineSegments>(null);

  const initialPositions = useMemo(() => {
    // 2 vértices por gota (inicio y final de estela) = 6 floats por estela
    const pos = new Float32Array(streakCount * 6);
    for (let i = 0; i < streakCount; i++) {
      const x = (deterministicUnit(i, 1) - 0.5) * 58;
      const y = 1.0 + deterministicUnit(i, 2) * 26;
      const z = (deterministicUnit(i, 3) - 0.5) * 46;
      const streakLen = 0.95 + deterministicUnit(i, 4) * 0.65;

      // Vértice superior
      pos[i * 6] = x;
      pos[i * 6 + 1] = y;
      pos[i * 6 + 2] = z;

      // Vértice inferior con ligera deriva aerodinámica por viento
      pos[i * 6 + 3] = x - 0.08;
      pos[i * 6 + 4] = y - streakLen;
      pos[i * 6 + 5] = z + 0.04;
    }
    return pos;
  }, [streakCount]);

  useFrame((_, delta) => {
    if (!linesRef.current || streakCount === 0) return;
    const pos = linesRef.current.geometry.attributes.position.array as Float32Array;
    const fallSpeed = 38.0; // Velocidad terminal física ~38 m/s
    for (let i = 0; i < streakCount; i++) {
      const y1Idx = i * 6 + 1;
      const y2Idx = i * 6 + 4;
      const streakLen = pos[y1Idx] - pos[y2Idx];

      pos[y1Idx] -= fallSpeed * delta;
      pos[y2Idx] -= fallSpeed * delta;

      if (pos[y2Idx] < 0.1) {
        const newY = 24.0 + deterministicUnit(i, 5) * 4.0;
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
        opacity={Math.min(0.88, 0.45 + (precipMm / 40) * 0.42)}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
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
  currentDay,
  totalDays,
}: WatershedMesh3DProps) {
  const hruCount = hruAggregates?.results?.length ?? hruAggregates?.hrus?.length ?? 0;

  // Ubicación del outlet USGS al final del río
  const outletZ = -17;
  const outletX = getRiverPathX(outletZ);
  const outletY = getTerrainElevation(outletX, outletZ);

  return (
    <group position={[0, -0.38, 0]}>
      {/* 1. Terreno con relieve continuo adaptado */}
      <WatershedCatchmentTerrain soilMoistureVol={soilMoistureVol} />

      {/* 2. Parcelas HRU drapeadas sobre el relieve (NUNCA tapadas por los montes) */}
      <AgriculturalHruParcel
        center={[-9, 5]}
        size={[13.5, 11.5]}
        color="#3c6b2a"
        onClick={onSelectSubbasin}
      />

      <AgriculturalHruParcel
        center={[9, 6]}
        size={[12.0, 10.5]}
        color="#6d6a2f"
      />

      <AgriculturalHruParcel
        center={[-10, -7]}
        size={[12.5, 9.5]}
        color="#546e32"
      />

      <AgriculturalHruParcel
        center={[10, -6]}
        size={[11.0, 9.0]}
        color="#395924"
      />

      {/* 3. Bosque Ribereño que sigue el curso fluvial */}
      <RiparianTreeBelt treeCount={28} />

      {/* 4. Río 3D Físico Sólido con Caudal Dinámico Q y Ondas */}
      <RealisticRiverSurface3D streamflowM3s={streamflowM3s} />

      {/* 5. Aforo USGS en el outlet */}
      <UsgsGaugingStation
        position={[outletX + 0.5, outletY, outletZ]}
        streamflowM3s={streamflowM3s}
        stationId={stationId}
        evidenceType={evidenceType}
      />

      {/* 6. Lluvia 3D Volumétrica Visible y Realista */}
      {showHydrologyFlow && <PrecipitationRainSystem precipMm={precipMm} />}

      {/* 7. Tarjetas 3D Claras y Visibles */}
      {showScientificLabels && (
        <>
          <Html position={[-18, 4.5, 13]} distanceFactor={15}>
            <div
              className="rounded-xl border border-cyan-400/50 bg-zinc-950/94 p-3.5 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
              style={{ minWidth: "260px" }}
            >
              <div className="flex items-center justify-between border-b border-cyan-500/30 pb-1.5">
                <span className="font-bold text-cyan-300">{watershedName ?? "Cuenca"} · Nivel Macro</span>
                <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] font-mono text-cyan-300">
                  {currentDay ? `Día ${currentDay}` : "Día 1"}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-[11px] font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Precipitación:</span>
                  <span className={`font-bold ${precipMm > 2 ? "text-amber-300 animate-pulse" : "text-sky-300"}`}>
                    {precipMm.toFixed(1)} mm/d
                  </span>
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
                  Vista esquemática cuenca: {hruCount ? `${hruCount} HRUs acopladas` : "HRUs configuradas"}.
                </div>
              </div>
            </div>
          </Html>

          <Html position={[-9, 2.2, 5]} center distanceFactor={14}>
            <div
              onClick={(e) => {
                e.stopPropagation();
                onSelectSubbasin();
              }}
              className="cursor-pointer rounded-xl border border-emerald-400/60 bg-zinc-950/94 px-3 py-2 font-sans text-xs text-emerald-300 shadow-xl backdrop-blur transition hover:scale-105 hover:border-emerald-300 text-center"
              style={{ minWidth: "170px" }}
            >
              <div className="font-bold flex items-center justify-center gap-1">
                <span>Parcela Agrícola</span>
                <span>→</span>
              </div>
              <div className="text-[10px] text-zinc-300 font-mono mt-0.5">Explorar Nivel Meso (1,000 plantas)</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

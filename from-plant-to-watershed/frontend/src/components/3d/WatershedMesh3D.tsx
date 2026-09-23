"use client";

import React, { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import southForkData from "../../data/south_fork_iowa_watershed.json";

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
  streamflowM3s: number | null;
  precipMm: number | null;
  rainEffectMm: number | null;
  precipitationUnit: string;
  periodLabel: string;
  hruAggregates?: { hrus?: HruSummary[]; results?: HruSummary[] };
  watershedName?: string;
  stationId?: string | null;
  evidenceType?: string;
  onSelectSubbasin?: () => void;
  showHruBorders?: boolean;
  showHydrologyFlow?: boolean;
  showScientificLabels?: boolean;
}

/**
 * Relieve contextual esquemático de South Fork Iowa; no reproduce un DEM validado.
 */
export function getTerrainElevation(x: number, z: number): number {
  const xNorm = (x + 28) / 56;
  const zNorm = (z + 22) / 44;
  // Pendiente regional hidráulica de NW a SE
  const regionalSlope = Math.max(0, 1.0 - (xNorm * 0.44 + zNorm * 0.56)) * 2.8;

  // Ondulaciones características de morrena glacial y lomas de Iowa (swells & swales)
  const glacialSwells =
    Math.sin(x * 0.22) * Math.cos(z * 0.18) * 0.26 +
    Math.sin(x * 0.48 + z * 0.36) * 0.12 +
    Math.cos(x * 0.11 - z * 0.14) * 0.16;

  return Math.max(0.06, regionalSlope + glacialSwells);
}

/**
 * Terreno base regional de Iowa con textura de suelos Mollisols y parcelación agrícola
 */
function IowaCatchmentTerrain() {
  // Contextual material: no verified basin-wide volumetric moisture is available.
  const moistureFactor = 0.5;

  const geometry = useMemo(() => {
    const width = 68;
    const height = 54;
    const segX = 136;
    const segY = 108;
    const geo = new THREE.PlaneGeometry(width, height, segX, segY);
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    const fertileSoil = new THREE.Color("#1a3014");
    const ridgeSoil = new THREE.Color("#3c4d1e");
    const externalPlains = new THREE.Color("#182613");

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const zWorld = -y;

      const elev = getTerrainElevation(x, zWorld);
      pos.setZ(i, elev);

      const agriculturalGrid =
        (Math.sin(x * 0.65) * Math.cos(zWorld * 0.65) > 0.08) ? fertileSoil : ridgeSoil;

      const isInsideBBox = Math.abs(x) < 26 && Math.abs(zWorld) < 20;
      const baseColor = isInsideBBox
        ? agriculturalGrid.clone().lerp(fertileSoil, 0.45)
        : externalPlains;

      colors[i * 3] = baseColor.r;
      colors[i * 3 + 1] = baseColor.g;
      colors[i * 3 + 2] = baseColor.b;
    }

    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return geo;
  }, []);

  const roughness = Math.max(0.46, 0.92 - moistureFactor * 0.38);

  return (
    <mesh geometry={geometry} rotation-x={-Math.PI / 2} receiveShadow>
      <meshStandardMaterial
        vertexColors
        roughness={roughness}
        metalness={moistureFactor * 0.08}
      />
    </mesh>
  );
}

/**
 * Divisoria Hidrográfica Exterior de la Cuenca South Fork Iowa River (Drainage Divide Perimeter)
 * Delinea exactamente el límite de la cuenca (560.9 km²) con cresta iluminada y faldón delimitador.
 */
function WatershedDivideBoundary({
  boundary,
  showLabels,
}: {
  boundary: Array<[number, number]>;
  showLabels?: boolean;
}) {
  const { linePoints, wallGeometry } = useMemo(() => {
    const linePts: [number, number, number][] = [];
    const wallVerts: number[] = [];
    const wallIndices: number[] = [];

    boundary.forEach(([x, z], i) => {
      const elev = getTerrainElevation(x, z);
      const topY = elev + 0.16;
      const bottomY = Math.max(-0.2, elev - 0.45);

      linePts.push([x, topY, z]);

      wallVerts.push(x, topY, z);
      wallVerts.push(x, bottomY, z);

      if (i < boundary.length - 1) {
        const row = i * 2;
        wallIndices.push(row, row + 1, row + 2);
        wallIndices.push(row + 1, row + 3, row + 2);
      }
    });

    const wallGeo = new THREE.BufferGeometry();
    wallGeo.setAttribute("position", new THREE.Float32BufferAttribute(wallVerts, 3));
    wallGeo.setIndex(wallIndices);
    wallGeo.computeVertexNormals();

    return { linePoints: linePts, wallGeometry: wallGeo };
  }, [boundary]);

  // Vértice de cabecera norte para el rótulo
  const northPeak = linePoints[25] || linePoints[0];

  return (
    <group>
      {/* 1. Cresta perimetral luminosa que define el límite de la cuenca */}
      <Line
        points={linePoints}
        color="#38bdf8"
        lineWidth={3.0}
        transparent
        opacity={0.92}
      />

      {/* 2. Faldón delimitador vertical translúcido */}
      <mesh geometry={wallGeometry}>
        <meshBasicMaterial
          color="#0284c7"
          transparent
          opacity={0.22}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* 3. Indicador Flotante de la Divisoria de Aguas */}
      {showLabels && northPeak && (
        <Html position={[northPeak[0], northPeak[1] + 1.8, northPeak[2]]} center distanceFactor={14}>
          <div className="flex items-center gap-1.5 rounded-xl border border-cyan-400/80 bg-zinc-950/95 px-3 py-1.5 font-mono text-[11px] text-cyan-200 shadow-2xl backdrop-blur-md whitespace-nowrap">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>Contorno contextual · South Fork Iowa (no reconstrucción GIS validada)</span>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * Polígonos contextuales heredados. No se asocian con HRU ni cultivos del registro temporal.
 */
function SubbasinHruMeshes({
  subbasins,
  onSelectSubbasin,
  showBorders = true,
  hoveredSubbasin,
  setHoveredSubbasin,
}: {
  subbasins: Array<{
    sub_id: number;
    area_km2: number;
    crop: string;
    centroid: [number, number];
    polygon: Array<[number, number]>;
  }>;
  onSelectSubbasin?: () => void;
  showBorders?: boolean;
  hoveredSubbasin: number | null;
  setHoveredSubbasin: (id: number | null) => void;
}) {
  const geometries = useMemo(() => {
    return subbasins.map((sub) => {
      const pts = sub.polygon;
      const shape = new THREE.Shape();
      if (pts.length < 3) return { id: sub.sub_id, geometry: null, outline: [] };

      shape.moveTo(pts[0][0], -pts[0][1]);
      for (let i = 1; i < pts.length; i++) {
        shape.lineTo(pts[i][0], -pts[i][1]);
      }

      const flatGeo = new THREE.ShapeGeometry(shape);
      const pos = flatGeo.attributes.position;

      for (let i = 0; i < pos.count; i++) {
        const vx = pos.getX(i);
        const vz = -pos.getY(i);
        const vy = getTerrainElevation(vx, vz) + 0.045;
        pos.setY(i, vy);
        pos.setZ(i, vz);
      }
      flatGeo.computeVertexNormals();

      const outlinePts: [number, number, number][] = pts.map(([px, pz]) => [
        px,
        getTerrainElevation(px, pz) + 0.065,
        pz,
      ]);

      return { id: sub.sub_id, geometry: flatGeo, outline: outlinePts };
    });
  }, [subbasins]);

  return (
    <group>
      {subbasins.map((sub, idx) => {
        const item = geometries[idx];
        if (!item || !item.geometry) return null;

        const isHovered = hoveredSubbasin === sub.sub_id;
        const baseColor = "#345e26";
        const finalColor = isHovered ? "#4ade80" : baseColor;

        return (
          <group
            key={`subbasin-${sub.sub_id}`}
            onPointerOver={(e) => {
              e.stopPropagation();
              setHoveredSubbasin(sub.sub_id);
            }}
            onPointerOut={(e) => {
              e.stopPropagation();
              setHoveredSubbasin(null);
            }}
            onClick={(e) => {
              e.stopPropagation();
              onSelectSubbasin?.();
            }}
          >
            <mesh geometry={item.geometry} receiveShadow>
              <meshStandardMaterial
                color={finalColor}
                roughness={0.78}
                metalness={isHovered ? 0.25 : 0.05}
                emissive={isHovered ? "#22c55e" : "#000000"}
                emissiveIntensity={isHovered ? 0.35 : 0}
              />
            </mesh>

            {/* Borde de la subcuenca */}
            {showBorders && item.outline.length > 0 && (
              <Line
                points={item.outline}
                color={isHovered ? "#ffffff" : "#a7f3d0"}
                lineWidth={isHovered ? 2.2 : 1.1}
                transparent
                opacity={isHovered ? 0.95 : 0.45}
              />
            )}
          </group>
        );
      })}

      {/* Tooltip interactivo flotante sobre la subcuenca activa */}
      {hoveredSubbasin !== null && (() => {
        const sub = subbasins.find((s) => s.sub_id === hoveredSubbasin);
        if (!sub) return null;
        const cy = getTerrainElevation(sub.centroid[0], sub.centroid[1]) + 1.2;
        return (
          <Html position={[sub.centroid[0], cy, sub.centroid[1]]} center distanceFactor={10}>
            <div className="pointer-events-none rounded-xl border border-emerald-400 bg-zinc-950/95 px-3 py-2 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md whitespace-nowrap">
              <div className="font-bold text-emerald-300">Sector contextual #{sub.sub_id}</div>
              <div className="mt-0.5 text-[11px] font-mono text-zinc-300">Sin correspondencia HRU→polígono verificada</div>
              {onSelectSubbasin && <div className="text-[10px] text-zinc-400 mt-0.5">Abrir campo FSPM no georreferenciado</div>}
            </div>
          </Html>
        );
      })()}
    </group>
  );
}

/**
 * Red Fluvial Completa de 37 Canales de la Cuenca South Fork Iowa River (Branching Stream Network)
 * Cada tramo tributario drena hacia el canal principal desembocando en el aforo USGS.
 */
function SouthForkRiverNetwork3D({
  channels,
  animate,
}: {
  channels: Array<{
    link_id: number;
    length_km: number;
    width_m: number;
    depth_m: number;
    elev_min_m: number;
    elev_max_m: number;
    points: Array<[number, number, number]>;
  }>;
  animate: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);

  const combinedGeometry = useMemo(() => {
    const vertices: number[] = [];
    const indices: number[] = [];
    const uvs: number[] = [];
    let vertOffset = 0;

    channels.forEach((ch) => {
      const pts = ch.points;
      if (pts.length < 2) return;

      // Ancho escalado: canales pequeños 0.22m, canal principal hasta 1.8m
      const baseWidth = Math.max(0.24, Math.min(1.8, ch.width_m / 24.0));

      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const prev = pts[Math.max(0, i - 1)];
        const next = pts[Math.min(pts.length - 1, i + 1)];

        const dx = next[0] - prev[0];
        const dz = next[2] - prev[2];
        const len = Math.hypot(dx, dz) || 1;

        const nx = (-dz / len) * baseWidth * 0.5;
        const nz = (dx / len) * baseWidth * 0.5;

        // Lámina de agua elevada sobre el lecho del canal
        const waterY = getTerrainElevation(p[0], p[2]) + 0.08;

        vertices.push(p[0] + nx, waterY, p[2] + nz);
        vertices.push(p[0] - nx, waterY, p[2] - nz);

        uvs.push(0, (i / pts.length) * 8);
        uvs.push(1, (i / pts.length) * 8);

        if (i < pts.length - 1) {
          const r = vertOffset + i * 2;
          indices.push(r, r + 1, r + 2);
          indices.push(r + 1, r + 3, r + 2);
        }
      }
      vertOffset += pts.length * 2;
    });

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    return geo;
  }, [channels]);

  // Animación física de corriente fluvial continua
  useFrame(({ clock }) => {
    if (!meshRef.current || !animate) return;
    const time = clock.getElapsedTime();
    const pos = meshRef.current.geometry.attributes.position;
    const count = pos.count;

    for (let i = 0; i < count; i += 2) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const ripple = Math.sin(x * 1.8 + z * 1.4 - time * 3.5) * 0.006;
      pos.setY(i, pos.getY(i) + ripple * 0.003);
    }
    pos.needsUpdate = true;
  });

  return (
    <mesh ref={meshRef} geometry={combinedGeometry} receiveShadow>
      <meshStandardMaterial
        color="#0284c7"
        roughness={0.06}
        metalness={0.28}
        transparent
        opacity={0.94}
      />
    </mesh>
  );
}

/**
 * Bosques de Galería y Franjas de Protección Ribereña a lo largo de los cauces de Iowa
 */
function RiparianVegetationBelt({
  channels,
}: {
  channels: Array<{ points: Array<[number, number, number]> }>;
}) {
  const treePositions = useMemo(() => {
    const list: Array<[number, number, number]> = [];
    // Muestreo a lo largo de los canales mayores
    channels.slice(0, 18).forEach((ch, chIdx) => {
      ch.points.forEach((p, pIdx) => {
        if (pIdx % 3 === 0) {
          const side = (chIdx + pIdx) % 2 === 0 ? 0.7 : -0.7;
          const x = p[0] + side;
          const z = p[2] + side * 0.5;
          const y = getTerrainElevation(x, z) + 0.04;
          list.push([x, y, z]);
        }
      });
    });
    return list;
  }, [channels]);

  return (
    <group>
      {treePositions.map((pos, idx) => (
        <group key={`riparian-tree-${idx}`} position={pos}>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.04, 0.06, 0.45, 5]} />
            <meshStandardMaterial color="#38281d" roughness={0.8} />
          </mesh>
          <mesh position={[0, 0.62, 0]} castShadow>
            <sphereGeometry args={[0.32 + (idx % 3) * 0.05, 7, 7]} />
            <meshStandardMaterial
              color={idx % 2 === 0 ? "#1c4a22" : "#245c2a"}
              roughness={0.65}
            />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/**
 * Estación de Aforo Fluvial USGS (#05451210 en New Providence, IA)
 * Situada en el outlet de la cuenca South Fork Iowa River.
 */
function UsgsGaugingStation({
  position,
  streamflowM3s,
  stationId,
  evidenceType,
}: {
  position: [number, number, number];
  streamflowM3s: number | null;
  stationId?: string | null;
  evidenceType?: string;
}) {
  return (
    <group position={position}>
      {/* Vertedero de aforo de concreto */}
      <mesh position={[0, 0.24, 0]} receiveShadow>
        <boxGeometry args={[2.8, 0.55, 1.4]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.7} />
      </mesh>

      {/* Caseta de monitoreo hidrométrico USGS */}
      <mesh position={[-0.85, 0.95, -0.2]} castShadow>
        <boxGeometry args={[0.7, 0.95, 0.7]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.35} />
      </mesh>

      {/* Panel solar de alimentación telemétrica */}
      <mesh position={[-0.85, 1.5, -0.2]} rotation-x={-0.55}>
        <boxGeometry args={[0.6, 0.6, 0.03]} />
        <meshStandardMaterial color="#1e3a8a" metalness={0.92} roughness={0.15} />
      </mesh>

      {/* Mástil de transmisión satelital GOES / Iridium */}
      <mesh position={[-0.85, 1.95, -0.2]}>
        <cylinderGeometry args={[0.016, 0.016, 0.95, 6]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} />
      </mesh>

      {/* Punto de referencia espacial; el caudal es el del registro de playback. */}
      <Html position={[0, 2.2, 0]} center distanceFactor={14}>
        <div
          className="flex flex-col items-center rounded-xl border border-cyan-400/80 bg-zinc-950/95 p-3 font-sans text-xs text-cyan-200 shadow-2xl backdrop-blur-md whitespace-nowrap"
          style={{ minWidth: "220px" }}
        >
          <div className="flex items-center gap-1.5 font-bold text-cyan-300">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400" />
            <span>Outlet · referencia USGS #{stationId || "05451210"}</span>
          </div>
          <div className="mt-1 text-zinc-100 font-mono text-[11px]">
            Q {evidenceType === "OBSERVED" ? "observado" : "modelado"}: <b className="text-teal-300 text-xs">{streamflowM3s === null ? "No disponible" : `${streamflowM3s.toFixed(2)} m³/s`}</b>
          </div>
          <div className="text-zinc-400 font-mono text-[10px] mt-0.5">
            South Fork Iowa River at New Providence, IA
          </div>
          <div className="text-emerald-400 font-mono text-[10px] mt-0.5">
            {evidenceType ?? "NOT_AVAILABLE"} · salida de cuenca
          </div>
        </div>
      </Html>
    </group>
  );
}

/**
 * Partículas ilustrativas proporcionales al dato diario disponible; no son una medición espacial.
 */
function PrecipitationRainSystem({ precipMm }: { precipMm: number }) {
  const streakCount = Math.min(2400, Math.max(8, Math.floor(precipMm * 85)));
  const linesRef = useRef<THREE.LineSegments>(null);

  const initialPositions = useMemo(() => {
    const pos = new Float32Array(streakCount * 6);
    for (let i = 0; i < streakCount; i++) {
      const x = (deterministicUnit(i, 1) - 0.5) * 58;
      const y = 1.0 + deterministicUnit(i, 2) * 26;
      const z = (deterministicUnit(i, 3) - 0.5) * 46;
      const streakLen = 0.95 + deterministicUnit(i, 4) * 0.65;

      pos[i * 6] = x;
      pos[i * 6 + 1] = y;
      pos[i * 6 + 2] = z;

      pos[i * 6 + 3] = x - 0.08;
      pos[i * 6 + 4] = y - streakLen;
      pos[i * 6 + 5] = z + 0.04;
    }
    return pos;
  }, [streakCount]);

  useFrame((_, delta) => {
    if (!linesRef.current || streakCount === 0) return;
    const pos = linesRef.current.geometry.attributes.position.array as Float32Array;
    const fallSpeed = 38.0;
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

  if (precipMm <= 0) return null;

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
  rainEffectMm,
  precipitationUnit,
  periodLabel,
  stationId,
  evidenceType,
  onSelectSubbasin,
  showHruBorders = true,
  showHydrologyFlow = true,
  showScientificLabels = true,
}: WatershedMesh3DProps) {
  const [hoveredSubbasin, setHoveredSubbasin] = useState<number | null>(null);

  // Datos contextuales heredados; el contrato no valida su correspondencia GIS con las HRU.
  const boundary = southForkData.boundary as Array<[number, number]>;
  const subbasins = southForkData.subbasins as Array<{
    sub_id: number;
    area_km2: number;
    crop: string;
    centroid: [number, number];
    polygon: Array<[number, number]>;
  }>;
  const channels = southForkData.channels as Array<{
    link_id: number;
    length_km: number;
    width_m: number;
    depth_m: number;
    elev_min_m: number;
    elev_max_m: number;
    points: Array<[number, number, number]>;
  }>;
  const outletPos = southForkData.outlet.position as [number, number, number];

  return (
    <group position={[0, -0.35, 0]}>
      {/* 1. Terreno Regional de Iowa (Des Moines Lobe Glacial Plain) */}
      <IowaCatchmentTerrain />

      {/* 2. Divisoria Hidrográfica Exterior (Watershed Drainage Divide) */}
      <WatershedDivideBoundary boundary={boundary} showLabels={showScientificLabels} />

      {/* 3. Polígonos contextuales sin asignación HRU o cultivo del registro */}
      <SubbasinHruMeshes
        subbasins={subbasins}
        onSelectSubbasin={onSelectSubbasin}
        showBorders={showHruBorders}
        hoveredSubbasin={hoveredSubbasin}
        setHoveredSubbasin={setHoveredSubbasin}
      />

      {/* 4. Red Fluvial Completa de 37 Canales y Tributarios de South Fork Iowa */}
      <SouthForkRiverNetwork3D channels={channels} animate={showHydrologyFlow && streamflowM3s !== null} />

      {/* 5. Bosque de Galería y Corredor de Amortiguación Ribereña */}
      <RiparianVegetationBelt channels={channels} />

      {/* 6. Estación de Aforo Fluvial USGS #05451210 en New Providence */}
      <UsgsGaugingStation
        position={outletPos}
        streamflowM3s={streamflowM3s}
        stationId={stationId || southForkData.outlet.stationId}
        evidenceType={evidenceType}
      />

      {/* 7. Lluvia volumétrica activa (precipitación sobre la cuenca) */}
      {showHydrologyFlow && rainEffectMm !== null && rainEffectMm > 0 && <PrecipitationRainSystem precipMm={rainEffectMm} />}

      {/* 8. Tarjeta Informativa Científica de la Cuenca South Fork Iowa */}
      {showScientificLabels && (
        <Html position={[-21, 4.8, 12]} distanceFactor={15}>
          <div
            className="rounded-xl border border-cyan-400/50 bg-zinc-950/94 p-3.5 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md"
            style={{ minWidth: "270px" }}
          >
            <div className="flex items-center justify-between border-b border-cyan-500/30 pb-1.5">
              <span className="font-bold text-cyan-300">Cuenca South Fork Iowa River</span>
              <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] font-mono text-cyan-300">
                {periodLabel}
              </span>
            </div>
            <div className="mt-2 space-y-1 text-[11px] font-mono">
              <div className="flex justify-between">
                <span className="text-zinc-400">Código HUC / USGS:</span>
                <span className="font-bold text-teal-300">05451210 · HUC-12</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Cobertura espacial:</span>
                <span className="font-bold text-teal-200">Contexto esquemático</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Precipitación:</span>
                <span className="font-bold text-sky-300">
                  {precipMm === null ? "No disponible" : `${precipMm.toFixed(1)} ${precipitationUnit}`}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Caudal en outlet Q:</span>
                <span className="font-bold text-teal-300">{streamflowM3s === null ? "No disponible" : `${streamflowM3s.toFixed(2)} m³/s`}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Terreno / canales:</span>
                <span className="font-bold text-emerald-300">Contexto esquemático</span>
              </div>
            </div>
            {onSelectSubbasin && <button
              onClick={(e) => {
                e.stopPropagation();
                onSelectSubbasin();
              }}
              className="mt-2.5 w-full cursor-pointer rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-500/40 py-1 text-[11px] font-bold text-cyan-200 transition text-center"
            >
              Ver campo FSPM disponible (Meso) →
            </button>}
          </div>
        </Html>
      )}
    </group>
  );
}

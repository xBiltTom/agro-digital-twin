"use client";

import React, { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

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
  hruAggregates?: { hrus?: HruSummary[] };
  onSelectSubbasin: () => void;
  showHruBorders?: boolean;
  showHydrologyFlow?: boolean;
  showScientificLabels?: boolean;
}

/**
 * 3D High-Fidelity Catchment Elevation Terrain (Corn Belt SWAT+ Basin)
 * Generates dendritic drainage valley, ridge boundaries, and alluvial floodplain.
 */
function WatershedCatchmentTerrain({
  soilMoistureVol,
}: {
  soilMoistureVol: number;
}) {
  const geometry = useMemo(() => {
    const width = 56;
    const height = 44;
    const segX = 90;
    const segY = 70;
    const geo = new THREE.PlaneGeometry(width, height, segX, segY);
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    const valleyCol = new THREE.Color("#2d4a27"); // Alluvial floodplain green
    const ridgeCol = new THREE.Color("#556b2f");  // Upland prairie olive
    const cropCol = new THREE.Color("#43662b");   // Corn Belt agricultural parcel

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);

      // Drainage divide ridge profile (elevated margins)
      const edgeDistX = Math.abs(x) / (width / 2);
      const edgeDistY = Math.abs(y) / (height / 2);
      const boundaryRidge =
        Math.pow(edgeDistX, 2.8) * 4.2 + Math.pow(edgeDistY, 2.6) * 3.6;

      // River valley incision: carving a meandering valley from top-left to bottom-right
      const riverPathX = -18 + (y + height / 2) * 0.75 + Math.sin(y * 0.16) * 4.0;
      const distToRiver = Math.abs(x - riverPathX);
      const valleyCarve = -Math.exp(-Math.pow(distToRiver / 4.8, 2)) * 1.8;

      // Rolling Midwestern glacial till topography
      const rollingTill =
        Math.sin(x * 0.18) * Math.cos(y * 0.15) * 1.2 +
        Math.sin(x * 0.38 + y * 0.22) * 0.6 +
        Math.cos(x * 0.08 - y * 0.12) * 0.8;

      const elevation = Math.max(-0.6, boundaryRidge + valleyCarve + rollingTill);
      pos.setZ(i, elevation);

      // Hypsometric tinting: valley floor vs upland ridges
      const normElev = Math.min(1, Math.max(0, (elevation + 0.6) / 5.5));
      const vertexColor =
        normElev < 0.35
          ? valleyCol.clone().lerp(cropCol, normElev / 0.35)
          : cropCol.clone().lerp(ridgeCol, (normElev - 0.35) / 0.65);

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
      <meshStandardMaterial
        vertexColors
        roughness={0.92}
        metalness={0.05}
      />
    </mesh>
  );
}

/**
 * 3D Thematic HRU Agricultural Parcel with realistic crop row patterns
 */
function AgriculturalHruParcel({
  position,
  size,
  color,
  rotation = 0,
  label,
  cropType,
  areaPercent,
  onClick,
}: {
  position: [number, number, number];
  size: [number, number];
  color: string;
  rotation?: number;
  label: string;
  cropType: string;
  areaPercent: number;
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
      {/* Parcel boundary base plane */}
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={size} />
        <meshStandardMaterial color={color} roughness={0.88} />
      </mesh>

      {/* Textured agricultural crop rows */}
      {Array.from({ length: rows }, (_, r) => (
        <mesh
          key={r}
          rotation-x={-Math.PI / 2}
          position={[0, 0.02, -size[1] / 2 + 0.6 + r * (size[1] - 1.2) / (rows - 1)]}
        >
          <planeGeometry args={[size[0] * 0.96, 0.08]} />
          <meshStandardMaterial color="#2b4523" roughness={0.9} />
        </mesh>
      ))}

      {/* Stylized parcel glowing border line */}
      <Line
        points={[
          [-size[0] / 2, 0.04, -size[1] / 2],
          [size[0] / 2, 0.04, -size[1] / 2],
          [size[0] / 2, 0.04, size[1] / 2],
          [-size[0] / 2, 0.04, size[1] / 2],
          [-size[0] / 2, 0.04, -size[1] / 2],
        ]}
        color="#86efac"
        lineWidth={1.2}
        transparent
        opacity={0.7}
      />
    </group>
  );
}

/**
 * Riparian Forest Buffer (Buffer Ribereño) lining the river corridors
 * Mitigates agricultural sediment and nutrient runoff into SWAT+ reaches
 */
function RiparianTreeBelt({
  curvePoints,
  treeCount = 20,
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
      const localT = (t * (curvePoints.length - 1)) - ptIdx;

      // Interpolate along river bank with lateral offset
      const x = p1[0] + (p2[0] - p1[0]) * localT + (i % 2 === 0 ? 0.75 : -0.75);
      const y = p1[1] + (p2[1] - p1[1]) * localT + 0.15;
      const z = p1[2] + (p2[2] - p1[2]) * localT + (i % 3 === 0 ? 0.4 : -0.4);
      list.push([x, y, z]);
    }
    return list;
  }, [curvePoints, treeCount]);

  return (
    <group>
      {treePositions.map((pos, idx) => (
        <group key={`tree-${idx}`} position={pos}>
          {/* Trunk */}
          <mesh position={[0, 0.3, 0]} castShadow>
            <cylinderGeometry args={[0.04, 0.065, 0.6, 6]} />
            <meshStandardMaterial color="#4a3728" roughness={0.8} />
          </mesh>
          {/* Deciduous leafy canopy */}
          <mesh position={[0, 0.78, 0]} castShadow>
            <sphereGeometry args={[0.34 + (idx % 3) * 0.05, 8, 8]} />
            <meshStandardMaterial color="#1b4d26" roughness={0.65} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/**
 * USGS Streamflow Gauging Station (#05451210) at Watershed Outlet
 */
function UsgsGaugingStation({
  position,
  streamflowM3s,
}: {
  position: [number, number, number];
  streamflowM3s: number;
}) {
  return (
    <group position={position}>
      {/* Concrete Weir / Flume Foundation */}
      <mesh position={[0, 0.25, 0]} receiveShadow>
        <boxGeometry args={[2.2, 0.5, 1.4]} />
        <meshStandardMaterial color="#94a3b8" roughness={0.8} />
      </mesh>
      {/* V-Notch Weir Crest */}
      <mesh position={[0, 0.45, 0.4]}>
        <boxGeometry args={[0.8, 0.2, 0.1]} />
        <meshStandardMaterial color="#475569" roughness={0.5} />
      </mesh>
      {/* USGS Shelter Enclosure Hut */}
      <mesh position={[-0.7, 0.95, -0.2]} castShadow>
        <boxGeometry args={[0.65, 0.9, 0.65]} />
        <meshStandardMaterial color="#e2e8f0" roughness={0.4} />
      </mesh>
      {/* Solar Panel on Hut Roof */}
      <mesh position={[-0.7, 1.45, -0.2]} rotation-x={-0.5}>
        <boxGeometry args={[0.55, 0.55, 0.02]} />
        <meshStandardMaterial color="#1e3a8a" metalness={0.9} roughness={0.2} />
      </mesh>
      {/* Antenna Mast */}
      <mesh position={[-0.7, 1.9, -0.2]}>
        <cylinderGeometry args={[0.015, 0.015, 0.9, 6]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} />
      </mesh>
      {/* Staff Gage on concrete wall */}
      <mesh position={[0.6, 0.4, 0.65]}>
        <boxGeometry args={[0.1, 0.5, 0.02]} />
        <meshStandardMaterial color="#fef08a" />
      </mesh>

      {/* USGS Station Badge Callout */}
      <Html position={[0, 1.8, 0]} center distanceFactor={16}>
        <div className="flex flex-col items-center rounded-xl border border-cyan-400/50 bg-slate-950/92 p-2.5 font-mono text-[10px] text-cyan-200 shadow-2xl backdrop-blur-md whitespace-nowrap">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="font-bold text-cyan-300">Marcador de referencia #05451210</span>
          </div>
          <div className="mt-1 text-slate-300 text-[9px]">
            Q simulado: <span className="font-bold text-teal-300">{streamflowM3s.toFixed(2)} m³/s</span>
          </div>
          <div className="text-slate-400 text-[8px]">
            Serie USGS registrada por separado · sin validación formal
          </div>
        </div>
      </Html>
    </group>
  );
}

/**
 * 3D Volumetric Rain Particle System (CMIP6 Precipitation Events)
 */
function PrecipitationRainSystem({ precipMm }: { precipMm: number }) {
  const count = Math.min(450, Math.floor(precipMm * 28));
  const pointsRef = useRef<THREE.Points>(null);

  const initialPositions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 48;
      pos[i * 3 + 1] = Math.random() * 22;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 38;
    }
    return pos;
  }, [count]);

  useFrame((_, delta) => {
    if (!pointsRef.current || count === 0) return;
    const pos = pointsRef.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < count; i++) {
      const yIdx = i * 3 + 1;
      pos[yIdx] -= 26 * delta; // Fast downward rain speed
      if (pos[yIdx] < 0.1) {
        pos[yIdx] = 18 + Math.random() * 4;
      }
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  if (precipMm < 0.5) return null;

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[initialPositions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color="#7dd3fc"
        transparent
        opacity={0.65}
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
  onSelectSubbasin,
  showHruBorders = true,
  showHydrologyFlow = true,
  showScientificLabels = true,
}: WatershedMesh3DProps) {
  // River geometry points along drainage path
  const riverPoints: [number, number, number][] = useMemo(
    () => [
      [-22, 1.4, 16],
      [-16, 0.9, 12],
      [-10, 0.55, 7],
      [-4, 0.32, 3],
      [3, 0.15, -1],
      [10, 0.05, -6],
      [17, -0.05, -10],
      [22, -0.15, -13.5],
    ],
    []
  );

  const tributaryPoints: [number, number, number][] = useMemo(
    () => [
      [-16, 1.6, -14],
      [-11, 0.95, -8],
      [-6, 0.55, -3],
      [3, 0.15, -1],
    ],
    []
  );

  // Dynamic river width scaling with streamflow Q
  const riverWidth = Math.min(1.2, 0.28 + (streamflowM3s / 35) * 0.65);

  return (
    <group position={[0, -0.4, 0]}>
      {/* 1. Catchment 3D Elevation Terrain */}
      <WatershedCatchmentTerrain soilMoistureVol={soilMoistureVol} />

      {/* 2. SWAT+ HRU Thematic Spatial Parcels */}
      {/* HRU 1: Corn Belt Cropland (Clickable - drills down to Meso field scale) */}
      <AgriculturalHruParcel
        position={[-9, 0.55, 6]}
        size={[14, 12]}
        color="#58853b"
        rotation={-0.12}
        label="HRU 1"
        cropType="Zea mays L."
        areaPercent={62}
        onClick={onSelectSubbasin}
      />

      {/* HRU 2: Conservation Agriculture (Siembra Directa) */}
      <AgriculturalHruParcel
        position={[8, 0.45, 7]}
        size={[12, 11]}
        color="#8f8745"
        rotation={0.14}
        label="HRU 2"
        cropType="Siembra Directa / Mulch"
        areaPercent={18}
      />

      {/* HRU 4: Upland Grassland / Pasture on ridge */}
      <AgriculturalHruParcel
        position={[-12, 1.15, -9]}
        size={[13, 10]}
        color="#6f8546"
        rotation={0.18}
        label="HRU 4"
        cropType="Pastizal / Pasture"
        areaPercent={10}
      />

      {/* HRU 5: Riparian & Wetland buffer */}
      <AgriculturalHruParcel
        position={[11, 0.22, -8]}
        size={[11, 9]}
        color="#4a7337"
        rotation={-0.15}
        label="HRU 5"
        cropType="Humedal / Ripario"
        areaPercent={10}
      />

      {/* 3. Riparian Forest Tree Belts lining river channel */}
      <RiparianTreeBelt curvePoints={riverPoints} treeCount={24} />

      {/* 4. Animated Dendritic River Network */}
      {/* Main Channel (Order 3) */}
      <Line
        points={riverPoints}
        color="#38bdf8"
        lineWidth={riverWidth * 12}
        transparent
        opacity={0.92}
      />
      {/* Tributary Creek (Order 2) */}
      <Line
        points={tributaryPoints}
        color="#60a5fa"
        lineWidth={riverWidth * 6}
        transparent
        opacity={0.82}
      />

      {/* 5. USGS Gauging Station at Outlet */}
      <UsgsGaugingStation
        position={[22, -0.15, -13.5]}
        streamflowM3s={streamflowM3s}
      />

      {/* 6. CMIP6 Precipitation Rain Simulation */}
      {showHydrologyFlow && (
        <PrecipitationRainSystem precipMm={precipMm} />
      )}

      {/* 7. Scientific 3D Callout Badges */}
      {showScientificLabels && (
        <>
          {/* Watershed Overview Callout */}
          <Html position={[-20, 3.8, 14]} distanceFactor={18}>
            <div className="w-72 rounded-xl border border-cyan-400/40 bg-zinc-950/90 p-3 font-mono text-[10px] text-zinc-200 shadow-2xl backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-cyan-500/30 pb-1">
                <span className="font-bold text-cyan-300">Cuenca procedural (Macro)</span>
                <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[9px] text-cyan-300">
                  ILLUSTRATIVE
                </span>
              </div>
              <div className="mt-1.5 space-y-1 text-[9px]">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Precipitación simulada:</span>
                  <span className="font-bold text-sky-300">{precipMm.toFixed(1)} mm/d</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Humedad media cuenca (θ):</span>
                  <span className="font-bold text-teal-300">{soilMoistureVol.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Descarga simulada (Q):</span>
                  <span className="font-bold text-cyan-300">{streamflowM3s.toFixed(2)} m³/s</span>
                </div>
                <div className="mt-1 border-t border-zinc-800 pt-1 text-emerald-400">
                  💡 Haz clic en la parcela verde para bajar a la vista de campo ilustrativa.
                </div>
              </div>
            </div>
          </Html>

          {/* HRU 1 Callout with click prompt */}
          <Html position={[-9, 1.6, 6]} center distanceFactor={16}>
            <div
              onClick={(e) => {
                e.stopPropagation();
                onSelectSubbasin();
              }}
              className="cursor-pointer rounded-lg border border-emerald-400/50 bg-slate-950/88 px-2.5 py-1.5 font-mono text-[9px] text-emerald-300 shadow-xl backdrop-blur transition hover:scale-105 hover:border-emerald-300"
            >
              <div className="font-bold flex items-center gap-1">
                <span>Región proxy: maíz</span>
                <span className="text-emerald-400">→</span>
              </div>
              <div className="text-[8px] text-zinc-400">Clic para explorar la muestra de 1000 plantas</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Cloud, Sparkles, Html } from "@react-three/drei";

interface WatershedMesh3DProps {
  streamflowM3s: number;
  precipMm: number;
  soilMoistureVol: number;
  onSelectSubbasin?: (subbasinName: string) => void;
}

export default function WatershedMesh3D({
  streamflowM3s,
  precipMm,
  soilMoistureVol,
  onSelectSubbasin,
}: WatershedMesh3DProps) {
  const rainLinesRef = useRef<THREE.LineSegments>(null);
  const riverMeshRef = useRef<THREE.Mesh>(null);
  const riverMaterialRef = useRef<THREE.MeshStandardMaterial>(null);
  const terrainMaterialRef = useRef<THREE.MeshStandardMaterial>(null);
  const runoffStreamsRef = useRef<THREE.LineSegments>(null);

  // 1. Generar malla topográfica 3D (DEM)
  const { geometry, riverPoints, runoffGeo } = useMemo(() => {
    const width = 64;
    const depth = 64;
    const segments = 80;
    const geom = new THREE.PlaneGeometry(width, depth, segments, segments);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    const colors = new Float32Array(pos.count * 3);
    const riverCoords: THREE.Vector3[] = [];

    // Colores base para hipsometría
    const valleyBase = new THREE.Color("#2d6a4f");
    const midSlopeColor = new THREE.Color("#6c584c");
    const rockColor = new THREE.Color("#4a5568");
    const snowPeakColor = new THREE.Color("#e2e8f0");

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      // Río meándrico
      const riverX = Math.sin(z * 0.08) * 8.0 - z * 0.2;
      const distToRiver = Math.abs(x - riverX);

      // Relieve montañoso
      const mountainRidge =
        Math.cos(x * 0.12) * Math.sin(z * 0.1) * 6.5 +
        Math.sin(x * 0.25) * 3.2 +
        Math.cos(z * 0.22) * 2.8;

      const valleyFactor = Math.min(1.0, Math.pow(distToRiver / 13.0, 1.2));
      let y = Math.max(0.4, valleyFactor * 9.0 + mountainRidge * valleyFactor);
      y += (z + depth / 2) * 0.16;

      pos.setY(i, y);

      // Colores de vértice según cota
      const vertexColor = new THREE.Color();
      if (y < 3.2) {
        vertexColor.copy(valleyBase);
      } else if (y < 8.0) {
        const t = (y - 3.2) / 4.8;
        vertexColor.copy(valleyBase).lerp(midSlopeColor, t);
      } else if (y < 13.0) {
        const t = (y - 8.0) / 5.0;
        vertexColor.copy(midSlopeColor).lerp(rockColor, t);
      } else {
        const t = Math.min(1.0, (y - 13.0) / 4.0);
        vertexColor.copy(rockColor).lerp(snowPeakColor, t);
      }

      colors[i * 3] = vertexColor.r;
      colors[i * 3 + 1] = vertexColor.g;
      colors[i * 3 + 2] = vertexColor.b;
    }

    geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geom.computeVertexNormals();

    // Trayectoria del río
    for (let z = -depth / 2 + 2; z <= depth / 2 - 2; z += 1.8) {
      const riverX = Math.sin(z * 0.08) * 8.0 - z * 0.2;
      const y = 0.75 + (z + depth / 2) * 0.16;
      riverCoords.push(new THREE.Vector3(riverX, y, z));
    }

    // Pequeñas líneas de escorrentía en laderas
    const runoffPositions = new Float32Array(40 * 6);
    for (let i = 0; i < 40; i++) {
      const rz = -20 + Math.random() * 40;
      const rx = (Math.random() > 0.5 ? 1 : -1) * (10 + Math.random() * 14);
      const riverX = Math.sin(rz * 0.08) * 8.0 - rz * 0.2;
      const ry = 4.0 + Math.random() * 4.0;

      runoffPositions[i * 6] = rx;
      runoffPositions[i * 6 + 1] = ry;
      runoffPositions[i * 6 + 2] = rz;

      runoffPositions[i * 6 + 3] = (rx + riverX) * 0.5;
      runoffPositions[i * 6 + 4] = ry - 1.5;
      runoffPositions[i * 6 + 5] = rz + 1.0;
    }
    const rGeo = new THREE.BufferGeometry();
    rGeo.setAttribute("position", new THREE.BufferAttribute(runoffPositions, 3));

    return { geometry: geom, riverPoints: riverCoords, runoffGeo: rGeo };
  }, []);

  // 2. Tubo 3D de Río con radio dinámico según caudal
  const riverGeometry = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(riverPoints);
    const radius = Math.max(0.45, Math.min(1.8, 0.4 + (streamflowM3s / 20.0) * 0.9));
    return new THREE.TubeGeometry(curve, 90, radius, 12, false);
  }, [riverPoints, streamflowM3s]);

  // 3. Sistema de Lluvia
  const rainLinesGeo = useMemo(() => {
    const count = Math.min(2200, Math.floor(precipMm * 60));
    if (count <= 0) return null;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 6);

    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 62;
      const y = Math.random() * 26 + 4;
      const z = (Math.random() - 0.5) * 62;
      const streakLength = 0.9 + Math.random() * 0.8;

      positions[i * 6] = x;
      positions[i * 6 + 1] = y;
      positions[i * 6 + 2] = z;

      positions[i * 6 + 3] = x;
      positions[i * 6 + 4] = y - streakLength;
      positions[i * 6 + 5] = z;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geom;
  }, [precipMm]);

  // Posición de la Parcela Agrícola en la terraza del valle
  const parcelPosition: [number, number, number] = [-6.5, 2.4, 4.0];

  // Animación en tiempo real: Flujo del agua, lluvia y brillo de humedad
  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    // 1. Animación del río (ondulaciones, brillo y velocidad según caudal)
    if (riverMaterialRef.current && riverMeshRef.current) {
      const flowSpeed = 1.0 + (streamflowM3s / 10.0) * 2.5;
      const wave = Math.sin(time * flowSpeed * 3.0) * 0.12;
      riverMaterialRef.current.emissiveIntensity = 0.6 + wave;

      // Pulso de hinchamiento visible en crecidas
      const swellScale = 1.0 + Math.sin(time * 2.0) * (streamflowM3s > 15 ? 0.08 : 0.03);
      riverMeshRef.current.scale.set(swellScale, swellScale, 1.0);
    }

    // 2. Terreno húmedo: cuando hay lluvia o humedad alta, aumenta el brillo especular y oscurece
    if (terrainMaterialRef.current) {
      const wetness = Math.min(1.0, (soilMoistureVol - 10) / 30.0 + (precipMm > 0 ? 0.3 : 0));
      terrainMaterialRef.current.roughness = 0.85 - wetness * 0.35;
      terrainMaterialRef.current.metalness = 0.05 + wetness * 0.25;
    }

    // 3. Caída de lluvia
    if (rainLinesRef.current && rainLinesGeo) {
      const pos = rainLinesRef.current.geometry.attributes.position;
      const dropSpeed = (35 + precipMm * 0.5) * delta;
      for (let i = 0; i < pos.count; i += 2) {
        let yTop = pos.getY(i) - dropSpeed;
        let yBot = pos.getY(i + 1) - dropSpeed;
        if (yBot < 0.5) {
          const resetHeight = 28 + Math.random() * 4;
          const len = yTop - yBot;
          yTop = resetHeight;
          yBot = resetHeight - len;
        }
        pos.setY(i, yTop);
        pos.setY(i + 1, yBot);
      }
      pos.needsUpdate = true;
    }

    // 4. Animación de escorrentías en laderas
    if (runoffStreamsRef.current) {
      runoffStreamsRef.current.visible = precipMm > 10;
    }
  });

  return (
    <group>
      {/* Terreno DEM 3D con Hipsometría y Brillo de Humedad */}
      <mesh
        geometry={geometry}
        receiveShadow
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelectSubbasin?.("Subcuenca Media Agrícola");
        }}
      >
        <meshStandardMaterial
          ref={terrainMaterialRef}
          vertexColors
          roughness={0.75}
          metalness={0.08}
          flatShading={false}
        />
      </mesh>

      {/* Malla científica sutil */}
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#38bdf8" wireframe transparent opacity={0.035} />
      </mesh>

      {/* Río 3D Animado */}
      <mesh ref={riverMeshRef} geometry={riverGeometry} castShadow>
        <meshStandardMaterial
          ref={riverMaterialRef}
          color="#06b6d4"
          emissive="#0284c7"
          emissiveIntensity={0.65}
          roughness={0.15}
          metalness={0.7}
          transparent
          opacity={0.88}
        />
      </mesh>

      {/* Escorrentías superficiales en laderas durante lluvia intensa */}
      <lineSegments ref={runoffStreamsRef} geometry={runoffGeo}>
        <lineBasicMaterial color="#67e8f9" transparent opacity={0.6} linewidth={2} />
      </lineSegments>

      {/* Marcador 3D Interactivo de la Parcela HRU sobre la terraza del valle */}
      <group
        position={parcelPosition}
        onClick={(e) => {
          e.stopPropagation();
          onSelectSubbasin?.("Subcuenca Media Agrícola");
        }}
      >
        {/* Base de la parcela verde */}
        <mesh position={[0, 0.1, 0]}>
          <boxGeometry args={[4.5, 0.2, 4.5]} />
          <meshStandardMaterial color="#15803d" roughness={0.7} />
        </mesh>
        {/* Minis árboles en la parcela macro */}
        {[-1.2, 0, 1.2].map((x) =>
          [-1.2, 0, 1.2].map((z) => (
            <mesh key={`${x}-${z}`} position={[x, 0.45, z]}>
              <sphereGeometry args={[0.22, 8, 8]} />
              <meshStandardMaterial color="#16a34a" />
            </mesh>
          ))
        )}
        {/* Etiqueta HTML 3D Flotante */}
        <Html position={[0, 1.4, 0]} center distanceFactor={25} className="pointer-events-none select-none">
          <div className="flex flex-col items-center bg-zinc-950/90 backdrop-blur-md border border-emerald-500/60 px-2.5 py-1 rounded-xl shadow-2xl text-[11px] font-sans text-emerald-300 font-bold whitespace-nowrap animate-bounce cursor-pointer">
            <span>📍 Parcela AP-3 (Palto Hass)</span>
            <span className="text-[9px] text-zinc-400 font-normal">Haz clic para zoom a Parcela</span>
          </div>
        </Html>
      </group>

      {/* Espuma y Turbulencia de Agua en el Exutorio */}
      <group position={riverPoints[0] ? [riverPoints[0].x, riverPoints[0].y + 0.3, riverPoints[0].z] : [0, 1, 0]}>
        <Sparkles
          count={Math.min(70, Math.floor(10 + streamflowM3s * 3.5))}
          scale={[3.5, 1.5, 3.5]}
          size={2.0}
          speed={1.8}
          color="#e0f2fe"
        />
        {/* Baliza Exutorio */}
        <mesh position={[0, 0.6, 0]}>
          <sphereGeometry args={[0.35, 16, 16]} />
          <meshStandardMaterial color="#f43f5e" emissive="#f43f5e" emissiveIntensity={1.5} />
        </mesh>
        <pointLight position={[0, 0.6, 0]} color="#f43f5e" intensity={3} distance={9} />
      </group>

      {/* Nubes Volumétricas */}
      <group position={[0, 18, -12]}>
        <Cloud
          opacity={precipMm > 0 ? 0.8 : 0.35}
          speed={0.25}
          segments={20}
          bounds={[24, 4, 16]}
          color={precipMm > 20 ? "#334155" : "#f8fafc"}
        />
      </group>

      {/* Gotas de Lluvia */}
      {rainLinesGeo && (
        <lineSegments ref={rainLinesRef} geometry={rainLinesGeo}>
          <lineBasicMaterial color="#7dd3fc" transparent opacity={0.7} linewidth={1} />
        </lineSegments>
      )}
    </group>
  );
}

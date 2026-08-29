"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

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
  const riverMaterialRef = useRef<THREE.MeshStandardMaterial>(null);
  const rainRef = useRef<THREE.Points>(null);

  // Generar malla topográfica 3D (DEM) de la cuenca
  const { geometry, riverPoints } = useMemo(() => {
    const width = 60;
    const depth = 60;
    const segments = 64;
    const geom = new THREE.PlaneGeometry(width, depth, segments, segments);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    const riverCoords: THREE.Vector3[] = [];

    // Crear relieve de valle montañoso interandino con cauce fluvial central
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      // Distancia al cauce principal del río (curva sinusoidal)
      const riverX = Math.sin(z * 0.08) * 8.0 - (z * 0.2);
      const distToRiver = Math.abs(x - riverX);

      // Elevación de las laderas montañosas
      const mountainRidge =
        Math.cos(x * 0.12) * Math.sin(z * 0.1) * 6.0 +
        Math.sin(x * 0.25) * 3.0 +
        Math.cos(z * 0.2) * 2.5;

      // El cauce crea una garganta/valle en V
      const valleyFactor = Math.min(1.0, distToRiver / 12.0);
      let y = Math.max(0.5, (valleyFactor * 8.5) + mountainRidge * valleyFactor);

      // Pendiente longitudinal de la cuenca (de cabecera alta a exutorio bajo)
      y += (z + depth / 2) * 0.15;

      pos.setY(i, y);
    }
    geom.computeVertexNormals();

    // Crear puntos para el río
    for (let z = -depth / 2 + 2; z <= depth / 2 - 2; z += 2) {
      const riverX = Math.sin(z * 0.08) * 8.0 - (z * 0.2);
      const y = 0.8 + (z + depth / 2) * 0.15;
      riverCoords.push(new THREE.Vector3(riverX, y, z));
    }

    return { geometry: geom, riverPoints: riverCoords };
  }, []);

  // Tubo 3D para el río
  const riverGeometry = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(riverPoints);
    const radius = Math.max(0.3, Math.min(1.2, 0.3 + (streamflowM3s / 30.0) * 0.7));
    return new THREE.TubeGeometry(curve, 64, radius, 8, false);
  }, [riverPoints, streamflowM3s]);

  // Partículas de lluvia cuando precipita
  const rainGeo = useMemo(() => {
    const count = Math.min(1500, Math.floor(precipMm * 50));
    if (count <= 0) return null;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 1] = Math.random() * 25 + 5;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 60;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geom;
  }, [precipMm]);

  // Animación del flujo del agua y caída de lluvia
  useFrame((_, delta) => {
    if (riverMaterialRef.current) {
      riverMaterialRef.current.opacity = 0.75 + Math.sin(Date.now() * 0.003) * 0.15;
    }
    if (rainRef.current && rainGeo) {
      const pos = rainRef.current.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) - delta * 35;
        if (y < 1) y = 25;
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    }
  });

  // Color de terreno según humedad de suelo (verde exuberante si húmedo, ocre/árido si seco)
  const terrainColor = useMemo(() => {
    const moisture = Math.max(10, Math.min(40, soilMoistureVol));
    const factor = (moisture - 10) / 30.0;
    // Interpolar entre marrón seco (#785233) y verde cuenca (#1e5e32)
    const dryColor = new THREE.Color("#6b4c2b");
    const lushColor = new THREE.Color("#1e5a32");
    return dryColor.clone().lerp(lushColor, factor);
  }, [soilMoistureVol]);

  return (
    <group>
      {/* Terreno DEM 3D */}
      <mesh
        geometry={geometry}
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelectSubbasin?.("Subcuenca Media Agrícola");
        }}
      >
        <meshStandardMaterial
          color={terrainColor}
          roughness={0.85}
          metalness={0.05}
          flatShading
        />
      </mesh>

      {/* Malla alámbrica sutil para efecto científico */}
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#10b981" wireframe transparent opacity={0.06} />
      </mesh>

      {/* Red Fluvial 3D (Río Santa Eulalia) */}
      <mesh geometry={riverGeometry}>
        <meshStandardMaterial
          ref={riverMaterialRef}
          color="#00f0ff"
          emissive="#007799"
          emissiveIntensity={0.6}
          roughness={0.1}
          metalness={0.8}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* Estación Hidrométrica Exutorio */}
      <group position={riverPoints[0] ? [riverPoints[0].x, riverPoints[0].y + 1, riverPoints[0].z] : [0, 1, 0]}>
        <mesh>
          <sphereGeometry args={[0.6, 16, 16]} />
          <meshStandardMaterial color="#f43f5e" emissive="#e11d48" emissiveIntensity={0.8} />
        </mesh>
        <pointLight color="#f43f5e" intensity={2} distance={6} />
      </group>

      {/* Partículas de Precipitación */}
      {rainGeo && (
        <points ref={rainRef} geometry={rainGeo}>
          <pointsMaterial color="#67e8f9" size={0.18} transparent opacity={0.7} />
        </points>
      )}
    </group>
  );
}

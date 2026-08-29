"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

interface FieldPlotMesh3DProps {
  soilMoistureVol: number;
  cwsiStress: number;
  onSelectPlant?: () => void;
}

export default function FieldPlotMesh3D({
  soilMoistureVol,
  cwsiStress,
  onSelectPlant,
}: FieldPlotMesh3DProps) {
  const moistureGlowRef = useRef<THREE.MeshStandardMaterial>(null);

  // Filas de cultivo de palto/frutales en la parcela
  const plantsGrid = useMemo(() => {
    const items: { x: number; z: number; scale: number }[] = [];
    for (let row = -3; row <= 3; row++) {
      for (let col = -3; col <= 3; col++) {
        // Dejar espacio central libre para la planta destacada
        if (row === 0 && col === 0) continue;
        items.push({
          x: col * 3.5,
          z: row * 4.0,
          scale: 0.75 + ((Math.abs(row) + Math.abs(col)) % 3) * 0.08,
        });
      }
    }
    return items;
  }, []);

  useFrame(() => {
    if (moistureGlowRef.current) {
      moistureGlowRef.current.opacity = 0.5 + Math.sin(Date.now() * 0.002) * 0.15;
    }
  });

  // Color de follaje de las plantas de parcela según estrés
  const canopyColor = useMemo(() => {
    const healthy = new THREE.Color("#10b981");
    const stressed = new THREE.Color("#eab308");
    const wilting = new THREE.Color("#b45309");
    if (cwsiStress < 0.3) {
      return healthy;
    } else if (cwsiStress < 0.6) {
      return healthy.clone().lerp(stressed, (cwsiStress - 0.3) / 0.3);
    } else {
      return stressed.clone().lerp(wilting, (cwsiStress - 0.6) / 0.4);
    }
  }, [cwsiStress]);

  return (
    <group>
      {/* Superficie de la Parcela Agrícola */}
      <mesh receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[28, 0.4, 32]} />
        <meshStandardMaterial color="#3f2e1e" roughness={0.9} />
      </mesh>

      {/* Surcos de Riego Tecnificado */}
      {[-10, -6, -2, 2, 6, 10].map((zPos) => (
        <mesh key={zPos} position={[0, 0.22, zPos]}>
          <boxGeometry args={[26, 0.05, 0.8]} />
          <meshStandardMaterial color="#2d1f14" roughness={0.95} />
        </mesh>
      ))}

      {/* Perfil Estratificado Subterráneo (Corte de Suelo en el Borde Frontal) */}
      <group position={[0, -2.2, 16.1]}>
        {/* Capa 0-30 cm: Horizonte A Orgánico */}
        <mesh position={[0, 1.4, 0]}>
          <boxGeometry args={[28, 1.2, 0.2]} />
          <meshStandardMaterial color="#2e1f14" roughness={0.9} />
        </mesh>
        {/* Capa 30-60 cm: Horizonte B Francoradicular */}
        <mesh position={[0, 0.2, 0]}>
          <boxGeometry args={[28, 1.2, 0.2]} />
          <meshStandardMaterial color="#4a3525" roughness={0.85} />
        </mesh>
        {/* Capa 60-100 cm: Horizonte C Arcillo-Arenoso */}
        <mesh position={[0, -1.0, 0]}>
          <boxGeometry args={[28, 1.2, 0.2]} />
          <meshStandardMaterial color="#614a38" roughness={0.8} />
        </mesh>
      </group>

      {/* Filas de Plantas en la Parcela */}
      {plantsGrid.map((p, idx) => (
        <group key={idx} position={[p.x, 0.2, p.z]} scale={p.scale}>
          {/* Tronco */}
          <mesh position={[0, 0.9, 0]}>
            <cylinderGeometry args={[0.08, 0.12, 1.8, 8]} />
            <meshStandardMaterial color="#5c3d24" roughness={0.9} />
          </mesh>
          {/* Copa foliar */}
          <mesh position={[0, 2.1, 0]}>
            <sphereGeometry args={[0.9, 12, 12]} />
            <meshStandardMaterial color={canopyColor} roughness={0.7} />
          </mesh>
        </group>
      ))}

      {/* Sensor IoT de Humedad y Salinidad en Parcela */}
      <group position={[3.5, 0.2, 1.8]}>
        {/* Vástago del sensor */}
        <mesh position={[0, 0.8, 0]}>
          <cylinderGeometry args={[0.04, 0.04, 1.6, 8]} />
          <meshStandardMaterial color="#0284c7" metalness={0.8} />
        </mesh>
        {/* Cabeza del sensor IoT (transmisor) */}
        <mesh position={[0, 1.7, 0]}>
          <boxGeometry args={[0.25, 0.35, 0.2]} />
          <meshStandardMaterial color="#0f172a" />
        </mesh>
        {/* LED Pulsante de Telemetría */}
        <mesh position={[0, 1.85, 0]}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial
            color="#38bdf8"
            emissive="#38bdf8"
            emissiveIntensity={1.2}
          />
        </mesh>
        <pointLight position={[0, 1.85, 0]} color="#38bdf8" intensity={1.5} distance={4} />
      </group>

      {/* Marcador para la Planta Central */}
      <group
        position={[0, 0.3, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onSelectPlant?.();
        }}
      >
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1.5, 1.8, 32]} />
          <meshBasicMaterial
            ref={moistureGlowRef}
            color="#10b981"
            transparent
            opacity={0.6}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>
    </group>
  );
}

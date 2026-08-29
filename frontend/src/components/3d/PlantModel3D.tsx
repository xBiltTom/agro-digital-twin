"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

interface PlantModel3DProps {
  transpirationMm: number;
  cwsiStress: number;
  sapFlowVelocityCmh: number;
  soilMoistureVol: number;
}

export default function PlantModel3D({
  transpirationMm,
  cwsiStress,
  sapFlowVelocityCmh,
  soilMoistureVol,
}: PlantModel3DProps) {
  const sapParticlesRef = useRef<THREE.Points>(null);
  const rootGlowRef = useRef<THREE.MeshStandardMaterial>(null);

  // Color de hojas dinámico según estrés hídrico CWSI
  const leafColor = useMemo(() => {
    const lush = new THREE.Color("#10b981");
    const warning = new THREE.Color("#eab308");
    const drought = new THREE.Color("#d97706");
    if (cwsiStress < 0.25) {
      return lush;
    } else if (cwsiStress < 0.55) {
      return lush.clone().lerp(warning, (cwsiStress - 0.25) / 0.3);
    } else {
      return warning.clone().lerp(drought, (cwsiStress - 0.55) / 0.45);
    }
  }, [cwsiStress]);

  // Partículas de flujo de savia xilemático ascendente
  const { sapParticlesGeo, speeds } = useMemo(() => {
    const count = 75;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const spds = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      // Radio dentro del tronco
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.random() * 0.12;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = -1.8 + Math.random() * 4.2; // Desde raíz profunda hasta copa
      positions[i * 3 + 2] = Math.sin(angle) * radius;
      spds[i] = 0.5 + Math.random() * 0.5;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return { sapParticlesGeo: geom, speeds: spds };
  }, []);

  // Animación del flujo de savia en tiempo real
  useFrame((_, delta) => {
    if (sapParticlesRef.current) {
      const pos = sapParticlesRef.current.geometry.attributes.position;
      // La velocidad de animación escala con el flujo de savia medido (cm/h)
      const speedFactor = Math.max(0.2, sapFlowVelocityCmh / 10.0);

      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) + delta * speedFactor * speeds[i] * 2.2;
        if (y > 2.5) {
          y = -1.8; // Reiniciar en la base de la raíz
        }
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    }

    if (rootGlowRef.current) {
      rootGlowRef.current.opacity = 0.4 + Math.sin(Date.now() * 0.003) * 0.15;
    }
  });

  // Ramificación radicular procedural
  const rootBranches = useMemo(() => {
    const branches: { start: [number, number, number]; end: [number, number, number]; radius: number }[] = [
      // Raíz pivotante central
      { start: [0, 0, 0], end: [0, -1.8, 0], radius: 0.1 },
      { start: [0, -0.4, 0], end: [0.6, -1.1, 0.4], radius: 0.06 },
      { start: [0, -0.6, 0], end: [-0.7, -1.3, -0.5], radius: 0.06 },
      { start: [0, -0.8, 0], end: [-0.5, -1.5, 0.6], radius: 0.05 },
      { start: [0, -1.0, 0], end: [0.7, -1.6, -0.4], radius: 0.05 },
      // Raíces laterales de absorción
      { start: [0.6, -1.1, 0.4], end: [1.1, -1.5, 0.7], radius: 0.03 },
      { start: [-0.7, -1.3, -0.5], end: [-1.2, -1.7, -0.8], radius: 0.03 },
    ];
    return branches;
  }, []);

  return (
    <group>
      {/* Tronco Principal (Xilema y Floema) */}
      <mesh position={[0, 1.2, 0]} castShadow>
        <cylinderGeometry args={[0.15, 0.22, 2.4, 16]} />
        <meshStandardMaterial color="#4a3525" roughness={0.85} />
      </mesh>

      {/* Ramas Principales de la Canopia */}
      <group position={[0, 2.0, 0]}>
        <mesh position={[0.4, 0.4, 0.3]} rotation={[0.4, 0.2, 0.5]}>
          <cylinderGeometry args={[0.08, 0.12, 1.2, 8]} />
          <meshStandardMaterial color="#4a3525" />
        </mesh>
        <mesh position={[-0.4, 0.5, -0.2]} rotation={[-0.3, 0.4, -0.6]}>
          <cylinderGeometry args={[0.08, 0.12, 1.3, 8]} />
          <meshStandardMaterial color="#4a3525" />
        </mesh>
        <mesh position={[0.1, 0.6, -0.4]} rotation={[-0.5, -0.2, 0.3]}>
          <cylinderGeometry args={[0.07, 0.11, 1.1, 8]} />
          <meshStandardMaterial color="#4a3525" />
        </mesh>
      </group>

      {/* Canopia Foliar / Racimos de Hojas */}
      <group position={[0, 2.8, 0]}>
        <mesh position={[0, 0.4, 0]} castShadow>
          <sphereGeometry args={[1.3, 16, 16]} />
          <meshStandardMaterial color={leafColor} roughness={0.6} />
        </mesh>
        <mesh position={[0.7, 0.1, 0.5]} castShadow>
          <sphereGeometry args={[0.85, 14, 14]} />
          <meshStandardMaterial color={leafColor} roughness={0.65} />
        </mesh>
        <mesh position={[-0.6, 0.2, -0.4]} castShadow>
          <sphereGeometry args={[0.9, 14, 14]} />
          <meshStandardMaterial color={leafColor} roughness={0.65} />
        </mesh>
        <mesh position={[0.1, 0.8, -0.5]} castShadow>
          <sphereGeometry args={[0.75, 14, 14]} />
          <meshStandardMaterial color={leafColor} roughness={0.65} />
        </mesh>
      </group>

      {/* Partículas de Flujo de Savia Ascendente */}
      <points ref={sapParticlesRef} geometry={sapParticlesGeo}>
        <pointsMaterial
          color="#38bdf8"
          size={0.07}
          transparent
          opacity={0.85}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Cilindro de Suelo Transparente / Zona Radicular */}
      <group position={[0, -1.0, 0]}>
        <mesh>
          <cylinderGeometry args={[1.6, 1.6, 2.0, 32, 1, true]} />
          <meshStandardMaterial
            color="#271c13"
            transparent
            opacity={0.35}
            roughness={0.9}
            side={THREE.DoubleSide}
          />
        </mesh>
        {/* Base del cilindro */}
        <mesh position={[0, -1.0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[1.6, 32]} />
          <meshStandardMaterial color="#1a120c" />
        </mesh>
      </group>

      {/* Red Radicular Subterránea (Root System) */}
      <group position={[0, 0, 0]}>
        {rootBranches.map((b, idx) => {
          const p1 = new THREE.Vector3(...b.start);
          const p2 = new THREE.Vector3(...b.end);
          const dir = p2.clone().sub(p1);
          const len = dir.length();
          const mid = p1.clone().add(p2).multiplyScalar(0.5);

          const quaternion = new THREE.Quaternion();
          quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
          const euler = new THREE.Euler().setFromQuaternion(quaternion);

          return (
            <mesh key={idx} position={[mid.x, mid.y, mid.z]} rotation={euler}>
              <cylinderGeometry args={[b.radius * 0.6, b.radius, len, 8]} />
              <meshStandardMaterial color="#8b5a2b" roughness={0.9} />
            </mesh>
          );
        })}
      </group>

      {/* Aura de Absorción Radicular de Feddes en el Suelo */}
      <mesh position={[0, -0.9, 0]}>
        <sphereGeometry args={[1.4, 24, 24]} />
        <meshBasicMaterial
          ref={rootGlowRef}
          color="#0ea5e9"
          transparent
          opacity={0.15}
          wireframe
        />
      </mesh>
    </group>
  );
}

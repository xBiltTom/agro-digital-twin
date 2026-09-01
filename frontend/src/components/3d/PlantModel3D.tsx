"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Float, Sparkles, Html } from "@react-three/drei";

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
  const vaporParticlesRef = useRef<THREE.Points>(null);
  const internalLightRef = useRef<THREE.PointLight>(null);
  const foliageGroupRef = useRef<THREE.Group>(null);
  const leafMaterialRef = useRef<THREE.MeshStandardMaterial>(null);

  // 1. Partículas de flujo de savia xilemático ascendente
  const { sapParticlesGeo, sapSpeeds } = useMemo(() => {
    const count = 160;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const spds = new Float32Array(count);

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.03 + Math.random() * 0.09;
      const y = -1.9 + Math.random() * 4.6;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = Math.sin(angle) * radius;
      spds[i] = 0.7 + Math.random() * 0.6;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return { sapParticlesGeo: geom, sapSpeeds: spds };
  }, []);

  // 2. Partículas de Vapor de Transpiración Foliar (subiendo al aire)
  const { vaporGeo } = useMemo(() => {
    const count = 50;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 1.8;
      positions[i * 3 + 1] = 2.8 + Math.random() * 2.0;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 1.8;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return { vaporGeo: geom };
  }, []);

  // Color de hojas dinámico según estrés hídrico CWSI
  const leafColor = useMemo(() => {
    const lush = new THREE.Color("#16a34a");
    const mild = new THREE.Color("#84cc16");
    const warning = new THREE.Color("#d97706");
    const wilting = new THREE.Color("#9a3412");

    if (cwsiStress < 0.25) {
      return lush;
    } else if (cwsiStress < 0.5) {
      return lush.clone().lerp(mild, (cwsiStress - 0.25) / 0.25);
    } else if (cwsiStress < 0.75) {
      return mild.clone().lerp(warning, (cwsiStress - 0.5) / 0.25);
    } else {
      return warning.clone().lerp(wilting, (cwsiStress - 0.75) / 0.25);
    }
  }, [cwsiStress]);

  // Animaciones en tiempo real: flujo de savia veloz, vapor de transpiración y marchitez
  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    // 1. Partículas de savia (velocidad acelerada por sapFlowVelocityCmh)
    if (sapParticlesRef.current) {
      const pos = sapParticlesRef.current.geometry.attributes.position;
      const speedFactor = Math.max(0.4, sapFlowVelocityCmh / 6.0);

      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) + delta * speedFactor * sapSpeeds[i] * 3.2;
        if (y > 2.8) {
          y = -1.9; // Reiniciar en raíces
        }
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    }

    // 2. Partículas de vapor de transpiración foliar
    if (vaporParticlesRef.current) {
      const pos = vaporParticlesRef.current.geometry.attributes.position;
      const vaporSpeed = Math.max(0.3, transpirationMm / 3.0) * delta * 1.5;

      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) + vaporSpeed;
        if (y > 5.0) {
          y = 2.6 + Math.random() * 0.4;
          pos.setX(i, (Math.random() - 0.5) * 1.8);
          pos.setZ(i, (Math.random() - 0.5) * 1.8);
        }
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    }

    // 3. Marchitez física de la copa de la planta (sagging en Y y contracción)
    if (foliageGroupRef.current) {
      const sagFactor = 1.0 - cwsiStress * 0.32;
      const breeze = Math.sin(time * 2.0) * 0.02;
      foliageGroupRef.current.scale.set(1.0 - cwsiStress * 0.1, sagFactor, 1.0 - cwsiStress * 0.1);
      foliageGroupRef.current.position.y = 2.7 - cwsiStress * 0.2 + breeze;
    }

    // 4. Luz interna fotosintética
    if (internalLightRef.current) {
      internalLightRef.current.intensity =
        0.8 + Math.sin(time * 3.0) * 0.4 * Math.max(0.4, transpirationMm / 3.0);
    }
  });

  // Ramificación radicular estratificada
  const rootBranches = useMemo(() => {
    const branches: { start: [number, number, number]; end: [number, number, number]; radius: number }[] = [
      { start: [0, 0, 0], end: [0, -1.9, 0], radius: 0.11 },
      { start: [0, -0.25, 0], end: [0.75, -0.65, 0.45], radius: 0.07 },
      { start: [0, -0.35, 0], end: [-0.8, -0.75, -0.5], radius: 0.07 },
      { start: [0, -0.5, 0], end: [0.55, -0.9, -0.6], radius: 0.06 },
      { start: [0, -0.65, 0], end: [-0.65, -1.05, 0.55], radius: 0.06 },
      { start: [0.75, -0.65, 0.45], end: [1.25, -1.2, 0.75], radius: 0.04 },
      { start: [-0.8, -0.75, -0.5], end: [-1.3, -1.35, -0.85], radius: 0.04 },
      { start: [0, -1.1, 0], end: [0.45, -1.65, 0.3], radius: 0.05 },
      { start: [0, -1.3, 0], end: [-0.4, -1.75, -0.35], radius: 0.05 },
    ];
    return branches;
  }, []);

  return (
    <group>
      {/* Tronco Principal con Capa Translúcida de Xilema Visible */}
      <group position={[0, 1.15, 0]}>
        {/* Médula / Xilema interior oscuro */}
        <mesh>
          <cylinderGeometry args={[0.07, 0.11, 2.3, 16]} />
          <meshStandardMaterial color="#1e130c" />
        </mesh>
        {/* Corteza translúcida que deja ver la savia */}
        <mesh>
          <cylinderGeometry args={[0.14, 0.21, 2.3, 16]} />
          <meshStandardMaterial
            color="#4a3319"
            roughness={0.75}
            transparent
            opacity={0.65}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>

      {/* Ramas Principales de la Canopia */}
      <group position={[0, 1.95, 0]}>
        <mesh position={[0.42, 0.45, 0.32]} rotation={[0.42, 0.2, 0.52]} castShadow>
          <cylinderGeometry args={[0.07, 0.11, 1.25, 8]} />
          <meshStandardMaterial color="#3e2716" roughness={0.88} />
        </mesh>
        <mesh position={[-0.42, 0.52, -0.22]} rotation={[-0.32, 0.4, -0.62]} castShadow>
          <cylinderGeometry args={[0.07, 0.11, 1.35, 8]} />
          <meshStandardMaterial color="#3e2716" roughness={0.88} />
        </mesh>
        <mesh position={[0.12, 0.65, -0.42]} rotation={[-0.52, -0.2, 0.32]} castShadow>
          <cylinderGeometry args={[0.06, 0.1, 1.15, 8]} />
          <meshStandardMaterial color="#3e2716" roughness={0.88} />
        </mesh>
      </group>

      {/* Copa Foliar Multi-Racimo con Marchitez Dinámica y Brisa */}
      <Float speed={1.5} rotationIntensity={0.12} floatIntensity={0.12}>
        <group ref={foliageGroupRef} position={[0, 2.7, 0]}>
          {/* Racimo central */}
          <mesh position={[0, 0.4, 0]} castShadow receiveShadow>
            <sphereGeometry args={[1.25, 18, 18]} />
            <meshStandardMaterial
              ref={leafMaterialRef}
              color={leafColor}
              roughness={0.55}
              metalness={0.08}
            />
          </mesh>

          {/* Racimos periféricos de follaje */}
          <mesh position={[0.72, 0.15, 0.52]} castShadow receiveShadow>
            <sphereGeometry args={[0.88, 16, 16]} />
            <meshStandardMaterial color={leafColor} roughness={0.55} />
          </mesh>
          <mesh position={[-0.68, 0.22, -0.42]} castShadow receiveShadow>
            <sphereGeometry args={[0.92, 16, 16]} />
            <meshStandardMaterial color={leafColor} roughness={0.55} />
          </mesh>
          <mesh position={[0.12, 0.85, -0.52]} castShadow receiveShadow>
            <sphereGeometry args={[0.78, 16, 16]} />
            <meshStandardMaterial color={leafColor} roughness={0.55} />
          </mesh>
          <mesh position={[-0.52, 0.75, 0.42]} castShadow receiveShadow>
            <sphereGeometry args={[0.72, 16, 16]} />
            <meshStandardMaterial color={leafColor} roughness={0.55} />
          </mesh>

          {/* Luz fotosintética interna en la canopia */}
          <pointLight
            ref={internalLightRef}
            position={[0, 0.4, 0]}
            color={cwsiStress > 0.5 ? "#f97316" : "#4ade80"}
            intensity={1.4}
            distance={4.5}
          />
        </group>
      </Float>

      {/* Partículas de Vapor de Transpiración Foliar (H₂O) */}
      <points ref={vaporParticlesRef} geometry={vaporGeo}>
        <pointsMaterial
          color="#a5f3fc"
          size={0.09}
          transparent
          opacity={0.65}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Partículas de Flujo de Savia Xilemática Ascendente (Glow Brillante) */}
      <points ref={sapParticlesRef} geometry={sapParticlesGeo}>
        <pointsMaterial
          color="#38bdf8"
          size={0.085}
          transparent
          opacity={0.95}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Cilindro de Suelo Científico Transparente / Rizosfera */}
      <group position={[0, -1.0, 0]}>
        <mesh receiveShadow>
          <cylinderGeometry args={[1.65, 1.65, 2.05, 32, 1, true]} />
          <meshStandardMaterial
            color="#22150c"
            transparent
            opacity={0.38}
            roughness={0.9}
            side={THREE.DoubleSide}
          />
        </mesh>
        <mesh position={[0, -1.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[1.65, 32]} />
          <meshStandardMaterial color="#140c06" />
        </mesh>
      </group>

      {/* Red Radicular Subterránea */}
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
            <mesh key={idx} position={[mid.x, mid.y, mid.z]} rotation={euler} castShadow>
              <cylinderGeometry args={[b.radius * 0.6, b.radius, len, 8]} />
              <meshStandardMaterial color="#854d0e" roughness={0.88} />
            </mesh>
          );
        })}
      </group>

      {/* Partículas de Absorción Radicular de Feddes en las Raíces */}
      <group position={[0, -1.0, 0]}>
        <Sparkles
          count={45}
          scale={[2.7, 1.9, 2.7]}
          size={1.8}
          speed={1.1}
          color="#38bdf8"
        />
      </group>

      {/* Etiqueta 3D Flotante con Fisiología Vegetal en Vivo */}
      <Html position={[0, 4.2, 0]} center distanceFactor={14} className="pointer-events-none select-none">
        <div className="bg-zinc-950/90 backdrop-blur-md border border-emerald-500/50 px-3 py-1.5 rounded-xl shadow-2xl text-[10px] font-mono text-zinc-200 flex flex-col items-center gap-0.5 whitespace-nowrap">
          <span className="font-bold text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            Fisiología: Palto Hass (Micro AP-3)
          </span>
          <div className="flex items-center gap-2 text-[9px] text-zinc-400">
            <span>
              Tr: <b className="text-emerald-300">{transpirationMm.toFixed(2)} mm/d</b>
            </span>
            <span>•</span>
            <span>
              Savia: <b className="text-sky-300">{sapFlowVelocityCmh.toFixed(1)} cm/h</b>
            </span>
            <span>•</span>
            <span>
              CWSI: <b className="text-amber-300">{cwsiStress.toFixed(2)}</b>
            </span>
          </div>
        </div>
      </Html>
    </group>
  );
}

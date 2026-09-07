"use client";

import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Float, Sparkles, Html } from "@react-three/drei";

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
  const signalGlowRef = useRef<THREE.PointLight>(null);
  const canopyGroupRef = useRef<THREE.Group>(null);
  const soilMaterialRef = useRef<THREE.MeshStandardMaterial>(null);
  const dripDropsRef = useRef<THREE.Points>(null);

  // Filas de cultivo de palto Hass en la parcela agrícola
  const plantsGrid = useMemo(() => {
    const items: {
      x: number;
      z: number;
      scale: number;
      rotationY: number;
      clusters: { offset: [number, number, number]; r: number }[];
    }[] = [];

    for (let row = -3; row <= 3; row++) {
      for (let col = -3; col <= 3; col++) {
        if (row === 0 && col === 0) continue; // Centro reservado para la planta micro

        const rot = ((row * 3 + col * 7) % 10) * 0.3;
        items.push({
          x: col * 3.6,
          z: row * 4.2,
          scale: 0.82 + ((Math.abs(row) + Math.abs(col)) % 3) * 0.09,
          rotationY: rot,
          clusters: [
            { offset: [0, 2.2, 0], r: 0.95 },
            { offset: [0.35, 2.0, 0.3], r: 0.65 },
            { offset: [-0.3, 2.1, -0.25], r: 0.68 },
            { offset: [0.1, 2.65, -0.1], r: 0.55 },
          ],
        });
      }
    }
    return items;
  }, []);

  // Partículas animadas de gotas de riego por goteo
  const { dripDropsGeo, dropOffsets } = useMemo(() => {
    const count = 48;
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const offs = new Float32Array(count);

    let idx = 0;
    [-12, -8, -4, 0, 4, 8, 12].forEach((zPos) => {
      for (let x = -10; x <= 10; x += 3.5) {
        if (idx < count) {
          positions[idx * 3] = x;
          positions[idx * 3 + 1] = 0.3 + Math.random() * 0.3;
          positions[idx * 3 + 2] = zPos;
          offs[idx] = Math.random();
          idx++;
        }
      }
    });

    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return { dripDropsGeo: geom, dropOffsets: offs };
  }, []);

  // Color de follaje según estrés hídrico CWSI
  const currentCanopyColor = useMemo(() => {
    const lush = new THREE.Color("#16a34a");
    const mild = new THREE.Color("#84cc16");
    const warning = new THREE.Color("#eab308");
    const wilting = new THREE.Color("#9a3412");

    if (cwsiStress < 0.25) {
      return lush;
    } else if (cwsiStress < 0.45) {
      return lush.clone().lerp(mild, (cwsiStress - 0.25) / 0.2);
    } else if (cwsiStress < 0.7) {
      return mild.clone().lerp(warning, (cwsiStress - 0.45) / 0.25);
    } else {
      return warning.clone().lerp(wilting, (cwsiStress - 0.7) / 0.3);
    }
  }, [cwsiStress]);

  // Animaciones en tiempo real: marchitez de hojas, gotas de riego y pulso de suelo
  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    // 1. Gotas de riego por goteo cayendo al suelo
    if (dripDropsRef.current) {
      const pos = dripDropsRef.current.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) - delta * 1.5;
        if (y < 0.05) {
          y = 0.35;
        }
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
    }

    // 2. Marchitez física de árboles cuando hay sequía (sagging vertical)
    if (canopyGroupRef.current) {
      const sagFactor = 1.0 - cwsiStress * 0.28;
      const breeze = Math.sin(time * 1.8) * 0.015;
      canopyGroupRef.current.scale.set(1.0 + breeze, sagFactor, 1.0 + breeze);
    }

    // 3. Color y humedad del suelo
    if (soilMaterialRef.current) {
      const moisture = Math.max(10, Math.min(40, soilMoistureVol));
      const factor = (moisture - 10) / 30.0;
      const dry = new THREE.Color("#5c4033");
      const wet = new THREE.Color("#24140b");
      soilMaterialRef.current.color.copy(dry.clone().lerp(wet, factor));
      soilMaterialRef.current.roughness = 0.95 - factor * 0.3;
    }

    // 4. Pulso de señal IoT
    if (signalGlowRef.current) {
      signalGlowRef.current.intensity = 1.2 + Math.sin(time * 4.0) * 0.8;
    }
  });

  return (
    <group>
      {/* Superficie de Suelo Agrícola con Sombra */}
      <mesh receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[30, 0.5, 34]} />
        <meshStandardMaterial ref={soilMaterialRef} color="#3d2719" roughness={0.92} />
      </mesh>

      {/* Surcos y Camellones de Riego */}
      {[-12, -8, -4, 0, 4, 8, 12].map((zPos) => (
        <group key={zPos} position={[0, 0.28, zPos]}>
          <mesh receiveShadow>
            <boxGeometry args={[28, 0.08, 1.2]} />
            <meshStandardMaterial color="#2d1c12" roughness={0.95} />
          </mesh>
          <mesh position={[0, 0.06, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.025, 0.025, 27.5, 8]} />
            <meshStandardMaterial color="#18181b" roughness={0.3} metalness={0.4} />
          </mesh>
        </group>
      ))}

      {/* Gotas de Riego por Goteo Animadas */}
      <points ref={dripDropsRef} geometry={dripDropsGeo}>
        <pointsMaterial color="#38bdf8" size={0.08} transparent opacity={0.85} />
      </points>

      {/* Perfil Estratificado Subterráneo (Corte de Suelo en el Borde Frontal) */}
      <group position={[0, -2.25, 17.05]}>
        <mesh position={[0, 1.4, 0]} receiveShadow>
          <boxGeometry args={[30, 1.2, 0.2]} />
          <meshStandardMaterial color="#1e120a" roughness={0.9} />
        </mesh>
        <mesh position={[0, 0.2, 0]} receiveShadow>
          <boxGeometry args={[30, 1.2, 0.2]} />
          <meshStandardMaterial color="#382215" roughness={0.88} />
        </mesh>
        <mesh position={[0, -1.0, 0]} receiveShadow>
          <boxGeometry args={[30, 1.2, 0.2]} />
          <meshStandardMaterial color="#4f3724" roughness={0.85} />
        </mesh>

        {/* Marcadores de cota de profundidad */}
        {[-30, -60, -100].map((depth, idx) => (
          <group key={depth} position={[14.2, 1.8 - idx * 1.2, 0.15]}>
            <mesh>
              <boxGeometry args={[0.8, 0.2, 0.05]} />
              <meshBasicMaterial color="#38bdf8" />
            </mesh>
          </group>
        ))}
      </group>

      {/* Filas de Árboles en la Parcela con Reacción Dinámica al Estrés */}
      <group ref={canopyGroupRef}>
        {plantsGrid.map((p, idx) => (
          <group
            key={idx}
            position={[p.x, 0.25, p.z]}
            scale={p.scale}
            rotation={[0, p.rotationY, 0]}
          >
            {/* Tronco */}
            <mesh position={[0, 0.9, 0]} castShadow receiveShadow>
              <cylinderGeometry args={[0.08, 0.13, 1.8, 8]} />
              <meshStandardMaterial color="#4a3319" roughness={0.9} />
            </mesh>

            {/* Ramas */}
            <mesh position={[0.2, 1.6, 0.1]} rotation={[0.4, 0, 0.4]} castShadow>
              <cylinderGeometry args={[0.04, 0.07, 0.8, 6]} />
              <meshStandardMaterial color="#4a3319" roughness={0.9} />
            </mesh>
            <mesh position={[-0.2, 1.7, -0.1]} rotation={[-0.3, 0, -0.5]} castShadow>
              <cylinderGeometry args={[0.04, 0.06, 0.9, 6]} />
              <meshStandardMaterial color="#4a3319" roughness={0.9} />
            </mesh>

            {/* Copa foliar con color reactivo a CWSI */}
            {p.clusters.map((c, cIdx) => (
              <mesh key={cIdx} position={c.offset} castShadow receiveShadow>
                <sphereGeometry args={[c.r, 12, 12]} />
                <meshStandardMaterial
                  color={currentCanopyColor}
                  roughness={0.6}
                  metalness={0.05}
                />
              </mesh>
            ))}
          </group>
        ))}
      </group>

      {/* Estación de Telemetría IoT en Parcela con Etiqueta 3D */}
      <group position={[3.8, 0.25, 2.0]}>
        <mesh position={[0, 1.0, 0]} castShadow>
          <cylinderGeometry args={[0.035, 0.045, 2.0, 8]} />
          <meshStandardMaterial color="#0284c7" metalness={0.85} roughness={0.2} />
        </mesh>
        <mesh position={[0, 1.8, -0.15]} rotation={[0.5, 0, 0]} castShadow>
          <boxGeometry args={[0.45, 0.02, 0.35]} />
          <meshStandardMaterial color="#0f172a" roughness={0.1} metalness={0.9} />
        </mesh>
        <mesh position={[0, 1.5, 0]} castShadow>
          <boxGeometry args={[0.28, 0.35, 0.22]} />
          <meshStandardMaterial color="#090d16" roughness={0.4} />
        </mesh>
        <mesh position={[0, 2.05, 0]}>
          <sphereGeometry args={[0.09, 12, 12]} />
          <meshStandardMaterial color="#38bdf8" emissive="#38bdf8" emissiveIntensity={1.8} />
        </mesh>
        <pointLight ref={signalGlowRef} position={[0, 2.05, 0]} color="#38bdf8" intensity={1.5} distance={5} />

        {/* Etiqueta HTML 3D Flotante con Telemetría en Vivo */}
        <Html position={[0, 2.4, 0]} center distanceFactor={18} className="pointer-events-none select-none">
          <div className="bg-zinc-950/90 backdrop-blur-md border border-cyan-500/50 px-2.5 py-1 rounded-xl shadow-xl text-[10px] font-mono text-cyan-300 flex flex-col items-center whitespace-nowrap">
            <span className="font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" /> Sonda IoT #01
            </span>
            <span className="text-[9px] text-zinc-300">
              θ: <b className="text-cyan-400">{soilMoistureVol.toFixed(1)}%</b> | CWSI: <b className="text-emerald-400">{cwsiStress.toFixed(2)}</b>
            </span>
          </div>
        </Html>
      </group>

      {/* Marcador Interactivo sobre la Planta Central */}
      <group position={[0, 0.4, 0]}>
        <Float speed={2.5} rotationIntensity={0.6} floatIntensity={0.8}>
          <group
            onClick={(e) => {
              e.stopPropagation();
              onSelectPlant?.();
            }}
          >
            <mesh rotation={[-Math.PI / 2, 0, 0]}>
              <ringGeometry args={[1.6, 1.9, 32]} />
              <meshBasicMaterial color="#10b981" transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
            <mesh position={[0, 3.8, 0]} rotation={[0, 0, Math.PI]}>
              <coneGeometry args={[0.28, 0.55, 16]} />
              <meshStandardMaterial color="#10b981" emissive="#10b981" emissiveIntensity={1.0} />
            </mesh>
          </group>
        </Float>
        {/* Etiqueta HTML para Planta Individual */}
        <Html position={[0, 4.4, 0]} center distanceFactor={16} className="pointer-events-none select-none">
          <div
            onClick={(e) => {
              e.stopPropagation();
              onSelectPlant?.();
            }}
            className="bg-zinc-950/90 backdrop-blur-md border border-emerald-500/60 px-3 py-1.5 rounded-xl shadow-2xl text-[11px] font-sans text-emerald-300 font-bold whitespace-nowrap animate-bounce cursor-pointer pointer-events-auto"
          >
            <span>🔬 Planta Individual AP-3</span>
            <span className="block text-[9px] text-zinc-400 font-normal">Haz clic para zoom Micro</span>
          </div>
        </Html>
      </group>
    </group>
  );
}

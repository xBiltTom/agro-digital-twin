"use client";

import React, { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";

export interface PlantModel3DProps {
  transpirationMm: number;
  cwsiStress: number;
  sapFlowVelocityCmh: number;
  soilMoistureVol: number;
  lai?: number;
  rootDepthCm?: number;
  showHydrologyFlow?: boolean;
  showSoilHorizons?: boolean;
  showScientificLabels?: boolean;
}

/**
 * Genera una textura procedimental en memoria de hoja de maíz (Zea mays L.):
 * Nervadura central prominente blanquecina-verdosa, venas secundarias paralelas y micrograno.
 */
function createMaizeLeafTexture(stress: number, isSenescent: boolean): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 1024;
  const ctx = canvas.getContext("2d");
  if (!ctx) return new THREE.CanvasTexture(canvas);

  // Fondo base de la lámina foliar
  const baseGrad = ctx.createLinearGradient(0, 0, canvas.width, 0);
  if (isSenescent) {
    baseGrad.addColorStop(0, "#8a6627");
    baseGrad.addColorStop(0.5, "#d4aa48");
    baseGrad.addColorStop(1, "#8a6627");
  } else if (stress > 0.45) {
    baseGrad.addColorStop(0, "#4a6e2e");
    baseGrad.addColorStop(0.5, "#8fa33b");
    baseGrad.addColorStop(1, "#4a6e2e");
  } else {
    baseGrad.addColorStop(0, "#275924");
    baseGrad.addColorStop(0.5, "#3e8c38");
    baseGrad.addColorStop(1, "#275924");
  }
  ctx.fillStyle = baseGrad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Nervadura central blanquecina (midrib)
  const midribGrad = ctx.createLinearGradient(
    canvas.width * 0.46,
    0,
    canvas.width * 0.54,
    0
  );
  const midColor = isSenescent ? "#dfcaa2" : "#9ed692";
  midribGrad.addColorStop(0, "rgba(255,255,255,0)");
  midribGrad.addColorStop(0.4, midColor);
  midribGrad.addColorStop(0.6, midColor);
  midribGrad.addColorStop(1, "rgba(255,255,255,0)");

  ctx.fillStyle = midribGrad;
  ctx.fillRect(canvas.width * 0.44, 0, canvas.width * 0.12, canvas.height);

  // Venas paralelas longitudinales (estriación típica del maíz)
  ctx.lineWidth = 1;
  for (let x = 12; x < canvas.width; x += 8) {
    if (Math.abs(x - canvas.width / 2) < 24) continue;
    ctx.strokeStyle = isSenescent
      ? "rgba(100, 75, 30, 0.25)"
      : "rgba(35, 80, 30, 0.28)";
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

/**
 * Procedural Leaf Blade:
 * Modelado botánico con ondulación marginal sinusoidal (wavy edges),
 * curvatura parabólica, nervio central en relieve y enrollamiento foliar bajo sequía.
 */
function RealisticMaizeLeaf({
  angle,
  nodeHeight,
  length,
  width,
  rise,
  droop,
  stress,
  isSenescent = false,
}: {
  angle: number;
  nodeHeight: number;
  length: number;
  width: number;
  rise: number;
  droop: number;
  stress: number;
  isSenescent?: boolean;
}) {
  // Factor de enrollamiento foliar (involute rolling en respuesta a estrés hídrico CWSI)
  const rollFactor = Math.min(1, Math.max(0, (stress - 0.28) * 1.7));

  const leafTexture = useMemo(
    () => createMaizeLeafTexture(stress, isSenescent),
    [stress, isSenescent]
  );

  const { geometry, midribPoints } = useMemo(() => {
    const segments = 22;
    const vertices: number[] = [];
    const indices: number[] = [];
    const uvs: number[] = [];
    const midrib: [number, number, number][] = [];

    const dirX = Math.cos(angle);
    const dirZ = Math.sin(angle);
    const sideX = -Math.sin(angle);
    const sideZ = Math.cos(angle);

    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const r = length * t;
      const y = rise * Math.sin(Math.PI * Math.pow(t, 0.75)) - droop * Math.pow(t, 1.85);

      const cx = dirX * r;
      const cy = y;
      const cz = dirZ * r;

      midrib.push([cx, cy + 0.008, cz]);

      // Ancho biológico de la hoja (estrecha en vaina, máxima a 35%, afilada en ápice)
      const widthProfile = Math.sin(Math.PI * Math.pow(t, 0.68)) * Math.pow(1 - t, 0.42);
      const halfW = width * widthProfile;

      // Ondulación natural del borde foliar del maíz (ruffled/wavy margins)
      const marginWave = Math.sin(t * Math.PI * 7.5) * halfW * 0.16 * (1 - Math.abs(2 * t - 1));

      // Enrollamiento por estrés hídrico
      const marginLift = rollFactor * halfW * 0.55 + marginWave;

      // Vértice izquierdo
      vertices.push(cx + sideX * halfW, cy + marginLift, cz + sideZ * halfW);
      uvs.push(0, t);

      // Vértice central (nervadura principal)
      vertices.push(cx, cy, cz);
      uvs.push(0.5, t);

      // Vértice derecho
      vertices.push(cx - sideX * halfW, cy - marginLift * 0.7 + marginWave, cz - sideZ * halfW);
      uvs.push(1, t);

      if (i < segments) {
        const row = i * 3;
        const nextRow = (i + 1) * 3;
        // Triángulos tira izquierda
        indices.push(row, row + 1, nextRow);
        indices.push(nextRow, row + 1, nextRow + 1);
        // Triángulos tira derecha
        indices.push(row + 1, row + 2, nextRow + 1);
        indices.push(nextRow + 1, row + 2, nextRow + 2);
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    return { geometry: geo, midribPoints: midrib };
  }, [angle, length, width, rise, droop, rollFactor]);

  return (
    <group position={[0, nodeHeight, 0]}>
      {/* Lámina foliar con textura procedural y translucidez física */}
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshPhysicalMaterial
          map={leafTexture}
          roughness={0.34}
          clearcoat={0.16}
          transmission={0.15}
          thickness={0.06}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* Nervadura central en resalte */}
      <Line
        points={midribPoints}
        color={isSenescent ? "#dfcaa2" : "#9ed692"}
        lineWidth={1.6}
        transparent
        opacity={0.85}
      />
    </group>
  );
}

/**
 * Panoja Apical Masculina (Tassel):
 * Raquis central con 12 ramas laterales caídas y cientos de espículas con anteras doradas.
 */
function RealisticMaizeTassel({ apexY }: { apexY: number }) {
  const branches = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => {
      const angle = (i / 12) * Math.PI * 2 + (i % 2 === 0 ? 0.1 : -0.1);
      const spread = 0.28 + (i % 3) * 0.08;
      const length = 0.52 + (i % 4) * 0.05;
      return { angle, spread, length };
    });
  }, []);

  return (
    <group position={[0, apexY, 0]}>
      {/* Raquis central erecto */}
      <mesh position={[0, 0.38, 0]} castShadow>
        <cylinderGeometry args={[0.009, 0.018, 0.76, 8]} />
        <meshStandardMaterial color="#cbb36c" roughness={0.65} />
      </mesh>

      {/* Ramas laterales con anteras */}
      {branches.map((b, i) => {
        const rad = b.angle;
        const pts: [number, number, number][] = [
          [0, 0.08 + (i % 4) * 0.03, 0],
          [Math.cos(rad) * b.spread * 0.45, 0.24 + (i % 3) * 0.03, Math.sin(rad) * b.spread * 0.45],
          [Math.cos(rad) * b.spread, 0.35 - (i % 3) * 0.04, Math.sin(rad) * b.spread],
          [Math.cos(rad) * (b.spread + 0.08), 0.26 - (i % 2) * 0.05, Math.sin(rad) * (b.spread + 0.08)],
        ];
        return (
          <group key={i}>
            <Line points={pts} color="#cbb36c" lineWidth={1.8} />
            {/* Espículas y anteras cargadas de polen */}
            <mesh position={[Math.cos(rad) * b.spread * 0.75, 0.3, Math.sin(rad) * b.spread * 0.75]}>
              <sphereGeometry args={[0.024, 6, 6]} />
              <meshStandardMaterial color="#e5ce79" roughness={0.5} />
            </mesh>
            <mesh position={[Math.cos(rad) * (b.spread + 0.06), 0.26, Math.sin(rad) * (b.spread + 0.06)]}>
              <sphereGeometry args={[0.018, 6, 6]} />
              <meshStandardMaterial color="#dfbf62" roughness={0.5} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

/**
 * Mazorca con Hojas de la Chala Envolventes y Estigmas Dorados (Silks)
 */
function RealisticMaizeEar({ nodeY, angle }: { nodeY: number; angle: number }) {
  return (
    <group position={[Math.cos(angle) * 0.07, nodeY, Math.sin(angle) * 0.07]} rotation-y={angle} rotation-z={-0.42}>
      {/* Pedúnculo de inserción */}
      <mesh position={[0, 0.06, 0]} castShadow>
        <cylinderGeometry args={[0.024, 0.028, 0.12, 10]} />
        <meshStandardMaterial color="#4a7c36" roughness={0.6} />
      </mesh>
      {/* Cuerpo de la mazorca envuelto en brácteas (chalas) */}
      <mesh position={[0, 0.26, 0]} castShadow>
        <cylinderGeometry args={[0.078, 0.095, 0.34, 16]} />
        <meshStandardMaterial color="#689a42" roughness={0.45} />
      </mesh>
      {/* Punta de brácteas afilada */}
      <mesh position={[0, 0.47, 0]} castShadow>
        <coneGeometry args={[0.079, 0.18, 16]} />
        <meshStandardMaterial color="#7ba64e" roughness={0.45} />
      </mesh>
      {/* Estigmas dorados (sedas de maíz) en cascada gravitatoria */}
      {Array.from({ length: 18 }, (_, i) => {
        const silkAngle = i * 0.35;
        const silkPts: [number, number, number][] = [
          [0, 0.54, 0],
          [Math.cos(silkAngle) * 0.04, 0.62, Math.sin(silkAngle) * 0.04],
          [Math.cos(silkAngle) * 0.075, 0.68 - (i % 3) * 0.04, Math.sin(silkAngle) * 0.075],
          [Math.cos(silkAngle) * 0.09, 0.61 - (i % 4) * 0.05, Math.sin(silkAngle) * 0.09],
          [Math.cos(silkAngle) * 0.08, 0.52 - (i % 3) * 0.06, Math.sin(silkAngle) * 0.08],
        ];
        return <Line key={i} points={silkPts} color="#d99f36" lineWidth={1.1} transparent opacity={0.88} />;
      })}
    </group>
  );
}

/**
 * Raíces Adventicias Aéreas de Anclaje (Brace Roots) en 3D volumétrico
 * Emergen de los primeros dos nudos por encima del suelo y penetran la tierra.
 */
function RealisticBraceRoots() {
  const rootTubes = useMemo(() => {
    const list: Array<[number, number, number][]> = [];
    const count = 12;
    for (let i = 0; i < count; i++) {
      const rad = (i / count) * Math.PI * 2;
      const isUpper = i % 2 === 0;
      const startY = isUpper ? 0.24 : 0.13;
      const groundRadius = isUpper ? 0.42 : 0.28;
      list.push([
        [Math.cos(rad) * 0.065, startY, Math.sin(rad) * 0.065],
        [Math.cos(rad) * groundRadius * 0.55, startY * 0.35, Math.sin(rad) * groundRadius * 0.55],
        [Math.cos(rad) * groundRadius, 0.0, Math.sin(rad) * groundRadius],
        [Math.cos(rad) * (groundRadius + 0.12), -0.22, Math.sin(rad) * (groundRadius + 0.12)],
      ]);
    }
    return list;
  }, []);

  return (
    <group>
      {rootTubes.map((pts, idx) => (
        <group key={`brace-${idx}`}>
          <Line points={pts} color="#c28b51" lineWidth={3.2} />
          {/* Caliptra / punta de la raíz */}
          <mesh position={pts[pts.length - 1]}>
            <sphereGeometry args={[0.022, 6, 6]} />
            <meshStandardMaterial color="#8e532b" roughness={0.8} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/**
 * Corte Pedológico SoilGrids 2.0:
 * Horizontes Ap (0-30cm), Bt (30-65cm) y C (>65cm) con marcadores de profundidad nítidos.
 */
function SoilGridsStratigraphyCutout({
  soilMoistureVol,
  rootDepthCm,
}: {
  soilMoistureVol: number;
  rootDepthCm: number;
}) {
  const depthM = Math.min(2.0, Math.max(1.0, rootDepthCm / 100));
  const moistureFactor = Math.min(1, Math.max(0, soilMoistureVol / 40));

  const apColor = moistureFactor > 0.5 ? "#281a10" : "#3b2618";
  const btColor = moistureFactor > 0.5 ? "#422a18" : "#563821";
  const cColor = moistureFactor > 0.5 ? "#61412a" : "#755034";

  return (
    <group position={[0, 0, 0]}>
      {/* Superficie arable (horizonte Ap superior) */}
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, 0.002, 0]}>
        <circleGeometry args={[2.9, 64]} />
        <meshStandardMaterial color={apColor} roughness={0.96} />
      </mesh>

      {/* Horizonte Ap: 0 a -0.30 m */}
      <mesh position={[0, -0.15, 0]}>
        <cylinderGeometry args={[2.88, 2.88, 0.3, 48, 1, true]} />
        <meshPhysicalMaterial
          color={apColor}
          transparent
          opacity={0.42}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Horizonte Bt: -0.30 a -0.65 m */}
      <mesh position={[0, -0.475, 0]}>
        <cylinderGeometry args={[2.86, 2.86, 0.35, 48, 1, true]} />
        <meshPhysicalMaterial
          color={btColor}
          transparent
          opacity={0.38}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Horizonte C: -0.65 a -depthM */}
      <mesh position={[0, -0.65 - (depthM - 0.65) / 2, 0]}>
        <cylinderGeometry args={[2.84, 2.84, depthM - 0.65, 48, 1, true]} />
        <meshPhysicalMaterial
          color={cColor}
          transparent
          opacity={0.32}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Franja capilar / nivel freático base */}
      <mesh position={[0, -depthM, 0]} rotation-x={-Math.PI / 2}>
        <circleGeometry args={[2.84, 48]} />
        <meshStandardMaterial color="#38bdf8" roughness={0.6} transparent opacity={0.65} />
      </mesh>

      {/* Anillos divisores de horizontes */}
      <mesh position={[0, -0.3, 0]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[2.82, 2.88, 48]} />
        <meshBasicMaterial color="#e2b170" transparent opacity={0.5} />
      </mesh>
      <mesh position={[0, -0.65, 0]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[2.80, 2.86, 48]} />
        <meshBasicMaterial color="#c29858" transparent opacity={0.45} />
      </mesh>
    </group>
  );
}

/**
 * Dinámica Fisiológica:
 * Partículas luminosas de savia en ascenso xilemático y vapor de transpiración en canopeo.
 */
function PhysiologicalFlowDynamics({
  sapFlowVelocityCmh,
  transpirationMm,
  cwsiStress,
  stemHeight,
}: {
  sapFlowVelocityCmh: number;
  transpirationMm: number;
  cwsiStress: number;
  stemHeight: number;
}) {
  const pointsRef = useRef<THREE.Points>(null);
  const vaporRef = useRef<THREE.Points>(null);

  const particleCount = 50;
  const initialPositions = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const angle = (i * 1.37) % (Math.PI * 2);
      const r = Math.random() * 0.038;
      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = -0.5 + Math.random() * (stemHeight + 0.5);
      pos[i * 3 + 2] = Math.sin(angle) * r;
    }
    return pos;
  }, [particleCount, stemHeight]);

  const vaporCount = 35;
  const vaporPositions = useMemo(() => {
    const pos = new Float32Array(vaporCount * 3);
    for (let i = 0; i < vaporCount; i++) {
      const angle = (i * 2.1) % (Math.PI * 2);
      const r = 0.18 + Math.random() * 0.75;
      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = 0.8 + Math.random() * (stemHeight * 0.8);
      pos[i * 3 + 2] = Math.sin(angle) * r;
    }
    return pos;
  }, [vaporCount, stemHeight]);

  useFrame((_, delta) => {
    const speed = Math.max(0.1, (sapFlowVelocityCmh / 15) * 1.3);
    if (pointsRef.current) {
      const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        const yIndex = i * 3 + 1;
        positions[yIndex] += speed * delta;
        if (positions[yIndex] > stemHeight + 0.1) {
          positions[yIndex] = -0.6;
        }
      }
      pointsRef.current.geometry.attributes.position.needsUpdate = true;
    }

    if (vaporRef.current) {
      const vPos = vaporRef.current.geometry.attributes.position.array as Float32Array;
      const vSpeed = 0.35 + (transpirationMm / 6) * 0.45;
      for (let j = 0; j < vaporCount; j++) {
        const yIndex = j * 3 + 1;
        vPos[yIndex] += vSpeed * delta;
        if (vPos[yIndex] > stemHeight + 1.2) {
          vPos[yIndex] = 0.7 + Math.random() * 0.4;
        }
      }
      vaporRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  const sapColor = cwsiStress > 0.5 ? "#f59e0b" : "#38bdf8";

  return (
    <group>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[initialPositions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.05}
          color={sapColor}
          transparent
          opacity={0.88}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {transpirationMm > 0.2 && (
        <points ref={vaporRef}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[vaporPositions, 3]} />
          </bufferGeometry>
          <pointsMaterial
            size={0.06}
            color="#a7f3d0"
            transparent
            opacity={Math.min(0.75, 0.2 + (transpirationMm / 7) * 0.5)}
            blending={THREE.AdditiveBlending}
          />
        </points>
      )}
    </group>
  );
}

export default function PlantModel3D({
  transpirationMm,
  cwsiStress,
  sapFlowVelocityCmh,
  soilMoistureVol,
  lai = 3.8,
  rootDepthCm = 115,
  showHydrologyFlow = true,
  showSoilHorizons = true,
  showScientificLabels = true,
}: PlantModel3DProps) {
  const stress = Math.min(1, Math.max(0, cwsiStress));
  const stemHeight = 2.5 + Math.min(0.9, (lai - 2.0) * 0.25);
  const totalNodes = 14;

  const [expandedCard, setExpandedCard] = useState<"canopy" | "soil" | null>("canopy");

  // Hojas phyllotáxicas con curvatura y enrollamiento
  const leaves = useMemo(() => {
    return Array.from({ length: totalNodes }, (_, i) => {
      const t = i / (totalNodes - 1);
      const angle = i * Math.PI * 0.94 + (i % 2 === 0 ? 0.08 : -0.06);
      const nodeHeight = 0.28 + t * (stemHeight - 0.55);

      const lengthCurve = Math.sin(Math.PI * Math.pow(t, 0.65));
      const length = 0.78 + lengthCurve * (1.15 + Math.min(0.4, lai * 0.08));
      const width = 0.10 + lengthCurve * 0.12;

      const rise = length * (0.24 - t * 0.06);
      const droop = length * (0.18 + stress * 0.24 + t * 0.08);
      const isSenescent = i < 2 && stress > 0.35;

      return {
        id: i,
        angle,
        nodeHeight,
        length,
        width,
        rise,
        droop,
        isSenescent,
      };
    });
  }, [totalNodes, stemHeight, lai, stress]);

  return (
    <group position={[0, -0.18, 0]}>
      {/* 1. Suelo SoilGrids 2.0 */}
      {showSoilHorizons && (
        <SoilGridsStratigraphyCutout
          soilMoistureVol={soilMoistureVol}
          rootDepthCm={rootDepthCm}
        />
      )}

      {/* 2. Raíces Adventicias Aéreas de Anclaje (Brace Roots) */}
      <RealisticBraceRoots />

      {/* 3. Tallo Botánico (Culmo de maíz con nudos y entrenudos en relieve) */}
      <group>
        <mesh castShadow position={[0, stemHeight / 2, 0]}>
          <cylinderGeometry args={[0.04, 0.068, stemHeight, 20]} />
          <meshStandardMaterial color="#4f7d2c" roughness={0.48} metalness={0.08} />
        </mesh>

        {/* Nudos anulares y vainas foliares */}
        {Array.from({ length: totalNodes }, (_, nodeIdx) => {
          const y = 0.28 + (nodeIdx / (totalNodes - 1)) * (stemHeight - 0.55);
          const taperRadius = 0.068 - (nodeIdx / totalNodes) * 0.028;
          return (
            <mesh key={`node-${nodeIdx}`} position={[0, y, 0]} castShadow>
              <torusGeometry args={[taperRadius + 0.005, 0.013, 8, 22]} />
              <meshStandardMaterial color="#689639" roughness={0.55} />
            </mesh>
          );
        })}
      </group>

      {/* 4. Hojas Phyllotáxicas Onduladas */}
      {leaves.map((leaf) => (
        <RealisticMaizeLeaf
          key={leaf.id}
          angle={leaf.angle}
          nodeHeight={leaf.nodeHeight}
          length={leaf.length}
          width={leaf.width}
          rise={leaf.rise}
          droop={leaf.droop}
          stress={stress}
          isSenescent={leaf.isSenescent}
        />
      ))}

      {/* 5. Mazorca con Brácteas y Sedas (Silks) */}
      <RealisticMaizeEar nodeY={0.96} angle={Math.PI * 0.42} />

      {/* 6. Panoja Apical Masculina (Tassel) */}
      <RealisticMaizeTassel apexY={stemHeight} />

      {/* 7. Dinámica Fisiológica de Savia y Vapor */}
      {showHydrologyFlow && (
        <PhysiologicalFlowDynamics
          sapFlowVelocityCmh={sapFlowVelocityCmh}
          transpirationMm={transpirationMm}
          cwsiStress={stress}
          stemHeight={stemHeight}
        />
      )}

      {/* 8. Tarjetas Informativas Nítidas y Bien Proporcionadas (No se pierden ni se reducen a píxeles) */}
      {showScientificLabels && (
        <>
          {/* Tarjeta del Canopeo FSPM */}
          <Html position={[0, stemHeight + 0.75, 0]} center distanceFactor={7.5}>
            <div
              onClick={() => setExpandedCard(expandedCard === "canopy" ? null : "canopy")}
              className="cursor-pointer rounded-xl border border-emerald-400/50 bg-zinc-950/92 px-3.5 py-2.5 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md transition hover:border-emerald-300"
              style={{ minWidth: "220px" }}
            >
              <div className="flex items-center justify-between border-b border-emerald-500/30 pb-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-bold text-emerald-300">Zea mays L. (FSPM 3D)</span>
                </div>
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-mono text-emerald-300">
                  Micro
                </span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono">
                <div>
                  <span className="text-zinc-400">Área Foliar LAI:</span>
                  <div className="font-bold text-emerald-300 text-xs">{lai.toFixed(2)}</div>
                </div>
                <div>
                  <span className="text-zinc-400">Estrés CWSI:</span>
                  <div
                    className={`font-bold text-xs ${
                      stress > 0.4 ? "text-amber-400" : "text-emerald-300"
                    }`}
                  >
                    {stress.toFixed(2)} {stress > 0.4 ? "⚠️ Sequía" : "✓ Óptimo"}
                  </div>
                </div>
                <div>
                  <span className="text-zinc-400">Transpiración:</span>
                  <div className="font-bold text-cyan-300 text-xs">{transpirationMm.toFixed(2)} mm/d</div>
                </div>
                <div>
                  <span className="text-zinc-400">Savia Xilema:</span>
                  <div className="font-bold text-sky-300 text-xs">{sapFlowVelocityCmh.toFixed(1)} cm/h</div>
                </div>
              </div>
            </div>
          </Html>

          {/* Tarjeta del Perfil Edafológico SoilGrids */}
          <Html position={[1.85, -0.45, 0]} center distanceFactor={7.5}>
            <div
              onClick={() => setExpandedCard(expandedCard === "soil" ? null : "soil")}
              className="cursor-pointer rounded-xl border border-amber-400/50 bg-zinc-950/92 px-3 py-2 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md transition hover:border-amber-300"
              style={{ minWidth: "200px" }}
            >
              <div className="font-bold text-amber-300 flex items-center justify-between border-b border-amber-500/30 pb-1">
                <span>SoilGrids 2.0 · Perfil Edafológico</span>
                <span className="text-[10px] font-mono text-amber-400">0-140cm</span>
              </div>
              <div className="mt-1.5 space-y-0.5 text-[11px] font-mono text-zinc-300">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Humedad matriz θ:</span>
                  <span className="font-bold text-cyan-300">{soilMoistureVol.toFixed(1)}% vol</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Prof. Radicular Zmax:</span>
                  <span className="font-bold text-amber-300">{rootDepthCm.toFixed(0)} cm</span>
                </div>
                <div className="text-[10px] text-zinc-400 pt-1">
                  Capas: Ap (0-30cm) · Bt (30-65cm) · C (&gt;65cm)
                </div>
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

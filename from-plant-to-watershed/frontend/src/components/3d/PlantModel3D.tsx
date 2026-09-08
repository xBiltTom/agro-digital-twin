"use client";

import React, { useMemo, useRef } from "react";
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
 * Procedural Leaf Blade with realistic maize geometry, midrib line,
 * and dynamic drought stress response (leaf rolling / folding along midrib & acute droop).
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
  // Leaf rolling effect: as stress increases, leaf folds upward in V-shape along midrib
  const rollFactor = Math.min(1, Math.max(0, (stress - 0.25) * 1.6));

  const { geometry, midribPoints } = useMemo(() => {
    const segments = 16;
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
      // Parabolic arch: initial upward rise then gravitational droop
      const r = length * t;
      const y = rise * Math.sin(Math.PI * Math.pow(t, 0.75)) - droop * Math.pow(t, 1.8);

      const cx = dirX * r;
      const cy = y;
      const cz = dirZ * r;

      midrib.push([cx, cy + 0.005, cz]);

      // Leaf blade width profile: starts narrow at sheath, widens at 35%, tapers to sharp apex
      const widthProfile = Math.sin(Math.PI * Math.pow(t, 0.7)) * Math.pow(1 - t, 0.45);
      const halfW = width * widthProfile;

      // Leaf rolling: margin vertices lift up in Y
      const marginLift = rollFactor * halfW * 0.45;

      // Left edge
      vertices.push(
        cx + sideX * halfW,
        cy + marginLift,
        cz + sideZ * halfW
      );
      uvs.push(0, t);

      // Center (midrib)
      vertices.push(cx, cy, cz);
      uvs.push(0.5, t);

      // Right edge
      vertices.push(
        cx - sideX * halfW,
        cy + marginLift,
        cz - sideZ * halfW
      );
      uvs.push(1, t);

      if (i < segments) {
        const row = i * 3;
        const nextRow = (i + 1) * 3;
        // Left triangle strip
        indices.push(row, row + 1, nextRow);
        indices.push(nextRow, row + 1, nextRow + 1);
        // Right triangle strip
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

  // Color gradient based on senescence and CWSI stress
  const leafColor = useMemo(() => {
    if (isSenescent) {
      return new THREE.Color("#c29d48"); // Senescent yellow-tan
    }
    const healthy = new THREE.Color("#3b8836");
    const stressed = new THREE.Color("#8fa63b");
    const chlorotic = new THREE.Color("#b59e38");
    if (stress < 0.3) return healthy;
    if (stress < 0.6) {
      return healthy.clone().lerp(stressed, (stress - 0.3) / 0.3);
    }
    return stressed.clone().lerp(chlorotic, (stress - 0.6) / 0.4);
  }, [stress, isSenescent]);

  return (
    <group position={[0, nodeHeight, 0]}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial
          color={leafColor}
          side={THREE.DoubleSide}
          roughness={0.45}
          metalness={0.05}
        />
      </mesh>
      {/* Whitish-green prominent maize midrib */}
      <Line
        points={midribPoints}
        color={isSenescent ? "#9a7c36" : "#68a858"}
        lineWidth={1.2}
        transparent
        opacity={0.8}
      />
    </group>
  );
}

/**
 * Realistic Maize Tassel (Panoja apical masculina)
 */
function MaizeTassel({ apexY }: { apexY: number }) {
  const branches = useMemo(() => {
    return [
      { angle: 0.0, length: 0.62, spread: 0.28 },
      { angle: 0.9, length: 0.54, spread: 0.32 },
      { angle: 1.8, length: 0.58, spread: 0.30 },
      { angle: 2.7, length: 0.52, spread: 0.34 },
      { angle: 3.6, length: 0.56, spread: 0.31 },
      { angle: 4.5, length: 0.50, spread: 0.33 },
      { angle: 5.4, length: 0.53, spread: 0.29 },
    ];
  }, []);

  return (
    <group position={[0, apexY, 0]}>
      {/* Central main spike (raquis central) */}
      <mesh position={[0, 0.35, 0]} castShadow>
        <cylinderGeometry args={[0.008, 0.016, 0.72, 8]} />
        <meshStandardMaterial color="#cbb36c" roughness={0.7} />
      </mesh>
      {/* Lateral tassel branches with spikelets */}
      {branches.map((b, i) => {
        const rad = b.angle;
        const pts: [number, number, number][] = [
          [0, 0.08 + i * 0.03, 0],
          [Math.cos(rad) * b.spread * 0.5, 0.22 + i * 0.02, Math.sin(rad) * b.spread * 0.5],
          [Math.cos(rad) * b.spread, 0.32 - i * 0.02, Math.sin(rad) * b.spread],
        ];
        return (
          <group key={i}>
            <Line points={pts} color="#cbb36c" lineWidth={1.6} />
            <mesh position={[Math.cos(rad) * b.spread * 0.8, 0.28, Math.sin(rad) * b.spread * 0.8]}>
              <sphereGeometry args={[0.022, 6, 6]} />
              <meshStandardMaterial color="#dfca7a" roughness={0.6} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

/**
 * Realistic Maize Ear (Mazorca con chalas envolventes y estigmas dorados)
 */
function MaizeEar({ nodeY, angle }: { nodeY: number; angle: number }) {
  return (
    <group position={[Math.cos(angle) * 0.06, nodeY, Math.sin(angle) * 0.06]} rotation-y={angle} rotation-z={-0.38}>
      {/* Ear shank / peduncle */}
      <mesh position={[0, 0.05, 0]} castShadow>
        <cylinderGeometry args={[0.022, 0.025, 0.1, 10]} />
        <meshStandardMaterial color="#4a7c36" roughness={0.6} />
      </mesh>
      {/* Main Ear cylinder (husk covered) */}
      <mesh position={[0, 0.24, 0]} castShadow>
        <cylinderGeometry args={[0.075, 0.09, 0.32, 14]} />
        <meshStandardMaterial color="#689a42" roughness={0.5} />
      </mesh>
      {/* Tapered husk tip */}
      <mesh position={[0, 0.44, 0]} castShadow>
        <coneGeometry args={[0.076, 0.16, 14]} />
        <meshStandardMaterial color="#7ba64e" roughness={0.5} />
      </mesh>
      {/* Corn Silks (estigmas de maíz) extending from tip */}
      {Array.from({ length: 12 }, (_, i) => {
        const silkAngle = i * 0.52;
        const silkPts: [number, number, number][] = [
          [0, 0.51, 0],
          [Math.cos(silkAngle) * 0.035, 0.58, Math.sin(silkAngle) * 0.035],
          [Math.cos(silkAngle) * 0.065, 0.65 - (i % 3) * 0.03, Math.sin(silkAngle) * 0.065],
          [Math.cos(silkAngle) * 0.08, 0.62 - (i % 2) * 0.04, Math.sin(silkAngle) * 0.08],
        ];
        return <Line key={i} points={silkPts} color="#d99f36" lineWidth={0.9} transparent opacity={0.85} />;
      })}
    </group>
  );
}

/**
 * FSPM Multi-Tier Root System Architecture:
 * 1. Brace roots (raíces adventicias / de anclaje aéreas emergiendo del nudo basal al suelo)
 * 2. Crown & seminal roots (densas en 0-30 cm)
 * 3. Deep taproot & lateral branches (profundidad SoilGrids 100-140 cm)
 */
function FSPMRootArchitecture({ rootDepthCm }: { rootDepthCm: number }) {
  const depthM = Math.min(2.0, Math.max(0.7, rootDepthCm / 100));

  // Aerial Brace Roots (emerging above ground from node 1 and 2)
  const braceRoots = useMemo(() => {
    const list: Array<[number, number, number][]> = [];
    const count = 12;
    for (let i = 0; i < count; i++) {
      const rad = (i / count) * Math.PI * 2;
      const isUpper = i % 2 === 0;
      const startY = isUpper ? 0.22 : 0.12;
      const groundRadius = isUpper ? 0.38 : 0.26;
      list.push([
        [Math.cos(rad) * 0.06, startY, Math.sin(rad) * 0.06],
        [Math.cos(rad) * groundRadius * 0.6, startY * 0.4, Math.sin(rad) * groundRadius * 0.6],
        [Math.cos(rad) * groundRadius, 0.0, Math.sin(rad) * groundRadius],
        [Math.cos(rad) * (groundRadius + 0.1), -0.18, Math.sin(rad) * (groundRadius + 0.1)],
      ]);
    }
    return list;
  }, []);

  // Underground Subsurface Root System
  const subterraneanRoots = useMemo(() => {
    const list: Array<{ pts: [number, number, number][]; color: string; width: number }> = [];
    // Primary deep taproots
    for (let i = 0; i < 6; i++) {
      const rad = (i / 6) * Math.PI * 2 + 0.2;
      const spread = 0.25 + (i % 3) * 0.1;
      list.push({
        pts: [
          [0, 0, 0],
          [Math.cos(rad) * spread * 0.35, -depthM * 0.3, Math.sin(rad) * spread * 0.35],
          [Math.cos(rad) * spread * 0.65, -depthM * 0.65, Math.sin(rad) * spread * 0.65],
          [Math.cos(rad) * spread * 0.4, -depthM * 0.95, Math.sin(rad) * spread * 0.4],
        ],
        color: "#c28848",
        width: 1.8,
      });
    }

    // Dense crown fibrous roots in topsoil (0-35cm)
    for (let j = 0; j < 28; j++) {
      const rad = j * 2.39996; // Golden angle distribution
      const spread = 0.35 + (j % 5) * 0.18;
      const rootY = -Math.min(depthM * 0.4, 0.15 + (j % 6) * 0.08);
      list.push({
        pts: [
          [0, -0.02, 0],
          [Math.cos(rad) * spread * 0.45, rootY * 0.5, Math.sin(rad) * spread * 0.45],
          [Math.cos(rad) * spread, rootY, Math.sin(rad) * spread],
          [Math.cos(rad) * (spread + 0.08), rootY - 0.08, Math.sin(rad) * (spread + 0.08)],
        ],
        color: j % 3 === 0 ? "#deb06e" : "#b0733d",
        width: 1.0,
      });
    }

    // Secondary lateral fine branching roots
    for (let k = 0; k < 22; k++) {
      const rad = k * 1.7;
      const startDepth = -0.2 - (k % 8) * 0.12;
      list.push({
        pts: [
          [Math.cos(rad) * 0.2, startDepth, Math.sin(rad) * 0.2],
          [Math.cos(rad) * 0.42, startDepth - 0.1, Math.sin(rad) * 0.42],
          [Math.cos(rad) * 0.62, startDepth - 0.18, Math.sin(rad) * 0.62],
        ],
        color: "#9e6739",
        width: 0.7,
      });
    }

    return list;
  }, [depthM]);

  return (
    <group>
      {/* Aerial Brace Roots */}
      {braceRoots.map((pts, idx) => (
        <Line key={`brace-${idx}`} points={pts} color="#c28b51" lineWidth={2.2} />
      ))}
      {/* Subsurface Roots */}
      {subterraneanRoots.map((r, idx) => (
        <Line key={`sub-${idx}`} points={r.pts} color={r.color} lineWidth={r.width} transparent opacity={0.88} />
      ))}
    </group>
  );
}

/**
 * SoilGrids 2.0 Stratigraphy Column Cutout:
 * Ap Horizon (0-30cm, organic loam)
 * Bt Horizon (30-60cm, clay illuviation)
 * C Horizon (60-120cm, parent material)
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

  // Colors based on moisture and SoilGrids organic carbon
  const apColor = moistureFactor > 0.5 ? "#2c1d13" : "#3d2a1b";
  const btColor = moistureFactor > 0.5 ? "#482f1b" : "#5d3c24";
  const cColor = moistureFactor > 0.5 ? "#69472e" : "#7d5538";

  return (
    <group position={[0, 0, 0]}>
      {/* Topsoil surface disc (Ap horizon top) with cultivated soil texture */}
      <mesh receiveShadow rotation-x={-Math.PI / 2} position={[0, 0.002, 0]}>
        <circleGeometry args={[2.8, 64]} />
        <meshStandardMaterial color={apColor} roughness={0.95} />
      </mesh>

      {/* Soil profile transparent cylinder display */}
      {/* Horizon Ap: 0 to -0.30 m */}
      <mesh position={[0, -0.15, 0]}>
        <cylinderGeometry args={[2.78, 2.78, 0.3, 48, 1, true]} />
        <meshPhysicalMaterial
          color={apColor}
          transparent
          opacity={0.35}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Horizon Bt: -0.30 to -0.65 m */}
      <mesh position={[0, -0.475, 0]}>
        <cylinderGeometry args={[2.76, 2.76, 0.35, 48, 1, true]} />
        <meshPhysicalMaterial
          color={btColor}
          transparent
          opacity={0.32}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Horizon C: -0.65 to -depthM */}
      <mesh position={[0, -0.65 - (depthM - 0.65) / 2, 0]}>
        <cylinderGeometry args={[2.74, 2.74, depthM - 0.65, 48, 1, true]} />
        <meshPhysicalMaterial
          color={cColor}
          transparent
          opacity={0.28}
          side={THREE.DoubleSide}
          roughness={0.9}
        />
      </mesh>

      {/* Base disc / Capillary fringe layer */}
      <mesh position={[0, -depthM, 0]} rotation-x={-Math.PI / 2}>
        <circleGeometry args={[2.74, 48]} />
        <meshStandardMaterial color="#406377" roughness={0.7} transparent opacity={0.6} />
      </mesh>

      {/* Horizon boundary divider rings */}
      <mesh position={[0, -0.3, 0]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[2.72, 2.78, 48]} />
        <meshBasicMaterial color="#d4b077" transparent opacity={0.4} />
      </mesh>
      <mesh position={[0, -0.65, 0]} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[2.70, 2.76, 48]} />
        <meshBasicMaterial color="#a88c60" transparent opacity={0.35} />
      </mesh>
    </group>
  );
}

/**
 * Animated Xylem Sap Flow & Transpiration Vapor:
 * Bioluminescent ascending pulses traveling through roots and stem into leaves,
 * with speed governed by sapFlowVelocityCmh.
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

  // Sap particles inside stem
  const particleCount = 45;
  const initialPositions = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const angle = (i * 1.37) % (Math.PI * 2);
      const r = Math.random() * 0.035;
      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = -0.5 + Math.random() * (stemHeight + 0.5);
      pos[i * 3 + 2] = Math.sin(angle) * r;
    }
    return pos;
  }, [particleCount, stemHeight]);

  // Transpiration vapor particles in canopy
  const vaporCount = 30;
  const vaporPositions = useMemo(() => {
    const pos = new Float32Array(vaporCount * 3);
    for (let i = 0; i < vaporCount; i++) {
      const angle = (i * 2.1) % (Math.PI * 2);
      const r = 0.15 + Math.random() * 0.7;
      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = 0.8 + Math.random() * (stemHeight * 0.8);
      pos[i * 3 + 2] = Math.sin(angle) * r;
    }
    return pos;
  }, [vaporCount, stemHeight]);

  useFrame((_, delta) => {
    // Sap flow speed scaled by velocity
    const speed = Math.max(0.1, (sapFlowVelocityCmh / 15) * 1.2);
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

    // Transpiration vapor rising
    if (vaporRef.current) {
      const vPos = vaporRef.current.geometry.attributes.position.array as Float32Array;
      const vSpeed = 0.35 + (transpirationMm / 6) * 0.4;
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
      {/* Ascending Xylem Sap Flow Particles */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[initialPositions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.045}
          color={sapColor}
          transparent
          opacity={0.85}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Canopy Transpiration Vapor Particles */}
      {transpirationMm > 0.2 && (
        <points ref={vaporRef}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[vaporPositions, 3]}
            />
          </bufferGeometry>
          <pointsMaterial
            size={0.055}
            color="#a7f3d0"
            transparent
            opacity={Math.min(0.7, 0.15 + (transpirationMm / 7) * 0.5)}
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
  // Plant height scales with LAI
  const stemHeight = 2.45 + Math.min(0.9, (lai - 2.0) * 0.25);
  const totalNodes = 14;

  // Generate 14 phyllotactic leaves
  const leaves = useMemo(() => {
    return Array.from({ length: totalNodes }, (_, i) => {
      const t = i / (totalNodes - 1);
      // Alternate phyllotaxis (180 deg + natural wobble)
      const angle = i * Math.PI * 0.94 + (i % 2 === 0 ? 0.08 : -0.06);
      const nodeY = 0.28 + t * (stemHeight - 0.55);

      // Leaves 4 to 8 are longest; basal and apical are shorter
      const lengthCurve = Math.sin(Math.PI * Math.pow(t, 0.65));
      const length = 0.75 + lengthCurve * (1.1 + Math.min(0.4, lai * 0.08));
      const width = 0.09 + lengthCurve * 0.11;

      // Upward rise and droop
      const rise = length * (0.24 - t * 0.06);
      const droop = length * (0.18 + stress * 0.24 + t * 0.08);

      const isSenescent = i < 2 && stress > 0.35;

      return {
        id: i,
        angle,
        nodeY,
        length,
        width,
        rise,
        droop,
        isSenescent,
      };
    });
  }, [totalNodes, stemHeight, lai, stress]);

  return (
    <group position={[0, -0.2, 0]}>
      {/* 1. SoilGrids 2.0 Pedological Column */}
      {showSoilHorizons && (
        <SoilGridsStratigraphyCutout
          soilMoistureVol={soilMoistureVol}
          rootDepthCm={rootDepthCm}
        />
      )}

      {/* 2. FSPM Multi-Tier Root Architecture */}
      <FSPMRootArchitecture rootDepthCm={rootDepthCm} />

      {/* 3. Zea mays Culm (Stem with realistic nodes & sheaths) */}
      <group>
        {/* Main stem cylinder with basal taper */}
        <mesh castShadow position={[0, stemHeight / 2, 0]}>
          <cylinderGeometry args={[0.038, 0.065, stemHeight, 18]} />
          <meshStandardMaterial color="#4f7d2c" roughness={0.55} />
        </mesh>

        {/* Annular nodes & leaf collars along the culm */}
        {Array.from({ length: totalNodes }, (_, nodeIdx) => {
          const y = 0.28 + (nodeIdx / (totalNodes - 1)) * (stemHeight - 0.55);
          const taperRadius = 0.065 - (nodeIdx / totalNodes) * 0.026;
          return (
            <mesh key={`node-${nodeIdx}`} position={[0, y, 0]} castShadow>
              <torusGeometry args={[taperRadius + 0.005, 0.012, 8, 20]} />
              <meshStandardMaterial color="#639137" roughness={0.6} />
            </mesh>
          );
        })}
      </group>

      {/* 4. Realistic Phyllotactic Arching & Rolling Leaves */}
      {leaves.map((leaf) => (
        <RealisticMaizeLeaf
          key={leaf.id}
          angle={leaf.angle}
          nodeHeight={leaf.nodeY}
          length={leaf.length}
          width={leaf.width}
          rise={leaf.rise}
          droop={leaf.droop}
          stress={stress}
          isSenescent={leaf.isSenescent}
        />
      ))}

      {/* 5. Maize Ear (Mazorca con chalas y estigmas en nudo 6) */}
      <MaizeEar nodeY={0.92} angle={Math.PI * 0.4} />

      {/* 6. Apical Tassel (Panoja apical masculina) */}
      <MaizeTassel apexY={stemHeight} />

      {/* 7. Physiological Dynamics (Sap flow pulses & Transpiration vapor) */}
      {showHydrologyFlow && (
        <PhysiologicalFlowDynamics
          sapFlowVelocityCmh={sapFlowVelocityCmh}
          transpirationMm={transpirationMm}
          cwsiStress={stress}
          stemHeight={stemHeight}
        />
      )}

      {/* 8. Scientific 3D Annotation Callouts */}
      {showScientificLabels && (
        <>
          {/* Canopy FSPM Callout */}
          <Html position={[0, stemHeight + 0.85, 0]} center distanceFactor={8.5}>
            <div className="w-64 rounded-xl border border-emerald-400/40 bg-zinc-950/90 p-2.5 font-mono text-[10px] text-zinc-200 shadow-2xl backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-emerald-500/30 pb-1">
                <span className="font-bold text-emerald-300">Zea mays L. · visual simplificado</span>
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] text-emerald-300">
                  Micro
                </span>
              </div>
              <div className="mt-1.5 grid grid-cols-2 gap-1 text-[9px]">
                <div>
                  <span className="text-zinc-400">LAI Foliar:</span>{" "}
                  <span className="font-bold text-emerald-300">{lai.toFixed(2)}</span>
                </div>
                <div>
                  <span className="text-zinc-400">Estrés CWSI:</span>{" "}
                  <span className={`font-bold ${stress > 0.4 ? "text-amber-400" : "text-emerald-300"}`}>
                    {stress.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-400">Transp. Tr:</span>{" "}
                  <span className="font-bold text-cyan-300">{transpirationMm.toFixed(2)} mm/d</span>
                </div>
                <div>
                  <span className="text-zinc-400">V. Xilema:</span>{" "}
                  <span className="font-bold text-sky-300">{sapFlowVelocityCmh.toFixed(1)} cm/h</span>
                </div>
              </div>
            </div>
          </Html>

          {/* SoilGrids Profile Callout */}
          <Html position={[1.8, -0.6, 0]} center distanceFactor={9}>
            <div className="w-56 rounded-lg border border-amber-500/30 bg-zinc-950/85 p-2 font-mono text-[9px] text-zinc-300 shadow-xl backdrop-blur">
              <div className="font-bold text-amber-300">Perfil edafológico ilustrativo</div>
              <div className="mt-1 text-zinc-400">
                Horizontes: Ap (0-30cm) · Bt (30-65cm) · C ({">"}65cm)
              </div>
              <div className="mt-0.5 text-zinc-300">
                θ Suelo: <span className="font-bold text-cyan-300">{soilMoistureVol.toFixed(1)}%</span> · Zmax:{" "}
                <span className="font-bold text-amber-200">{rootDepthCm.toFixed(0)} cm</span>
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

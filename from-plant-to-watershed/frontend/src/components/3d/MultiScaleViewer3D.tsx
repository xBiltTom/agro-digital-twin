"use client";

import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Sky, Stars, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import WatershedMesh3D from "./WatershedMesh3D";
import FieldPlotMesh3D, { PlantSample3D } from "./FieldPlotMesh3D";
import PlantModel3D from "./PlantModel3D";

export type ScaleMode = "MACRO" | "MESO" | "MICRO";

interface MultiScaleViewer3DProps {
  scaleMode: ScaleMode;
  onChangeScale: (scale: ScaleMode) => void;
  streamflowM3s: number;
  precipMm: number;
  soilMoistureVol: number;
  transpirationMm: number;
  cwsiStress: number;
  sapFlowVelocityCmh: number;
  plantSample?: PlantSample3D[];
  plantCount?: number;
  fieldAggregates?: Record<string, unknown>;
  hruAggregates?: { hrus?: Array<{ hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string }> };
  showHydrologyFlow?: boolean;
  showSoilHorizons?: boolean;
  showSensors?: boolean;
  showScientificLabels?: boolean;
}

// Controlador de transición cinemática suave de cámara según la escala activa
function CameraController({ scaleMode }: { scaleMode: ScaleMode }) {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3(0, 34, 46));
  const lookAtPos = useRef(new THREE.Vector3(2, 0, -2));

  useEffect(() => {
    if (scaleMode === "MACRO") {
      targetPos.current.set(2, 32, 44);
      lookAtPos.current.set(2, 0, -2);
    } else if (scaleMode === "MESO") {
      targetPos.current.set(0, 16, 22);
      lookAtPos.current.set(0, 1, 0);
    } else if (scaleMode === "MICRO") {
      targetPos.current.set(4.5, 2.5, 5.2);
      lookAtPos.current.set(0, 1.25, 0);
    }
  }, [scaleMode]);

  useFrame(() => {
    // Lerp adaptativo para suavidad cinemática
    const dist = camera.position.distanceTo(targetPos.current);
    const lerpFactor = dist > 8 ? 0.05 : 0.08;
    camera.position.lerp(targetPos.current, lerpFactor);
    camera.lookAt(lookAtPos.current);
  });

  return null;
}

export default function MultiScaleViewer3D({
  scaleMode,
  onChangeScale,
  streamflowM3s,
  precipMm,
  soilMoistureVol,
  transpirationMm,
  cwsiStress,
  sapFlowVelocityCmh,
  plantSample = [],
  plantCount = 1000,
  fieldAggregates,
  hruAggregates,
  showHydrologyFlow = true,
  showSoilHorizons = true,
  showSensors = true,
  showScientificLabels = true,
}: MultiScaleViewer3DProps) {
  // Posición del sol según escala
  const sunPosition: [number, number, number] =
    scaleMode === "MACRO"
      ? [60, 48, 60]
      : scaleMode === "MESO"
      ? [32, 42, 22]
      : [14, 24, 16];

  return (
    <div className="w-full h-full relative bg-gradient-to-b from-zinc-950 via-slate-950 to-zinc-950 overflow-hidden rounded-2xl border border-zinc-800 shadow-2xl">
      <Canvas
        shadows
        camera={{ position: [0, 34, 46], fov: 44 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.18,
        }}
      >
        {/* Skybox atmosférico procedural */}
        <Sky
          distance={450000}
          sunPosition={sunPosition}
          inclination={0.52}
          azimuth={0.25}
          turbidity={scaleMode === "MACRO" ? 6 : 8}
          rayleigh={scaleMode === "MACRO" ? 0.8 : 0.5}
          mieCoefficient={0.005}
          mieDirectionalG={0.82}
        />

        {/* Campo estelar sutil */}
        <Stars
          radius={120}
          depth={40}
          count={scaleMode === "MACRO" ? 1400 : 500}
          factor={3}
          saturation={0}
          fade
          speed={0.5}
        />

        {/* Iluminación solar física y ambiental */}
        <ambientLight intensity={0.58} />
        <hemisphereLight
          args={["#7dd3fc", "#1e293b", 0.65]}
          position={[0, 50, 0]}
        />
        <directionalLight
          position={sunPosition}
          intensity={1.85}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-bias={-0.0001}
          shadow-camera-near={1}
          shadow-camera-far={130}
          shadow-camera-left={-35}
          shadow-camera-right={35}
          shadow-camera-top={35}
          shadow-camera-bottom={-35}
        />

        {/* Luces de relleno sutiles */}
        <pointLight position={[-20, 18, -15]} intensity={0.45} color="#38bdf8" />
        <pointLight position={[20, 6, 20]} intensity={0.4} color="#34d399" />

        {/* Niebla atmosférica */}
        <fog
          attach="fog"
          args={[
            "#0c1427",
            scaleMode === "MICRO" ? 14 : scaleMode === "MESO" ? 30 : 45,
            scaleMode === "MICRO" ? 32 : scaleMode === "MESO" ? 85 : 120,
          ]}
        />

        {/* Transición cinemática de cámara */}
        <CameraController scaleMode={scaleMode} />

        {/* Controles de órbita */}
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          maxDistance={scaleMode === "MICRO" ? 16 : scaleMode === "MESO" ? 45 : 85}
          minDistance={scaleMode === "MICRO" ? 1.6 : scaleMode === "MESO" ? 4 : 8}
          maxPolarAngle={Math.PI / 2.04}
        />

        {/* Sombras de contacto para Meso y Micro */}
        {(scaleMode === "MESO" || scaleMode === "MICRO") && (
          <ContactShadows
            position={[0, scaleMode === "MICRO" ? -0.22 : -0.12, 0]}
            opacity={0.7}
            scale={scaleMode === "MICRO" ? 8 : 34}
            blur={2.0}
            far={8}
            resolution={512}
            color="#090d16"
          />
        )}

        {/* Escala MACRO: Cuenca SWAT+, Red Fluvial, HRUs, USGS */}
        {scaleMode === "MACRO" && (
          <WatershedMesh3D
            streamflowM3s={streamflowM3s}
            precipMm={precipMm}
            soilMoistureVol={soilMoistureVol}
            hruAggregates={hruAggregates}
            onSelectSubbasin={() => onChangeScale("MESO")}
            showHruBorders={showSoilHorizons}
            showHydrologyFlow={showHydrologyFlow}
            showScientificLabels={showScientificLabels}
          />
        )}

        {/* Escala MESO: Campo de Maíz n=1000 con Variabilidad Espacial BARC */}
        {scaleMode === "MESO" && (
          <FieldPlotMesh3D
            soilMoistureVol={soilMoistureVol}
            cwsiStress={cwsiStress}
            plantSample={plantSample}
            plantCount={plantCount}
            onSelectPlant={() => onChangeScale("MICRO")}
            showSensors={showSensors}
            showScientificLabels={showScientificLabels}
          />
        )}

        {/* Escala MICRO: Zea mays L. FSPM Nivel 1 */}
        {scaleMode === "MICRO" && (
          <PlantModel3D
            transpirationMm={transpirationMm}
            cwsiStress={cwsiStress}
            sapFlowVelocityCmh={sapFlowVelocityCmh}
            soilMoistureVol={soilMoistureVol}
            lai={Number(fieldAggregates?.mean_lai) || undefined}
            rootDepthCm={plantSample[0]?.root_depth_cm}
            showHydrologyFlow={showHydrologyFlow}
            showSoilHorizons={showSoilHorizons}
            showScientificLabels={showScientificLabels}
          />
        )}
      </Canvas>
    </div>
  );
}

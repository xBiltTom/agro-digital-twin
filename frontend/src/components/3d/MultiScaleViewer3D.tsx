"use client";

import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import WatershedMesh3D from "./WatershedMesh3D";
import FieldPlotMesh3D from "./FieldPlotMesh3D";
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
}

// Controlador de transición suave de cámara según la escala activa
function CameraController({ scaleMode }: { scaleMode: ScaleMode }) {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3(0, 35, 45));
  const lookAtPos = useRef(new THREE.Vector3(0, 0, 0));

  useEffect(() => {
    if (scaleMode === "MACRO") {
      targetPos.current.set(0, 32, 42);
      lookAtPos.current.set(0, 2, 0);
    } else if (scaleMode === "MESO") {
      targetPos.current.set(0, 12, 18);
      lookAtPos.current.set(0, 1, 0);
    } else if (scaleMode === "MICRO") {
      targetPos.current.set(0, 2.2, 5.5);
      lookAtPos.current.set(0, 1.2, 0);
    }
  }, [scaleMode]);

  useFrame(() => {
    camera.position.lerp(targetPos.current, 0.05);
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
}: MultiScaleViewer3DProps) {
  return (
    <div className="w-full h-full relative bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-950 overflow-hidden rounded-2xl border border-zinc-800 shadow-2xl">
      <Canvas
        shadows
        camera={{ position: [0, 35, 45], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
      >
        <color attach="background" args={["#050811"]} />
        
        {/* Iluminación ambiental y solar */}
        <ambientLight intensity={0.45} />
        <hemisphereLight args={["#38bdf8", "#0f172a", 0.6]} />
        <directionalLight
          position={[25, 40, 20]}
          intensity={1.2}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />
        <pointLight position={[-15, 10, -10]} intensity={0.4} color="#10b981" />

        {/* Niebla volumétrica científica */}
        <fog attach="fog" args={["#050811", 30, 95]} />

        {/* Transición cinemática de cámara */}
        <CameraController scaleMode={scaleMode} />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          maxDistance={70}
          minDistance={2}
          maxPolarAngle={Math.PI / 2.05}
        />

        {/* Renderizado condicional o integrado por escala */}
        {scaleMode === "MACRO" && (
          <WatershedMesh3D
            streamflowM3s={streamflowM3s}
            precipMm={precipMm}
            soilMoistureVol={soilMoistureVol}
            onSelectSubbasin={() => onChangeScale("MESO")}
          />
        )}

        {scaleMode === "MESO" && (
          <FieldPlotMesh3D
            soilMoistureVol={soilMoistureVol}
            cwsiStress={cwsiStress}
            onSelectPlant={() => onChangeScale("MICRO")}
          />
        )}

        {scaleMode === "MICRO" && (
          <PlantModel3D
            transpirationMm={transpirationMm}
            cwsiStress={cwsiStress}
            sapFlowVelocityCmh={sapFlowVelocityCmh}
            soilMoistureVol={soilMoistureVol}
          />
        )}
      </Canvas>
    </div>
  );
}

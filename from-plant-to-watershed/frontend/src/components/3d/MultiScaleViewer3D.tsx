"use client";

import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Sky, Stars, ContactShadows } from "@react-three/drei";
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

// Controlador de transición cinemática suave de cámara según la escala activa
function CameraController({ scaleMode }: { scaleMode: ScaleMode }) {
  const { camera } = useThree();
  const targetPos = useRef(new THREE.Vector3(0, 32, 42));
  const lookAtPos = useRef(new THREE.Vector3(0, 2, 0));

  useEffect(() => {
    if (scaleMode === "MACRO") {
      targetPos.current.set(0, 30, 40);
      lookAtPos.current.set(0, 2, 0);
    } else if (scaleMode === "MESO") {
      targetPos.current.set(0, 14, 20);
      lookAtPos.current.set(0, 1, 0);
    } else if (scaleMode === "MICRO") {
      targetPos.current.set(0, 2.0, 5.2);
      lookAtPos.current.set(0, 1.2, 0);
    }
  }, [scaleMode]);

  useFrame(() => {
    // Lerp adaptativo: transición rápida inicial y suave desaceleración al aproximarse
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
}: MultiScaleViewer3DProps) {
  // Ajuste de sol según escala y estrés
  const sunPosition: [number, number, number] =
    scaleMode === "MACRO"
      ? [60, 45, 60]
      : scaleMode === "MESO"
      ? [30, 40, 20]
      : [15, 25, 15];

  return (
    <div className="w-full h-full relative bg-gradient-to-b from-zinc-950 via-slate-950 to-zinc-950 overflow-hidden rounded-2xl border border-zinc-800 shadow-2xl">
      <Canvas
        shadows
        camera={{ position: [0, 32, 42], fov: 45 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.15,
        }}
      >
        {/* Skybox atmosférico procedural con dispersión de luz física */}
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

        {/* Campo estelar sutil para fondo de alta cota */}
        <Stars
          radius={120}
          depth={40}
          count={scaleMode === "MACRO" ? 1500 : 600}
          factor={3}
          saturation={0}
          fade
          speed={0.5}
        />

        {/* Iluminación solar física y ambiental */}
        <ambientLight intensity={0.55} />
        <hemisphereLight
          args={["#7dd3fc", "#1e293b", 0.65]}
          position={[0, 50, 0]}
        />
        <directionalLight
          position={sunPosition}
          intensity={1.8}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-bias={-0.0001}
          shadow-camera-near={1}
          shadow-camera-far={120}
          shadow-camera-left={-35}
          shadow-camera-right={35}
          shadow-camera-top={35}
          shadow-camera-bottom={-35}
        />

        {/* Luz de relleno suave y científica */}
        <pointLight position={[-20, 15, -15]} intensity={0.5} color="#38bdf8" />
        <pointLight position={[20, 5, 20]} intensity={0.4} color="#34d399" />

        {/* Niebla atmosférica adaptada al color del cielo */}
        <fog attach="fog" args={["#0c1427", scaleMode === "MICRO" ? 12 : 35, scaleMode === "MICRO" ? 30 : 100]} />

        {/* Transición cinemática de cámara */}
        <CameraController scaleMode={scaleMode} />

        {/* Controles de órbita suaves */}
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          maxDistance={scaleMode === "MICRO" ? 18 : 75}
          minDistance={scaleMode === "MICRO" ? 1.5 : 4}
          maxPolarAngle={Math.PI / 2.05}
        />

        {/* Sombras de contacto suaves para Meso y Micro */}
        {(scaleMode === "MESO" || scaleMode === "MICRO") && (
          <ContactShadows
            position={[0, scaleMode === "MICRO" ? -2.0 : -0.05, 0]}
            opacity={0.7}
            scale={scaleMode === "MICRO" ? 8 : 36}
            blur={2.0}
            far={8}
            resolution={512}
            color="#090d16"
          />
        )}

        {/* Renderizado por escala */}
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

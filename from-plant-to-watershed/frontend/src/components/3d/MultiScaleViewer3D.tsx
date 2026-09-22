"use client";

import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Sky, Stars, ContactShadows, Environment, Lightformer } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";

type OrbitControlsImpl = {
  target: THREE.Vector3;
  update: () => void;
};
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
  hruAggregates?: { hrus?: Array<{ hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string }>; results?: Array<{ hru_id?: string; hru_number?: number; area_fraction?: number; crop?: string }> };
  watershedName?: string;
  stationId?: string | null;
  evidenceType?: string;
  showHydrologyFlow?: boolean;
  showSoilHorizons?: boolean;
  showSensors?: boolean;
  showScientificLabels?: boolean;
  currentDay?: number;
  totalDays?: number;
}

/**
 * Controlador de transición cinemática suave:
 * IMPORTANTE: Solo anima durante el cambio de escala (~1.1 segundos).
 * Una vez finalizada la transición, cede el 100% del control a OrbitControls
 * para que el zoom y la rotación NO reboten ni vuelvan a su posición inicial.
 */
function CameraController({
  scaleMode,
  controlsRef,
}: {
  scaleMode: ScaleMode;
  controlsRef: React.RefObject<any>;
}) {
  const { camera } = useThree();

  const isTransitioning = useRef(false);
  const transitionProgress = useRef(1);
  const startPos = useRef(new THREE.Vector3());
  const startTarget = useRef(new THREE.Vector3());
  const destPos = useRef(new THREE.Vector3());
  const destTarget = useRef(new THREE.Vector3());

  useEffect(() => {
    // Definir destinos de cámara y objetivos de rotación según la escala
    if (scaleMode === "MACRO") {
      destPos.current.set(0, 36, 42);
      destTarget.current.set(0, 0, 0);
    } else if (scaleMode === "MESO") {
      destPos.current.set(0, 15, 21);
      destTarget.current.set(0, 0.5, 0);
    } else if (scaleMode === "MICRO") {
      destPos.current.set(2.8, 1.8, 3.4);
      destTarget.current.set(0, 1.1, 0);
    }

    startPos.current.copy(camera.position);
    startTarget.current.copy(
      controlsRef.current ? controlsRef.current.target : new THREE.Vector3(0, 1, 0)
    );

    transitionProgress.current = 0;
    isTransitioning.current = true;
  }, [scaleMode, camera, controlsRef]);

  useFrame((_, delta) => {
    if (!isTransitioning.current) return;

    // Avanzar animación con curva suave ease-out cubic
    transitionProgress.current = Math.min(1, transitionProgress.current + delta * 1.3);
    const p = transitionProgress.current;
    const easeOut = 1 - Math.pow(1 - p, 3);

    camera.position.lerpVectors(startPos.current, destPos.current, easeOut);

    if (controlsRef.current) {
      controlsRef.current.target.lerpVectors(startTarget.current, destTarget.current, easeOut);
      controlsRef.current.update();
    } else {
      camera.lookAt(destTarget.current);
    }

    if (p >= 1) {
      isTransitioning.current = false;
      if (controlsRef.current) {
        controlsRef.current.target.copy(destTarget.current);
        controlsRef.current.update();
      }
    }
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
  watershedName,
  stationId,
  evidenceType,
  showHydrologyFlow = true,
  showSoilHorizons = true,
  showSensors = true,
  showScientificLabels = true,
  currentDay = 1,
  totalDays = 365,
}: MultiScaleViewer3DProps) {
  const controlsRef = useRef<any>(null);

  // Iluminación solar física ajustada por escala
  const sunPosition: [number, number, number] =
    scaleMode === "MACRO"
      ? [55, 45, 50]
      : scaleMode === "MESO"
      ? [28, 36, 22]
      : [12, 22, 15];

  // Distancias de zoom adaptadas para evitar que el usuario se pierda
  const minDistance = scaleMode === "MICRO" ? 0.7 : scaleMode === "MESO" ? 2.5 : 8;
  const maxDistance = scaleMode === "MICRO" ? 12 : scaleMode === "MESO" ? 42 : 85;

  return (
    <div className="w-full h-full relative bg-gradient-to-b from-zinc-950 via-slate-950 to-zinc-950 overflow-hidden rounded-2xl">
      <Canvas
        shadows
        camera={{ position: [0, 36, 42], fov: 44 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.22,
        }}
      >
        {/* Cielo con atmósfera física */}
        <Sky
          distance={450000}
          sunPosition={sunPosition}
          inclination={0.52}
          azimuth={0.25}
          turbidity={scaleMode === "MACRO" ? 6 : 8}
          rayleigh={scaleMode === "MACRO" ? 0.75 : 0.45}
          mieCoefficient={0.005}
          mieDirectionalG={0.84}
        />

        {/* Estrellas lejanas sutiles */}
        <Stars
          radius={120}
          depth={40}
          count={scaleMode === "MACRO" ? 1200 : 400}
          factor={3}
          saturation={0}
          fade
          speed={0.5}
        />

        {/* Entorno PBR de Iluminación Global IBL (reflejos físicos en hojas, suelo, agua y metales) */}
        <Environment background={false}>
          <mesh scale={100}>
            <sphereGeometry args={[1, 32, 32]} />
            <meshBasicMaterial side={THREE.BackSide} color="#0c192c" />
          </mesh>
          <Lightformer
            form="circle"
            intensity={scaleMode === "MICRO" ? 3.8 : 3.0}
            position={[sunPosition[0] * 0.8, sunPosition[1] * 0.8, sunPosition[2] * 0.8]}
            scale={scaleMode === "MICRO" ? 14 : 28}
            color="#fff7ed"
          />
          <Lightformer
            form="ring"
            intensity={1.6}
            position={[0, 45, 0]}
            scale={35}
            color="#38bdf8"
          />
          <Lightformer
            form="rect"
            intensity={0.9}
            position={[0, 4, -35]}
            scale={[55, 12]}
            color="#fef08a"
          />
          <Lightformer
            form="rect"
            intensity={0.65}
            position={[0, -15, 0]}
            scale={45}
            color="#2d4a1d"
          />
        </Environment>

        {/* Iluminación solar física con sombras suaves de alta resolución */}
        <ambientLight intensity={0.55} />
        <hemisphereLight
          args={["#a7f3d0", "#1e293b", 0.6]}
          position={[0, 50, 0]}
        />
        <directionalLight
          position={sunPosition}
          intensity={2.3}
          color="#fffdf5"
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-bias={-0.00012}
          shadow-camera-near={1}
          shadow-camera-far={130}
          shadow-camera-left={-34}
          shadow-camera-right={34}
          shadow-camera-top={34}
          shadow-camera-bottom={-34}
        />

        {/* Luces de rebote y relleno para evitar partes negras artificiales */}
        <pointLight position={[-18, 16, -14]} intensity={0.5} color="#38bdf8" />
        <pointLight position={[18, 5, 18]} intensity={0.4} color="#34d399" />

        {/* Niebla de profundidad */}
        <fog
          attach="fog"
          args={[
            "#0b1324",
            scaleMode === "MICRO" ? 16 : scaleMode === "MESO" ? 35 : 50,
            scaleMode === "MICRO" ? 36 : scaleMode === "MESO" ? 90 : 130,
          ]}
        />

        {/* Controlador cinemático que NO interfiere con el OrbitControls */}
        <CameraController scaleMode={scaleMode} controlsRef={controlsRef} />

        {/* Controles de órbita completamente libres y suaves */}
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.07}
          rotateSpeed={0.8}
          zoomSpeed={1.2}
          panSpeed={0.8}
          minDistance={minDistance}
          maxDistance={maxDistance}
          maxPolarAngle={Math.PI / 2.02}
        />

        {/* Sombras de contacto suaves para Meso y Micro */}
        {(scaleMode === "MESO" || scaleMode === "MICRO") && (
          <ContactShadows
            position={[0, scaleMode === "MICRO" ? -0.22 : -0.12, 0]}
            opacity={0.75}
            scale={scaleMode === "MICRO" ? 9 : 36}
            blur={2.2}
            far={9}
            resolution={512}
            color="#080c14"
          />
        )}

        {/* Escala MACRO: Cuenca SWAT+, Red Fluvial, HRUs, USGS */}
        {scaleMode === "MACRO" && (
          <WatershedMesh3D
            streamflowM3s={streamflowM3s}
            precipMm={precipMm}
            soilMoistureVol={soilMoistureVol}
            hruAggregates={hruAggregates}
            watershedName={watershedName}
            stationId={stationId}
            evidenceType={evidenceType}
            onSelectSubbasin={() => onChangeScale("MESO")}
            showHruBorders={showSoilHorizons}
            showHydrologyFlow={showHydrologyFlow}
            showScientificLabels={showScientificLabels}
            currentDay={currentDay}
            totalDays={totalDays}
          />
        )}

        {/* Escala MESO: campo FSPM agregado y muestra de planta persistida */}
        {scaleMode === "MESO" && (
          <FieldPlotMesh3D
            soilMoistureVol={soilMoistureVol}
            cwsiStress={cwsiStress}
            plantSample={plantSample}
            plantCount={plantCount}
            fieldAggregate={fieldAggregates}
            onSelectPlant={() => onChangeScale("MICRO")}
            showSensors={showSensors}
            showScientificLabels={showScientificLabels}
            currentDay={currentDay}
            totalDays={totalDays}
            precipMm={precipMm}
          />
        )}

        {/* Escala MICRO: Zea mays L. FSPM Nivel 1 */}
        {scaleMode === "MICRO" && (
          <PlantModel3D
            transpirationMm={transpirationMm}
            cwsiStress={cwsiStress}
            sapFlowVelocityCmh={sapFlowVelocityCmh}
            soilMoistureVol={soilMoistureVol}
            lai={Number(fieldAggregates?.mean_LAI ?? fieldAggregates?.mean_lai) || undefined}
            rootDepthCm={plantSample[0]?.root_depth_cm}
            plantHeightM={plantSample[0]?.plant_height_m ?? (Number(fieldAggregates?.plant_height_mean_m) || undefined)}
            leafCount={plantSample[0]?.leaf_count}
            leafAreaM2={plantSample[0]?.leaf_area_m2}
            phenologicalStage={plantSample[0]?.phenological_stage}
            stateLabel={plantSample.length > 0 ? "Muestra FSPM persistida" : "Agregado de campo FSPM"}
            showHydrologyFlow={showHydrologyFlow}
            showSoilHorizons={showSoilHorizons}
            showScientificLabels={showScientificLabels}
            currentDay={currentDay}
            totalDays={totalDays}
            precipMm={precipMm}
          />
        )}

        {/* Post-procesado cinemático: Bloom para reflejos especulares, agua y savia, con viñeteado óptico */}
        <EffectComposer multisampling={2}>
          <Bloom
            luminanceThreshold={0.82}
            luminanceSmoothing={0.25}
            intensity={0.45}
            mipmapBlur
          />
          <Vignette eskil={false} offset={0.28} darkness={0.42} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}

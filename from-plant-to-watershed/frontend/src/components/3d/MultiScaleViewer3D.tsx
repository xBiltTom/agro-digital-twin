"use client";

import React, { useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Sky, Stars, ContactShadows, Environment, Lightformer, Html } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";

type OrbitControlsImpl = React.ComponentRef<typeof OrbitControls>;
import WatershedMesh3D from "./WatershedMesh3D";
import FieldPlotMesh3D from "./FieldPlotMesh3D";
import PlantModel3D from "./PlantModel3D";
import { hasSouthForkContext, periodLabel, type SceneState } from "../../lib/playback-scene";

export type ScaleMode = "MACRO" | "MESO" | "MICRO";

interface MultiScaleViewer3DProps {
  scaleMode: ScaleMode;
  onChangeScale: (scale: ScaleMode) => void;
  scene: SceneState | null;
  watershedName?: string;
  stationId?: string | null;
  showHydrologyFlow?: boolean;
  showSoilHorizons?: boolean;
  showSensors?: boolean;
  showScientificLabels?: boolean;
  onSelectPlant?: (plantId?: string) => void;
}

import { maizeFromScene } from "../../lib/visual-state";

/**
 * Controlador de transición cinemática suave:
 * IMPORTANTE: Solo anima durante el cambio de escala (~1.1 segundos) o ajuste
 * de encuadre en Micro. Cede el 100% del control a OrbitControls para que
 * el usuario mantenga libertad total de órbita y zoom.
 */
function CameraController({
  scaleMode,
  controlsRef,
  targetHeight,
}: {
  scaleMode: ScaleMode;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  targetHeight?: number;
}) {
  const { camera } = useThree();

  const isTransitioning = useRef(false);
  const transitionProgress = useRef(1);
  const startPos = useRef(new THREE.Vector3());
  const startTarget = useRef(new THREE.Vector3());
  const destPos = useRef(new THREE.Vector3());
  const destTarget = useRef(new THREE.Vector3());
  const lastScale = useRef<ScaleMode | null>(null);
  const lastHeight = useRef<number | undefined>(undefined);

  useEffect(() => {
    const scaleChanged = scaleMode !== lastScale.current;
    const heightChanged = scaleMode === "MICRO" && Math.abs((lastHeight.current ?? 1.8) - (targetHeight ?? 1.8)) > 0.35;

    if (!scaleChanged && !heightChanged && lastScale.current !== null) return;
    lastScale.current = scaleMode;
    lastHeight.current = targetHeight;

    // Definir destinos de cámara y objetivos de rotación según la escala
    if (scaleMode === "MACRO") {
      destPos.current.set(0, 36, 42);
      destTarget.current.set(0, 0, 0);
    } else if (scaleMode === "MESO") {
      destPos.current.set(0, 15, 21);
      destTarget.current.set(0, 0.5, 0);
    } else if (scaleMode === "MICRO") {
      if (targetHeight && targetHeight > 0 && targetHeight < 0.9) {
        // Maíz joven / plántula: encuadrar más cerca y centrado
        destPos.current.set(1.5, 0.75, 1.8);
        destTarget.current.set(0, Math.max(0.12, targetHeight * 0.5), 0);
      } else {
        // Maíz desarrollado y referencia: encuadre canónico completo
        destPos.current.set(2.8, 1.8, 3.4);
        destTarget.current.set(0, 1.1, 0);
      }
    }

    startPos.current.copy(camera.position);
    startTarget.current.copy(
      controlsRef.current ? controlsRef.current.target : new THREE.Vector3(0, 1, 0)
    );

    transitionProgress.current = 0;
    isTransitioning.current = true;
  }, [scaleMode, camera, controlsRef, targetHeight]);

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

function GenericRain({ intensity }: { intensity: number }) {
  const group = useRef<THREE.Group>(null);
  const count = Math.max(8, Math.floor(intensity * 700));
  useFrame((_, delta) => { if (group.current) group.current.position.y = (group.current.position.y - delta * 10 + 20) % 20; });
  return <group ref={group}>{Array.from({ length: count }, (_, i) =>
    <mesh key={i} position={[
      (((i * 73) % 701) / 701 - 0.5) * 42,
      ((i * 47) % 211) / 211 * 20,
      (((i * 137) % 709) / 709 - 0.5) * 32,
    ]}>
      <boxGeometry args={[0.025, 0.4, 0.025]} />
      <meshBasicMaterial color="#9bdaf6" transparent opacity={0.5} />
    </mesh>)}</group>;
}

export default function MultiScaleViewer3D({
  scaleMode,
  onChangeScale,
  scene,
  watershedName,
  stationId,
  showHydrologyFlow = true,
  showSoilHorizons = true,
  showSensors = true,
  showScientificLabels = true,
  onSelectPlant,
}: MultiScaleViewer3DProps) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const southForkContext = scene ? hasSouthForkContext(scene.record, stationId) : stationId === "05451210";
  const plant = maizeFromScene(scene);
  const targetPlantHeight = plant.heightM ?? (plant.reference ? 2.1 : undefined);

  // Iluminación solar física ajustada por escala
  const sunPosition: [number, number, number] =
    scaleMode === "MACRO"
      ? [55, 45, 50]
      : scaleMode === "MESO"
      ? [28, 36, 22]
      : [12, 22, 15];

  // Distancias de zoom adaptadas para evitar que el usuario se pierda
  const minDistance = scaleMode === "MICRO" ? 0.35 : scaleMode === "MESO" ? 2.5 : 8;
  const maxDistance = scaleMode === "MICRO" ? 14 : scaleMode === "MESO" ? 45 : 95;

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
        <CameraController scaleMode={scaleMode} controlsRef={controlsRef} targetHeight={targetPlantHeight} />

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
        {scaleMode === "MACRO" && southForkContext && (
          <WatershedMesh3D
            streamflowM3s={scene?.streamflowM3s ?? null}
            precipMm={scene?.rainMm ?? null}
            rainEffectMm={scene?.record.resolution === "DAILY" ? scene.rainMm : null}
            precipitationUnit={scene?.record.weather.precipitation_mm?.unit ?? "mm"}
            periodLabel={scene ? periodLabel(scene.record) : "Referencia visual sin fecha científica"}
            watershedName={watershedName}
            stationId={stationId}
            evidenceType={scene?.record.hydrology.streamflow_m3s?.evidence ?? "NOT_AVAILABLE"}
            onSelectSubbasin={() => onChangeScale("MESO")}
            fieldNavigationLabel={!scene ? "Explorar parcela de referencia (Meso)" :
              scene.cropActive && scene.cropSupported ? "Ver campo FSPM (Meso)" : "Explorar parcela contextual (Meso)"}
            showHruBorders={showSoilHorizons}
            showHydrologyFlow={showHydrologyFlow}
            showScientificLabels={showScientificLabels}
          />
        )}
        {scaleMode === "MACRO" && !southForkContext && <group>
          <mesh receiveShadow rotation-x={-Math.PI / 2}>
            <planeGeometry args={[45, 35]} />
            <meshStandardMaterial color="#264133" roughness={0.9} />
          </mesh>
          <Html position={[0, 4, 0]} center distanceFactor={16}>
            <div className="rounded-xl border border-cyan-500/40 bg-zinc-950/95 p-3 text-xs text-zinc-200">
              <b>Cuenca {scene?.record.watershed_code ?? scene?.record.watershed_id ?? watershedName ?? "contextual"}</b>
              <p>{scene ? "Geometría espacial no disponible para esta corrida. Los valores del outlet se muestran en el HUD." :
                "Referencia visual sin geometría de cuenca verificada ni registro temporal."}</p>
            </div>
          </Html>
          {showHydrologyFlow && scene?.rainIntensity !== null && scene?.rainIntensity !== undefined && scene.rainIntensity > 0 && <GenericRain intensity={scene.rainIntensity} />}
        </group>}

        {/* Escala MESO: campo FSPM agregado y muestra de planta persistida */}
        {scaleMode === "MESO" && (
          <FieldPlotMesh3D
            scene={scene}
            onSelectPlant={(plantId) => { onSelectPlant?.(plantId); onChangeScale("MICRO"); }}
            showSensors={showSensors}
            showScientificLabels={showScientificLabels}
            showHydrologyFlow={showHydrologyFlow}
          />
        )}

        {/* Escala MICRO: Zea mays L. FSPM Nivel 1 */}
        {scaleMode === "MICRO" && (
          <PlantModel3D
            scene={scene}
            showHydrologyFlow={showHydrologyFlow}
            showSoilHorizons={showSoilHorizons}
            showScientificLabels={showScientificLabels}
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

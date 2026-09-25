"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import * as THREE from "three";
import type { SceneState } from "../../lib/playback-scene";
import { fieldCanopyAvailable, maizeReproductive } from "../../lib/visual-state";
import {
  createCurvedMaizeLeafGeometry,
  EddyCovarianceTower,
  MesoRainSystem,
  SoilMoistureProbeStation,
} from "./FieldVisuals3D";

interface Props {
  scene: SceneState | null;
  onSelectPlant: (plantId?: string) => void;
  showSensors?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

/** 26 × 39 decorative maize meshes (1,014 plants), driven by the field mean with traveling organic wind waves. */
function RichCanopy({
  heightM,
  lai,
  cover,
  stress,
  stage,
}: {
  heightM: number;
  lai: number;
  cover: number | null;
  stress: number | null;
  stage: string | null;
}) {
  const stems = useRef<THREE.InstancedMesh>(null);
  const lower = useRef<THREE.InstancedMesh>(null);
  const middle = useRef<THREE.InstancedMesh>(null);
  const upper = useRef<THREE.InstancedMesh>(null);
  const tassels = useRef<THREE.InstancedMesh>(null);

  const rows = 26;
  const columns = 39;
  const count = rows * columns;

  const leafGeoA = useMemo(() => createCurvedMaizeLeafGeometry(0.88, 0.17, 0.35), []);
  const leafGeoB = useMemo(() => createCurvedMaizeLeafGeometry(0.82, 0.15, 0.28), []);
  const leafGeoC = useMemo(() => createCurvedMaizeLeafGeometry(0.68, 0.13, 0.20), []);

  useEffect(() => () => {
    leafGeoA.dispose();
    leafGeoB.dispose();
    leafGeoC.dispose();
  }, [leafGeoA, leafGeoB, leafGeoC]);

  // Almacenar matrices base para animación física de viento sin derivas acumulativas
  const baseData = useRef<{
    positions: THREE.Vector3[];
    rotations: THREE.Euler[];
    scales: THREE.Vector3[];
  }>({ positions: [], rotations: [], scales: [] });

  useEffect(() => {
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const scale = new THREE.Vector3();
    const rotation = new THREE.Euler();
    const quaternion = new THREE.Quaternion();

    const height = Math.max(0.05, Math.min(3.4, heightM)); // metre for metre
    const leafScale = Math.max(0.08, Math.min(1.2, lai / 3.8)) *
      (cover === null ? 1 : Math.max(0.1, Math.min(1, cover)));

    const leafColor = stress === null
      ? new THREE.Color("#38782a")
      : new THREE.Color("#22631a").lerp(new THREE.Color("#989e30"), Math.max(0, Math.min(1, stress)));

    baseData.current.positions = [];
    baseData.current.rotations = [];
    baseData.current.scales = [];

    for (let i = 0; i < count; i++) {
      const col = i % columns;
      const row = Math.floor(i / columns);
      const x = (col - (columns - 1) / 2) * 0.54;
      const z = (row - (rows - 1) / 2) * 0.82;
      const turn = i * 0.73;

      baseData.current.positions.push(new THREE.Vector3(x, 0, z));
      baseData.current.rotations.push(new THREE.Euler(0, turn, 0));
      baseData.current.scales.push(new THREE.Vector3(leafScale, height, leafScale));

      // 1. Tallos
      position.set(x, height / 2, z);
      rotation.set(0, turn, 0);
      scale.set(1, height, 1);
      matrix.compose(position, quaternion.setFromEuler(rotation), scale);
      stems.current?.setMatrixAt(i, matrix);
      stems.current?.setColorAt(i, new THREE.Color("#3f6e24"));

      // 2. Capas de hojas (inferior, media, superior)
      [lower, middle, upper].forEach((ref, layer) => {
        position.set(x, height * (0.32 + layer * 0.24), z);
        rotation.set(0, turn + (layer * Math.PI) / 2, (stress ?? 0) * 0.22);
        const horizontal = leafScale * (layer === 2 ? 0.72 : 1);
        scale.set(horizontal, horizontal, horizontal * (0.55 + height * 0.28));
        matrix.compose(position, quaternion.setFromEuler(rotation), scale);
        ref.current?.setMatrixAt(i, matrix);
        ref.current?.setColorAt(i, leafColor);
      });

      // 3. Panojas apicales masculinas en etapa reproductiva
      const isRepro = maizeReproductive(stage);
      position.set(x, height - (isRepro ? 0.08 : 0), z);
      rotation.set(0, turn, 0);
      const tasselSize = isRepro ? 0.75 : 0.001;
      scale.set(tasselSize, tasselSize, tasselSize);
      matrix.compose(position, quaternion.setFromEuler(rotation), scale);
      tassels.current?.setMatrixAt(i, matrix);
    }

    [stems, lower, middle, upper, tassels].forEach((ref) => {
      if (ref.current) {
        ref.current.instanceMatrix.needsUpdate = true;
        if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      }
    });
  }, [heightM, lai, cover, stress, stage, count, columns, rows]);

  // Animación continua de ola de viento travelling sobre el dosel vegetal
  useFrame(({ clock }) => {
    if (!middle.current || !upper.current || baseData.current.positions.length < count) return;
    const time = clock.getElapsedTime();
    const windSpeed = 2.4;
    const windStrength = 0.055 * (1 + (stress ?? 0) * 0.45);

    const matrix = new THREE.Matrix4();
    const pos = new THREE.Vector3();
    const rot = new THREE.Euler();
    const scl = new THREE.Vector3();
    const q = new THREE.Quaternion();

    const height = Math.max(0.05, Math.min(3.4, heightM));
    const leafScale = Math.max(0.08, Math.min(1.2, lai / 3.8)) *
      (cover === null ? 1 : Math.max(0.1, Math.min(1, cover)));

    for (let i = 0; i < count; i++) {
      const bPos = baseData.current.positions[i];
      const bRot = baseData.current.rotations[i];
      if (!bPos || !bRot) continue;

      const wave = Math.sin(time * windSpeed + bPos.x * 0.42 + bPos.z * 0.32) * windStrength;

      // Actualizar capa superior
      pos.set(bPos.x, height * 0.8, bPos.z);
      rot.set(wave * 0.4, bRot.y + Math.PI + wave, (stress ?? 0) * 0.22 + wave);
      const horizUpper = leafScale * 0.72;
      scl.set(horizUpper, horizUpper, horizUpper * (0.55 + height * 0.28));
      matrix.compose(pos, q.setFromEuler(rot), scl);
      upper.current.setMatrixAt(i, matrix);

      // Actualizar capa media
      pos.set(bPos.x, height * 0.56, bPos.z);
      rot.set(wave * 0.25, bRot.y + Math.PI / 2 + wave * 0.6, (stress ?? 0) * 0.22 + wave * 0.5);
      scl.set(leafScale, leafScale, leafScale * (0.55 + height * 0.28));
      matrix.compose(pos, q.setFromEuler(rot), scl);
      middle.current.setMatrixAt(i, matrix);
    }

    middle.current.instanceMatrix.needsUpdate = true;
    upper.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <group data-testid="rich-field-canopy">
      <instancedMesh ref={stems} args={[undefined, undefined, count]} castShadow>
        <cylinderGeometry args={[0.022, 0.038, 1, 8]} />
        <meshPhysicalMaterial roughness={0.4} clearcoat={0.35} />
      </instancedMesh>
      {[
        [lower, leafGeoA],
        [middle, leafGeoB],
        [upper, leafGeoC],
      ].map(([ref, geometry], index) => (
        <instancedMesh
          key={index}
          ref={ref as React.RefObject<THREE.InstancedMesh>}
          args={[geometry as THREE.BufferGeometry, undefined, count]}
          castShadow
          receiveShadow
        >
          <meshPhysicalMaterial
            side={THREE.DoubleSide}
            roughness={0.28}
            clearcoat={0.72}
            clearcoatRoughness={0.18}
          />
        </instancedMesh>
      ))}
      <instancedMesh ref={tassels} args={[undefined, undefined, count]} castShadow>
        <coneGeometry args={[0.08, 0.32, 6]} />
        <meshStandardMaterial color="#e5ce79" roughness={0.55} />
      </instancedMesh>
    </group>
  );
}

export default function FieldPlotMesh3D({
  scene,
  onSelectPlant,
  showSensors = true,
  showScientificLabels = true,
  showHydrologyFlow = true,
}: Props) {
  const reference = scene === null;
  const [showReferenceCanopy, setShowReferenceCanopy] = useState(false);

  // La vegetación científica se dibuja cuando fieldCanopyAvailable es verdadero;
  // En HYDROLOGY_ONLY o DATA_UNAVAILABLE el usuario puede activar explícitamente vegetación ilustrativa.
  const scientificCropAvailable = fieldCanopyAvailable(scene);
  const showCrop = scientificCropAvailable || (showReferenceCanopy && !reference);

  const height = reference || showReferenceCanopy ? 2.1 : scene?.fieldHeightM ?? null;
  const lai = reference || showReferenceCanopy ? 3.5 : scene?.fieldLai ?? null;

  const soilColor = scene?.soilMoisturePercent === null || !scene
    ? "#422b18"
    : new THREE.Color("#53351c").lerp(
        new THREE.Color("#22140a"),
        Math.max(0, Math.min(1, scene.soilMoisturePercent / 45))
      );

  const sampleMarkers = scene?.cropActive && scene.cropSupported ? scene.record.plant_samples : [];
  const selectedPlantId = scene?.sample?.plant_id ?? null;

  return (
    <group position={[0, -0.12, 0]}>
      {/* 1. Suelo Agrícola Mollisol de Iowa con reactividad a humedad de matriz */}
      <mesh receiveShadow rotation-x={-Math.PI / 2}>
        <planeGeometry args={[24, 24, 32, 32]} />
        <meshStandardMaterial color={soilColor} roughness={0.85} />
      </mesh>

      {/* 2. Surcos Agrícolas Continuos con rastrojo protector (Siembra directa) */}
      {Array.from({ length: 26 }, (_, row) => (
        <group key={row} position={[0, 0.012, (row - 12.5) * 0.82]}>
          <mesh rotation-x={-Math.PI / 2}>
            <planeGeometry args={[22.5, 0.16]} />
            <meshStandardMaterial color="#170c06" roughness={0.8} />
          </mesh>
          <mesh rotation-x={-Math.PI / 2} position={[0, 0.005, 0.38]}>
            <planeGeometry args={[22, 0.32]} />
            <meshStandardMaterial color="#8a7650" transparent opacity={0.82} roughness={0.88} />
          </mesh>
        </group>
      ))}

      {/* 3. Población de maíz instanciada (1,014 plantas) con PBR y física de viento */}
      {showCrop && height !== null && lai !== null && (
        <RichCanopy
          heightM={height}
          lai={lai}
          cover={reference || showReferenceCanopy ? null : scene!.canopyCover}
          stress={reference || showReferenceCanopy ? null : scene!.stress}
          stage={reference || showReferenceCanopy ? "REPRODUCTIVE" : scene!.record.crop?.phenological_stage ?? null}
        />
      )}

      {/* 4. Instrumentación micrometeorológica y sensores contextuales */}
      {showSensors && (
        <>
          <EddyCovarianceTower position={[-9.5, 0, -8.5]} />
          <SoilMoistureProbeStation
            position={[8.2, 0, 7.5]}
            label="Sonda contextual Hondonada"
            valuePercent={scene?.soilMoisturePercent !== null && scene?.soilMoisturePercent !== undefined ? scene.soilMoisturePercent + 2.5 : null}
          />
          <SoilMoistureProbeStation
            position={[-7.5, 0, 8.2]}
            label="Sonda contextual Loma"
            valuePercent={scene?.soilMoisturePercent !== null && scene?.soilMoisturePercent !== undefined ? Math.max(0, scene.soilMoisturePercent - 2.8) : null}
          />
        </>
      )}

      {/* 5. Marcadores de muestras individuales FSPM persistidas con baliza luminosa */}
      {sampleMarkers.map((sample) => {
        if (!Number.isFinite(sample.x_m) || !Number.isFinite(sample.y_m)) return null;
        const posX = sample.x_m - 11.6;
        const posZ = sample.y_m - 3.1;
        const isSelected = selectedPlantId === sample.plant_id;

        return (
          <group key={sample.plant_id} position={[posX, 0.035, posZ]}>
            {/* Anillo de detección en suelo */}
            <mesh
              rotation-x={-Math.PI / 2}
              onClick={(event) => {
                event.stopPropagation();
                onSelectPlant(sample.plant_id);
              }}
            >
              <ringGeometry args={[isSelected ? 0.32 : 0.2, isSelected ? 0.48 : 0.3, 32]} />
              <meshBasicMaterial color={isSelected ? "#10b981" : "#06b6d4"} side={THREE.DoubleSide} />
            </mesh>

            {/* Baliza vertical luminosa que señala la muestra seleccionada */}
            {isSelected && (
              <Line
                points={[
                  [0, 0, 0],
                  [0, (height ?? 1.8) + 0.9, 0],
                ]}
                color="#34d399"
                lineWidth={3.0}
              />
            )}

            {/* Rótulo interactivo de la muestra */}
            {showScientificLabels && (
              <Html position={[0, isSelected ? (height ?? 1.8) + 1.1 : 0.45, 0]} center distanceFactor={10}>
                {isSelected ? (
                  <div className="flex flex-col items-center gap-1.5 rounded-xl border border-emerald-400/80 bg-zinc-950/95 p-2.5 font-sans text-xs text-zinc-100 shadow-2xl backdrop-blur-md whitespace-nowrap">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-300">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
                      <span>Muestra FSPM {sample.plant_id}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-2 text-[10px] font-mono text-zinc-300">
                      <span>Alt: <b>{sample.variables.height_m?.value !== null ? `${Number(sample.variables.height_m?.value).toFixed(2)}m` : "Sin dato"}</b></span>
                      <span>LAI: <b>{sample.variables.lai?.value !== null ? Number(sample.variables.lai?.value).toFixed(2) : "Sin dato"}</b></span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPlant(sample.plant_id);
                      }}
                      className="mt-1 cursor-pointer rounded-lg bg-emerald-600/90 hover:bg-emerald-500 px-2.5 py-1 text-[10px] font-bold text-white transition text-center"
                    >
                      Analizar FSPM Individual (Micro) →
                    </button>
                  </div>
                ) : (
                  <button
                    className="rounded border border-cyan-400/60 bg-zinc-950/90 px-2 py-0.5 text-[9px] font-mono text-cyan-200 hover:border-emerald-400 hover:text-emerald-200 transition"
                    onClick={() => onSelectPlant(sample.plant_id)}
                  >
                    {sample.plant_id}
                  </button>
                )}
              </Html>
            )}
          </group>
        );
      })}

      {/* 6. Lluvia volumétrica meso sobre el cultivo */}
      {showHydrologyFlow && scene?.rainMm !== null && scene?.rainMm !== undefined && scene.rainIntensity !== null && scene.rainMm > 0 && (
        <MesoRainSystem precipMm={scene.rainMm} />
      )}

      {/* 7. Tarjeta Informativa Científica de la Parcela Meso */}
      {showScientificLabels && (
        <Html position={[-10.8, 4.2, -9.5]} distanceFactor={18}>
          <div className="w-68 rounded-xl border border-teal-400/50 bg-zinc-950/95 p-3.5 text-xs text-zinc-100 shadow-2xl backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-teal-500/30 pb-1.5">
              <b className="text-teal-300">
                {reference
                  ? "Parcela de referencia · ilustrativa"
                  : showReferenceCanopy
                  ? "Parcela con vegetación de referencia · ilustrativa"
                  : `Campo FSPM · ${scene.record.date}`}
              </b>
              <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[10px] font-mono text-teal-300">
                Meso
              </span>
            </div>

            <p className="mt-1.5 text-zinc-300">
              {reference
                ? "Vegetación y surcos contextuales"
                : showReferenceCanopy
                ? "Cultivo de referencia ilustrativo (sin FSPM acoplado en esta corrida)"
                : scene.cropActive
                ? `${scene.record.crop?.crop ?? "Cultivo"} · ${scene.record.crop?.phenological_stage ?? "Etapa no disponible"}`
                : "Sin cultivo activo"}
            </p>

            {!reference && scene.cropActive && !scene.cropSupported && (
              <p className="text-amber-300 text-[11px] mt-1">Geometría de este cultivo no disponible.</p>
            )}
            {!reference && scene.cropActive && scene.cropSupported && !scientificCropAvailable && !showReferenceCanopy && (
              <p className="text-amber-300 text-[11px] mt-1">Altura o LAI no disponibles.</p>
            )}

            <div className="mt-2 space-y-0.5 text-[11px] font-mono text-zinc-300">
              <div>
                <span className="text-zinc-400">LAI:</span>{" "}
                <b className="text-emerald-300">
                  {reference || showReferenceCanopy ? "Referencia visual" : lai === null ? "No disponible" : lai.toFixed(2)}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Altura:</span>{" "}
                <b className="text-emerald-300">
                  {reference || showReferenceCanopy ? "Referencia visual" : height === null ? "No disponible" : `${height.toFixed(2)} m`}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Población gráfica:</span>{" "}
                <span className="text-teal-200">1,014 plantas instanciadas</span>
              </div>
            </div>

            <p className="mt-2 text-[10px] text-zinc-400">
              Las instancias son vegetación decorativa; {sampleMarkers.length} muestras FSPM persistidas con ID propio.
            </p>

            {scene?.record.crop?.window_status === "APPROXIMATE_PLANTING_WINDOW" && (
              <p className="text-amber-300 text-[10px] mt-1">Ventana agrícola aproximada por PHU.</p>
            )}

            {/* Opción para activar/desactivar vegetación de referencia en simulaciones sin FSPM */}
            {!reference && !scientificCropAvailable && (
              <div className="mt-2.5 pt-2 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowReferenceCanopy((prev) => !prev)}
                  className={`w-full rounded-lg px-2.5 py-1 text-[11px] font-bold transition text-center ${
                    showReferenceCanopy
                      ? "bg-amber-800/50 hover:bg-amber-700/60 text-amber-200 border border-amber-600/40"
                      : "bg-cyan-700/60 hover:bg-cyan-600 text-white"
                  }`}
                >
                  {showReferenceCanopy
                    ? "Ocultar vegetación de referencia"
                    : "Activar vegetación de referencia (ilustrativa) →"}
                </button>
              </div>
            )}

            {scene?.sample && (
              <button
                className="mt-2 block w-full rounded bg-emerald-700/40 hover:bg-emerald-700/60 py-1 text-center text-[11px] font-bold text-emerald-200 transition"
                onClick={() => onSelectPlant(scene.sample!.plant_id)}
              >
                Ver muestra {scene.sample.plant_id} (Micro) →
              </button>
            )}

            {reference && (
              <button
                className="mt-2 block w-full rounded bg-emerald-700/40 hover:bg-emerald-700/60 py-1 text-center text-[11px] font-bold text-emerald-200 transition"
                onClick={() => onSelectPlant()}
              >
                Explorar planta de referencia →
              </button>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

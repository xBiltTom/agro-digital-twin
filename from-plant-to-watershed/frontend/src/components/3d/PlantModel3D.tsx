"use client";

import { useState } from "react";
import { Html } from "@react-three/drei";
import type { SceneState } from "../../lib/playback-scene";
import { maizeFromScene, maizeReproductive, REFERENCE_MAIZE } from "../../lib/visual-state";
import {
  MicroRainSystem,
  PhysiologicalFlowDynamics,
  RealisticBraceRoots,
  RealisticMaizeEar,
  RealisticMaizeLeaf,
  RealisticMaizeTassel,
  SoilGridsStratigraphyCutout,
} from "./MaizeVisuals3D";

interface Props {
  scene: SceneState | null;
  showSoilHorizons?: boolean;
  showScientificLabels?: boolean;
  showHydrologyFlow?: boolean;
}

/** The sample's measured/modelled height maps directly to scene metres; leaf anatomy is illustrative. */
export default function PlantModel3D({
  scene,
  showSoilHorizons = true,
  showScientificLabels = true,
  showHydrologyFlow = true,
}: Props) {
  const [showReferencePlant, setShowReferencePlant] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const plant = maizeFromScene(scene);

  // If no sample is available in the scientific record, allow explicit exploration of reference maize
  const isDisplayingReference = plant.reference || (plant.heightM === null && showReferencePlant);
  const activePlant = isDisplayingReference ? REFERENCE_MAIZE : plant;

  const height = activePlant.heightM === null ? null : Math.max(0.05, Math.min(3.4, activePlant.heightM));
  const lai = activePlant.lai;
  const stress = activePlant.stress;

  // Utilizar el número de hojas simulado por FSPM cuando esté disponible; de lo contrario, estimar según LAI
  const simulatedLeafCount = activePlant.leafCount;
  const leafCount = simulatedLeafCount !== null && Number.isFinite(simulatedLeafCount) && simulatedLeafCount > 0
    ? Math.max(1, Math.min(24, Math.round(simulatedLeafCount)))
    : lai === null || lai <= 0 ? 0 : Math.max(2, Math.min(18, Math.round(lai * 2.7 + 2)));

  const leaves = height === null ? [] : Array.from({ length: leafCount }, (_, i) => {
    const t = (i + 1) / (leafCount + 1);
    const spread = activePlant.leafAreaM2 && activePlant.leafCount && activePlant.leafCount > 0
      ? Math.min(1.2, Math.max(0.1, Math.sqrt(activePlant.leafAreaM2 / activePlant.leafCount) * 1.8))
      : Math.min(1, Math.max(0.08, (lai ?? 0) / 4));
    const length = (0.28 + 1.14 * Math.sin(Math.PI * t)) * spread;
    return {
      angle: i * Math.PI * 0.94 + (i % 2 === 0 ? 0.08 : -0.06),
      nodeHeight: height * t,
      length,
      width: (0.045 + 0.14 * Math.sin(Math.PI * t)) * spread,
      rise: length * (0.23 - t * 0.06),
      droop: length * (0.16 + (stress ?? 0) * 0.46 + t * 0.1),
    };
  });

  const reproductive = maizeReproductive(activePlant.stage);
  const showRain = Boolean(scene && showHydrologyFlow && scene.rainIntensity !== null && scene.rainMm !== null && scene.rainMm > 0);
  const rootDepthM = activePlant.rootDepthM ?? (isDisplayingReference ? 1.0 : null);
  const transpirationVal = activePlant.transpirationMmDay ?? (isDisplayingReference ? 1.4 : null);

  return (
    <group position={[0, -0.18, 0]}>
      {/* 1. Perfil estratigráfico del suelo (Ap, Bt, C) con brillo óptico según humedad volumétrica */}
      {showSoilHorizons && (
        <SoilGridsStratigraphyCutout
          soilMoistureVol={activePlant.soilMoisturePercent}
          rootDepthCm={rootDepthM !== null ? rootDepthM * 100 : null}
        />
      )}

      {/* 2. Modelo anatómico del maíz Zea mays L. */}
      {height !== null && height > 0 && (
        <group data-testid="detailed-maize-plant">
          {/* Tallo 3D con nudos anulares y curvatura bajo estrés de sequía */}
          <group rotation-z={stress !== null && stress > 0.35 ? (stress - 0.35) * 0.15 : 0}>
            {/* Tallo ahusado principal */}
            <mesh castShadow position={[0, height / 2, 0]}>
              <cylinderGeometry args={[0.024 + Math.min(0.015, height * 0.008), 0.038 + Math.min(0.02, height * 0.012), height, 20]} />
              <meshPhysicalMaterial
                color={stress !== null && stress > 0.4 ? "#6b7a2d" : "#4f7d2c"}
                roughness={0.38}
                clearcoat={0.35}
                clearcoatRoughness={0.22}
              />
            </mesh>

            {/* Nudos anulares y vainas foliares a lo largo del tallo */}
            {leaves.map((leaf, nodeIdx) => (
              <mesh key={`node-${nodeIdx}`} position={[0, leaf.nodeHeight, 0]} rotation-x={Math.PI / 2} castShadow>
                <torusGeometry args={[0.038 + (1 - (nodeIdx / leafCount)) * 0.012, 0.011, 8, 22]} />
                <meshStandardMaterial
                  color={stress !== null && stress > 0.4 ? "#7a8536" : "#689639"}
                  roughness={0.55}
                />
              </mesh>
            ))}
          </group>

          {/* Hojas phyllotáxicas curvas con nervadura central, textura cuticular y física de viento */}
          {leaves.map((leaf, i) => (
            <RealisticMaizeLeaf key={i} {...leaf} stress={stress ?? 0} />
          ))}

          {/* Raíces adventicias de anclaje (brace roots) y red radicular subterránea */}
          {rootDepthM !== null && rootDepthM > 0 && (
            <RealisticBraceRoots
              rootDepthCm={rootDepthM * 100}
              stemHeight={height}
            />
          )}

          {/* Estructuras reproductivas: mazorca con sedas doradas y panoja apical masculina */}
          {reproductive && (
            <>
              <RealisticMaizeEar nodeY={height * 0.46} angle={Math.PI * 0.42} />
              <RealisticMaizeTassel apexY={height} />
            </>
          )}

          {/* Dinámica fisiológica: savia xilemática en ascenso y vapor de transpiración ilustrativos */}
          {showHydrologyFlow && transpirationVal !== null && (
            <PhysiologicalFlowDynamics
              transpirationMm={transpirationVal}
              cwsiStress={stress ?? 0}
              stemHeight={height}
            />
          )}
        </group>
      )}

      {/* 3. Lluvia volumétrica activa a escala micro */}
      {showRain && <MicroRainSystem precipMm={scene!.rainMm!} />}

      {/* 4. Tarjeta Informativa Científica de la Planta FSPM */}
      {showScientificLabels && (
        <Html
          position={[
            height !== null && height < 0.9 ? 0.9 : 1.5,
            height !== null && height < 0.9 ? 0.6 : 2.4,
            0,
          ]}
          distanceFactor={1.8}
        >
          <div className="w-72 rounded-xl border border-emerald-500/40 bg-zinc-950/95 p-3.5 text-xs text-zinc-100 shadow-2xl backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-emerald-500/30 pb-1.5">
              <span className="font-bold text-emerald-300">
                {isDisplayingReference ? "Maíz de referencia · ilustrativo" : `Muestra FSPM ${plant.sampleId ?? "no disponible"}`}
              </span>
              <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-mono text-emerald-300">
                Micro
              </span>
            </div>
            <div className="mt-1.5 text-[11px] font-mono text-zinc-300">
              {scene?.record.date ?? "Sin fecha científica"} · {isDisplayingReference ? "Anatomía reproductiva ilustrativa" : plant.stage ?? "Etapa no disponible"}
            </div>

            {/* Calendario y HRUs asociadas */}
            {!isDisplayingReference && (plant.calendarId || plant.hruIds.length > 0) && (
              <div className="mt-1 rounded bg-zinc-900/80 px-2 py-1 text-[10px] font-mono text-zinc-400">
                <div>Calendario: <span className="text-zinc-200">{plant.calendarId ?? "General"}</span></div>
                {plant.hruIds.length > 0 && (
                  <div>HRUs asociadas: <span className="text-teal-300">{plant.hruIds.join(", ")}</span></div>
                )}
              </div>
            )}

            <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px] font-mono">
              <div>
                <span className="text-zinc-400">Altura:</span>{" "}
                <b className="text-emerald-300">
                  {isDisplayingReference ? "Referencia visual" : height === null ? "No disponible" : `${height.toFixed(2)} m`}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">LAI:</span>{" "}
                <b className="text-emerald-300">
                  {isDisplayingReference ? "Referencia visual" : lai === null ? "No disponible" : lai.toFixed(2)}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Hojas:</span>{" "}
                <b className="text-emerald-300">
                  {isDisplayingReference ? "16 (ref)" : plant.leafCount !== null ? `${Math.round(plant.leafCount)} (sim)` : "Aprox."}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Área foliar:</span>{" "}
                <b className="text-teal-300">
                  {isDisplayingReference ? "Referencia" : plant.leafAreaM2 !== null ? `${plant.leafAreaM2.toFixed(3)} m²` : "No disponible"}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Raíz:</span>{" "}
                <b className="text-teal-300">
                  {isDisplayingReference ? "Referencia visual" : plant.rootDepthM === null ? "No disponible" : `${plant.rootDepthM.toFixed(2)} m`}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Biomasa:</span>{" "}
                <b className="text-emerald-300">
                  {isDisplayingReference ? "Referencia" : plant.biomassG !== null ? `${plant.biomassG.toFixed(1)} g` : "No disponible"}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Estrés:</span>{" "}
                <b className={stress !== null && stress > 0.4 ? "text-amber-400" : "text-emerald-300"}>
                  {stress === null ? "No disponible" : stress.toFixed(2)}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Transpiración:</span>{" "}
                <b className="text-cyan-300">
                  {transpirationVal === null ? "No disponible" : `${transpirationVal.toFixed(2)} mm/d`}
                </b>
              </div>
            </div>

            {/* Toggle para inspeccionar detalles científicos sin saturar */}
            <button
              type="button"
              onClick={() => setShowDetails((prev) => !prev)}
              className="mt-2 text-[10px] text-cyan-400 hover:text-cyan-300 underline font-mono cursor-pointer"
            >
              {showDetails ? "▲ Ocultar procedencia" : "▼ Ver procedencia y limitaciones"}
            </button>

            {showDetails && (
              <div className="mt-1.5 space-y-1 rounded bg-zinc-900/90 p-2 text-[10px] font-mono text-zinc-300 border border-zinc-800">
                <div>
                  <span className="text-zinc-400">Humedad de suelo:</span>{" "}
                  <b className="text-teal-300">
                    {activePlant.soilMoisturePercent !== null ? `${activePlant.soilMoisturePercent.toFixed(2)} %` : "No disponible"}
                  </b>
                  <p className="text-[9px] text-amber-300/90 mt-0.5">Estimación derivada del perfil SWAT+, no medición por capa.</p>
                </div>
                {scene?.sample && (
                  <div className="text-[9px] text-zinc-400">
                    Fuente: <span className="text-cyan-300">{scene.sample.variables.height_m?.source ?? "PlantPopulation"}</span> (Evidencia: {scene.sample.variables.height_m?.evidence ?? "SIMPLIFIED_FSPM"})
                  </div>
                )}
                <div className="text-[9px] text-zinc-400 border-t border-zinc-800 pt-1">
                  Órganos anatómicos (hojas, mazorca, raíces laterales) son representación geométrica ilustrativa gobernada por variables de estado.
                </div>
              </div>
            )}

            {!scene && <p className="mt-1 text-amber-300 text-[10px]">Sin trayectoria individual persistida.</p>}

            {scene && !scene.sample && (
              <div className="mt-1.5 rounded bg-amber-950/40 border border-amber-500/30 p-2 text-[10px] text-amber-300">
                {scene.record.plant_samples.length > 0 ? (
                  <p>La muestra seleccionada no está activa en esta fecha (su grupo de calendario fue cosechado o no ha iniciado). Hay {scene.record.plant_samples.length} muestras de otros calendarios en la escena.</p>
                ) : (
                  <p>Fuera de la temporada de cultivo FSPM: no hay plantas activas en esta fecha.</p>
                )}
              </div>
            )}

            {/* Toggle de exploración explícita de planta de referencia cuando no hay muestra */}
            {scene && !scene.sample && (
              <button
                type="button"
                onClick={() => setShowReferencePlant((prev) => !prev)}
                className="mt-2 w-full cursor-pointer rounded-lg bg-emerald-700/60 hover:bg-emerald-600 px-2 py-1 text-[11px] font-bold text-white transition text-center"
              >
                {showReferencePlant ? "Ocultar maqueta de referencia" : "Explorar maíz de referencia (ilustrativo) →"}
              </button>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

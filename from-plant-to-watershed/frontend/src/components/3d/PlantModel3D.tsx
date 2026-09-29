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
  const plant = maizeFromScene(scene);

  // If no sample is available in the scientific record, allow explicit exploration of reference maize
  const isDisplayingReference = plant.reference || (plant.heightM === null && showReferencePlant);
  const activePlant = isDisplayingReference ? REFERENCE_MAIZE : plant;

  const height = activePlant.heightM === null ? null : Math.max(0.05, Math.min(3.4, activePlant.heightM));
  const lai = activePlant.lai;
  const stress = activePlant.stress;
  const leafCount = lai === null || lai <= 0 ? 0 : Math.max(2, Math.min(18, Math.round(lai * 2.7 + 2)));

  const leaves = height === null ? [] : Array.from({ length: leafCount }, (_, i) => {
    const t = (i + 1) / (leafCount + 1);
    const spread = Math.min(1, Math.max(0.08, (lai ?? 0) / 4));
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
          <div className="w-68 rounded-xl border border-emerald-500/40 bg-zinc-950/95 p-3.5 text-xs text-zinc-100 shadow-2xl backdrop-blur-md">
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
                <span className="text-zinc-400">Raíz:</span>{" "}
                <b className="text-teal-300">
                  {isDisplayingReference ? "Referencia visual" : plant.rootDepthM === null ? "No disponible" : `${plant.rootDepthM.toFixed(2)} m`}
                </b>
              </div>
              <div>
                <span className="text-zinc-400">Estrés:</span>{" "}
                <b className={stress !== null && stress > 0.4 ? "text-amber-400" : "text-emerald-300"}>
                  {stress === null ? "No disponible" : stress.toFixed(2)}
                </b>
              </div>
              <div className="col-span-2">
                <span className="text-zinc-400">Transpiración:</span>{" "}
                <b className="text-cyan-300">
                  {transpirationVal === null ? "No disponible" : `${transpirationVal.toFixed(2)} mm/día`}
                </b>
              </div>
            </div>

            {scene?.sample && (
              <div className="mt-1.5 text-[10px] text-cyan-300 font-mono">
                {scene.sample.variables.height_m?.evidence ?? "NOT_AVAILABLE"} · {scene.sample.variables.height_m?.source ?? "Sin fuente"}
              </div>
            )}

            <div className="mt-1.5 text-[10px] text-zinc-400">
              Hojas, mazorca, raíces laterales y perfil del suelo son ilustrativos.
            </div>

            {!scene && <p className="mt-1 text-amber-300 text-[10px]">Sin trayectoria individual persistida.</p>}

            {scene && !scene.sample && (
              <p className="mt-1 text-amber-300 text-[10px]">Esta corrida/fecha no contiene muestra FSPM activa.</p>
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

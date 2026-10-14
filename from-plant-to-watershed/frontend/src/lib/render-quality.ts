/** Rendering budgets only: these must never change scientific playback values. */
export type RenderQuality = "FAST" | "BALANCED" | "DETAIL";
export const RENDER_QUALITY = {
  FAST: { label: "Fluida", maxDpr: 1, shadowSize: 512, contactShadows: false, effects: false },
  BALANCED: { label: "Equilibrada", maxDpr: 1.5, shadowSize: 1024, contactShadows: true, effects: false },
  DETAIL: { label: "Detallada", maxDpr: 2, shadowSize: 2048, contactShadows: true, effects: true },
} as const;

/** Shared by matrix initialization and wind: harvested plants stay hidden. */
export function canopyInstanceActive(rank: number, count: number, fraction: number): boolean {
  const safeFraction = Number.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
  return rank >= 0 && rank < Math.round(safeFraction * count);
}

/** Deterministic visual rain, independent of the scientific precipitation value. */
export function rainStreakPositions(intensity: number): Float32Array {
  const bounded = Number.isFinite(intensity) ? Math.max(0, Math.min(1, intensity)) : 0;
  const count = bounded > 0 ? Math.max(8, Math.floor(bounded * 700)) : 0;
  const positions = new Float32Array(count * 6);
  for (let i = 0; i < count; i++) {
    const x = (((i * 73) % 701) / 701 - 0.5) * 42;
    const y = ((i * 47) % 211) / 211 * 20;
    const z = (((i * 137) % 709) / 709 - 0.5) * 32;
    positions.set([x, y, z, x, y - 0.4, z], i * 6);
  }
  return positions;
}

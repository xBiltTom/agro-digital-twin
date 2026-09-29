import type { SimulationRun } from "../types/simulation";

export type SimulationEvidenceClass =
  | "SIMPLIFIED"
  | "SWAT_EXECUTED"
  | "COUPLED_EXECUTED"
  | "HISTORICAL_IMPORT"
  | "UNKNOWN";

const LEGACY_SOUTH_FORK_EXPERIMENT_ID = "south-fork-final-coupled-2015-2020";

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

/** Mirrors the backend provenance precedence so imported evidence is never presented as a fresh execution. */
export function classifySimulationEvidence(simulation: SimulationRun): SimulationEvidenceClass {
  const provenance = asRecord(simulation.provenance);
  const requested = asRecord(simulation.requested_config);
  const requestedSwat = asRecord(requested.swat_plus);
  const effective = asRecord(simulation.effective_config);
  const metrics = asRecord(simulation.summary_metrics);
  const experiment = asRecord(provenance.experiment);
  const lineage = asRecord(provenance.lineage);
  const experimentIds = [
    provenance.experiment_id,
    experiment.experiment_id,
    experiment.id,
    lineage.experiment_id,
    requestedSwat.experiment_id,
    effective.experiment_id,
    metrics.experiment_id,
  ];

  if (
    provenance.source_kind === "HISTORICAL_IMPORT" ||
    experimentIds.some((value) => value === LEGACY_SOUTH_FORK_EXPERIMENT_ID)
  ) {
    return "HISTORICAL_IMPORT";
  }

  if (provenance.evidence_type === "REAL_SWAT_PLUS_COUPLED") return "COUPLED_EXECUTED";
  if (provenance.evidence_type === "REAL_SWAT_PLUS") return "SWAT_EXECUTED";

  const hydrology = asRecord(provenance.hydrology);
  const plant = asRecord(provenance.plant);
  if (
    simulation.hydrology_backend === "SIMPLIFIED" ||
    provenance.source_kind === "SIMPLIFIED" ||
    [provenance.run_evidence_type, provenance.evidence_type].some((value) => value === "DEMO" || value === "SIMPLIFIED") ||
    hydrology.model === "SimplifiedHydrologyModel" ||
    plant.model === "SimplifiedPlantModel"
  ) {
    return "SIMPLIFIED";
  }

  return "UNKNOWN";
}

export function simulationEvidenceLabel(evidence: SimulationEvidenceClass): string {
  switch (evidence) {
    case "SIMPLIFIED": return "Motor simplificado";
    case "SWAT_EXECUTED": return "SWAT+ ejecutado · línea base";
    case "COUPLED_EXECUTED": return "SWAT+ ejecutado · acoplado";
    case "HISTORICAL_IMPORT": return "SWAT+ importado";
    default: return "Procedencia no confirmada";
  }
}

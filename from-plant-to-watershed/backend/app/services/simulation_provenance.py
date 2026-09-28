"""Shared classification of persisted simulation origin and evidence."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping


LEGACY_SOUTH_FORK_V2_EXPERIMENT_ID = "south-fork-final-coupled-2015-2020"


class SimulationProvenanceClass(StrEnum):
    SWAT_EXECUTED = "SWAT_EXECUTED"
    COUPLED_EXECUTED = "COUPLED_EXECUTED"
    HISTORICAL_IMPORT = "HISTORICAL_IMPORT"
    SIMPLIFIED = "SIMPLIFIED"
    UNKNOWN = "UNKNOWN"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _experiment_ids(simulation: Any, provenance: Mapping[str, Any]) -> set[str]:
    requested = _mapping(getattr(simulation, "requested_config", None))
    requested_swat = _mapping(requested.get("swat_plus"))
    effective = _mapping(getattr(simulation, "effective_config", None))
    metrics = _mapping(getattr(simulation, "summary_metrics", None))
    experiment = _mapping(provenance.get("experiment"))
    lineage = _mapping(provenance.get("lineage"))
    raw_ids = (
        getattr(simulation, "experiment_id", None),
        provenance.get("experiment_id"),
        experiment.get("experiment_id"),
        experiment.get("id"),
        lineage.get("experiment_id"),
        requested_swat.get("experiment_id"),
        effective.get("experiment_id"),
        metrics.get("experiment_id"),
    )
    return {str(value) for value in raw_ids if value is not None}


def classify_simulation_provenance(simulation_or_provenance: Any) -> SimulationProvenanceClass:
    """Classify a run without relying on its visible name or requested run type.

    Historical provenance wins over inherited evidence labels. In particular,
    the original South Fork v2 row may contain ``REAL_SWAT_PLUS`` even though it
    was imported from a report and was not executed by this service.
    """
    if isinstance(simulation_or_provenance, Mapping):
        simulation = None
        provenance = simulation_or_provenance
    else:
        simulation = simulation_or_provenance
        provenance = _mapping(getattr(simulation, "provenance", None))

    if (provenance.get("source_kind") == "HISTORICAL_IMPORT"
            or LEGACY_SOUTH_FORK_V2_EXPERIMENT_ID in _experiment_ids(simulation, provenance)):
        return SimulationProvenanceClass.HISTORICAL_IMPORT

    evidence_type = provenance.get("evidence_type")
    if evidence_type == "REAL_SWAT_PLUS_COUPLED":
        return SimulationProvenanceClass.COUPLED_EXECUTED
    if evidence_type == "REAL_SWAT_PLUS":
        return SimulationProvenanceClass.SWAT_EXECUTED

    hydrology = _mapping(provenance.get("hydrology"))
    plant = _mapping(provenance.get("plant"))
    known_simplified = (
        provenance.get("source_kind") == "SIMPLIFIED"
        or provenance.get("run_evidence_type") in {"DEMO", "SIMPLIFIED"}
        or evidence_type in {"DEMO", "SIMPLIFIED"}
        or hydrology.get("model") == "SimplifiedHydrologyModel"
        or plant.get("model") == "SimplifiedPlantModel"
    )
    if known_simplified:
        return SimulationProvenanceClass.SIMPLIFIED
    return SimulationProvenanceClass.UNKNOWN


def public_origin(provenance_class: SimulationProvenanceClass) -> str:
    """Keep the legacy coarse origin enum stable while exposing the exact class."""
    if provenance_class is SimulationProvenanceClass.HISTORICAL_IMPORT:
        return "HISTORICAL_IMPORT"
    if provenance_class is SimulationProvenanceClass.UNKNOWN:
        return "UNKNOWN"
    return "EXECUTED"

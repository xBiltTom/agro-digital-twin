"""Pure, dependency-free scientific models used by the application layer."""

from .config import RunConfig
from .pipeline import MultiscaleRun, MultiscaleSimulationOrchestrator, SimulationOrchestrator, ScientificRun
from .provenance import EvidenceType, Provenance
from .multiscale import FieldToHRUCoupler, PlantPopulation, PlantState, PlantToFieldAggregator
from .validation import ValidationEngine
from .splits import assign_temporal_split, validate_spatial_split

__all__ = ["EvidenceType", "Provenance", "RunConfig", "ScientificRun", "SimulationOrchestrator",
           "PlantPopulation", "PlantState", "PlantToFieldAggregator", "FieldToHRUCoupler", "ValidationEngine"]
__all__ += ["MultiscaleRun", "MultiscaleSimulationOrchestrator"]
__all__ += ["assign_temporal_split", "validate_spatial_split"]

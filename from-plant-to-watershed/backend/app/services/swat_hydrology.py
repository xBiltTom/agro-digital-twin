"""Deprecated compatibility import; this model does not execute SWAT+."""

from scientific_core.hydrology import SimplifiedHydrologyModel

SWATHydrologyEngine = SimplifiedHydrologyModel

__all__ = ["SimplifiedHydrologyModel", "SWATHydrologyEngine"]

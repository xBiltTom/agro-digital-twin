"""Honest Phase-C contracts for planned datasets; none perform a fake ingestion."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedDatasetContract:
    provider: str
    dataset_name: str
    variable: str
    temporal_resolution: str
    spatial_support: str
    status: str = "NOT_IMPLEMENTED"
    limitation: str = "Provider contract only; no artifact or normalized observation has been ingested."


PLANNED_DATASETS = (
    PlannedDatasetContract("USDA NASS", "Quick Stats / county yield", "maize_yield", "annual", "county", limitation="County support cannot be interpolated to a watershed without a documented crosswalk."),
    PlannedDatasetContract("CHIRPS", "CHIRPS precipitation", "precipitation", "daily", "gridded"),
    PlannedDatasetContract("ISRIC", "SoilGrids 2.0", "soil_properties", "static/versioned", "gridded"),
    PlannedDatasetContract("USGS", "Landsat Collection 2", "land_surface_products", "scene/composite", "raster"),
)

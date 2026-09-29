"""Normalize API playback records into a provenance-preserving daily table."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping, Optional

import pandas as pd


def _state_value(group: Mapping[str, Any], name: str) -> Any:
    state = group.get(name)
    if not isinstance(state, Mapping) or state.get("availability") != "AVAILABLE":
        return None
    return state.get("value")


def playback_records_to_dataframe(
    records: list[Mapping[str, Any]],
    *,
    simulation: Optional[Mapping[str, Any]] = None,
    availability: Optional[Mapping[str, Any]] = None,
    source_label: str = "FastAPI playback",
) -> tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """Flatten one paginated playback response without dropping evidence labels."""
    rows = []
    variable_rows = []
    for record in records:
        weather = record.get("weather") or {}
        hydrology = record.get("hydrology") or {}
        field = record.get("field") or {}
        plant_context = record.get("plant_sample_context") or {}
        row = {
            "date": pd.to_datetime(record.get("date"), errors="raise"),
            "precip_mm": _state_value(weather, "precipitation_mm"),
            "temp_mean_c": _state_value(weather, "temperature_c"),
            "solar_radiation": _state_value(weather, "solar_radiation_mj_m2"),
            "relative_humidity_percent": _state_value(weather, "relative_humidity_percent"),
            "wind_speed_ms": _state_value(weather, "wind_speed_ms"),
            "pet_mm": _state_value(weather, "potential_et_mm"),
            "infiltration_mm": _state_value(hydrology, "percolation_mm"),
            "et_mm": _state_value(hydrology, "evapotranspiration_mm"),
            "runoff_mm": _state_value(hydrology, "runoff_mm"),
            "streamflow_m3s": _state_value(hydrology, "streamflow_m3s"),
            "soil_water_storage_mm": _state_value(hydrology, "soil_water_mm"),
            "soil_water_average_mm": _state_value(hydrology, "soil_water_average_mm"),
            "soil_moisture_derived_percent": _state_value(field, "soil_moisture_vol_percent"),
            "lai": _state_value(field, "lai"),
            "root_depth_m": _state_value(field, "root_depth_m"),
            "transpiration_mm": _state_value(field, "actual_transpiration_mm_day"),
            "water_stress": _state_value(field, "water_stress"),
            "fspm_biomass_g_plant": _state_value(field, "biomass_g_plant"),
            "hru_count": len(record.get("hru_results") or []),
            "channel_count": len(record.get("channel_results") or []),
            "plant_sample_count": int(plant_context.get("captured_count", len(record.get("plant_samples") or []))),
            "watershed_id": record.get("watershed_id"),
            "hru_id": "basin",
            "simulation_id": record.get("simulation_id"),
        }
        rows.append(row)
        for group_name in ("weather", "field", "hydrology"):
            for variable, state in (record.get(group_name) or {}).items():
                if isinstance(state, Mapping):
                    variable_rows.append({
                        "grupo": group_name,
                        "variable": variable,
                        "unidad": state.get("unit"),
                        "evidencia": state.get("evidence"),
                        "origen": state.get("source"),
                        "limitacion": state.get("limitation"),
                    })

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("date").reset_index(drop=True)
    classification = "SIMULATION_API_PLAYBACK"
    provenance_class = (availability or {}).get("provenance_class")
    limitations = list((availability or {}).get("limitations") or [])
    for record in records:
        limitations.extend(record.get("limitations") or [])
    metadata = {
        "dataset_id": (simulation or {}).get("id") or (records[0].get("simulation_id") if records else None),
        "dataset_version": (simulation or {}).get("id") or "api-playback",
        "source_kind": "api_simulation",
        "artifact_classification": classification,
        "is_synthetic_training_data": False,
        "is_observation": False,
        "origin": source_label,
        "simulation_provenance_class": provenance_class or "UNKNOWN",
        "simulation_status": (simulation or {}).get("status"),
        "period": [str(frame["date"].min().date()), str(frame["date"].max().date())] if not frame.empty else None,
        "temporal_resolution": "DAILY",
        "limitations": sorted(set(limitations + [
            "Playback contiene estados modelados; no son observaciones de campo.",
            "La humedad radicular derivada se identifica como estimación y no como medición por capa.",
        ])),
        "simulation": dict(simulation or {}),
        "availability": dict(availability or {}),
        "imported_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    variable_catalog = pd.DataFrame(variable_rows).drop_duplicates().reset_index(drop=True)
    if not frame.empty:
        frame["dataset_id"] = metadata["dataset_id"]
        frame["data_classification"] = classification
        frame["data_provenance"] = source_label
        frame["is_synthetic"] = False
        frame["is_observation"] = False
        frame["temporal_resolution"] = "DAILY"
    return frame, metadata, variable_catalog

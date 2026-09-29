"""Dataset sources exposed by the AI laboratory."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from src.core.datasets.real_loader import (
    default_south_fork_artifact_dir,
    load_real_artifact_dataset,
)
from src.core.datasets.simulation_dataset import playback_records_to_dataframe
from src.core.integrations.fastapi_client import FastAPIClient
from src.core.dataset_generator import get_dataset
from src.core.features.schema import TARGET_REGISTRY, get_default_feature_schema, get_target_schema


SYNTHETIC_SOURCE = "synthetic_demo"
SOUTH_FORK_SOURCE = "south_fork_2019_v3"
API_SOURCE_PREFIX = "api_simulation:"


def configured_real_artifact_dir() -> Path:
    configured = os.environ.get("AGRO_TWIN_ARTIFACT_DIR") or os.environ.get("AGRO_TWIN_REAL_ARTIFACT_DIR")
    return Path(configured).expanduser() if configured else default_south_fork_artifact_dir()


def load_lab_dataset(source: str, artifact_dir: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """Return the learning table, provenance metadata and variable catalog."""
    if source == SYNTHETIC_SOURCE:
        frame = get_dataset()
        metadata = {
            "dataset_id": "synthetic-development-dataset",
            "dataset_version": "v1.0-synthetic-cornbelt",
            "source_kind": "synthetic_demo",
            "artifact_classification": "SYNTHETIC_DEVELOPMENT_ARTIFACT",
            "is_synthetic_training_data": True,
            "is_observation": False,
            "origin": "Plant-to-Watershed synthetic development generator",
            "period": [str(frame["date"].min().date()), str(frame["date"].max().date())],
            "limitations": ["Datos generados para validar la arquitectura; no son observaciones."],
        }
        unit_map = {feature.name: feature.unit for feature in get_default_feature_schema().features}
        unit_map.update({target: get_target_schema(target).unit for target in TARGET_REGISTRY})
        variable_catalog = pd.DataFrame({
            "archivo": "synthetic_generator",
            "variable": frame.columns,
            "unidad": [unit_map.get(column, "n/d") for column in frame.columns],
            "origen": metadata["origin"],
            "escala": "multi-scale synthetic demo",
        })
        return frame, metadata, variable_catalog

    if source != SOUTH_FORK_SOURCE:
        raise ValueError(f"Unknown dataset source: {source}")
    artifact = load_real_artifact_dataset(artifact_dir or configured_real_artifact_dir())
    metadata = dict(artifact.metadata)
    metadata["temporal_resolution"] = "DAILY"
    metadata["imported_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return artifact.build_daily_learning_dataset(), metadata, artifact.variable_summary()


def load_api_simulation_dataset(
    client: FastAPIClient,
    simulation_id: str,
    simulation: Optional[Dict[str, Any]] = None,
):
    """Load one API playback snapshot through the client cache."""
    snapshot = client.get_simulation_snapshot(simulation_id, resolution="DAILY", simulation=simulation)
    return playback_records_to_dataframe(
        list(snapshot["playback"].get("records", [])),
        simulation=snapshot.get("simulation"),
        availability=snapshot.get("availability"),
        source_label="FastAPI playback verificado",
    )


def source_labels() -> Dict[str, str]:
    labels = {SYNTHETIC_SOURCE: "Demo sintética (existente)"}
    artifact_dir = configured_real_artifact_dir()
    if artifact_dir.joinpath("manifest.json").is_file():
        if os.environ.get("AGRO_TWIN_ARTIFACT_DIR") or os.environ.get("AGRO_TWIN_REAL_ARTIFACT_DIR"):
            labels[SOUTH_FORK_SOURCE] = f"Resultados reales configurados ({artifact_dir.name})"
        else:
            labels[SOUTH_FORK_SOURCE] = f"{artifact_dir.name} (resultados simulados SWAT+ / FSPM)"
    return labels

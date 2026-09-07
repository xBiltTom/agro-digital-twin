"""
Reusable Python Inference Service for AgroTwin-AI.
Zero dependency on Streamlit.
Designed to be directly imported by Next.js + FastAPI backend.
"""

import os
from typing import Dict, Any, Optional, Union
import pandas as pd

from .bundle import ModelBundle

_BUNDLE_CACHE: Dict[str, ModelBundle] = {}


def load_model_bundle(artifact_dir: str, use_cache: bool = True) -> ModelBundle:
    """
    Loads and optionally caches a ModelBundle.
    """
    if use_cache and artifact_dir in _BUNDLE_CACHE:
        return _BUNDLE_CACHE[artifact_dir]

    bundle = ModelBundle.load(artifact_dir)
    if use_cache:
        _BUNDLE_CACHE[artifact_dir] = bundle
    return bundle


def predict(
    artifact_dir: str,
    payload: Union[Dict[str, Any], pd.DataFrame]
) -> Dict[str, Any]:
    """
    Executes prediction with the model stored in artifact_dir.
    """
    bundle = load_model_bundle(artifact_dir)
    return bundle.predict(payload)


def validate_features(artifact_dir: str, payload: Dict[str, Any]) -> bool:
    """
    Validates input features against the schema contract stored in the model bundle.
    """
    bundle = load_model_bundle(artifact_dir)
    try:
        bundle.validate_features(payload)
        return True
    except Exception as e:
        raise ValueError(f"Feature validation failed: {e}")


def predict_runoff(
    payload: Dict[str, Any],
    artifact_dir: Optional[str] = None,
    base_artifact_dir: str = "artifacts"
) -> Dict[str, Any]:
    """
    High-level convenience endpoint for predicting monthly runoff.
    Defaults to the champion runoff model.
    """
    target_dir = artifact_dir or os.path.join(base_artifact_dir, "monthly_runoff_mm", "champion")
    if not os.path.exists(target_dir):
        # Fallback to random_forest if champion is not yet copied
        alt_dir = os.path.join(base_artifact_dir, "monthly_runoff_mm", "random_forest")
        if os.path.exists(alt_dir):
            target_dir = alt_dir
        else:
            raise FileNotFoundError(f"No trained runoff model found in {target_dir} or {alt_dir}. Please train models first.")

    return predict(target_dir, payload)


def predict_yield(
    payload: Dict[str, Any],
    artifact_dir: Optional[str] = None,
    base_artifact_dir: str = "artifacts"
) -> Dict[str, Any]:
    """
    High-level convenience endpoint for predicting maize yield.
    Defaults to the champion yield model.
    """
    target_dir = artifact_dir or os.path.join(base_artifact_dir, "maize_yield_t_ha", "champion")
    if not os.path.exists(target_dir):
        alt_dir = os.path.join(base_artifact_dir, "maize_yield_t_ha", "random_forest")
        if os.path.exists(alt_dir):
            target_dir = alt_dir
        else:
            raise FileNotFoundError(f"No trained yield model found in {target_dir} or {alt_dir}. Please train models first.")

    return predict(target_dir, payload)

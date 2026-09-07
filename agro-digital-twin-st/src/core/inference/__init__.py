"""
Inference package for AgroTwin-AI.
Exposes ModelBundle, standalone inference service, and prediction endpoints.
"""

from .bundle import ModelBundle, promote_to_champion
from .service import (
    load_model_bundle,
    predict,
    validate_features,
    predict_runoff,
    predict_yield
)

__all__ = [
    "ModelBundle",
    "promote_to_champion",
    "load_model_bundle",
    "predict",
    "validate_features",
    "predict_runoff",
    "predict_yield"
]

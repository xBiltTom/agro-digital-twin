"""
Feature contracts and preprocessing package for AgroTwin-AI.
"""

from .schema import (
    FeatureDefinition,
    ModelFeatureSchema,
    TargetSchema,
    get_default_feature_schema,
    get_target_schema,
    FEATURE_GROUPS
)
from .preprocessor import MultiScaleDataPreprocessor
from .sequences import build_grouped_temporal_sequences, build_temporal_sequences_from_matrix

__all__ = [
    "FeatureDefinition",
    "ModelFeatureSchema",
    "TargetSchema",
    "get_default_feature_schema",
    "get_target_schema",
    "FEATURE_GROUPS",
    "MultiScaleDataPreprocessor",
    "build_grouped_temporal_sequences",
    "build_temporal_sequences_from_matrix"
]

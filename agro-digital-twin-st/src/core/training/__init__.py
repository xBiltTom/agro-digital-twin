"""
Training package for AgroTwin-AI.
Contains leak-free splitters and multi-scale trainer.
"""

from .splitters import (
    TemporalHoldoutSplitter,
    WatershedHoldoutSplitter,
    TimeSeriesWalkForwardSplitter,
    get_validation_split
)
from .trainer import MultiScaleTrainer, train_models_pipeline

__all__ = [
    "TemporalHoldoutSplitter",
    "WatershedHoldoutSplitter",
    "TimeSeriesWalkForwardSplitter",
    "get_validation_split",
    "MultiScaleTrainer",
    "train_models_pipeline"
]

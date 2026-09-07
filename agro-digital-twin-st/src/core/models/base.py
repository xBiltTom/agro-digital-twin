"""
Abstract Base Model Interface for Multi-Scale AgroTwin-AI Models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np


class BaseMultiScaleModel(ABC):
    """Common interface for traditional, deep learning, and hybrid models."""

    def __init__(self, name: str, model_type: str):
        self.name = name
        self.model_type = model_type  # traditional, deep_learning, hybrid
        self.is_fitted = False
        self.params: Dict[str, Any] = {}

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 25,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "BaseMultiScaleModel":
        """Fits the model onto training data."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generates continuous regression predictions."""
        pass

    @abstractmethod
    def save(self, artifact_dir: str) -> str:
        """Saves model files into artifact_dir. Returns path to main model file."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, artifact_dir: str) -> "BaseMultiScaleModel":
        """Loads model files from artifact_dir."""
        pass

    def get_params(self) -> Dict[str, Any]:
        """Returns hyperparameters and configuration."""
        return self.params

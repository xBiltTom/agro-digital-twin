"""
Preprocessing Pipeline for Multi-Scale Plant-to-Watershed Data.
Encapsulates feature scaling, validation, and serialization with joblib.
Completely independent of Streamlit to allow reuse in FastAPI.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from sklearn.preprocessing import StandardScaler

from .schema import ModelFeatureSchema, get_default_feature_schema


class MultiScaleDataPreprocessor:
    """
    Handles feature validation and standard scaling for traditional and deep learning models.
    """

    def __init__(
        self,
        schema: Optional[ModelFeatureSchema] = None,
        scale_features: bool = True
    ):
        self.schema = schema or get_default_feature_schema()
        self.scale_features = scale_features
        self.scaler = StandardScaler() if scale_features else None
        self.is_fitted = False
        self.feature_names = self.schema.feature_names

    def fit(self, df: pd.DataFrame) -> "MultiScaleDataPreprocessor":
        """Fits the scaler using a validated DataFrame."""
        validated_df = self.schema.validate_dataframe(df)
        X = validated_df.values
        if self.scaler is not None:
            self.scaler.fit(X)
        self.is_fitted = True
        return self

    def transform(self, data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> np.ndarray:
        """Transforms input data to scaled NumPy matrix."""
        if isinstance(data, dict):
            # Single payload
            ordered_vals = self.schema.validate_payload(data)
            X = np.array([ordered_vals], dtype=np.float64)
        elif isinstance(data, list):
            # List of payloads
            rows = [self.schema.validate_payload(d) for d in data]
            X = np.array(rows, dtype=np.float64)
        elif isinstance(data, pd.DataFrame):
            validated_df = self.schema.validate_dataframe(data)
            X = validated_df.values
        elif isinstance(data, np.ndarray):
            if data.ndim == 2:
                if data.shape[1] != len(self.feature_names):
                    raise ValueError(f"Expected {len(self.feature_names)} features, got {data.shape[1]}")
                X = data
            elif data.ndim == 3:
                if data.shape[2] != len(self.feature_names):
                    raise ValueError(f"Expected {len(self.feature_names)} features in last dim, got {data.shape[2]}")
                N, T, F = data.shape
                flat_X = data.reshape(-1, F)
                if self.scaler is not None and self.is_fitted:
                    scaled_flat = self.scaler.transform(flat_X)
                    return scaled_flat.reshape(N, T, F)
                return data
            else:
                raise ValueError(f"Unsupported array ndim: {data.ndim}")
        else:
            raise TypeError(f"Unsupported data type for transform: {type(data)}")

        if self.scaler is not None and self.is_fitted:
            return self.scaler.transform(X)
        return X

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Fits and transforms input DataFrame."""
        self.fit(df)
        return self.transform(df)

    def save(self, filepath: str) -> None:
        """Serializes preprocessor state to disk using joblib."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        payload = {
            "schema_dict": self.schema.to_dict(),
            "scale_features": self.scale_features,
            "scaler": self.scaler,
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names
        }
        joblib.dump(payload, filepath)

    @classmethod
    def load(cls, filepath: str) -> "MultiScaleDataPreprocessor":
        """Deserializes preprocessor state from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Preprocessing artifact not found at: {filepath}")
        payload = joblib.load(filepath)
        schema = ModelFeatureSchema.from_dict(payload["schema_dict"])
        instance = cls(schema=schema, scale_features=payload.get("scale_features", True))
        instance.scaler = payload.get("scaler")
        instance.is_fitted = payload.get("is_fitted", False)
        instance.feature_names = payload.get("feature_names", schema.feature_names)
        return instance

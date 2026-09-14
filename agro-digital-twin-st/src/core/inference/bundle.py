"""
Model Artifact Bundle & Standalone Inference Service for AgroTwin-AI.
CRITICAL ARCHITECTURE REQUIREMENT:
- Complete decoupling from Streamlit.
- Uniform artifact bundle structure:
    model.joblib / model.keras
    preprocessing.joblib
    metadata.json
    metrics.json
    feature_schema.json
- Directly importable and consumable from Next.js + FastAPI backend.
"""

import os
import sys
import json
import shutil
import platform
import joblib
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
import sklearn

from src.core.features.schema import ModelFeatureSchema, get_target_schema, TargetSchema
from src.core.features.preprocessor import MultiScaleDataPreprocessor
from src.core.models.base import BaseMultiScaleModel
from src.core.models.traditional import RandomForestModel, XGBoostModel, SVRModel


class ModelBundle:
    """
    Self-contained model package encapsulating the estimator, preprocessor,
    feature schema, and complete provenance metadata.
    """

    def __init__(
        self,
        artifact_dir: str,
        model: Any,
        preprocessor: MultiScaleDataPreprocessor,
        schema: ModelFeatureSchema,
        metadata: Dict[str, Any],
        metrics: Dict[str, float]
    ):
        self.artifact_dir = artifact_dir
        self.model = model
        self.preprocessor = preprocessor
        self.schema = schema
        self.metadata = metadata
        self.metrics = metrics
        self.target_name = metadata.get("target_name", "monthly_runoff_mm")
        self.mode = metadata.get("learning_mode", "direct")
        self.target_schema = get_target_schema(self.target_name)

    @classmethod
    def save_bundle(
        cls,
        artifact_dir: str,
        model: BaseMultiScaleModel,
        preprocessor: MultiScaleDataPreprocessor,
        schema: ModelFeatureSchema,
        target_name: str,
        learning_mode: str,
        metrics: Dict[str, float],
        validation_strategy: str,
        train_split_desc: str,
        random_seed: int = 42,
        dataset_version: str = "v1.0-synthetic-cornbelt",
        is_champion: bool = False
    ) -> "ModelBundle":
        """
        Creates and writes the complete artifact bundle to disk.
        """
        os.makedirs(artifact_dir, exist_ok=True)

        # 1. Save Preprocessing
        preprocessor_file = os.path.join(artifact_dir, "preprocessing.joblib")
        preprocessor.save(preprocessor_file)

        # 2. Save Feature Schema
        schema_file = os.path.join(artifact_dir, "feature_schema.json")
        with open(schema_file, "w", encoding="utf-8") as f:
            f.write(schema.to_json())

        # 3. Save Metrics
        metrics_file = os.path.join(artifact_dir, "metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        # 4. Save Model Files
        model.save(artifact_dir)

        # 5. Save Metadata
        library_versions = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        }
        try:
            import tensorflow as tf
            library_versions["tensorflow"] = tf.__version__
        except Exception:
            pass
        try:
            import xgboost
            library_versions["xgboost"] = xgboost.__version__
        except Exception:
            pass

        timesteps = getattr(model, "timesteps", None)
        is_sequence_model = timesteps is not None and timesteps > 1

        metadata = {
            "model_name": model.name,
            "model_type": model.model_type,
            "target_name": target_name,
            "learning_mode": learning_mode,  # direct or residual
            "features": schema.feature_names,
            "feature_order": schema.feature_names,
            "is_sequence_model": is_sequence_model,
            "timesteps": timesteps if is_sequence_model else None,
            "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_version": dataset_version,
            "random_seed": random_seed,
            "train_split": train_split_desc,
            "validation_strategy": validation_strategy,
            "metrics": metrics,
            "is_champion": is_champion,
            "is_synthetic_training_data": True,
            "artifact_classification": "SYNTHETIC_DEVELOPMENT_ARTIFACT",
            "deployment_status": "demo_only",
            "data_provenance": "Plant-to-Watershed Multi-Scale Simulator (Zea mays / SWAT+)",
            "library_versions": library_versions
        }

        metadata_file = os.path.join(artifact_dir, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        bundle = cls(
            artifact_dir=artifact_dir,
            model=model,
            preprocessor=preprocessor,
            schema=schema,
            metadata=metadata,
            metrics=metrics
        )
        return bundle

    @classmethod
    def load(cls, artifact_dir: str) -> "ModelBundle":
        """
        Loads the complete artifact bundle from disk.
        Does not require Streamlit.
        """
        if not os.path.exists(artifact_dir):
            raise FileNotFoundError(f"Bundle directory does not exist: {artifact_dir}")

        metadata_file = os.path.join(artifact_dir, "metadata.json")
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(f"Metadata file missing in: {artifact_dir}")
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        # Pre-freeze bundles predate the explicit classification. Preserve their
        # metrics but never let their synthetic training data look observational.
        if metadata.get("is_synthetic_training_data", False):
            metadata.setdefault("artifact_classification", "SYNTHETIC_DEVELOPMENT_ARTIFACT")
            metadata.setdefault("deployment_status", "demo_only")

        metrics_file = os.path.join(artifact_dir, "metrics.json")
        metrics = {}
        if os.path.exists(metrics_file):
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)

        # Load Schema
        schema_file = os.path.join(artifact_dir, "feature_schema.json")
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = ModelFeatureSchema.from_json(f.read())

        # Load Preprocessor
        preprocessor_file = os.path.join(artifact_dir, "preprocessing.joblib")
        preprocessor = MultiScaleDataPreprocessor.load(preprocessor_file)

        # Load Estimator Model
        model_name = metadata.get("model_name", "")
        model_name_l = model_name.lower()

        if "random forest" in model_name_l and "autoencoder" not in model_name_l:
            model = RandomForestModel.load(artifact_dir)
        elif "xgboost" in model_name_l:
            model = XGBoostModel.load(artifact_dir)
        elif "svr" in model_name_l or "support vector" in model_name_l:
            model = SVRModel.load(artifact_dir)
        elif "autoencoder" in model_name_l:
            from src.core.models.hybrid_ae_rf import LSTMAERandomForestModel
            model = LSTMAERandomForestModel.load(artifact_dir)
        elif "cnn-lstm" in model_name_l:
            from src.core.models.deep_learning import CNNLSTMModel
            model = CNNLSTMModel.load(artifact_dir)
        elif "mlp" in model_name_l or "dnn" in model_name_l:
            from src.core.models.deep_learning import DeepMLPModel
            model = DeepMLPModel.load(artifact_dir)
        elif "1d-cnn" in model_name_l:
            from src.core.models.deep_learning import Conv1DModel
            model = Conv1DModel.load(artifact_dir)
        elif "lstm" in model_name_l:
            from src.core.models.deep_learning import LSTMModel
            model = LSTMModel.load(artifact_dir)
        else:
            # Generic fallback
            if os.path.exists(os.path.join(artifact_dir, "model.joblib")):
                data = joblib.load(os.path.join(artifact_dir, "model.joblib"))
                model = data.get("estimator", data)
            elif os.path.exists(os.path.join(artifact_dir, "model.keras")):
                from src.core.models.deep_learning import CNNLSTMModel
                model = CNNLSTMModel.load(artifact_dir)
            else:
                raise RuntimeError(f"Unknown model format in {artifact_dir}")

        return cls(
            artifact_dir=artifact_dir,
            model=model,
            preprocessor=preprocessor,
            schema=schema,
            metadata=metadata,
            metrics=metrics
        )

    def validate_features(self, payload: Dict[str, Any]) -> List[float]:
        """Validates features according to schema contract."""
        return self.schema.validate_payload(payload)

    def predict(
        self,
        payload: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame, np.ndarray]
    ) -> Dict[str, Any]:
        """
        Executes inference.
        Supports both Direct Prediction and Residual Correction modes.
        """
        # 1. Transform features
        X_scaled = self.preprocessor.transform(payload)

        # 2. Raw model prediction
        if hasattr(self.model, "predict"):
            raw_pred = self.model.predict(X_scaled)
        else:
            raw_pred = self.model(X_scaled)

        raw_pred = np.asarray(raw_pred, dtype=np.float64).flatten()

        is_single = isinstance(payload, dict) or (isinstance(payload, np.ndarray) and payload.ndim == 2 and payload.shape[0] == 1)

        # 3. Handle Mode A (Direct) vs Mode B (Residual Correction)
        baseline_col = self.target_schema.get_baseline_col()

        if self.mode == "residual":
            if baseline_col is None:
                raise ValueError(f"Target '{self.target_name}' does not have a defined SWAT baseline variable.")

            if is_single:
                if isinstance(payload, dict):
                    baseline_val = float(payload.get(baseline_col, 0.0))
                elif isinstance(payload, pd.DataFrame):
                    baseline_val = float(payload[baseline_col].iloc[0])
                elif isinstance(payload, np.ndarray):
                    if baseline_col in self.schema.feature_names:
                        idx = self.schema.feature_names.index(baseline_col)
                        baseline_val = float(payload[0, idx])
                    else:
                        baseline_val = 0.0
                else:
                    baseline_val = 0.0

                residual = float(raw_pred[0])
                corrected_val = max(0.0, baseline_val + residual)
                return {
                    "target": self.target_name,
                    "mode": "residual_correction",
                    "value": round(corrected_val, 3),
                    "predicted_residual": round(residual, 3),
                    "swat_baseline_value": round(baseline_val, 3),
                    "unit": self.target_schema.unit,
                    "model_used": self.metadata.get("model_name"),
                    "artifact_dir": self.artifact_dir
                }
            else:
                # Batch prediction
                if isinstance(payload, pd.DataFrame):
                    baseline_vals = payload[baseline_col].values
                elif isinstance(payload, list):
                    baseline_vals = np.array([float(d.get(baseline_col, 0.0)) for d in payload])
                elif isinstance(payload, np.ndarray):
                    if baseline_col in self.schema.feature_names:
                        idx = self.schema.feature_names.index(baseline_col)
                        baseline_vals = payload[:, idx] if payload.ndim == 2 else payload[:, -1, idx]
                    else:
                        baseline_vals = np.zeros(len(raw_pred))
                else:
                    baseline_vals = np.zeros(len(raw_pred))

                corrected_vals = np.maximum(0.0, baseline_vals + raw_pred)
                return {
                    "target": self.target_name,
                    "mode": "residual_correction",
                    "values": [round(float(v), 3) for v in corrected_vals],
                    "predicted_residuals": [round(float(r), 3) for r in raw_pred],
                    "swat_baseline_values": [round(float(b), 3) for b in baseline_vals],
                    "unit": self.target_schema.unit,
                    "model_used": self.metadata.get("model_name")
                }
        else:
            # Mode A: Direct Prediction
            if is_single:
                val = max(0.0, float(raw_pred[0]))
                return {
                    "target": self.target_name,
                    "mode": "direct_prediction",
                    "value": round(val, 3),
                    "unit": self.target_schema.unit,
                    "model_used": self.metadata.get("model_name"),
                    "artifact_dir": self.artifact_dir
                }
            else:
                vals = [round(max(0.0, float(v)), 3) for v in raw_pred]
                return {
                    "target": self.target_name,
                    "mode": "direct_prediction",
                    "values": vals,
                    "unit": self.target_schema.unit,
                    "model_used": self.metadata.get("model_name")
                }


def promote_to_champion(target_name: str, model_folder: str, base_artifact_dir: str = "artifacts") -> str:
    """
    Copies a model bundle to the champion directory for the target:
    artifacts/<target>/champion/
    """
    source_dir = os.path.join(base_artifact_dir, target_name, model_folder)
    champ_dir = os.path.join(base_artifact_dir, target_name, "champion")

    if not os.path.exists(source_dir):
        raise FileNotFoundError(f"Source model directory not found: {source_dir}")

    os.makedirs(champ_dir, exist_ok=True)

    # Copy files
    for f_name in os.listdir(source_dir):
        s_file = os.path.join(source_dir, f_name)
        d_file = os.path.join(champ_dir, f_name)
        if os.path.isfile(s_file):
            shutil.copy2(s_file, d_file)

    # Update metadata to reflect champion status
    meta_path = os.path.join(champ_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["is_champion"] = True
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    return champ_dir

"""Runtime reader for the versioned AgroTwin ModelBundle contract.

This module deliberately has no Streamlit dependency. It understands the
serialized contract produced by ``agro-digital-twin-st`` and does not treat a
hybrid RF head as a complete model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


TARGET_UNITS = {
    "monthly_runoff_mm": "mm/month",
    "monthly_streamflow_m3s": "m3/s",
    "maize_yield_t_ha": "t/ha",
}
BASELINE_FEATURES = {
    "monthly_runoff_mm": "swat_baseline_runoff_mm",
    "monthly_streamflow_m3s": "swat_baseline_streamflow_m3s",
}


class ExternalModelBundleAdapter:
    REQUIRED_JSON = ("metadata.json", "feature_schema.json", "metrics.json")

    def __init__(self, bundle_path: str | Path):
        self.path = Path(bundle_path).expanduser().resolve()
        self.metadata: dict[str, Any] = {}
        self.schema: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.model: Any = None
        self.encoder: Any = None
        self.preprocessor_payload: dict[str, Any] = {}
        self.model_kind: str | None = None
        self.timesteps: int = 1

    def _feature_names(self) -> list[str]:
        names = self.schema.get("feature_names") or [item["name"] for item in self.schema.get("features", [])]
        return list(names)

    def _target(self) -> str:
        return self.metadata.get("target_name") or self.metadata.get("target")

    def _detect_kind(self) -> str:
        if (self.path / "encoder.keras").is_file() and (self.path / "rf_head.joblib").is_file():
            return "keras_hybrid"
        if (self.path / "model.keras").is_file():
            return "keras"
        if (self.path / "model.joblib").is_file():
            return "joblib"
        raise ValueError("invalid bundle; missing model artifact")

    def validate_bundle(self) -> dict[str, Any]:
        if not self.path.is_dir():
            raise ValueError(f"bundle directory does not exist: {self.path}")
        missing = [name for name in self.REQUIRED_JSON if not (self.path / name).is_file()]
        if not (self.path / "preprocessing.joblib").is_file():
            missing.append("preprocessing.joblib")
        if missing:
            raise ValueError(f"invalid bundle; missing: {', '.join(missing)}")
        self.metadata = json.loads((self.path / "metadata.json").read_text())
        self.schema = json.loads((self.path / "feature_schema.json").read_text())
        self.metrics = json.loads((self.path / "metrics.json").read_text())
        names = self._feature_names()
        if not names or self.metadata.get("feature_order", names) != names:
            raise ValueError("metadata feature_order does not match feature_schema")
        target = self._target()
        if target not in TARGET_UNITS:
            raise ValueError(f"unsupported or missing model target: {target}")
        self.model_kind = self._detect_kind()
        if self.model_kind == "keras_hybrid" and not (self.path / "hybrid_meta.json").is_file():
            raise ValueError("hybrid bundle is missing hybrid_meta.json")
        framework = {"joblib": "scikit-learn/joblib", "keras": "keras", "keras_hybrid": "keras-hybrid-random-forest"}[self.model_kind]
        return {
            "status": "VALID", "target": target, "framework": framework, "feature_order": names,
            "checksum": self.checksum(), "metadata": self.metadata, "metrics": self.metrics,
            "bundle_contract_version": self.metadata.get("bundle_contract_version", "agrotwin-modelbundle/v1"),
            "learning_mode": self.metadata.get("learning_mode", "direct"),
            "training_data_type": "SYNTHETIC" if self.metadata.get("is_synthetic_training_data") else "AS_DECLARED_BY_BUNDLE",
            "requires_tensorflow": self.model_kind in {"keras", "keras_hybrid"},
        }

    def checksum(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(item for item in self.path.iterdir() if item.is_file()):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def read_feature_schema(self) -> dict[str, Any]:
        if not self.schema:
            self.validate_bundle()
        return self.schema

    def _ordered_features(self, payload: dict[str, Any]) -> list[float]:
        schema = self.read_feature_schema()
        definitions = {item["name"]: item for item in schema.get("features", [])}
        ordered: list[float] = []
        for name in self._feature_names():
            definition = definitions.get(name, {})
            if name not in payload:
                if definition.get("required", True):
                    raise ValueError(f"missing required features: {name}")
                value = definition.get("default")
            else:
                value = payload[name]
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"feature {name} must be numeric") from exc
            if definition.get("min_val") is not None and numeric < float(definition["min_val"]):
                raise ValueError(f"feature {name} is below min_val")
            if definition.get("max_val") is not None and numeric > float(definition["max_val"]):
                raise ValueError(f"feature {name} is above max_val")
            ordered.append(numeric)
        return ordered

    def load(self) -> "ExternalModelBundleAdapter":
        self.validate_bundle()
        try:
            import joblib
        except ImportError as exc:
            raise RuntimeError("ML_JOBLIB_NOT_AVAILABLE: install joblib/scikit-learn for ModelBundle inference") from exc
        loaded_preprocessor = joblib.load(self.path / "preprocessing.joblib")
        if not isinstance(loaded_preprocessor, dict) or "feature_names" not in loaded_preprocessor:
            raise ValueError("preprocessing.joblib is not an AgroTwin preprocessor payload")
        if list(loaded_preprocessor["feature_names"]) != self._feature_names():
            raise ValueError("preprocessing feature_names do not match feature_schema")
        self.preprocessor_payload = loaded_preprocessor
        self.model_kind = self.model_kind or self._detect_kind()
        if self.model_kind == "joblib":
            loaded = joblib.load(self.path / "model.joblib")
            self.model = loaded.get("estimator", loaded) if isinstance(loaded, dict) else loaded
        else:
            try:
                from tensorflow import keras
            except ImportError as exc:
                raise RuntimeError("ML_KERAS_NOT_AVAILABLE: TensorFlow/Keras is required for the selected bundle") from exc
            if self.model_kind == "keras_hybrid":
                self.encoder = keras.models.load_model(self.path / "encoder.keras", compile=False)
                self.model = joblib.load(self.path / "rf_head.joblib")
                saved = json.loads((self.path / "hybrid_meta.json").read_text())
                input_shape = getattr(self.encoder, "input_shape", None)
                if not input_shape or len(input_shape) != 3:
                    raise ValueError("hybrid encoder must accept (samples, timesteps, features)")
                self.timesteps = int(input_shape[1] or saved.get("timesteps", 1))
                n_features = int(input_shape[2] or saved.get("n_features", 0))
                if n_features != len(self._feature_names()):
                    raise ValueError("hybrid encoder feature dimension does not match feature_schema")
            else:
                self.model = keras.models.load_model(self.path / "model.keras", compile=False)
                shape = getattr(self.model, "input_shape", None)
                self.timesteps = int(shape[1] or 1) if shape and len(shape) == 3 else 1
        return self

    def _transform_rows(self, payloads: Iterable[dict[str, Any]]):
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("numpy is required for ModelBundle inference") from exc
        matrix = np.asarray([self._ordered_features(payload) for payload in payloads], dtype=float)
        scaler = self.preprocessor_payload.get("scaler")
        if self.preprocessor_payload.get("scale_features") and self.preprocessor_payload.get("is_fitted") and scaler is not None:
            matrix = scaler.transform(matrix)
        return matrix

    def _apply_learning_mode(self, value: float, payload: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        mode = self.metadata.get("learning_mode", "direct")
        if mode == "direct":
            return max(0.0, value), {"learning_mode": "direct"}
        if mode != "residual":
            raise ValueError(f"unsupported learning_mode: {mode}")
        baseline_name = BASELINE_FEATURES.get(self._target())
        if not baseline_name or baseline_name not in payload:
            raise ValueError("MISSING_BASELINE_FEATURE: residual bundle requires its declared mechanistic baseline")
        baseline = float(payload[baseline_name])
        return max(0.0, baseline + value), {"learning_mode": "residual", "predicted_residual": value, "baseline_value": baseline}

    def predict(self, payload: dict[str, Any], *, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if self.model is None:
            self.load()
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("numpy is required for ModelBundle inference") from exc
        if self.model_kind == "keras_hybrid":
            sequence = [*(history or []), payload]
            if len(sequence) != self.timesteps:
                raise ValueError(f"INSUFFICIENT_HISTORY: hybrid bundle requires {self.timesteps} consecutive monthly rows from one watershed/HRU")
            transformed = self._transform_rows(sequence)
            latent = self.encoder.predict(transformed.reshape(1, self.timesteps, transformed.shape[1]), verbose=0)
            raw = self.model.predict(np.hstack([transformed[-1:].reshape(1, -1), latent]))
        elif self.model_kind == "keras" and self.timesteps > 1:
            sequence = [*(history or []), payload]
            if len(sequence) != self.timesteps:
                raise ValueError(f"INSUFFICIENT_HISTORY: sequence bundle requires {self.timesteps} consecutive monthly rows from one watershed/HRU")
            transformed = self._transform_rows(sequence)
            raw = self.model.predict(transformed.reshape(1, self.timesteps, transformed.shape[1]), verbose=0)
        else:
            transformed = self._transform_rows([payload])
            raw = self.model.predict(transformed, verbose=0) if self.model_kind == "keras" else self.model.predict(transformed)
        value = float(np.asarray(raw, dtype=float).reshape(-1)[0])
        final_value, mode_metadata = self._apply_learning_mode(value, payload)
        target = self._target()
        return {
            "status": "PREDICTED", "target": target, "value": final_value, "unit": TARGET_UNITS[target],
            "model_name": self.metadata.get("model_name"), "framework": self.validate_bundle()["framework"],
            "feature_order": self._feature_names(), "timesteps": self.timesteps, **mode_metadata,
            "provenance": {"artifact_path": str(self.path), "checksum": self.checksum(),
                           "training_data": "SYNTHETIC" if self.metadata.get("is_synthetic_training_data") else "AS_DECLARED_BY_BUNDLE",
                           "bundle_contract_version": self.metadata.get("bundle_contract_version", "agrotwin-modelbundle/v1")},
        }

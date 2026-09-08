"""Standalone external ModelBundle adapter; never imports Streamlit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ExternalModelBundleAdapter:
    REQUIRED_JSON = ("metadata.json", "feature_schema.json", "metrics.json")

    def __init__(self, bundle_path: str | Path):
        self.path = Path(bundle_path).expanduser().resolve()
        self.metadata: dict[str, Any] = {}
        self.schema: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.model: Any = None
        self.preprocessor: Any = None

    def validate_bundle(self) -> dict[str, Any]:
        if not self.path.is_dir():
            raise ValueError(f"bundle directory does not exist: {self.path}")
        missing = [name for name in self.REQUIRED_JSON if not (self.path / name).is_file()]
        model_files = [p for p in (self.path / "model.joblib", self.path / "model.keras", self.path / "rf_head.joblib") if p.is_file()]
        if missing or not model_files:
            raise ValueError(f"invalid bundle; missing: {', '.join(missing + ([] if model_files else ['model artifact']))}")
        self.metadata = json.loads((self.path / "metadata.json").read_text())
        self.schema = json.loads((self.path / "feature_schema.json").read_text())
        self.metrics = json.loads((self.path / "metrics.json").read_text())
        names = self.schema.get("feature_names") or [item["name"] for item in self.schema.get("features", [])]
        if not names or self.metadata.get("feature_order", names) != names:
            raise ValueError("metadata feature_order does not match feature_schema")
        target = self.metadata.get("target_name") or self.metadata.get("target")
        if target not in {"monthly_runoff_mm", "seasonal_maize_yield", "maize_yield_t_ha"}:
            raise ValueError(f"unsupported or missing model target: {target}")
        framework = "keras" if any(p.suffix == ".keras" for p in model_files) else "scikit-learn/joblib"
        return {"status": "VALID", "target": target, "framework": framework, "feature_order": names,
                "checksum": self.checksum(), "metadata": self.metadata, "metrics": self.metrics}

    def checksum(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(p for p in self.path.iterdir() if p.is_file()):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def read_feature_schema(self) -> dict[str, Any]:
        if not self.schema:
            self.validate_bundle()
        return self.schema

    def _ordered_features(self, payload: dict[str, Any]) -> list[float]:
        schema = self.read_feature_schema()
        features = schema.get("features", [])
        names = schema.get("feature_names") or [item["name"] for item in features]
        definitions = {item["name"]: item for item in features}
        missing = [name for name in names if name not in payload]
        if missing:
            raise ValueError(f"missing required features: {', '.join(missing)}")
        ordered = []
        for name in names:
            try:
                value = float(payload[name])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"feature {name} must be numeric") from exc
            definition = definitions.get(name, {})
            if definition.get("min_val") is not None and value < definition["min_val"]:
                raise ValueError(f"feature {name} is below min_val")
            if definition.get("max_val") is not None and value > definition["max_val"]:
                raise ValueError(f"feature {name} is above max_val")
            ordered.append(value)
        return ordered

    def load(self) -> "ExternalModelBundleAdapter":
        info = self.validate_bundle()
        if info["framework"] == "keras":
            try:
                from tensorflow import keras
            except ImportError as exc:
                raise RuntimeError("TensorFlow is required for this Keras bundle") from exc
            self.model = keras.models.load_model(self.path / "model.keras", compile=False)
        else:
            try:
                import joblib
            except ImportError as exc:
                raise RuntimeError("joblib/scikit-learn dependencies are required") from exc
            model_path = self.path / ("model.joblib" if (self.path / "model.joblib").is_file() else "rf_head.joblib")
            loaded = joblib.load(model_path)
            self.model = loaded.get("estimator", loaded) if isinstance(loaded, dict) else loaded
            prep_path = self.path / "preprocessing.joblib"
            if prep_path.is_file():
                loaded_prep = joblib.load(prep_path)
                self.preprocessor = loaded_prep.get("scaler", loaded_prep) if isinstance(loaded_prep, dict) else loaded_prep
        return self

    def apply_preprocessing(self, payload: dict[str, Any]) -> Any:
        row = [self._ordered_features(payload)]
        return self.preprocessor.transform(row) if self.preprocessor is not None else row

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.model is None:
            self.load()
        transformed = self.apply_preprocessing(payload)
        raw = self.model.predict(transformed, verbose=0) if self.model.__class__.__module__.startswith("keras") else self.model.predict(transformed)
        value = float(raw[0][0] if getattr(raw[0], "__len__", None) else raw[0])
        target = self.metadata.get("target_name") or self.metadata.get("target")
        return {"target": target, "value": max(0.0, value), "unit": "mm/month" if target == "monthly_runoff_mm" else "t/ha",
                "model_name": self.metadata.get("model_name"), "framework": "keras" if self.path.joinpath("model.keras").exists() else "scikit-learn/joblib",
                "feature_order": self.schema.get("feature_names"), "provenance": {"artifact_path": str(self.path), "checksum": self.checksum(),
                "training_data": "SYNTHETIC" if self.metadata.get("is_synthetic_training_data") else "AS_DECLARED_BY_BUNDLE"}}

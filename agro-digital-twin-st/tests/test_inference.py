"""
Tests for ModelBundle serialization, loading, and inference consistency.
"""

import pytest
import os
import numpy as np
import pandas as pd
from src.core.features.schema import get_default_feature_schema
from src.core.features.preprocessor import MultiScaleDataPreprocessor
from src.core.models.traditional import RandomForestModel
from src.core.inference.bundle import ModelBundle


def test_model_bundle_save_load_predict(tmp_path):
    bundle_dir = str(tmp_path / "test_bundle")
    schema = get_default_feature_schema(mode="direct")

    # Generate synthetic training data
    n_samples = 40
    data = {f.name: np.random.uniform(5, 50, size=n_samples) for f in schema.features}
    df = pd.DataFrame(data)
    y = np.random.uniform(10, 40, size=n_samples)

    preprocessor = MultiScaleDataPreprocessor(schema=schema)
    X_scaled = preprocessor.fit_transform(df)

    rf = RandomForestModel(n_estimators=10, random_state=42)
    rf.fit(X_scaled, y)

    metrics = {"rmse": 1.5, "mae": 1.1, "r2": 0.95, "nse": 0.94, "pbias": 0.5}

    # Save Bundle
    bundle = ModelBundle.save_bundle(
        artifact_dir=bundle_dir,
        model=rf,
        preprocessor=preprocessor,
        schema=schema,
        target_name="monthly_runoff_mm",
        learning_mode="direct",
        metrics=metrics,
        validation_strategy="temporal",
        train_split_desc="Temporal split test"
    )

    # Check that required files exist
    assert os.path.exists(os.path.join(bundle_dir, "model.joblib"))
    assert os.path.exists(os.path.join(bundle_dir, "preprocessing.joblib"))
    assert os.path.exists(os.path.join(bundle_dir, "feature_schema.json"))
    assert os.path.exists(os.path.join(bundle_dir, "metadata.json"))
    assert os.path.exists(os.path.join(bundle_dir, "metrics.json"))

    # Load Bundle independently
    loaded_bundle = ModelBundle.load(bundle_dir)
    assert loaded_bundle.target_name == "monthly_runoff_mm"
    assert loaded_bundle.mode == "direct"
    assert loaded_bundle.metadata["model_name"] == "Random Forest Regressor"

    # Single payload prediction
    sample_payload = {f.name: 25.0 for f in schema.features}
    pred_orig = bundle.predict(sample_payload)
    pred_loaded = loaded_bundle.predict(sample_payload)

    assert pytest.approx(pred_orig["value"], 0.001) == pred_loaded["value"]

    # Array input prediction
    arr_payload = np.ones((5, len(schema.features))) * 25.0
    arr_pred = loaded_bundle.predict(arr_payload)
    assert len(arr_pred["values"]) == 5


def test_model_bundle_residual_mode(tmp_path):
    bundle_dir = str(tmp_path / "residual_bundle")
    schema = get_default_feature_schema(mode="residual", include_baseline=True)

    n_samples = 30
    data = {f.name: np.random.uniform(5, 50, size=n_samples) for f in schema.features}
    data["swat_baseline_runoff_mm"] = np.random.uniform(10, 20, size=n_samples)
    df = pd.DataFrame(data)
    residuals = np.random.uniform(-2, 2, size=n_samples)

    preprocessor = MultiScaleDataPreprocessor(schema=schema)
    X_scaled = preprocessor.fit_transform(df)

    rf = RandomForestModel(n_estimators=10, random_state=42)
    rf.fit(X_scaled, residuals)

    bundle = ModelBundle.save_bundle(
        artifact_dir=bundle_dir,
        model=rf,
        preprocessor=preprocessor,
        schema=schema,
        target_name="monthly_runoff_mm",
        learning_mode="residual",
        metrics={"rmse": 0.8},
        validation_strategy="temporal",
        train_split_desc="Temporal test"
    )

    loaded = ModelBundle.load(bundle_dir)
    test_dict = {f.name: 20.0 for f in schema.features}
    test_dict["swat_baseline_runoff_mm"] = 15.0

    res = loaded.predict(test_dict)
    assert res["mode"] == "residual_correction"
    assert "predicted_residual" in res
    assert "swat_baseline_value" in res
    assert res["swat_baseline_value"] == 15.0

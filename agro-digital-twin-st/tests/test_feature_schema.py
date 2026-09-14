"""
Tests for Feature Contract and ModelFeatureSchema.
"""

import pytest
import numpy as np
import pandas as pd
from src.core.features.schema import (
    FeatureDefinition,
    ModelFeatureSchema,
    get_default_feature_schema
)
from src.core.features.preprocessor import MultiScaleDataPreprocessor


def test_feature_validation_and_clipping():
    feat = FeatureDefinition("test_feat", "float", "mm", "Climate", min_val=0.0, max_val=100.0, default=10.0)
    assert feat.validate_value(50.0) == 50.0
    assert feat.validate_value(-10.0) == 0.0  # Clipped lower
    assert feat.validate_value(150.0) == 100.0  # Clipped upper
    assert feat.validate_value(None) == 10.0  # Default used


def test_schema_json_roundtrip():
    schema = get_default_feature_schema(mode="direct")
    json_str = schema.to_json()
    reloaded = ModelFeatureSchema.from_json(json_str)

    assert reloaded.feature_names == schema.feature_names
    assert len(reloaded.features) == len(schema.features)


def test_preprocessor_fit_transform(tmp_path):
    schema = get_default_feature_schema(mode="direct")
    preprocessor = MultiScaleDataPreprocessor(schema=schema)

    dummy_data = {feat: np.random.uniform(10, 50, size=20) for feat in schema.feature_names}
    df = pd.DataFrame(dummy_data)

    X_scaled = preprocessor.fit_transform(df)
    assert X_scaled.shape == (20, len(schema.feature_names))

    # Test serialization
    prep_path = str(tmp_path / "preprocessing.joblib")
    preprocessor.save(prep_path)

    loaded_prep = MultiScaleDataPreprocessor.load(prep_path)
    assert loaded_prep.is_fitted
    assert loaded_prep.feature_names == preprocessor.feature_names

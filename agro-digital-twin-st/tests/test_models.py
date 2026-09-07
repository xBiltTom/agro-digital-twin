"""
Unit tests for all 3 Traditional and 2 Hybrid model architectures on CPU.
"""

import pytest
import numpy as np
from src.core.models.traditional import RandomForestModel, XGBoostModel, SVRModel
from src.core.models.deep_learning import CNNLSTMModel
from src.core.models.hybrid_ae_rf import LSTMAERandomForestModel


@pytest.fixture
def dummy_data():
    np.random.seed(42)
    X = np.random.uniform(1.0, 10.0, size=(30, 8))
    y = np.random.uniform(5.0, 25.0, size=30)
    return X, y


def test_random_forest_fit_predict(dummy_data):
    X, y = dummy_data
    model = RandomForestModel(n_estimators=10, random_state=42)
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert model.is_fitted


def test_xgboost_fit_predict(dummy_data):
    X, y = dummy_data
    model = XGBoostModel(n_estimators=10, random_state=42)
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert model.is_fitted


def test_svr_fit_predict(dummy_data):
    X, y = dummy_data
    model = SVRModel(C=1.0)
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert model.is_fitted


def test_cnn_lstm_fit_predict(dummy_data):
    X, y = dummy_data
    model = CNNLSTMModel(input_dim=8)
    model.fit(X, y, epochs=2, batch_size=16)
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert model.is_fitted


def test_hybrid_ae_rf_fit_predict(dummy_data):
    X, y = dummy_data
    model = LSTMAERandomForestModel(input_dim=8, latent_dim=4, n_estimators=10, random_state=42)
    model.fit(X, y, epochs=2, batch_size=16)
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert model.is_fitted

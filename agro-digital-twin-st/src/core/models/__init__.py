"""
Model Architectures package for AgroTwin-AI.
Supports 3 Traditional algorithms:
  - Random Forest Regressor
  - XGBoost Regressor
  - Support Vector Regression (SVR)
And 2 Hybrid algorithms:
  - CNN-LSTM
  - LSTM Autoencoder + Random Forest
Plus reusable experimental models (MLP, 1D-CNN, LSTM).
"""

from .base import BaseMultiScaleModel
from .traditional import RandomForestModel, XGBoostModel, SVRModel
from .deep_learning import (
    CNNLSTMModel,
    DeepMLPModel,
    Conv1DModel,
    LSTMModel,
    build_cnn_lstm_model,
    build_mlp_model,
    build_cnn1d_model,
    build_lstm_model
)
from .hybrid_ae_rf import LSTMAERandomForestModel

__all__ = [
    "BaseMultiScaleModel",
    "RandomForestModel",
    "XGBoostModel",
    "SVRModel",
    "CNNLSTMModel",
    "DeepMLPModel",
    "Conv1DModel",
    "LSTMModel",
    "LSTMAERandomForestModel",
    "build_cnn_lstm_model",
    "build_mlp_model",
    "build_cnn1d_model",
    "build_lstm_model"
]

"""
Model Architectures Facade for AgroTwin-AI.
Maintains backwards compatibility while referencing modular architectures in src.core.models.
"""

from src.core.runtime import configure_tensorflow_runtime

configure_tensorflow_runtime()
import keras
from src.core.models import (
    build_cnn_lstm_model,
    build_mlp_model,
    build_cnn1d_model,
    build_lstm_model,
    RandomForestModel,
    XGBoostModel,
    SVRModel,
    CNNLSTMModel,
    LSTMAERandomForestModel
)


def get_model_by_name(name: str, input_dim: int, lr: float = 0.001, dropout: float = 0.25):
    """Factory helper to instantiate models by display name."""
    name_l = name.lower()
    if "random forest" in name_l:
        return RandomForestModel()
    elif "xgboost" in name_l:
        return XGBoostModel()
    elif "svr" in name_l or "support vector" in name_l:
        return SVRModel()
    elif "cnn-lstm" in name_l:
        return CNNLSTMModel(input_dim=input_dim, lr=lr, dropout=dropout)
    elif "autoencoder" in name_l:
        return LSTMAERandomForestModel(input_dim=input_dim, lr=lr)
    elif "mlp" in name_l or "dnn" in name_l:
        return build_mlp_model(input_dim, lr, dropout)
    elif "1d-cnn" in name_l:
        return build_cnn1d_model(input_dim, lr, dropout)
    elif "lstm" in name_l:
        return build_lstm_model(input_dim, lr, dropout)
    else:
        return RandomForestModel()

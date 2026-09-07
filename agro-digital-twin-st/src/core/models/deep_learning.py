"""
Deep Learning Architectures (TensorFlow / Keras) for AgroTwin-AI.
1. CNN-LSTM Hybrid Architecture with Real Temporal Sequences (P0.1)
2. Standalone Experimental Architectures: Deep MLP, 1D-CNN, LSTM
All models are fully CPU compatible with opportunistic GPU usage.
Lazy imports ensure TensorFlow is only required when deep learning models are used.
"""

import os
import json
from typing import Dict, Any, Optional
import numpy as np

from .base import BaseMultiScaleModel


def _get_keras():
    """Lazy import for Keras / TensorFlow."""
    try:
        import keras
        return keras
    except ImportError as e:
        raise ImportError(
            "TensorFlow/Keras is required for deep learning models. "
            "Please install tensorflow via 'pip install tensorflow'. "
            f"Original error: {e}"
        )


def build_cnn_lstm_model(
    timesteps: int = 12,
    n_features: int = 10,
    lr: float = 0.001,
    dropout: float = 0.25
) -> Any:
    """
    CNN-LSTM Hybrid Model with Real Temporal Sequences (P0.1).
    Input shape: (timesteps, n_features)
    1D Convolution extracts local cross-variable temporal features along timesteps.
    LSTM captures sequential hydrological inertia and multi-month lag.
    """
    keras = _get_keras()
    from keras import layers, regularizers

    inputs = layers.Input(shape=(timesteps, n_features), name="sequence_input")

    # 1D Convolutional feature extractor across temporal steps
    kernel_size = min(3, max(1, timesteps))
    x = layers.Conv1D(filters=32, kernel_size=kernel_size, padding="same", activation="relu")(inputs)
    x = layers.BatchNormalization()(x)
    if timesteps >= 4:
        x = layers.MaxPooling1D(pool_size=2, padding="same")(x)

    # Recurrent LSTM stage
    x = layers.LSTM(units=32, return_sequences=False)(x)
    x = layers.Dropout(dropout)(x)

    # Dense regression head
    x = layers.Dense(32, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(x)
    outputs = layers.Dense(1, activation="linear", name="regression_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="CNN_LSTM_Temporal_Hybrid")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_mlp_model(input_dim: int, lr: float = 0.001, dropout: float = 0.25) -> Any:
    """Deep Multi-Layer Perceptron (DNN)."""
    keras = _get_keras()
    from keras import layers, regularizers

    inputs = layers.Input(shape=(input_dim,), name="features_input")
    x = layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout)(x)
    x = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="linear", name="regression_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="Deep_MLP")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_cnn1d_model(input_dim: int, lr: float = 0.001, dropout: float = 0.25) -> Any:
    """1D-CNN (Feature ConvNet)."""
    keras = _get_keras()
    from keras import layers

    inputs = layers.Input(shape=(input_dim,), name="features_input")
    x = layers.Reshape((input_dim, 1))(inputs)
    x = layers.Conv1D(filters=32, kernel_size=3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(pool_size=2)(x)
    x = layers.Flatten()(x)
    x = layers.Dense(32, activation="relu")(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(1, activation="linear", name="regression_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="1D_CNN")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_lstm_model(timesteps: int = 12, n_features: int = 10, lr: float = 0.001, dropout: float = 0.25) -> Any:
    """LSTM Recurrent Sequence Model."""
    keras = _get_keras()
    from keras import layers

    inputs = layers.Input(shape=(timesteps, n_features), name="sequence_input")
    x = layers.LSTM(32, return_sequences=False)(inputs)
    x = layers.Dropout(dropout)(x)
    x = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="linear", name="regression_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="LSTM_Recurrent")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


class CNNLSTMModel(BaseMultiScaleModel):
    """
    CNN-LSTM Hybrid wrapper implementing BaseMultiScaleModel.
    Supports real temporal 3D sequences: (samples, timesteps, features).
    """

    def __init__(
        self,
        timesteps: int = 12,
        n_features: int = 10,
        input_dim: Optional[int] = None,  # backwards compatibility
        lr: float = 0.001,
        dropout: float = 0.25,
        name: str = "CNN-LSTM Hybrid"
    ):
        super().__init__(name=name, model_type="hybrid_deep")
        self.timesteps = timesteps
        self.n_features = input_dim if input_dim is not None else n_features
        self.params = {
            "timesteps": self.timesteps,
            "n_features": self.n_features,
            "lr": lr,
            "dropout": dropout
        }
        self.keras_model: Optional[Any] = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 25,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "CNNLSTMModel":
        # Handle shape
        if X_train.ndim == 3:
            self.timesteps = X_train.shape[1]
            self.n_features = X_train.shape[2]
            X_tr = X_train
        elif X_train.ndim == 2:
            # If 2D tabular data passed, reshape as (N, 1, features)
            self.timesteps = 1
            self.n_features = X_train.shape[1]
            X_tr = np.expand_dims(X_train, axis=1)
        else:
            raise ValueError(f"Expected 2D or 3D input, got ndim={X_train.ndim}")

        self.params["timesteps"] = self.timesteps
        self.params["n_features"] = self.n_features

        self.keras_model = build_cnn_lstm_model(
            timesteps=self.timesteps,
            n_features=self.n_features,
            lr=self.params["lr"],
            dropout=self.params["dropout"]
        )

        val_data = None
        if X_val is not None and y_val is not None:
            if X_val.ndim == 2:
                X_v = np.expand_dims(X_val, axis=1) if self.timesteps == 1 else X_val
            else:
                X_v = X_val
            if len(X_v) == len(y_val):
                val_data = (X_v, y_val)

        self.keras_model.fit(
            X_tr,
            y_train,
            validation_data=val_data,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose
        )
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.keras_model is None:
            raise RuntimeError("Model is not fitted yet.")

        k_shape = getattr(self.keras_model, "input_shape", None)
        is_2d_model = (k_shape is not None and len(k_shape) == 2)

        if is_2d_model:
            X_in = X[:, -1, :] if X.ndim == 3 else X
        elif X.ndim == 3:
            X_in = X
        elif X.ndim == 2:
            if self.timesteps == 1:
                X_in = np.expand_dims(X, axis=1)
            elif X.shape[0] == 1:
                # Single payload repeated across time window
                X_in = np.repeat(np.expand_dims(X, axis=1), self.timesteps, axis=1)
            elif X.shape[0] >= self.timesteps:
                # Build rolling sequences
                from src.core.features.sequences import build_temporal_sequences_from_matrix
                X_in, _ = build_temporal_sequences_from_matrix(X, np.zeros(len(X)), sequence_length=self.timesteps)
            else:
                X_in = np.repeat(np.expand_dims(X[:1], axis=1), self.timesteps, axis=1)
        else:
            raise ValueError(f"Unsupported input dimension for prediction: {X.ndim}")

        preds = self.keras_model.predict(X_in, verbose=0)
        return preds.flatten()

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.keras")
        if self.keras_model is not None:
            self.keras_model.save(model_file)

        # Save sequence dimensions metadata
        seq_meta_file = os.path.join(artifact_dir, "sequence_meta.json")
        with open(seq_meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "timesteps": self.timesteps,
                "n_features": self.n_features,
                "params": self.params
            }, f, indent=2)

        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "CNNLSTMModel":
        keras = _get_keras()
        model_file = os.path.join(artifact_dir, "model.keras")
        if not os.path.exists(model_file):
            h5_file = os.path.join(artifact_dir, "model.h5")
            if os.path.exists(h5_file):
                model_file = h5_file
            else:
                raise FileNotFoundError(f"Model file not found in: {artifact_dir}")

        keras_model = keras.models.load_model(model_file, compile=False)

        # Retrieve sequence metadata
        seq_meta_file = os.path.join(artifact_dir, "sequence_meta.json")
        timesteps = 12
        n_features = 10
        if os.path.exists(seq_meta_file):
            with open(seq_meta_file, "r", encoding="utf-8") as f:
                s_meta = json.load(f)
                timesteps = s_meta.get("timesteps", 12)
                n_features = s_meta.get("n_features", 10)
        elif keras_model.input_shape and len(keras_model.input_shape) == 3:
            timesteps = keras_model.input_shape[1] or 12
            n_features = keras_model.input_shape[2] or 10
        elif keras_model.input_shape and len(keras_model.input_shape) == 2:
            timesteps = 1
            n_features = keras_model.input_shape[1] or 10

        instance = cls(timesteps=timesteps, n_features=n_features)
        instance.keras_model = keras_model
        instance.is_fitted = True
        return instance


class DeepMLPModel(BaseMultiScaleModel):
    """Deep MLP wrapper."""

    def __init__(self, input_dim: int = 10, lr: float = 0.001, dropout: float = 0.25):
        super().__init__(name="Deep MLP (DNN)", model_type="deep_learning")
        self.params = {"input_dim": input_dim, "lr": lr, "dropout": dropout}
        self.keras_model: Optional[Any] = None

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None, epochs: int = 25, batch_size: int = 32, verbose: int = 0) -> "DeepMLPModel":
        if X_train.ndim == 3:
            X_tr = X_train[:, -1, :]  # use current timestep
        else:
            X_tr = X_train
        input_dim = X_tr.shape[1]
        self.params["input_dim"] = input_dim
        self.keras_model = build_mlp_model(input_dim, self.params["lr"], self.params["dropout"])
        val_data = (X_val[:, -1, :] if (X_val is not None and X_val.ndim == 3) else X_val, y_val) if (X_val is not None and y_val is not None and len(X_val) == len(y_val)) else None
        self.keras_model.fit(X_tr, y_train, validation_data=val_data, epochs=epochs, batch_size=batch_size, verbose=verbose)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_in = X[:, -1, :] if X.ndim == 3 else X
        return self.keras_model.predict(X_in, verbose=0).flatten()

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.keras")
        self.keras_model.save(model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "DeepMLPModel":
        keras = _get_keras()
        model_file = os.path.join(artifact_dir, "model.keras")
        keras_model = keras.models.load_model(model_file, compile=False)
        instance = cls(input_dim=keras_model.input_shape[1])
        instance.keras_model = keras_model
        instance.is_fitted = True
        return instance


class Conv1DModel(BaseMultiScaleModel):
    """1D-CNN wrapper."""

    def __init__(self, input_dim: int = 10, lr: float = 0.001, dropout: float = 0.25):
        super().__init__(name="1D-CNN (Temporal ConvNet)", model_type="deep_learning")
        self.params = {"input_dim": input_dim, "lr": lr, "dropout": dropout}
        self.keras_model: Optional[Any] = None

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None, epochs: int = 25, batch_size: int = 32, verbose: int = 0) -> "Conv1DModel":
        X_tr = X_train[:, -1, :] if X_train.ndim == 3 else X_train
        input_dim = X_tr.shape[1]
        self.params["input_dim"] = input_dim
        self.keras_model = build_cnn1d_model(input_dim, self.params["lr"], self.params["dropout"])
        val_data = (X_val[:, -1, :] if (X_val is not None and X_val.ndim == 3) else X_val, y_val) if (X_val is not None and y_val is not None and len(X_val) == len(y_val)) else None
        self.keras_model.fit(X_tr, y_train, validation_data=val_data, epochs=epochs, batch_size=batch_size, verbose=verbose)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_in = X[:, -1, :] if X.ndim == 3 else X
        return self.keras_model.predict(X_in, verbose=0).flatten()

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.keras")
        self.keras_model.save(model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "Conv1DModel":
        keras = _get_keras()
        model_file = os.path.join(artifact_dir, "model.keras")
        keras_model = keras.models.load_model(model_file, compile=False)
        instance = cls(input_dim=keras_model.input_shape[1])
        instance.keras_model = keras_model
        instance.is_fitted = True
        return instance


class LSTMModel(BaseMultiScaleModel):
    """LSTM Recurrent Sequence wrapper."""

    def __init__(self, timesteps: int = 12, n_features: int = 10, input_dim: Optional[int] = None, lr: float = 0.001, dropout: float = 0.25):
        super().__init__(name="LSTM Recurrente", model_type="deep_learning")
        self.timesteps = timesteps
        self.n_features = input_dim if input_dim is not None else n_features
        self.params = {"timesteps": self.timesteps, "n_features": self.n_features, "lr": lr, "dropout": dropout}
        self.keras_model: Optional[Any] = None

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None, epochs: int = 25, batch_size: int = 32, verbose: int = 0) -> "LSTMModel":
        if X_train.ndim == 3:
            self.timesteps = X_train.shape[1]
            self.n_features = X_train.shape[2]
            X_tr = X_train
        else:
            self.timesteps = 1
            self.n_features = X_train.shape[1]
            X_tr = np.expand_dims(X_train, axis=1)

        self.keras_model = build_lstm_model(self.timesteps, self.n_features, self.params["lr"], self.params["dropout"])
        val_data = None
        if X_val is not None and y_val is not None:
            X_v = np.expand_dims(X_val, axis=1) if X_val.ndim == 2 else X_val
            if len(X_v) == len(y_val):
                val_data = (X_v, y_val)

        self.keras_model.fit(X_tr, y_train, validation_data=val_data, epochs=epochs, batch_size=batch_size, verbose=verbose)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if X.ndim == 3:
            X_in = X
        elif self.timesteps == 1:
            X_in = np.expand_dims(X, axis=1)
        elif X.shape[0] == 1:
            X_in = np.repeat(np.expand_dims(X, axis=1), self.timesteps, axis=1)
        else:
            from src.core.features.sequences import build_temporal_sequences_from_matrix
            X_in, _ = build_temporal_sequences_from_matrix(X, np.zeros(len(X)), sequence_length=self.timesteps)
        return self.keras_model.predict(X_in, verbose=0).flatten()

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        model_file = os.path.join(artifact_dir, "model.keras")
        self.keras_model.save(model_file)
        return model_file

    @classmethod
    def load(cls, artifact_dir: str) -> "LSTMModel":
        keras = _get_keras()
        model_file = os.path.join(artifact_dir, "model.keras")
        keras_model = keras.models.load_model(model_file, compile=False)
        instance = cls(input_dim=keras_model.input_shape[2] if len(keras_model.input_shape) == 3 else 10)
        instance.keras_model = keras_model
        instance.is_fitted = True
        return instance

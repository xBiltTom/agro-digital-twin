"""
Hybrid Model: LSTM Autoencoder + Random Forest (LSTMAE_RF_Model)
Combines deep recurrent representation learning with tree-based ensemble regression:
1. Stage 1: LSTM Autoencoder with Real Temporal Sequences (P0.2) compresses multi-step dynamics into latent space.
2. Stage 2: Latent code + current timestep state are passed to a Random Forest Regressor.
Rigorous Leak-Free Protocol:
- Trained ONLY on TRAIN set.
- Validation / Test are transformed using fitted preprocessor and passed strictly for out-of-sample inference.
"""

import os
import json
import joblib
from typing import Dict, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from .base import BaseMultiScaleModel


def _get_keras():
    """Lazy import for Keras / TensorFlow."""
    try:
        import keras
        return keras
    except ImportError as e:
        raise ImportError(
            "TensorFlow/Keras is required for LSTM Autoencoder + Random Forest hybrid model. "
            "Please install tensorflow via 'pip install tensorflow'. "
            f"Original error: {e}"
        )


def build_lstm_autoencoder(
    timesteps: int = 12,
    n_features: int = 10,
    latent_dim: int = 8,
    lr: float = 0.001
) -> Tuple[Any, Any]:
    """
    Constructs an LSTM Sequence Autoencoder and extracts the encoder sub-network.
    Input shape: (timesteps, n_features) -> Latent code: (latent_dim) -> Reconstructed: (timesteps, n_features).
    """
    keras = _get_keras()
    from keras import layers

    inputs = layers.Input(shape=(timesteps, n_features), name="sequence_input")

    # Encoder LSTM (temporal compression across time steps)
    x = layers.LSTM(32, activation="relu", return_sequences=True)(inputs)
    latent_seq = layers.LSTM(latent_dim, activation="relu", return_sequences=False, name="latent_layer")(x)

    encoder = keras.Model(inputs=inputs, outputs=latent_seq, name="LSTM_Sequence_Encoder")

    # Decoder LSTM (sequence reconstruction)
    d = layers.RepeatVector(timesteps)(latent_seq)
    d = layers.LSTM(latent_dim, activation="relu", return_sequences=True)(d)
    d = layers.LSTM(32, activation="relu", return_sequences=True)(d)
    decoded = layers.TimeDistributed(layers.Dense(n_features), name="reconstructed_sequence")(d)

    autoencoder = keras.Model(inputs=inputs, outputs=decoded, name="LSTM_Sequence_Autoencoder")
    autoencoder.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error"
    )
    return autoencoder, encoder


class LSTMAERandomForestModel(BaseMultiScaleModel):
    """
    Hybrid Architecture: LSTM Autoencoder + Random Forest Regressor.
    Operates on 3D temporal sequence windows (samples, timesteps, features).
    """

    def __init__(
        self,
        timesteps: int = 12,
        n_features: int = 10,
        input_dim: Optional[int] = None,  # backwards compatibility
        latent_dim: int = 8,
        n_estimators: int = 100,
        max_depth: Optional[int] = 12,
        lr: float = 0.001,
        random_state: int = 42
    ):
        super().__init__(name="LSTM Autoencoder + Random Forest", model_type="hybrid_traditional_deep")
        self.timesteps = timesteps
        self.n_features = input_dim if input_dim is not None else n_features
        self.latent_dim = latent_dim
        self.params = {
            "timesteps": self.timesteps,
            "n_features": self.n_features,
            "latent_dim": latent_dim,
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "lr": lr,
            "random_state": random_state
        }
        self.encoder: Optional[Any] = None
        self.autoencoder: Optional[Any] = None
        self.rf: Optional[RandomForestRegressor] = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 20,
        batch_size: int = 32,
        verbose: int = 0
    ) -> "LSTMAERandomForestModel":
        if X_train.ndim == 3:
            self.timesteps = X_train.shape[1]
            self.n_features = X_train.shape[2]
            X_tr = X_train
        elif X_train.ndim == 2:
            self.timesteps = 1
            self.n_features = X_train.shape[1]
            X_tr = np.expand_dims(X_train, axis=1)
        else:
            raise ValueError(f"Expected 2D or 3D input, got ndim={X_train.ndim}")

        self.params["timesteps"] = self.timesteps
        self.params["n_features"] = self.n_features

        # 1. Build and train LSTM Autoencoder ONLY on TRAIN set sequences (unsupervised reconstruction)
        self.autoencoder, self.encoder = build_lstm_autoencoder(
            timesteps=self.timesteps,
            n_features=self.n_features,
            latent_dim=self.latent_dim,
            lr=self.params["lr"]
        )

        val_data = None
        if X_val is not None:
            X_v = np.expand_dims(X_val, axis=1) if X_val.ndim == 2 else X_val
            val_data = (X_v, X_v)

        self.autoencoder.fit(
            X_tr,
            X_tr,
            validation_data=val_data,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose
        )

        # 2. Extract latent representations for TRAIN set
        latent_train = self.encoder.predict(X_tr, verbose=0)
        # Combine current timestep features at t with deep latent code
        current_state_features = X_tr[:, -1, :]
        X_train_augmented = np.hstack([current_state_features, latent_train])

        # 3. Train Random Forest on augmented latent feature space
        self.rf = RandomForestRegressor(
            n_estimators=self.params["n_estimators"],
            max_depth=self.params["max_depth"],
            random_state=self.params["random_state"],
            n_jobs=-1
        )
        self.rf.fit(X_train_augmented, y_train)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.encoder is None or self.rf is None:
            raise RuntimeError("Hybrid model is not fitted yet.")

        enc_shape = getattr(self.encoder, "input_shape", None)
        is_2d_encoder = (enc_shape is not None and len(enc_shape) == 2)

        if is_2d_encoder:
            # 2D Tabular encoder
            if X.ndim == 3:
                X_in = X[:, -1, :]  # current/latest state
            elif X.ndim == 2:
                X_in = X
            else:
                raise ValueError(f"Unsupported input dimension for 2D encoder: {X.ndim}")

            latent = self.encoder.predict(X_in, verbose=0)
            X_augmented = np.hstack([X_in, latent])
            return self.rf.predict(X_augmented)
        else:
            # 3D Sequence encoder
            if X.ndim == 3:
                X_in = X
            elif X.ndim == 2:
                if self.timesteps == 1:
                    X_in = np.expand_dims(X, axis=1)
                elif X.shape[0] == 1:
                    X_in = np.repeat(np.expand_dims(X, axis=1), self.timesteps, axis=1)
                elif X.shape[0] >= self.timesteps:
                    from src.core.features.sequences import build_temporal_sequences_from_matrix
                    X_in, _ = build_temporal_sequences_from_matrix(X, np.zeros(len(X)), sequence_length=self.timesteps)
                else:
                    X_in = np.repeat(np.expand_dims(X[:1], axis=1), self.timesteps, axis=1)
            else:
                raise ValueError(f"Unsupported input dimension for prediction: {X.ndim}")

            latent = self.encoder.predict(X_in, verbose=0)
            current_state = X_in[:, -1, :]
            X_augmented = np.hstack([current_state, latent])
            return self.rf.predict(X_augmented)

    def save(self, artifact_dir: str) -> str:
        os.makedirs(artifact_dir, exist_ok=True)
        # Save encoder
        encoder_file = os.path.join(artifact_dir, "encoder.keras")
        if self.encoder is not None:
            self.encoder.save(encoder_file)

        # Save RF
        rf_file = os.path.join(artifact_dir, "rf_head.joblib")
        joblib.dump(self.rf, rf_file)

        # Save metadata
        meta_file = os.path.join(artifact_dir, "hybrid_meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "timesteps": self.timesteps,
                "n_features": self.n_features,
                "latent_dim": self.latent_dim,
                "params": self.params
            }, f, indent=2)

        return encoder_file

    @classmethod
    def load(cls, artifact_dir: str) -> "LSTMAERandomForestModel":
        keras = _get_keras()
        meta_file = os.path.join(artifact_dir, "hybrid_meta.json")
        timesteps = 12
        n_features = 10
        latent_dim = 8
        params = {}
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                timesteps = saved.get("timesteps", 12)
                n_features = saved.get("n_features", 10)
                latent_dim = saved.get("latent_dim", 8)
                params = saved.get("params", {})

        instance = cls(timesteps=timesteps, n_features=n_features, latent_dim=latent_dim, **{k: v for k, v in params.items() if k not in ["timesteps", "n_features", "latent_dim"]})

        encoder_file = os.path.join(artifact_dir, "encoder.keras")
        instance.encoder = keras.models.load_model(encoder_file, compile=False)

        # Inspect actual input_shape of the loaded encoder
        enc_shape = getattr(instance.encoder, "input_shape", None)
        if enc_shape is not None:
            if len(enc_shape) == 2:
                instance.timesteps = 1
                instance.n_features = enc_shape[1]
            elif len(enc_shape) == 3:
                instance.timesteps = enc_shape[1] or timesteps
                instance.n_features = enc_shape[2] or n_features

        rf_file = os.path.join(artifact_dir, "rf_head.joblib")
        instance.rf = joblib.load(rf_file)
        instance.is_fitted = True
        return instance

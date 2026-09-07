"""
Módulo de Arquitecturas de Redes Neuronales (TensorFlow / Keras) para AgroTwin-AI.
Define las 5 arquitecturas de Deep Learning para predecir el índice de estrés hídrico (CWSI).
"""

import keras
from keras import layers, regularizers

def build_mlp_model(input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """
    1. Deep Multi-Layer Perceptron (DNN Profundo)
    Red Densa con Normalización por Lotes y Regularización Dropout.
    """
    inputs = layers.Input(shape=(input_dim,), name="input_features")
    x = layers.Dense(128, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout)(x)
    
    x = layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout)(x)
    
    x = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="linear", name="output_cwsi")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="Deep_MLP_Model")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_cnn1d_model(input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """
    2. 1D-CNN (Temporal / Feature Convolutional Neural Network)
    Captura correlaciones locales multivariables mediante filtros convolucionales 1D.
    """
    inputs = layers.Input(shape=(input_dim,), name="input_features")
    x = layers.Reshape((input_dim, 1))(inputs)
    
    x = layers.Conv1D(64, kernel_size=3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(pool_size=2)(x)
    
    x = layers.Conv1D(32, kernel_size=3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Flatten()(x)
    
    x = layers.Dense(32, activation="relu")(x)
    x = layers.Dropout(dropout)(x)
    outputs = layers.Dense(1, activation="linear", name="output_cwsi")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="1D_CNN_Model")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_lstm_model(input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """
    3. LSTM (Long Short-Term Memory)
    Red Neuronal Recurrente para aprender dependencias e inercia hídrica en secuencias.
    """
    inputs = layers.Input(shape=(input_dim,), name="input_features")
    x = layers.Reshape((input_dim, 1))(inputs)
    
    x = layers.LSTM(64, return_sequences=True)(x)
    x = layers.Dropout(dropout)(x)
    x = layers.LSTM(32, return_sequences=False)(x)
    x = layers.Dropout(dropout)(x)
    
    x = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="linear", name="output_cwsi")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="LSTM_Recurrent_Model")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_cnn_lstm_model(input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """
    4. Híbrido CNN-LSTM
    Etapa convolucional para extracción de features espaciales + celda recurrente LSTM.
    """
    inputs = layers.Input(shape=(input_dim,), name="input_features")
    x = layers.Reshape((input_dim, 1))(inputs)
    
    x = layers.Conv1D(64, kernel_size=3, padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(pool_size=2)(x)
    
    x = layers.LSTM(32, return_sequences=False)(x)
    x = layers.Dropout(dropout)(x)
    
    x = layers.Dense(32, activation="relu")(x)
    outputs = layers.Dense(1, activation="linear", name="output_cwsi")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="Hybrid_CNN_LSTM_Model")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def build_autoencoder_regressor_model(input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """
    5. Híbrido Autoencoder con Cabezal de Regresión
    Comprime la dimensionalidad ruidosa de los sensores y predice sobre el espacio latente.
    """
    inputs = layers.Input(shape=(input_dim,), name="input_features")
    
    # Encoder
    enc = layers.Dense(64, activation="relu")(inputs)
    enc = layers.BatchNormalization()(enc)
    latent = layers.Dense(16, activation="relu", name="latent_space")(enc)
    
    # Regressor Head conectado al espacio latente
    reg = layers.Dense(32, activation="relu")(latent)
    reg = layers.Dropout(dropout)(reg)
    outputs = layers.Dense(1, activation="linear", name="output_cwsi")(reg)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="Hybrid_Autoencoder_Model")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="mean_squared_error",
        metrics=["mae", "mse"]
    )
    return model


def get_model_by_name(name: str, input_dim: int, lr: float = 0.001, dropout: float = 0.3) -> keras.Model:
    """Instancia el modelo correspondiente según su nombre."""
    if "MLP" in name or "DNN" in name:
        return build_mlp_model(input_dim, lr, dropout)
    elif "CNN-LSTM" in name:
        return build_cnn_lstm_model(input_dim, lr, dropout)
    elif "1D-CNN" in name or "Conv" in name:
        return build_cnn1d_model(input_dim, lr, dropout)
    elif "LSTM" in name:
        return build_lstm_model(input_dim, lr, dropout)
    elif "Autoencoder" in name:
        return build_autoencoder_regressor_model(input_dim, lr, dropout)
    else:
        return build_mlp_model(input_dim, lr, dropout)

"""
Módulo de Entrenamiento y Validación Cruzada (K-Fold CV) para AgroTwin-AI.
Orquesta el entrenamiento de los 5 modelos, cálculo de métricas y exportación a .keras y .h5.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

from src.utils.config import (
    DATASET_RAW_PATH,
    MODELS_DIR,
    HISTORY_PATH,
    SCALER_PATH,
    MODEL_PATHS
)
from src.core.dataset_generator import get_dataset
from src.core.model_architectures import get_model_by_name

FEATURE_COLS = [
    "temp_max",
    "temp_min",
    "temp_mean",
    "solar_rad",
    "rh_mean",
    "vpd_kpa",
    "wind_speed",
    "precip_mm",
    "precip_3d",
    "streamflow_m3s",
    "soil_moisture_vol",
    "et0_mm"
]
TARGET_COL = "cwsi_stress_index"

MODEL_NAMES = [
    "Deep MLP (DNN)",
    "1D-CNN (Temporal ConvNet)",
    "LSTM Recurrente",
    "Híbrido CNN-LSTM",
    "Híbrido Autoencoder"
]

def calculate_nse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calcula el Coeficiente de Eficiencia de Nash-Sutcliffe (NSE)."""
    denominator = np.sum((y_true - np.mean(y_true)) ** 2)
    if denominator == 0:
        return 1.0
    numerator = np.sum((y_true - y_pred) ** 2)
    return float(1.0 - (numerator / denominator))


def train_pipeline(
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 0.001,
    dropout: float = 0.3,
    k_folds: int = 5,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline completo de entrenamiento con K-Fold CV sobre los 5 modelos.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # 1. Carga y preparación del dataset
    df = get_dataset()
    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values
    
    # Ajustar y guardar el escalador global
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
        
    kf = KFold(n_splits=k_folds, shuffle=True, random_state=42)
    input_dim = len(FEATURE_COLS)
    
    results = {}
    history_records = {}
    best_overall_model = None
    best_overall_score = -999.0
    best_model_name = None
    best_predictions = None
    y_test_all = None
    
    total_steps = len(MODEL_NAMES) * k_folds
    step = 0
    
    for model_name in MODEL_NAMES:
        fold_r2 = []
        fold_rmse = []
        fold_mae = []
        fold_nse = []
        fold_histories = []
        
        all_y_true = []
        all_y_pred = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_scaled, y)):
            step += 1
            if progress_callback:
                pct = step / total_steps
                progress_callback(pct, f"Entrenando {model_name} (Fold {fold + 1}/{k_folds})...")
                
            X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = get_model_by_name(model_name, input_dim=input_dim, lr=lr, dropout=dropout)
            
            # Entrenamiento silencioso por fold
            h = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                verbose=0
            )
            
            val_preds = model.predict(X_val, verbose=0).flatten()
            
            r2 = float(r2_score(y_val, val_preds))
            rmse = float(np.sqrt(mean_squared_error(y_val, val_preds)))
            mae = float(mean_absolute_error(y_val, val_preds))
            nse = float(calculate_nse(y_val, val_preds))
            
            fold_r2.append(r2)
            fold_rmse.append(rmse)
            fold_mae.append(mae)
            fold_nse.append(nse)
            
            all_y_true.extend(y_val.tolist())
            all_y_pred.extend(val_preds.tolist())
            
            # Guardar pérdidas para curvas de aprendizaje
            fold_histories.append({
                "loss": [float(x) for x in h.history.get("loss", [])],
                "val_loss": [float(x) for x in h.history.get("val_loss", [])],
                "mae": [float(x) for x in h.history.get("mae", [])],
                "val_mae": [float(x) for x in h.history.get("val_mae", [])]
            })
            
        mean_r2 = float(np.mean(fold_r2))
        mean_rmse = float(np.mean(fold_rmse))
        mean_mae = float(np.mean(fold_mae))
        mean_nse = float(np.mean(fold_nse))
        
        results[model_name] = {
            "r2": round(mean_r2, 4),
            "rmse": round(mean_rmse, 4),
            "mae": round(mean_mae, 4),
            "nse": round(mean_nse, 4),
            "y_true": all_y_true,
            "y_pred": all_y_pred,
            "fold_r2": [round(x, 4) for x in fold_r2],
            "fold_rmse": [round(x, 4) for x in fold_rmse]
        }
        
        history_records[model_name] = fold_histories
        
        # Entrenar modelo final completo con todo el dataset para exportación
        final_model = get_model_by_name(model_name, input_dim=input_dim, lr=lr, dropout=dropout)
        final_model.fit(X_scaled, y, epochs=epochs, batch_size=batch_size, verbose=0)
        
        # Guardar archivo individual .keras
        model_path = MODEL_PATHS.get(model_name)
        if model_path:
            final_model.save(model_path)
            
        # Comprobar si es el campeón
        if mean_r2 > best_overall_score:
            best_overall_score = mean_r2
            best_overall_model = final_model
            best_model_name = model_name
            best_predictions = all_y_pred
            y_test_all = all_y_true
            
    # Guardar el modelo campeón en formatos .keras y .h5
    if best_overall_model is not None:
        best_keras_path = MODEL_PATHS["Modelo Campeón (.keras)"]
        best_h5_path = MODEL_PATHS["Modelo Campeón (.h5)"]
        best_overall_model.save(best_keras_path)
        best_overall_model.save(best_h5_path)
        print(f"🏆 Modelo Campeón guardado: {best_model_name} (R² = {best_overall_score:.4f})")
        
    # Guardar resumen en history.json
    history_payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "best_model_name": best_model_name,
        "best_r2_score": round(best_overall_score, 4),
        "hyperparameters": {
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": lr,
            "dropout": dropout,
            "k_folds": k_folds
        },
        "models": {k: {m: v for m, v in vals.items() if m not in ["y_true", "y_pred"]} for k, vals in results.items()},
        "training_curves": history_records
    }
    
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history_payload, f, indent=2)
        
    return {
        "best_model_name": best_model_name,
        "best_r2_score": best_overall_score,
        "results": results,
        "history": history_payload
    }

"""
Módulo de Inferencia y Diagnóstico de Estrés Hídrico para AgroTwin-AI.
Carga modelos con caché de Streamlit y calcula dosificación de riego en tiempo real.
"""

import os
import pickle
import numpy as np
import streamlit as st
import keras

from src.utils.config import MODEL_PATHS, SCALER_PATH, STRESS_CLASSES
from src.core.trainer import FEATURE_COLS

@st.cache_resource
def load_scaler():
    """Carga el escalador StandardScaler entrenado."""
    if not os.path.exists(SCALER_PATH):
        return None
    with open(SCALER_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_resource
def load_single_model(model_key: str = "Modelo Campeón (.keras)"):
    """
    Carga un modelo Keras con caché de Streamlit.
    Busca preferentemente el archivo .keras o el fallback .h5.
    """
    path = MODEL_PATHS.get(model_key)
    if not path or not os.path.exists(path):
        # Fallback al campeón
        path = MODEL_PATHS.get("Modelo Campeón (.keras)")
        if not path or not os.path.exists(path):
            path = MODEL_PATHS.get("Modelo Campeón (.h5)")
            
    if not path or not os.path.exists(path):
        return None
        
    try:
        model = keras.models.load_model(path, compile=False)
        return model
    except Exception as e:
        print(f"❌ Error al cargar modelo {model_key}: {e}")
        return None


def predict_stress_and_irrigation(input_dict: dict, model_key: str = "Modelo Campeón (.keras)") -> dict:
    """
    Realiza la inferencia completa:
    1. Preprocesamiento con StandardScaler
    2. Predicción de CWSI con la Red Neuronal
    3. Categorización del semáforo de estrés
    4. Cálculo de prescripción de riego tecnificado (mm, m3/ha, L/árbol).
    """
    scaler = load_scaler()
    model = load_single_model(model_key)
    
    # Vector de entrada ordenado según FEATURE_COLS
    features = []
    for col in FEATURE_COLS:
        val = input_dict.get(col, 0.0)
        features.append(float(val))
        
    features_arr = np.array([features])
    
    if scaler is not None:
        features_scaled = scaler.transform(features_arr)
    else:
        features_scaled = features_arr
        
    if model is not None:
        raw_pred = float(model.predict(features_scaled, verbose=0)[0][0])
        cwsi = round(max(0.0, min(1.0, raw_pred)), 3)
    else:
        # Fallback analítico aproximado de Feddes si no se ha entrenado aún
        theta = input_dict.get("soil_moisture_vol", 25.0)
        cwsi = round(max(0.0, min(1.0, 1.0 - (theta - 12.0) / 20.0)), 3)
        
    # Clasificación semafórica
    if cwsi < 0.25:
        category = 0
        severity_label = "Óptimo"
        css_class = "healthy"
    elif cwsi < 0.55:
        category = 1
        severity_label = "Moderado"
        css_class = "warning"
    else:
        category = 2
        severity_label = "Crítico"
        css_class = "critical"
        
    stress_info = STRESS_CLASSES[category]
    
    # Cálculo agronómico de riego tecnificado
    et0 = input_dict.get("et0_mm", 4.0)
    theta_curr = input_dict.get("soil_moisture_vol", 22.0)
    
    # Transpiración real estimada
    actual_tr = round(et0 * 1.05 * (1.0 - cwsi), 2)
    
    # Lámina neta requerida (mm)
    if cwsi > 0.15:
        # Reposición de déficit hasta Capacidad de Campo (32% vol)
        deficit = max(0.0, 32.0 - theta_curr)
        # Lámina neta (mm) = Deficit / 100 * Profundidad Radicular Efectiva (800 mm) * Fracción agotada
        net_irrigation_mm = round(max(0.0, (deficit / 100.0) * 800.0 * 0.18 + (cwsi * 2.8)), 2)
    else:
        net_irrigation_mm = 0.0
        
    # Eficiencia de riego por goteo (85%)
    gross_irrigation_mm = round(net_irrigation_mm / 0.85, 2)
    
    # Volumen en m3/ha (1 mm = 10 m3/ha)
    volume_m3_ha = round(gross_irrigation_mm * 10.0, 1)
    
    # Litros por árbol (densidad típica 333 árboles/ha para palto Hass)
    liters_per_tree = round((volume_m3_ha * 1000.0) / 333.0, 1)
    
    return {
        "cwsi": cwsi,
        "category": category,
        "category_name": stress_info["name"],
        "severity_label": severity_label,
        "badge": stress_info["badge"],
        "color": stress_info["color"],
        "css_class": css_class,
        "description": stress_info["desc"],
        "actual_transpiration_mm": actual_tr,
        "net_irrigation_mm": net_irrigation_mm,
        "gross_irrigation_mm": gross_irrigation_mm,
        "volume_m3_ha": volume_m3_ha,
        "liters_per_tree": liters_per_tree,
        "model_used": model_key
    }

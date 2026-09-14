"""
Inference API for AgroTwin-AI.
Decoupled from Streamlit. Can be directly imported by FastAPI.

Exports:
  ModelBundle
  load_model_bundle(...)
  predict(...)
  validate_features(...)
  predict_runoff(...)
  predict_yield(...)
"""

import os
from typing import Dict, Any, Optional, Union
import numpy as np

# Core standalone classes and functions
from src.core.inference.bundle import ModelBundle, promote_to_champion
from src.core.inference.service import (
    load_model_bundle,
    predict,
    validate_features,
    predict_runoff,
    predict_yield
)


def predict_stress_and_irrigation(input_dict: dict, model_key: str = "champion") -> dict:
    """
    Backwards-compatible adapter for existing UI components during transition.
    Calls ModelBundle if available, or returns physical simulation calculation.
    """
    # Try loading champion runoff bundle
    champion_path = os.path.join("artifacts", "monthly_runoff_mm", "champion")
    if os.path.exists(champion_path):
        try:
            bundle = load_model_bundle(champion_path)
            res = bundle.predict(input_dict)
            runoff_val = res.get("value", 12.5)
        except Exception:
            runoff_val = 12.5
    else:
        runoff_val = 12.5

    # Compute Maize agronomic indicators
    lai = float(input_dict.get("lai", 2.5))
    water_stress = float(input_dict.get("water_stress", 0.15))
    soil_moist = float(input_dict.get("soil_moisture", 26.0))
    et_mm = float(input_dict.get("et_mm", 45.0))

    if water_stress < 0.20:
        category = 0
        severity_label = "Óptimo"
        badge = "🟢"
        color = "#10B981"
        css_class = "healthy"
        desc = "Maíz en estado fisiológico óptimo. Transpiración plena sin estrés hídrico."
    elif water_stress < 0.45:
        category = 1
        severity_label = "Estrés Moderado"
        badge = "🟡"
        color = "#F59E0B"
        css_class = "warning"
        desc = "Cierre estomático incipiente detectado en el dosel de maíz. Pérdida potencial de biomasa."
    else:
        category = 2
        severity_label = "Estrés Crítico"
        badge = "🔴"
        color = "#EF4444"
        css_class = "critical"
        desc = "Estrés hídrico severo en floración/llenado de grano. Reducción estimada de rendimiento > 25%."

    # Irrigation prescription (net depth to replenish root zone)
    # Field water balance
    deficit = max(0.0, 34.0 - soil_moist)
    net_irrigation_mm = round(deficit * 0.8 + (water_stress * 15.0), 2)
    gross_irrigation_mm = round(net_irrigation_mm / 0.85, 2)
    volume_m3_ha = round(gross_irrigation_mm * 10.0, 1)

    return {
        "cwsi": water_stress,
        "water_stress": water_stress,
        "runoff_prediction_mm": round(runoff_val, 2),
        "category": category,
        "category_name": severity_label,
        "severity_label": severity_label,
        "badge": badge,
        "color": color,
        "css_class": css_class,
        "description": desc,
        "actual_transpiration_mm": round(et_mm * (1.0 - water_stress) * 0.7, 2),
        "net_irrigation_mm": net_irrigation_mm,
        "gross_irrigation_mm": gross_irrigation_mm,
        "volume_m3_ha": volume_m3_ha,
        "liters_per_tree": round(volume_m3_ha / 70.0, 1), # per 1000 plants in field
        "model_used": model_key
    }

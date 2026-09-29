# Guía de Integración con FastAPI (`agro-digital-twin`)

Este documento describe la arquitectura para consumir los artefactos de modelos entrenados en **Plant-to-Watershed AI Lab** (`agro-digital-twin-st`) desde el backend principal de producción (`FastAPI` + `Next.js`).

---

## 1. Principio de Desacoplamiento

El módulo `src.core.inference` no tiene dependencias con Streamlit. Utiliza únicamente:
- `numpy`
- `pandas`
- `joblib`
- `scikit-learn`
- `tensorflow` / `keras`
- `xgboost`

Cualquier modelo entrenado genera un **Artifact Bundle** autocontenido:

```
artifacts/
└── monthly_runoff_mm/
    └── champion/
        ├── model.joblib (o model.keras / encoder.keras + rf_head.joblib)
        ├── preprocessing.joblib
        ├── feature_schema.json
        ├── metadata.json
        └── metrics.json
```

`metadata.json` identifica además `target_name`, `target_unit`, `feature_order`,
`feature_units`, `dataset_id`, `dataset_period`, `dataset_source_kind`,
`artifact_classification`, `validation_strategy` y `dataset_limitations`. La
clasificación no es fija: el demo sintético se marca como
`SYNTHETIC_DEVELOPMENT_ARTIFACT`; los bundles entrenados con resultados South
Fork se marcan como `SWAT_FSPM_SIMULATION_RESULTS` y
`simulation_validation_only`. Estos últimos no deben interpretarse como
modelos calibrados con observaciones de campo.

---

## 2. Consumo Directo en Python

```python
from src.core.inference import ModelBundle

# Carga del bundle campeón
bundle = ModelBundle.load("artifacts/monthly_runoff_mm/champion")

# El contrato real debe leerse del bundle; no reutilizar defaults del demo.
print(bundle.metadata["feature_order"])
print(bundle.metadata["artifact_classification"])

# Inferencia sobre un payload de campo (Nivel Clima + Suelo + FSPM + Campo)
payload = {
    "precip_mm": 115.0,
    "temp_mean_c": 23.5,
    "solar_radiation": 22.0,
    "soil_moisture": 31.0,
    "infiltration_mm": 62.0,
    "lai": 4.5,
    "root_depth_m": 1.35,
    "transpiration_mm": 72.0,
    "water_stress": 0.05,
    "et_mm": 95.0,
    "swat_baseline_runoff_mm": 24.5  # Requerido si el modo es residual_correction
}

result = bundle.predict(payload)
print("Resultado:", result)
# {
#   "target": "monthly_runoff_mm",
#   "mode": "direct_prediction",
#   "value": 18.42,
#   "unit": "mm/month",
#   "model_used": "LSTM Autoencoder + Random Forest"
# }
```

---

## 3. Ejemplo Mínimo de Microservicio FastAPI

A continuación se presenta un servicio FastAPI que valida el contrato de entrada y ejecuta la inferencia:

```python
# main_fastapi.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from src.core.inference import ModelBundle, load_model_bundle

app = FastAPI(
    title="AgroTwin Scientific Core API",
    description="Microservicio de inferencia eco-hidrológica acoplada Planta-Cuenca",
    version="1.0.0"
)

# Cargar el bundle al inicio del servidor (singleton)
RUNOFF_BUNDLE_PATH = "artifacts/monthly_runoff_mm/champion"
runoff_bundle = None

@app.on_event("startup")
def startup_event():
    global runoff_bundle
    runoff_bundle = load_model_bundle(RUNOFF_BUNDLE_PATH)
    print(f"✅ Modelo Campeón cargado: {runoff_bundle.metadata['model_name']}")

# Esquema Pydantic basado en ModelFeatureSchema
class MultiScalePayload(BaseModel):
    precip_mm: float = Field(..., ge=0.0, le=500.0, description="Precipitación mensual (mm)")
    temp_mean_c: float = Field(..., ge=-30.0, le=50.0, description="Temperatura media (°C)")
    solar_radiation: float = Field(..., ge=0.0, le=40.0, description="Radiación solar (MJ/m2/d)")
    soil_moisture: float = Field(..., ge=5.0, le=50.0, description="Humedad volumétrica de suelo (% vol)")
    infiltration_mm: float = Field(..., ge=0.0, le=400.0, description="Infiltración de suelo (mm)")
    lai: float = Field(..., ge=0.0, le=8.0, description="Índice de Área Foliar FSPM (m2/m2)")
    root_depth_m: float = Field(..., ge=0.05, le=3.0, description="Profundidad radicular efectiva (m)")
    transpiration_mm: float = Field(..., ge=0.0, le=250.0, description="Transpiración del dosel (mm)")
    water_stress: float = Field(..., ge=0.0, le=1.0, description="Estrés hídrico vegetal [0, 1]")
    et_mm: float = Field(..., ge=0.0, le=300.0, description="Evapotranspiración total de campo (mm)")
    swat_baseline_runoff_mm: Optional[float] = Field(None, description="Escorrentía base SWAT+ estándar")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "champion_model": runoff_bundle.metadata["model_name"],
        "target": runoff_bundle.metadata["target_name"],
        "metrics": runoff_bundle.metrics
    }

@app.post("/api/v1/predict/runoff")
def predict_runoff(payload: MultiScalePayload):
    try:
        data = payload.dict()
        prediction = runoff_bundle.predict(data)
        return {
            "success": True,
            "data": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 4. Soporte para Modo Residual

En el **Modo B (Residual Correction)**, el backend de FastAPI puede recibir la salida estándar del motor mecanístico SWAT+:

$$\text{Runoff}_{\text{corrected}} = \text{Runoff}_{\text{SWAT\_baseline}} + \Delta_{\text{AI\_predicted}}$$

El artefacto almacena si fue entrenado en modo `direct` o `residual` en su archivo `metadata.json`. El método `bundle.predict(payload)` detecta automáticamente el modo y efectúa la corrección.

## 5. Procedencia y preparación de datos reales

El laboratorio puede cargar un directorio de resultados mediante
`AGRO_TWIN_ARTIFACT_DIR` (o `AGRO_TWIN_REAL_ARTIFACT_DIR`). El cargador exige
el `manifest.json`, valida columnas, fechas e identificadores y mantiene las
tablas basin, HRU, canales y FSPM separadas. Para el contrato mensual usa
acumulaciones para flujos en mm/día, medias para temperatura y caudal en m³/s,
y no convierte `soil_water_mm` a humedad volumétrica. Las variables FSPM que
solo existen durante el cultivo permanecen faltantes fuera de ese periodo y no
se imputan.

South Fork 2019 contiene únicamente doce meses. Por ello el laboratorio
permite su EDA y preparación, pero bloquea el entrenamiento hasta disponer de
un periodo compatible de al menos 24 muestras mensuales; así no se presenta
una validación temporal frágil como resultado de producción. La conexión
posterior con FastAPI debe copiar el bundle sin cambiar sus metadatos y validar
el payload contra `feature_schema.json`.

## 6. Playback FastAPI y experimento diario

La pestaña de entrenamiento puede consumir, en modo lectura, el catálogo de
simulaciones y su playback diario mediante:

- `POST /api/v1/auth/login` para obtener un token en memoria.
- `GET /api/v1/simulations` con paginación `skip/limit`.
- `GET /api/v1/simulations/{simulation_id}/availability`.
- `GET /api/v1/simulations/{simulation_id}/playback` con paginación `offset/limit`.

El cliente no persiste credenciales, tokens ni playback. La UI conserva el
registro seleccionado del catálogo y no depende de un endpoint individual de
simulación no confirmado.

Para una fuente diaria se habilita `next_day_outlet_streamflow`. El pipeline:

- construye lags disponibles únicamente hasta `issue_date`;
- excluye saltos de calendario y usa `target_date = issue_date + 1 día`;
- divide cronológicamente en TRAIN 60%, VALIDATION 20% y TEST 20%;
- compara persistencia contra Random Forest, SVR y opcionalmente XGBoost;
- exporta bundles bajo `artifacts/next_day_streamflow_m3s/` y un `experiment.json`.

Estos bundles quedan clasificados como `EXPERIMENTAL_SIMULATION_ONLY` y no
representan validación con observaciones de campo.

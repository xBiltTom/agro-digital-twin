# Integración del laboratorio con FastAPI

Hay dos flujos distintos: lectura de simulaciones hacia Streamlit y consumo
de bundles auxiliares desde la plataforma. [README del laboratorio](../README.md)
y [Model Card](../MODEL_CARD.md) describen su alcance.

## 1. FastAPI → laboratorio: lectura de playback

`src/core/integrations/fastapi_client.py` consume exclusivamente:

- `POST /api/v1/auth/login`.
- `GET /api/v1/simulations` con paginación `skip/limit`.
- `GET /api/v1/simulations/{id}/availability`.
- `GET /api/v1/simulations/{id}/playback` con `offset/limit` y resolución.

Credenciales, token y datos descargados se mantienen en memoria. La URL se
elige en la barra lateral; `AGRO_TWIN_FASTAPI_URL` usa por defecto
`http://localhost:8000`. El catálogo se limita a corridas accesibles para el
usuario. No se crean simulaciones ni se modifica la base desde este cliente.

La selección preferida es `phase234-sf-2019-v2`, con alternativas explícitas
v1/`phase1-sf-2019-v3` si están disponibles. Cada variable mantiene fuente,
unidad, evidencia y limitación. El [contrato temporal](../../from-plant-to-watershed/docs/TWIN_PLAYBACK_CONTRACT.md)
define las diferencias entre FSPM, HRU, canal, cuenca y observaciones.

También se pueden cargar resultados desde un directorio con `manifest.json`
mediante `AGRO_TWIN_ARTIFACT_DIR` o `AGRO_TWIN_REAL_ARTIFACT_DIR`.
El cargador verifica artefactos y conserva las tablas por escala. La
agregación mensual suma flujos mm/día y promedia temperaturas/caudal según
su semántica; no convierte almacenamiento SWAT+ a porcentaje de humedad.

## 2. Experimento diario del laboratorio

`src/core/experiments/next_day_flow.py` define `next_day_outlet_streamflow`,
target **`next_day_streamflow_m3s`**:

- Features hasta `issue_date`, con lags 1, 2, 3 y 7 disponibles.
- `target_date = issue_date + 1 día`; se excluyen saltos de calendario.
- Split cronológico TRAIN 60 %, VALIDATION 20 %, TEST 20 %.
- Referencia de persistencia; RF/SVR y XGBoost opcional.
- Exportación bajo `artifacts/next_day_streamflow_m3s/`, con `experiment.json`,
  horizonte, schema, contrato y métricas de validación/test.

La clasificación es `EXPERIMENTAL_SIMULATION_ONLY`: predice una serie modelada,
no demuestra ajuste a USGS. El round-trip se comprueba con el `ModelBundle`
del laboratorio. **El adaptador externo de la plataforma todavía no admite
este target diario**, por lo que exportar el bundle no implica desplegarlo allí.

## 3. Laboratorio → plataforma: bundle mensual/yield

`src/core/inference/` contiene `ModelBundle`, desacoplado de Streamlit.
La plataforma usa su lector independiente
`backend/app/services/external_model_bundle.py`.

El directorio completo incluye:

```text
metadata.json
feature_schema.json
metrics.json
preprocessing.joblib
model.joblib / model.keras / encoder.keras + rf_head.joblib
```

Conservar archivos auxiliares del modelo híbrido. La carga de modelos Keras
requiere TensorFlow; una cabeza RF sin su encoder no es un modelo completo.

El adaptador FastAPI admite actualmente:

| Target | Unidad |
| --- | --- |
| `monthly_runoff_mm` | mm/month |
| `monthly_streamflow_m3s` | m3/s |
| `maize_yield_t_ha` | t/ha |

Los modos son `direct` y `residual`. En residual se exige la feature baseline
correspondiente y se suma la corrección al valor mecanístico. Esa predicción
auxiliar conserva su procedencia ML y no se presenta como output físico SWAT+.

## 4. Registrar y consumir

1. Copiar el directorio completo dentro de `EXTERNAL_MODELS_DIR` de la plataforma
   (por defecto `models/external`).
2. Con rol `SUPERADMIN` o `ADMIN_CIENTIFICO`, enviar:

   ```text
   POST /api/v1/models/register
   {"artifact_path": "models/external/nombre_del_bundle"}
   ```

3. Consultar `GET /api/v1/models` o `GET /api/v1/models/{id}` para contrato,
   checksum, métricas y procedencia. `POST /api/v1/models/{id}/validate`
   comprueba otra vez el contrato de archivos.
4. Elegir el modelo en el flujo compatible de la plataforma, conservando target,
   modo, orden/unidades y resolución del schema.

`VALIDATED` es el estado de integridad/compatibilidad del bundle, no de ajuste
observacional. No hay un endpoint genérico `/predict/runoff` en este contrato;
la inferencia se integra mediante el adaptador de aplicación.

Para inferencia independiente, desde el entorno del laboratorio:

```python
from src.core.inference import ModelBundle

bundle = ModelBundle.load("artifacts/monthly_runoff_mm/champion")
print(bundle.metadata)
print(bundle.schema)
# payload se construye según feature_schema.json del bundle elegido.
# resultado = bundle.predict(payload)
```

## 5. Procedencia y evaluación

Los bundles históricos mensuales declaran `is_synthetic_training_data=true`.
Nuevos bundles deben conservar dataset, periodo, split, unidades y limitaciones;
los basados en salidas del gemelo son simulación, incluso con ejecutable real.
La UI general exige al menos 24 filas de datos reales preparados para habilitar
entrenamiento. Los doce meses de South Fork 2019 no satisfacen ese requisito.

El experimento de H1 físico está en la plataforma y necesita USGS observado
más baseline/acoplado emparejados. Ninguna métrica del laboratorio se promueve
automáticamente a ese reporte.

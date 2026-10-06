# Plant-to-Watershed AI Lab

Laboratorio Streamlit independiente para explorar datos, entrenar modelos
auxiliares y exportar bundles. La hidrología y el gemelo operativo residen en
la [plataforma FastAPI + Next.js](../from-plant-to-watershed/README.md).

## Fuentes y alcance

| Fuente | Uso | Evidencia |
| --- | --- | --- |
| Generador sintético | Desarrollo y demostración mensual de entrenamiento/inferencia. | `SYNTHETIC_DEVELOPMENT_ARTIFACT`. |
| Bundle South Fork con manifiesto | Exploración de tablas y preparación de resultados SWAT+/FSPM. | Simulación experimental con procedencia por variable. |
| Playback FastAPI diario | Experimento de pronóstico `next_day_streamflow_m3s`. | `EXPERIMENTAL_SIMULATION_ONLY`, no validación USGS. |

Los modelos mensuales presentes en `artifacts/monthly_runoff_mm/` fueron
entrenados con datos sintéticos. Su campeón LSTM Autoencoder + Random Forest
reporta NSE 0,9861 y RMSE 2,5809 mm/mes **sobre ese dataset sintético**.
No son resultados de la hipótesis de acoplamiento planta–cuenca.
Véase [Model Card](MODEL_CARD.md).

## Ejecutar

Desde esta carpeta:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

TensorFlow/Keras es necesario para CNN-LSTM e híbridos profundos; los bundles
tradicionales tienen carga independiente. El runtime solicita CPU por defecto
mediante `AGROTWIN_FORCE_CPU=1`.

## Cargar resultados del gemelo

Para un bundle local usar `AGRO_TWIN_ARTIFACT_DIR` o
`AGRO_TWIN_REAL_ARTIFACT_DIR` apuntando al directorio que contiene `manifest.json`.
El cargador valida hashes, columnas, fechas y claves; mantiene distintas las
tablas de cuenca, HRU, canales y plantas.

Para consumir la API, elegir la fuente FastAPI en la barra lateral. La URL
predeterminada es `http://localhost:8000`, configurable con
`AGRO_TWIN_FASTAPI_URL`. Login, token y playback permanecen en memoria de sesión.
El cliente pagina el catálogo, availability y playback, respetando el dueño de
la corrida. Prioriza `phase234-sf-2019-v2` cuando está disponible.

## Entrenamiento

- Pipeline general: Random Forest, XGBoost, SVR, CNN-LSTM y LSTM-AE + RF;
  particiones temporales/espaciales y preprocesador ajustado en TRAIN.
  Las ventanas se construyen dentro de unidad espacial y partición.
- South Fork 2019 solo aporta doce meses. La UI exige al menos 24 filas para
  habilitar entrenamiento de datos reales preparados; doce meses pueden
  explorarse, pero no justifican un modelo mensual validado.
- Experimento diario: lags 1, 2, 3 y 7 hasta `issue_date`, objetivo del día
  siguiente y exclusión de saltos de calendario; TRAIN/VALIDATION/TEST
  cronológico 60/20/20.
- Se comparan persistencia, RF, SVR y XGBoost opcional, con RMSE, MAE, R²,
  NSE, KGE y PBIAS. El resultado diario evalúa una parte posterior del mismo
  año simulado, no generalización observacional ni multicuenca.

Los porcentajes y etiquetas del pipeline actual no reescriben los metadatos
de los bundles históricos: cada artefacto se interpreta por su propio contrato.

## Código y exportación

- `src/core/datasets/`: fuentes sintéticas y carga de resultados con manifiesto.
- `src/core/integrations/fastapi_client.py`: cliente autenticado de lectura.
- `src/core/training/`: pipeline general y particiones.
- `src/core/experiments/next_day_flow.py`: experimento diario.
- `src/core/inference/`: `ModelBundle`, sin dependencia de Streamlit.
- `src/ui/`: presentación del flujo CRISP-DM.

La [guía de integración](docs/FASTAPI_INTEGRATION.md) explica los bundles y el
contrato aceptado por FastAPI. El target diario aún no está admitido por el
adaptador de modelos externos de la plataforma.

## Verificación

```bash
pytest
```

La verificación de fase 6B documentó 35 pruebas aprobadas de 37; las dos de
modelos profundos fallaron por ausencia de TensorFlow/Keras en aquel entorno.
También comprobó 365 filas del playback v1, 358 muestras preparadas y round-trip
RF/SVR. Es evidencia histórica de integración, no una ejecución nueva sobre v2.

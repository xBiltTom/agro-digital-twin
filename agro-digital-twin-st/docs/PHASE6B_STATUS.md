# Fase 6B: Estado de Cierre

## Alcance

La Fase 6B conecta el laboratorio Streamlit con el catálogo de simulaciones
FastAPI en modo lectura y añade un experimento reproducible de pronóstico diario
de caudal para South Fork.

## Entregado

- Cliente FastAPI autenticado en memoria, con paginación, caché y manejo de errores.
- Consumo exclusivo de login, catálogo, availability y playback.
- Normalización del playback a una tabla diaria con procedencia, unidades,
  evidencias y limitaciones.
- Selector de simulación FastAPI en la barra lateral de Streamlit.
- Selección automática de `phase234-sf-2019-v2`, con fallback explícito a v1 y
  `phase1-sf-2019-v3` cuando el artefacto exista.
- Experimento `next_day_streamflow_m3s` con lags 1, 2, 3 y 7, sin usar datos
  posteriores a `issue_date`.
- Exclusión de saltos de calendario para conservar un horizonte real de un día.
- Split cronológico TRAIN 60% / VALIDATION 20% / TEST 20%.
- Comparación contra persistencia y modelos Random Forest, SVR y XGBoost opcional.
- Métricas RMSE, MAE, R2, NSE, KGE y PBIAS.
- Bundles con `feature_schema.json`, `metadata.json`, `metrics.json`, horizonte,
  contrato de inferencia y clasificación `EXPERIMENTAL_SIMULATION_ONLY`.
- Reporte reproducible `experiment.json`.
- Documentación y pruebas de contrato/paginación, autenticación, preparación
  temporal y ausencia de fuga.

## Verificación

- Compilación de `src` y `tests`: correcta.
- Suite actual: `37` colectadas, `35` pasan; fallan únicamente los dos tests
  de modelos profundos.
- Los dos tests restantes requieren TensorFlow/Keras, dependencia declarada en
  `requirements.txt` pero no instalada en el entorno local usado para esta
  validación.
- Importación headless de Streamlit: correcta.
- Ejecución sobre `phase234-sf-2019-v1`: `365` filas diarias, `358` filas
  preparadas, bundles RF/SVR exportados y round-trip de inferencia verificado.
- En esa corrida, Random Forest fue el mejor candidato por RMSE, pero el
  resultado permanece clasificado como simulación experimental y no como
  validación observacional.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
pytest
```

La ejecución diaria se encuentra en la pestaña de entrenamiento cuando la
fuente activa tiene resolución `DAILY`.

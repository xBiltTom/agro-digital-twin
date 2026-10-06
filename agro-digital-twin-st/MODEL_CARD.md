# Model Card — modelos auxiliares Plant-to-Watershed

Revisión documental: 2026-10-05. El estado de investigación de la plataforma
está en [CURRENT_STATE](../from-plant-to-watershed/docs/CURRENT_STATE.md).

## Artefactos disponibles y uso previsto

Los bundles mensuales versionados en `artifacts/monthly_runoff_mm/` usan datos
de desarrollo sintéticos. El campeón es **LSTM Autoencoder + Random Forest**;
los candidatos incluyen RF, XGBoost, SVR, CNN-LSTM y LSTM-AE + RF.

Metadatos del campeón: `dataset_version=v1.0-synthetic-cornbelt`, seed 42 e
`is_synthetic_training_data=true`. Reporta RMSE 2,5809 mm/mes, NSE/R² 0,9861,
MAE 1,5438 mm/mes y PBIAS 1,77 %. Son métricas de ese artefacto sintético,
no desempeño observado en South Fork.

Uso previsto: desarrollo de pipelines, exploración e inferencia auxiliar bajo
el schema del bundle. Un bundle entrenado sobre resultados SWAT+/FSPM aprende
una simulación; no queda validado con datos de campo por usar un motor real.
Una corrección residual ML tampoco demuestra el efecto físico del acoplamiento.

## Targets y contratos

| Target | Unidad | Soporte |
| --- | --- | --- |
| `monthly_runoff_mm` | mm/mes | Laboratorio y adaptador FastAPI. |
| `monthly_streamflow_m3s` | m³/s | Laboratorio y adaptador FastAPI. |
| `maize_yield_t_ha` | t/ha | Laboratorio y adaptador FastAPI; sin validación observada HRU/cuenca demostrada. |
| `next_day_streamflow_m3s` | m³/s, horizonte 1 día | Experimento diario del laboratorio; aún no aceptado por el adaptador FastAPI externo. |

Leer `feature_schema.json`, orden, unidades, modo de aprendizaje, horizonte y
limitaciones del artefacto específico. No reutilizar features/defaults del demo
para un experimento nuevo. `soil_water_mm` SWAT+ no es humedad volumétrica.

## Datos, particiones y límites

- Demo histórico: tres etiquetas de cuenca, nueve etiquetas HRU y 2.808 filas
  sintéticas entre 2015 y 2029. No son cuencas de validación observacional.
- Pipeline general actual: partición TRAIN/VALIDATION/TEST, preprocesador en
  TRAIN y ventanas aisladas por unidad/partición. El manifiesto específico
  determina el split realmente usado por cada modelo guardado.
- Yield se prepara por temporada/año, no con ceros mensuales de rendimiento.
- Experimento diario South Fork: lags históricos, horizonte real de un día,
  split 60/20/20 y referencia de persistencia; clasificación
  `EXPERIMENTAL_SIMULATION_ONLY`.
- Un año simulado no demuestra transferencia a otros años/cuencas. La fuente
  meteorológica y la aproximación hídrica mantienen sus límites originales.
- La evaluación de modelos no sustituye la comparación emparejada física
  SWAT+ baseline/acoplado contra USGS que requiere la hipótesis.

## Bundle y dependencias

```text
bundle/
├── metadata.json
├── feature_schema.json
├── metrics.json
├── preprocessing.joblib
└── model.joblib / model.keras / encoder.keras + rf_head.joblib
```

Algunos modelos añaden archivos auxiliares, como `hybrid_meta.json`. Se conserva
el directorio completo. RF/SVR/XGBoost pueden cargar sin TensorFlow; los modelos
Keras y sus híbridos lo requieren. La forma de entrada se toma del modelo/schema,
incluidas ventanas 3D cuando proceden.

`VALIDATED` en el catálogo externo FastAPI significa que pasó validación del
contrato de archivos, no calibración ni validación científica observacional.
Instrucciones: [integración FastAPI](docs/FASTAPI_INTEGRATION.md).

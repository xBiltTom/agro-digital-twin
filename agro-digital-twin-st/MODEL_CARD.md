# Model Card — modelos auxiliares Plant-to-Watershed

Revisión documental: 2026-10-06. El estado de investigación de la plataforma
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

### Bundles observacionales C/D — `sf-ml-v1`

`artifacts/south_fork_monthly_residual_v1/C` y `D` predicen
`monthly_streamflow_m3s` en modo residual: `max(0, Q_físico + residual)`.
El target usa caudal USGS observado; los predictores son meteorología y estados
SWAT+/FSPM modelados. TRAIN 2013–2017 tiene 60 meses; VALIDATION 2018–2020,
previamente explorada, tiene 36. TEST 2021–2025 permanece reservado.

La búsqueda congelada de seis candidatos por brazo seleccionó Ridge α = 10
para ambos; pesos y StandardScaler permanecen ajustados solo en TRAIN.
RMSE VALIDATION: C 2,978153 y D 2,989931 m³/s, frente a A 4,007009 y B 3,921403.
D no supera C en desarrollo. El contraste cambia baseline y features; no aísla
el aporte FSPM. La referencia física conserva el sesgo exploratorio de calibración.

C requiere 14 features y D 21, según el esquema de cada bundle. D representa
estrés ausente mediante cero y fracción de disponibilidad; ese cero no es una
observación de ausencia de estrés. No se usan observaciones ni flags QC como
features. La inferencia consume el mes completo y es retrospectiva. No autoriza
extrapolación climática, decisiones agronómicas ni conclusiones de H1.
Clasificación `OBSERVATIONAL_DEVELOPMENT_ARTIFACT`, despliegue
`development_only_pending_reserved_test`; IDs pglocal `sf-ml-v1-c` y `sf-ml-v1-d`.
Véase [protocolo y resultados](../from-plant-to-watershed/docs/ML_RESIDUAL_DELIVERY_3.md).

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

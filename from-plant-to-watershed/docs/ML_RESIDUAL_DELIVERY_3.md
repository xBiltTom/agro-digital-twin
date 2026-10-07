# Entrega 3 — corrección residual mensual observacional

**Fecha:** 2026-10-06. **Experimento:** `sf-ml-v1`.
**Estado:** completado en pglocal; H1 `NOT_EVALUATED`, TEST reservado.

## Diseño congelado

El [protocolo ML](../research_domain/south_fork_ml_protocol_v1.json) se copió
con su recibo y hashes de implementación antes del primer ajuste. Consume el
dataset pareado `sf-multi-v1-monthly-ab`: 60 meses TRAIN (2013–2017) y 36 meses
VALIDATION (2018–2020), por brazo. VALIDATION ya se exploró y es desarrollo.
No se consultaron observaciones ni se publicaron predicciones de TEST 2021–2025.

- C: referencia física A y 14 features comunes.
- D: referencia física B, las mismas 14 features y siete rasgos FSPM.
- Target: `Q_observado − Q_físico`; salida: `max(0, Q_físico + residual_predicho)`.
- Features comunes: caudal físico, cinco variables meteorológicas, seis estados/
  flujos hídricos SWAT+ y seno/coseno del mes.
- Features adicionales D: LAI, profundidad radicular, biomasa, transpiración,
  estrés, fracción de días activos y fracción de días con estrés disponible.
- El cero que sustituye estrés ausente es un marcador acompañado de disponibilidad;
  no representa una medición de ausencia de estrés. Se conservan los ceros de
  cultivo inactivo y se rechazan faltantes estructurales o entradas no finitas.
- StandardScaler y estimadores se ajustan únicamente en los 60 meses TRAIN.
  Observado, residual, flags QC, IDs y particiones quedan fuera de las features.

La búsqueda usa exactamente seis candidatos en cada brazo: Ridge α = 0,1/1/10
y Random Forest de 100 árboles, hoja mínima de tres muestras, profundidad
2/4/sin límite, semilla 42. Todos cubren los mismos 36 meses de VALIDATION.
Se minimiza RMSE del caudal corregido, sin redondear; empate exacto por ID.
Los ganadores conservan pesos y scalers TRAIN, sin reajuste TRAIN+VALIDATION.

## Resultados de desarrollo

| Serie | RMSE VALIDATION (m³/s) |
| --- | ---: |
| A: SWAT+ estándar | 4,007009 |
| B: SWAT+ con parámetros vegetales congelados | 3,921403 |
| C: A + residual Ridge α = 10 | 2,978153 |
| D: B + FSPM + residual Ridge α = 10 | 2,989931 |
| Corrección afín A | 3,846913 |
| Corrección afín B | 3,847487 |
| Climatología mensual | 7,146630 |

Las referencias simples se ajustaron solo en TRAIN: media por mes calendario
y mínimos cuadrados afines con pendiente no negativa y clipping de salida.
Sus coeficientes y los doce candidatos completos están en
[el reporte de entrega](../research_domain/south_fork_ml_delivery_3_v1.json).
Las métricas usan `scientific_core.ValidationEngine`: PBIAS simulado menos
observado, KGE con cociente de coeficientes de variación.

C/D superan las referencias simples en estos años de desarrollo; D queda
ligeramente detrás de C. No demuestra ventaja adicional FSPM ni resuelve H1.
D vs C cambia simultáneamente la referencia física y las features, por lo que
no constituye una ablación que aísle el aporte de los rasgos vegetales.

La referencia física sigue siendo `BUDGET_EXHAUSTED_EXPLORATORY_REFERENCE`
por sesgo de calibración. ML no valida fisiología ni conserva un balance de
agua: corrige el caudal de salida. Las entradas abarcan el mes completo;
la inferencia es retrospectiva, sin promesa de pronóstico anticipado.

## Artefactos e integración

Los [bundles C/D](../../agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1/)
incluyen pesos, scalers, esquema estricto, metadata y métricas. También se
versionan protocolo, recibo previo al ajuste, selección, 432 predicciones de
candidatos en VALIDATION, 672 predicciones de desarrollo y manifiesto SHA-256.

Se registraron en la base **digitaltwin existente**:

- Modelos externos `sf-ml-v1-c` y `sf-ml-v1-d`.
- Dataset derivado `sf-ml-v1-development` y sus 17 artefactos.

El estado de registro `VALIDATED` significa contrato de bundle e inferencia
comprobados. Su procedencia declara desarrollo pendiente de TEST; no es una
validación científica externa. Las 96 inferencias de cada brazo coinciden
entre estimador entrenado, bundle del laboratorio y adaptador del backend
con tolerancia absoluta 10⁻¹⁰ m³/s. El backend puede consumir los bundles mediante
su API de modelos externos; el recorrido de usuario integrado corresponde
a la entrega 5.

Desde backend:

```bash
venv/bin/python scripts/run_south_fork_ml.py
```

Al repetir, reutiliza los pesos congelados y verifica hashes; cambios al
protocolo, inputs, implementación fijada o artefactos requieren investigar y
abrir una nueva versión experimental. No amplía el presupuesto ni reentrena
silenciosamente un ajuste incompleto.

## Reparaciones del laboratorio

Se eliminó la segunda suma del baseline al observado tabular; las secuencias
reconstruyen el observado con el baseline físico de la fecha objetivo y guardan
ese baseline aparte de las features escaladas. La selección mensual y diaria
usa VALIDATION, sin elegir al campeón por TEST. La inferencia residual exige
baseline y longitudes compatibles, y conserva precisión completa.
TensorFlow/XGBoost se cargan cuando se selecciona un modelo que los necesita.

La auditoría de inferencia se ejecutó como parte de la publicación científica
en pglocal. No se ejecutó una suite de tests ni se inspeccionó el navegador.

## Siguiente entrega

Entrega 4: publicar A/B sobre TEST reservado con parámetros ya congelados,
aplicar C/D y referencias simples sin ajustar pesos, y evaluar D vs A mediante
bootstrap temporal pareado de bloques de 12 meses, 2.000 réplicas, semilla 42 e
intervalo del 95 %. Añadir los contrastes secundarios y sensibilidad al excluir
valores USGS estimados. Una mejora en desarrollo no determina esa decisión.

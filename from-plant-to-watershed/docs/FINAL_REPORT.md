# Reporte científico publicado — piloto South Fork

## Versión y alcance

La API `GET /api/v1/reports/final-scientific` publica actualmente
**`south-fork-final-v2`**, según `research_domain/current_contract_status.json`.
El handler lee `research_domain/final_report_v2.json`. El resultado v1 permanece
en `research_domain/final_report.json` y se expone por separado en
`GET /api/v1/reports/final-scientific/archive-v1`.

La cuenca es South Fork Iowa River, estación `USGS 05451210`, HUC8 `07080207`.
Es una comparación temporal en una cuenca agrícola, no validación espacial
multicuenca. La [ficha técnica](../project_framework.md) establece la hipótesis.

## Resultados del experimento v2

- Periodo de simulación: 2015–2020.
- Warm-up: 2015–2017; evaluación USGS: 2018–2020.
- Baseline y acoplado comparten proyecto, clima, periodo y configuración general.
- Calibración `LIMITED_CALIBRATION`: no se optimizaron parámetros hidrológicos.
- El contrato v2 mapea diez parámetros vegetales de FSPM a `plants.plt`.

| Métrica mensual | Baseline | Acoplado |
| --- | ---: | ---: |
| RMSE (m³/s) | 9,4471246463 | 9,4471246463 |
| NSE | −0,6745616519 | −0,6745616519 |
| PBIAS (%) | −79,5795038821 | −79,5795038821 |
| KGE | −0,0812409027 | −0,0812409027 |
| R² | 0,0721072675 | 0,0721072675 |
| Reducción de RMSE | — | 0 % |

Conclusión guardada: **`H1_NOT_SUPPORTED`**.
Efecto guardado: `ZERO_WITH_CURRENT_PARAMETERIZATION`, etiqueta relativa a ese
experimento v2, no a toda versión posterior del software.

El evaluador usa caudal medio mensual del outlet en **m³/s**. No es la misma
variable que escorrentía superficial SWAT+ en mm. El umbral de reducción del
15 % es un criterio de desempeño; `ValidationEngine` declara
`NOT_FORMAL_HYPOTHESIS_TEST`. La serie diaria se reporta como diagnóstico,
sin convertirla en el contraste primario mensual.

## Interpretación después de las correcciones

El reporte v2 conserva el FSPM anterior a la corrección de humedad: una fracción
`0.24` fue interpretada como **0,24 %**, en lugar de 24 %. El código fue corregido
y los resultados históricos permanecen como se calcularon.

La [auditoría de fase 3.5](audits/PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md)
identificó además una incompatibilidad de serialización integral en el proyecto
de fase 3.4: `days_mat=120.00000` podía interrumpir la lectura del registro de
planta sin provocar el fallo del proceso SWAT+. En copias compatibles e
instrumentadas sí se observaron diferencias vegetales e hidrológicas.
Esa evidencia diagnóstica no repara retrospectivamente los reportes archivados.

La corrida posterior **`phase234-sf-2019-v2`** agrega calendarios ejecutados y
feedback hídrico aproximado. Su `validation` sigue como `NOT_AVAILABLE`:
es un gemelo operativo experimental, no un nuevo resultado de H1. Véanse
[estado actual](CURRENT_STATE.md) y [contrato de acoplamiento](FSPM_SWAT_PLUS_COUPLING.md).

## Escenarios, estadísticas y datos pendientes

El JSON v2 conserva escenarios `TEMPERATURE_PLUS_2C`,
`PRECIPITATION_MINUS_15PCT`, `NO_TILL` y `MAIZE_TO_SORGHUM`.
Sus deltas usan `HISTORICAL_COUPLED_V2` como referencia. No deben mezclarse
con los deltas v1 ni con los estados de la corrida diaria corregida.

- Los escenarios de temperatura/precipitación son perturbaciones controladas,
  no proyecciones normalizadas CMIP6.
- CMIP6 SSP2-4.5/SSP5-8.5: `NOT_AVAILABLE` en este experimento.
- Rendimiento observado a escala cuenca/HRU: sin crosswalk NASS validado.
- KS y Wilcoxon se conservan con sus estados y limitaciones en el JSON.
  La igualdad de errores no constituye evidencia favorable al acoplamiento.
- Sobol y bootstrap de rendimiento SSP5-8.5 no cuentan con una ejecución
  completa/evidencia suficiente para una conclusión final.

## Reproducción: qué hace hoy el runner final

Desde `from-plant-to-watershed/`, con el entorno Python preparado:

```bash
PYTHONPATH=backend \
SOUTH_FORK_SWAT_PROJECT=/ruta/al/proyecto/TxtInOut \
SWAT_PLUS_EXECUTABLE=/ruta/al/ejecutable/swatplus \
SOUTH_FORK_CDL_COMPOSITION=/ruta/a/hru_crop_composition.parquet \
SOUTH_FORK_FINAL_RUN_ROOT=/ruta/a/workspaces-nuevos \
backend/.venv/bin/python backend/scripts/run_final_south_fork.py
```

El script actual escribe, si termina correctamente:

- `research_domain/final_report_v3.json`.
- `research_domain/final_report_v3.status.json`.
- `data/final/experiment_dataset_v3.parquet` y su schema.

No hay esos reportes v3 en el repositorio revisado. El runner no cambia el
puntero publicado v2 y todavía usa **humedad FSPM constante asumida**.
Por tanto, este comando no reproduce byte por byte el experimento v2 ni evalúa
íntegramente el flujo diario con feedback de `swat_coupled_runner.py`.
Un experimento de esa ruta necesita su propia configuración, pareja, validación
observacional y reporte versionado.

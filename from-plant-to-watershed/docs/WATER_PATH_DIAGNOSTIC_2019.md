# Recorrido del agua y balance South Fork 2019

Fecha: **2026-10-06**. Continuación del
[diagnóstico de referencia](BASELINE_DIAGNOSTIC_2019.md).
Evidencia de desarrollo en PostgreSQL local `digitaltwin`; **H1 no evaluada**.

## Hallazgos

1. El drenaje generado sin conexión `til` deja unos **36,03 hm³** fuera del
   recorrido hacia los canales en la prueba 2019.
2. Hay además un error de reporte: la variante conectada transporta
   **103,55 hm³** al outlet, mientras `channel_sd_day.txt` informa **68,02 hm³**.
3. Las conexiones conservan el volumen transportado; referencia y variante
   conectada tienen residuos parciales de cuenca cercanos a **−0,012 mm**.
4. Persiste subestimación frente a USGS y los 37 canales funcionan como
   conexiones sin transformación física.

## Reporte y unidades

En SWAT+ **61.0.2.61**, la rama de canales artificiales conserva internamente
la suma de entradas, pero publica el último aporte recibido. Esta interpretación
proviene del [código oficial `command.f90`](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/command.f90)
y se contrastó con hidrogramas de entrada/salida de la corrida.

`hydin_day`, `hydout_day` y `ru_day` escriben `hyd_output.flo`, un volumen en
**m³**, aunque su encabezado declara m³/s. Lo establecen el
[tipo oficial del hidrograma](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/hydrograph_module.f90)
y la [rutina de escritura](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/hydin_output.f90).
Multiplicar esos volúmenes por 86400 introduciría un error de unidades.

El parser suma entradas ya afectadas por sus fracciones y divide por 86400
para obtener caudal medio diario. La corrección se restringe a la versión
auditada, salidas diarias y canales verificados como bypass mediante parámetros
y conectividad. Comprueba cada conexión esperada y rechaza duplicados o entradas
incompletas. Un canal sin conexiones de entrada tiene flujo cero por la
operación explícita del motor.

Las salidas afectadas sin hidrogramas diarios suficientes publican caudal
normalizado no disponible y conservan el valor original por separado.
No se aplica esta conversión a otras versiones o canales físicos.

## Comparación con lectura consistente

Las tres corridas comparten evaluación 2019, warm-up de 19 años, forcing,
escenario neutral, outlet GIS `153`, binario y fuente original. Cada una tiene
365 frames, 365 días USGS emparejados, 86 valores estimados y 12 meses comparables.

| Corrida | Intervención | Volumen outlet (hm³) | RMSE mensual (m³/s) | NSE mensual | PBIAS mensual (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| `sf19-flow-v1-reference` | Referencia sin activar drenaje | 100,420 | 8,574 | −0,587 | −65,085 |
| `sf19-flow-v1-tile-probe` | Drenaje sin conexión `til` | 67,523 | 9,603 | −0,990 | −76,514 |
| `sf19-trace-v3-tile-routed` | Drenaje con conexión `til` | 103,553 | 7,776 | −0,305 | −64,165 |

Volumen observado USGS 2019: **289,423 hm³**. La asignación de drenaje a las
32 HRU de maíz es experimental; no reconstruye una máscara histórica observada.
Corregir la lectura de salidas por sí solo no mejora el modelo físico. Los NSE
siguen negativos. Las métricas de `sf19-diag-*` y `sf19-trace-v1-tile-routed`
conservan la lectura anterior y no deben mezclarse con estas al atribuir efectos.

## Balance de conexiones

En la variante conectada, las entradas directas a la red son:

| Aporte | Volumen anual (hm³) |
| --- | ---: |
| Escorrentía superficial desde RU | 61,612 |
| Flujo lateral desde RU | 0,847 |
| Drenaje desde RU | 36,029 |
| Acuíferos hacia canales | 5,064 |
| Total de entradas directas | 103,553 |
| Outlet terminal | 103,553 |

El residuo total es **−0,926 m³**, sobre 103,55 millones de m³. La mayor
diferencia diaria entre entrada y salida real de un canal no terminal es
**0,180 m³**. Son diferencias numéricas de las salidas impresas. Las aristas entre
canales se comprueban por separado y no se suman como nuevas entradas externas.

La red de la prueba desconectada conserva lo que recibe, pero nunca recibe su
drenaje generado. Cerrar las conexiones no basta para cerrar toda la cuenca.

## Balance parcial de cuenca

Se contabilizan lluvia, ET de HRU, revap de acuíferos, caudal terminal y cambios
de almacenamiento en suelo, nieve, acuíferos y retrasos del ruteo. La ventana es
**2019-01-02 a 2019-12-31**: usa estados finales del 1 de enero como inicio,
sin inventar el estado inicial de acuíferos del primer día.

```text
residuo = P − ET_HRU − revap − Q_outlet
          − ΔS_suelo − ΔS_nieve − ΔS_acuíferos − ΔS_retrasos
```

| Variante | Residuo parcial (mm) |
| --- | ---: |
| Referencia | −0,01220 |
| Drenaje sin conexión | 64,22407 |
| Drenaje con conexión | −0,01215 |

El residuo desconectado corresponde al drenaje sin salida, con diferencias de
ventana y redondeo. En la variante conectada, los acuíferos almacenan unos
**23,01 hm³** adicionales y extraen **11,54 hm³** mediante revap en esa ventana.

El estado es `PARTIAL_ACCOUNTING`: faltan estados independientes sin redondear
y almacenamiento de dosel. Estos resultados diagnostican conservación; no
validan todos los procesos ni la hipótesis.

## Área, ET y ruteo físico pendiente

La suma de áreas HRU es **560,888 km²**. USGS publica **224 mi²**, aproximadamente
**580,158 km²**, para la [estación 05451210](https://waterdata.usgs.gov/monitoring-location/USGS-05451210/).
La diferencia es −3,32 % y no explica por sí sola la subestimación de caudal.
El outlet GIS `153` es el único terminal.

La variante conectada reporta 1080,817 mm de lluvia y 834,971 mm de ET:
321,848 mm de transpiración vegetal, 491,172 mm de evaporación de suelo y
21,943 mm de evaporación de dosel. Su suma difiere 0,008 mm del total por
redondeo. La evaporación de suelo representa aproximadamente el 58,8 % de ET.
Son cantidades modeladas que requieren contraste externo.

Los **37 canales tienen `len = 0,00050 km`** y usan la rama sin transformación.
Los hidrogramas recuperan el flujo transportado, pero no añaden tránsito,
almacenamiento, evaporación o infiltración fluvial. La geometría debe resolverse
antes de compensar sus limitaciones mediante calibración de otros parámetros.

## Integración y reproducción

- El adaptador activa salidas de acuíferos, RU e hidrogramas; elimina archivos
  heredados en la copia antes de ejecutar y registra checksums.
- El parser guarda caudal normalizado, caudal original y fuente. El playback
  etiqueta el caudal normalizado como `DERIVED` y mantiene USGS como `OBSERVED`.
- Simulaciones e Informes muestran volumen, diferencia de reporte, residuo,
  área modelada y alcance parcial. CSV/JSON conservan valores originales.

Disponibilidad, playback del 15 de julio y CSV/JSON de la variante conectada
respondieron HTTP 200 mediante API autenticada sobre PostgreSQL. La consulta del
frame guardado confirmó su fuente y evidencia `DERIVED`; el CSV conserva 365
observaciones y ambos volúmenes. Se comprobó sintaxis Python y tipos del frontend;
no se ejecutaron suites de tests ni se revisó visualmente el navegador.

Resumen: [south_fork_water_path_2019.json](../research_domain/south_fork_water_path_2019.json).
Archivos completos: `backend/data/baseline-diagnostic-flow-v1/` y
`backend/data/baseline-diagnostic-trace-v3/`, con fuentes originales preservadas.
La corrida instrumentada inicial está en `baseline-diagnostic-trace-v1/`.
`sf19-trace-v2-tile-routed` permanece `FAILED`: el parser inicial rechazó un
canal sin aportes; se corrigió el caso de conectividad vacía antes de ejecutar v3.

Desde `backend/`, el inspector lee corridas existentes; no modifica sus registros:

```bash
venv/bin/python scripts/inspect_swat_water_path.py \
  --simulation-id sf19-flow-v1-reference \
  --simulation-id sf19-flow-v1-tile-probe \
  --simulation-id sf19-trace-v3-tile-routed \
  --output data/baseline-diagnostic-inspection-nueva/report.json
```

Nuevas ejecuciones usan `run_south_fork_baseline_diagnostic.py`, descrito en el
diagnóstico anterior, con IDs/carpetas nuevos. El inspector exige PostgreSQL local
`digitaltwin` y rechaza sobrescribir informes.

## Siguiente tarea

La [prueba de longitudes delineadas](CHANNEL_GEOMETRY_DIAGNOSTIC_2019.md)
ya ejecutó una pareja controlada con 37 cauces físicos y una copia diagnóstica
del motor que permite underflow. El balance continúa parcial y el NSE negativo.
Falta fijar el motor definitivo y recuperar estados de llanura de inundación.
Después, contrastar ET/PET y manejo, delimitar parámetros
y periodo de calibración, y reservar la evaluación temporal. La referencia A/B
necesita superar estos pasos antes de entrenar C/D.

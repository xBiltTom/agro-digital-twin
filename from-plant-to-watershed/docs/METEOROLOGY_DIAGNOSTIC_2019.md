# Meteorología y evapotranspiración — South Fork 2019

**Fecha:** 2026-10-06. Diagnóstico de desarrollo sobre las corridas existentes
`sf19-src-v2-geom-routed` y `sf19-src-ctrl-v2-tile-routed` en **pglocal**.
Se inspeccionan entradas y salidas; no se ejecuta una nueva simulación ni se calibra.

## Evidencia y procedencia

El [informe completo](../research_domain/south_fork_meteorology_2019_v2.json)
conserva conversiones, fechas, checksums, ponderaciones, comparaciones mensuales,
archivos conflictivos y manifiestos de descargas. La auditoría se adjunta a
`validation.meteorology_diagnostic` de ambas corridas. Los registros históricos
de procedencia, caudal, métricas y playback mantienen su contenido original.
La [primera revisión](../research_domain/south_fork_meteorology_2019.json), con
el contraste externo de viento todavía pendiente, queda conservada también en
`validation.meteorology_diagnostic_history`.

El builder identifica **gridMET**, commit
`9397584e4ca116fbfe757039523ad8bae68ea90c`. Se archivaron dentro del workspace
4.677 archivos de metadata, caché NetCDF y forcing, con 98.503.221 bytes y
manifiesto de checksums. Este archivo no contiene una base de datos alternativa.

Los 25 puntos meteorológicos cubren 2000–2025; la corrida utiliza 2000–2019,
con 19 años de warm-up y salidas diarias de 2019. Las comprobaciones relacionan
los hashes de inputs del motor y de forcing del playback con los archivos
inspeccionados. La etiqueta antigua de origen sin verificar se conserva en su
linaje; este diagnóstico aporta evidencia adicional y alertas específicas.

[gridMET](https://www.climatologylab.org/gridmet.html) proporciona estimaciones
diarias en una malla de aproximadamente 4 km, con meteorología derivada de
PRISM y reanálisis. Los puntos del proyecto representan celdas de un producto
grillado, no estaciones meteorológicas observadas.

## Conversiones y calendario

| Variable | Conversión reconstruida |
| --- | --- |
| Precipitación | mm → mm; redondeo a 0,01 mm. |
| Temperatura máxima/mínima | K − 273,15 → °C; redondeo a 0,01 °C. |
| Radiación | Media diaria W/m² × 86.400 / 10⁶ → MJ/m²/día; redondeo a 0,01. |
| Humedad relativa | `(RHmin + RHmax) / 200` → fracción; redondeo a 0,001. |
| Viento | m/s a 10 m, conservado en el archivo; ajuste de altura dentro de SWAT+. |

El lector NetCDF aplica máscara de faltantes, tipo sin signo, `scale_factor` y
`add_offset`. Comprueba coordenadas y la forma real tiempo/latitud/longitud:
el atributo textual `dimensions` de estas respuestas NCSS es inconsistente
con el orden real del array. La tolerancia de reconstrucción corresponde a la
mitad del paso de redondeo del builder más 10⁻⁸; no es tolerancia de precisión física.

Las descargas originales omiten **31 de diciembre en años bisiestos**.
Los valores presentes en SWAT+ se contrastan con interpolación de los días
adyacentes y con nuevas descargas gridMET para las fechas ausentes. En la ventana
ejecutada deben revisarse 2000, 2004, 2008, 2012 y 2016; 2020 y 2024 pertenecen
al archivo disponible y quedan fuera de esta corrida. No hay códigos diarios
faltantes en los archivos completos; eso no demuestra ausencia de datos rellenados.

También se detectaron conflictos de precipitación de 2011 y viento de 2015
entre descargas que cubren la misma celda: seis comparaciones de punto/variable/año
para precipitación y doce para viento. Se agrupan series idénticas y se usa el grupo único de
mayor tamaño para auditar consistencia, conservando todos los archivos
conflictivos y sus hashes. La selección no depende de parecido con SWAT+.
Nuevas descargas de precipitación de 2011 y viento de 2015 contrastan cada variante y el
forcing realmente almacenado. El informe cuantifica las diferencias; no se
atribuye todavía una causa al servidor o al builder.

El forcing de `s42522n93585w` difiere de la referencia nueva en **192 días de
2011**, con 215 mm adicionales en ese punto y **5,189 mm** en el agregado de
cuenca. La reconstrucción identifica además **328 valores diarios de viento de
2015** distintos del consenso. La descarga nueva confirma ese consenso; el punto
afectado es `s42480n93450w`, con sesgo medio **−0,1063 m/s** y diferencia diaria
máxima **7,5 m/s**. Su efecto sobre el viento medio ponderado de 2015 es
**−0,0004743 m/s**. Estas anomalías pertenecen al warm-up; en 2019
hay **cero discrepancias** contra la caché original dentro del redondeo declarado.
Las siete fechas interpoladas del archivo completo coinciden con la interpolación
de celdas fuente adyacentes; cinco de ellas intervienen en el warm-up ejecutado.

La ausencia de triggers de generación para las variables diarias directas no
elimina la posible participación de WGN en características subdiarias de tormenta.

## ET y PET: comparación de productos

Los totales siguientes son de **2019**, obtenidos de `basin_wb_day.txt` y de
productos externos muestreados en los puntos asignados, ponderados por área
de HRU. No son una integración espacial sobre el polígono de la cuenca.

| Magnitud, mm/año | SWAT+ | gridMET | TerraClimate v1.1 |
| --- | ---: | ---: | ---: |
| Precipitación | 1.080,817 | Forcing reconstruido | 1.017,006 |
| ET real modelada | 834,971 | — | 683,073 |
| PET / ET de referencia | 978,812 | 1.191,273, alfalfa | 772,647 |

La ET de SWAT+ supera en aproximadamente **22,24 %** la AET de TerraClimate.
Los componentes nativos son `esoil` **491,172 mm**, `eplant` **321,848 mm** y
`ecanopy` **21,943 mm**. La diferencia de 0,008 mm entre su suma y ET corresponde
a la precisión de impresión de las salidas. `esoil` debe interpretarse según
el código del motor: puede incluir consumo evaporativo de nieve y agua
superficial; no se lo equipara automáticamente a evaporación de suelo desnudo.

La PET de SWAT+ es menor que ETr gridMET y mayor que PET TerraClimate. El
motor usa `codes.bsn.pet=1`, Penman–Monteith con referencia de alfalfa de 0,4 m,
`pet_co=1`, y ajusta el viento mediante `(1.7/10)^0.2` en
[`et_pot.f90`](https://github.com/swat-model/swatplus/blob/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d/src/et_pot.f90).
Una segunda conversión de altura en el archivo alteraría el forcing.
Las diferencias de referencia vegetal, CO₂, albedo de nieve y presión de vapor
impiden interpretar estos contrastes como errores respecto de una verdad medida.

La comparación PET con ETr comparte proveedor meteorológico. La
[documentación de TerraClimate](https://www.climatologylab.org/terraclimate.html)
define v1.1 con ERA5/WorldClim y un balance mensual que usa cobertura vegetal
estática. Su AET es una estimación de otro modelo, no una medición de ET de la
cuenca. No se realizó validación con torres de flujo o ET satelital.

Se archivó también [Daymet v4](https://daymet.ornl.gov/overview) para los mismos
25 puntos de 2019. Su radiación es una media durante las horas de luz: se
convierte mediante `srad * dayl / 10⁶`, que difiere de la conversión gridMET.
El informe compara lluvia, temperatura media y energía solar. Ambos productos
pueden compartir observaciones de estaciones; no se supone independencia
estadística. Para ampliar a años bisiestos se debe definir explícitamente el
calendario de Daymet, que contiene 365 registros por año.

Para el mismo soporte espacial, Daymet aporta **1.200,631 mm** de precipitación,
frente a **1.080,823 mm** del agregado gridMET. La temperatura media gridMET
difiere en **+0,134 °C** y la energía solar acumulada en **+325,371 MJ/m²**.
Estos contrastes entre productos no establecen cuál reproduce mejor la cuenca.

## Agregación y consumo en la aplicación

SWAT+ pondera las estaciones asignadas por área de HRU. El agregado antiguo
de playback y `total_precip_mm` usaba promedio simple de estaciones. La nueva
lectura de baseline usa todas las áreas y asignaciones de `hru.con`; se conserva
el agregado histórico de corridas completadas. El informe cuantifica su diferencia
y verifica la nueva lluvia diaria contra la salida nativa impresa.

El promedio simple antiguo suma **1.083,108 mm** y el ponderado **1.080,823 mm**:
diferencia **2,285 mm**. La lluvia ponderada difiere como máximo **0,000523 mm/día**
de la impresión nativa SWAT+; la suma impresa es 1.080,817 mm. Cambiar el agregado
de presentación no cambia las ecuaciones o los caudales del motor.

Las páginas que presentan evidencia SWAT+ incorporan un panel con los totales,
dos curvas mensuales separadas para ET y PET, y alertas de calendario/caché.
La descarga JSON existente incluye la auditoría adjunta. El reporte científico
histórico `south-fork-final-v2` mantiene su propio linaje.

## Reproducción

Desde `backend/`, para nuevas descargas en directorios que no existan:

```bash
venv/bin/python scripts/fetch_south_fork_weather_benchmarks.py \
  --project data/phase34-cdl-2019/project --output data/baseline-diagnostic-meteorology-v2/benchmarks
venv/bin/python scripts/fetch_south_fork_weather_benchmarks.py \
  --project data/phase34-cdl-2019/project --output data/baseline-diagnostic-meteorology-v2/calendar-edges --calendar-edges
venv/bin/python scripts/fetch_south_fork_weather_benchmarks.py \
  --project data/phase34-cdl-2019/project --output data/baseline-diagnostic-meteorology-v2/cache-reference-2011 --gridmet-precip-year 2011
venv/bin/python scripts/fetch_south_fork_weather_benchmarks.py \
  --project data/phase34-cdl-2019/project --output data/baseline-diagnostic-meteorology-v2/cache-reference-2015-wind --gridmet-wind-year 2015
```

Para repetir la auditoría leyendo las corridas existentes, con el archivo
meteorológico v1 disponible y sin modificar PostgreSQL:

```bash
venv/bin/python scripts/inspect_swat_meteorology.py \
  --simulation-id sf19-src-v2-geom-routed --simulation-id sf19-src-ctrl-v2-tile-routed \
  --builder-archive data/baseline-diagnostic-meteorology-v1/builder-weather-archive \
  --benchmarks data/baseline-diagnostic-meteorology-v1/benchmarks \
  --calendar-edges data/baseline-diagnostic-meteorology-v1/calendar-edges \
  --cache-reference data/baseline-diagnostic-meteorology-v1/cache-reference-2011 \
  --cache-reference data/baseline-diagnostic-meteorology-v1/cache-reference-2015-wind \
  --output data/baseline-diagnostic-meteorology-v1/new-readonly-audit.json
```

`--persist` adjunta una auditoría nueva; rechaza sobrescribir informes. Una
revisión adicional requiere `--append-audit`, que archiva el diagnóstico
anterior por ID antes de adjuntar el nuevo. Los manifiestos fijan bytes, URLs y versiones
de descarga. Un timeout interrumpió el primer lote de calendario; se conservaron
48 archivos y se completó el restante. Sus registros distinguen la hora de archivo
local y la ausencia de recibo HTTP original; no inventan headers de transferencia.

## Decisión para la siguiente tarea

Crear una variante de forcing con los cierres de año recuperados y resolver
las discrepancias de precipitación de 2011 y viento de 2015. Ejecutar una comparación controlada contra la referencia
preservada, con el mismo motor, geometría, parámetros, periodo y observaciones.
Después estudiar sensibilidad de partición ET, nieve/cobertura y pérdidas
fluviales. Los productos externos actuales no justifican imponer un factor
global de reducción de PET.

La evaluación de H1 y la calibración multianual siguen pendientes. El año 2019
fue explorado durante desarrollo y no puede presentarse como TEST independiente.

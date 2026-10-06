# Longitudes de cauces South Fork 2019

Fecha: **2026-10-06**. Continuación del
[recorrido del agua](WATER_PATH_DIAGNOSTIC_2019.md).
Etapa posterior: [motor desde fuente y almacenamiento](SWAT_SOURCE_BUILD_2019.md).
Corridas y playback en PostgreSQL local `digitaltwin`; evidencia de desarrollo,
**sin calibración ni evaluación de H1**.

## Recuperación de la delineación

La fuente existente es `delin/shapes/channels.gpkg` del artefacto
`south_fork_05451210_2000_2025_retry` del builder. Se abre exclusivamente como
fuente geográfica de lectura. No se crean bases de datos para simulaciones.

- Los 37 `link_id` coinciden uno a uno con `gis_id` de `chandeg.con`.
- Las 36 conexiones coinciden con `delin/routing_graph.graphml`: red dirigida
  sin ciclos y un único terminal GIS `153`.
- CRS **EPSG:5070**, unidades métricas. `length_m / 1000` produce `len` en km.
- Cada atributo de longitud coincide con su polilínea 2D dentro de 0,01 m.
- Anchos, profundidades y pendientes existentes coinciden con la delineación
  a la precisión de entrada; la intervención modifica solo `len`.

| Propiedad | Valor |
| --- | ---: |
| Longitud total recuperada | 212,63707 km |
| Longitud mínima | 0,58204 km |
| Longitud máxima | 29,52960 km |
| Longitud del cauce terminal | 8,98534 km |
| Canales artificiales después de restaurar | 0 de 37 |

La versión anterior tenía 0,00050 km por canal: 18,5 m de longitud total.
Las longitudes proceden del DEM, no de un levantamiento de campo. Ancho y
profundidad siguen siendo estimaciones del builder. Esta tarea recupera inputs
hidráulicos; las mallas 3D del frontend conservan su alcance ilustrativo.

## Fallos y política numérica

`sf19-geom-v1-geom-routed` conservó los parámetros originales de nutrientes
y falló durante warm-up con `SIGFPE` en `wq_semianalyt`/`ch_watqual4`.
`sf19-geom-v2-geom-routed` intentó entradas de cinética cero y falló después
en `sd_channel_sediment3`. Ambas permanecen `FAILED` en PostgreSQL.

La segunda intervención **no desactivó la química**. El
[lector oficial ch_read_nut](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/ch_read_nut.f90)
sustituye muchas entradas cero por valores predeterminados no nulos. Su
configuración histórica conserva el intento, con esta corrección de
interpretación en el informe. Ese perfil no se usó en la comparación final.

Un depurador sobre una copia de v2 registró `si_code=5` (`FPE_FLTUND`) en
`xflowf`, confirmando **underflow**, no overflow, para el fallo de sedimentos.
El transcript se conserva por SHA-256. No se atribuye al primer fallo una
categoría IEEE confirmada por ese transcript.

La compilación GNU distribuida activa `_gfortran_set_fpe(29)`: operación
inválida, división por cero, overflow y underflow. Los bits están documentados
por [GNU Fortran](https://gcc.gnu.org/onlinedocs/gfortran/_005fgfortran_005fset_005ffpe.html).
Una **copia diagnóstica** cambia exclusivamente ese argumento a 13, permitiendo
underflow y conservando las otras tres paradas. Las rutinas del modelo y el
binario original quedan intactos.

| Artefacto | SHA-256 |
| --- | --- |
| Binario oficial GNU 61.0.2.61 | `5f0e6b43833bce1dbd6d416813bffc7b742dcff79ae1e7008d8f65bacd9b314e` |
| Copia diagnóstica | `aa8cdbd8e05374f55f4c352dea05be265f2d751b12ea9044c9c49967b08463a2` |

La transformación exige ese SHA original y la secuencia de arranque auditada;
cambia un byte en offset 4614363 y rechaza sobrescrituras. El manifiesto está
junto al ejecutable y en la procedencia de la corrida. Es una intervención de
desarrollo, **no una nueva versión oficial de SWAT+**.

## Comparación controlada

Ambas corridas nuevas usan el mismo ejecutable diagnóstico, proyecto original,
drenaje conectado, forcing, observaciones, outlet y warm-up de 19 años.
Evalúan 2019: **365 frames**, 365 pares USGS, 86 valores estimados conservados
y 12 meses completos por corrida.

| Corrida | Longitudes | Volumen outlet (hm³) | RMSE mensual (m³/s) | NSE mensual | PBIAS mensual (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| `sf19-geom-ctrl-v1-tile-routed` | Artificiales | 103,553 | 7,776 | −0,305 | −64,165 |
| `sf19-geom-v3-geom-routed` | Delineadas | 94,460 | 8,081 | −0,409 | −67,297 |

El control reproduce el volumen y las métricas de `sf19-trace-v3-tile-routed`.
Entre los inputs trazables de las nuevas corridas solo difiere `hyd-sed-lte.cha`,
campo `len`. Los términos terrestres anuales son idénticos; las entradas directas
RU/acuíferos siguen siendo 103,553 hm³. Los nutrientes conservan sus parámetros
originales. El volumen disminuye **9,092 hm³** y el RMSE aumenta **0,305 m³/s**.
No se eligieron longitudes para optimizar métricas ni se interpreta esto como H1.

## Ruteo y balance parcial

Los cauces ejecutan la rama física con Muskingum (`rte_cha=1`). El
[código de ruteo](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/ch_rtmusk.f90)
calcula almacenamiento, evaporación y transmisión al lecho. Su caudal usa la
conversión nativa a m³/s; no requiere la corrección del reporte de bypass.

Ventana: **2019-01-02 a 2019-12-31**, usando estados finales del 1 de enero.

| Término de la red física | hm³ |
| --- | ---: |
| Entradas externas RU/acuíferos en la ventana | 103,353 |
| Precipitación fluvial reportada | 7,749 |
| Salida terminal en la ventana | 92,711 |
| Evaporación fluvial | 0,900 |
| Infiltración fluvial reportada | 16,347 |
| Cambio de almacenamiento en cauces | 0,327 |
| Residuo parcial de la red | 0,817 |

El residuo de cuenca, incluyendo suelo, nieve, acuíferos y retrasos, es
**1,445 mm**. Ambos balances llevan estado `PARTIAL_ACCOUNTING`.
[La rutina de salida](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/sd_channel_output.f90)
imprime `ch_stor` en `flo_stor`; falta el estado independiente de llanura de
inundación. No se sustituye ese estado por el residuo ni se declara cierre total.
También faltan dosel y estados sin redondeo.

Las diferencias máximas entre caudales reportados e hidrogramas son unos
431,75 m³ por conexión/día. Contabilizando intervalos de medio dígito de ambas
salidas impresas, el exceso máximo es inferior a 0,00001 m³. Es coherencia de
archivos, no validación de precisión física.

Lluvia terrestre: 1080,817 mm; ET terrestre: 834,971 mm; PET: 978,812 mm.
Mantienen la referencia anterior. Precipitación y pérdidas fluviales son términos
adicionales del motor; su soporte espacial y parámetros requieren diagnóstico.

## Software y reproducción

El runner crea IDs/carpetas nuevos y usa la persistencia normal del backend.
El informe versionado incluye comparación, intentos fallidos y checksums:
[south_fork_channel_geometry_2019.json](../research_domain/south_fork_channel_geometry_2019.json).
Archivos completos: `backend/data/baseline-diagnostic-geometry-v3/` y
`backend/data/baseline-diagnostic-geometry-control-v1/`.

El panel de Simulaciones/Informes distingue ruteo físico y artificial, muestra
longitud, pérdidas, alcance parcial y advertencia del ejecutable diagnóstico.
Las corridas quedan disponibles para los contratos existentes de CSV/JSON y
playback. No se ejecutaron suites de tests ni comprobaciones de navegador.

Desde `backend/`, con IDs existentes en pglocal y un nombre/carpeta nuevos:

```bash
venv/bin/python scripts/run_south_fork_baseline_diagnostic.py \
  --experiment-id sf19-geometria-nueva \
  --owner-id UUID_USUARIO --watershed-id UUID_CUENCA \
  --scenario-id UUID_ESCENARIO --dataset-id UUID_USGS \
  --output-root data/baseline-diagnostic-geometria-nueva \
  --routing-probe --underflow-diagnostic \
  --channel-geometry /ruta/delin/shapes/channels.gpkg \
  --routing-graph /ruta/delin/routing_graph.graphml
```

Para el control, usar otro ID/carpeta y omitir los dos argumentos de delineación.
El inspector acepta `--compare CONTROL TRATAMIENTO` y audita inputs, motor,
cobertura y términos terrestres. La huella del proyecto fuente permaneció
`623c8130f05b86ed4b7c339cecfde57ab7ae8a3a2d420807ac5a1f961e098eaa`.

## Siguiente etapa

Fijar un motor reproducible desde fuente o una distribución oficial con la
política numérica adecuada y repetir esta pareja antes del experimento del
paper. Recuperar el estado de llanura de inundación, revisar pérdidas fluviales
y contrastar ET/PET con evidencia externa. Después se delimita calibración y
holdout temporal; A/B aún requieren estos pasos antes de entrenar/evaluar C/D.

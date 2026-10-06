# Motor SWAT+ desde fuente y almacenamiento fluvial

Fecha: **2026-10-06**. Continuación del
[diagnóstico de longitudes](CHANNEL_GEOMETRY_DIAGNOSTIC_2019.md).
Las corridas usan el PostgreSQL local `digitaltwin`, sus observaciones USGS y
la ruta normal de ejecución, persistencia y playback de la aplicación.

## Compilación fija

Fuente oficial: [SWAT+ 61.0.2.61](https://github.com/swat-model/swatplus/tree/61.0.2.61),
commit `77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d`.
El archivo fuente y los paquetes de herramientas tienen locks SHA-256 en
`backend/scripts/swat_research_source.lock.json` y
`backend/scripts/swat_research_toolchain.lock.json`.
Los cuatro paquetes descargados coinciden con los hashes del índice local
de repositorios pacman. Se extraen en el workspace; no se instalan paquetes
en el sistema ni se crean bases de datos de simulaciones.

La [configuración GNU oficial](https://github.com/swat-model/swatplus/blob/61.0.2.61/CMakeLists.txt)
incluye la trampa de underflow. La receta conserva sus demás opciones de
compilación y permite underflow, manteniendo las trampas por operaciones
inválidas, división por cero y overflow. Las opciones están descritas en
[GNU Fortran](https://gcc.gnu.org/onlinedocs/gfortran/Debugging-Options.html).
La segunda intervención añade exclusivamente escritura de diagnóstico a
`sd_channel_output.f90`; las ecuaciones y parámetros del modelo se conservan.
Es una **compilación de investigación**, no una distribución oficial nueva.

El manifiesto registra compilador, frontend, CMake, flags efectivos, paquetes,
archivos de soporte GCC, librerías dinámicas, patches y ejecutable. El backend
comprueba los hashes del ejecutable y librerías antes de ejecutarlo, copia el
manifiesto al workspace y lo incorpora a la procedencia en PostgreSQL.

`SOURCE_DATE_EPOCH=1768521600`, zona UTC y nombres relativos de archivos
Fortran fijan fechas y rutas del binario. Las rutas incrustadas en mensajes
de comprobación de límites de GNU Fortran requieren un launcher: solamente
`-ffile-prefix-map` no consiguió eliminar esas diferencias locales.
El alcance de reproducción corresponde al compilador y runtime registrados;
no se afirma reproducción binaria entre arquitecturas o compiladores distintos.

## Salida independiente

`channel_storage_day.txt` contiene **37 × 365 = 13.505 filas**: cauce y
llanura, almacenamiento total y de humedales, entrada/salida nativas,
precipitación, evaporación e infiltración. Se escribe al final del día, bajo
las mismas condiciones de impresión de `channel_sd_day.txt`, omitiendo warm-up.
Los estados originales de precisión simple se promueven solo al escribirlos:
el diagnóstico conserva sus cifras, sin aumentar la precisión del modelo.

La contabilidad exige el manifiesto, marcador de esquema, cobertura completa,
identificadores, valores finitos no negativos y consistencia con las salidas
estándar dentro de su redondeo. Comprueba también la partición cauce/llanura.
El alcance auditado requiere un outlet, conexiones internas `tot` de fracción
uno, `gwflow=0`, `i_fpwet=0` y almacenamiento de humedales nulo.

Se usan estados finales del 1 de enero para el balance del **2 de enero al
31 de diciembre de 2019**. Las entradas externas se reconstruyen cancelando
salidas internas de las entradas nativas de todos los canales. El volumen
anual publicado en playback conserva la serie normalizada de caudal; los
volúmenes nativos se distinguen en los campos de contabilidad de la ventana.
Se comprueban **13.468 balances cauce/día** además del agregado de red.

## Resultados de la pareja definitiva

Ambas corridas están `COMPLETED`, con **365 frames**, 365 pares USGS,
86 valores estimados conservados y 12 meses completos por corrida. Comparten
motor, proyecto fuente, forcing, drenaje conectado, observaciones, outlet y
19 años de warm-up. Solo difiere `hyd-sed-lte.cha`, campo `len`.

| Corrida | Longitudes | Outlet anual (hm³) | RMSE mensual (m³/s) | NSE mensual |
| --- | --- | ---: | ---: | ---: |
| `sf19-src-ctrl-v2-tile-routed` | Artificiales | 103,553 | 7,776 | −0,305 |
| `sf19-src-v2-geom-routed` | Delineadas | 94,460 | 8,081 | −0,409 |

Las dos compilaciones independientes `compile-v4` y `compile-v5` producen
el mismo ejecutable SHA-256:
`56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d`.
Se ejecutó la pareja con `compile-v4`; ambos manifiestos se conservan en el
informe. Las primeras corridas `sf19-src-ctrl-v1-tile-routed` y
`sf19-src-v1-geom-routed` usaron el build anterior con rutas absolutas y
permanecen como evidencia del proceso en pglocal.

La nueva receta reproduce exactamente las **365 lecturas diarias de caudal**,
volúmenes, métricas y términos terrestres de las respectivas corridas con
la copia binaria diagnóstica anterior. Esto comprueba la reproducción local
del experimento explorado; no es una validación externa del modelo.

| Contabilidad nativa de la red física, 2 de enero–31 de diciembre | m³ |
| --- | ---: |
| Entradas externas reconstruidas | 103.353.485,849 |
| Precipitación fluvial | 7.749.506,573 |
| Salida terminal | 92.711.141,535 |
| Evaporación fluvial | 900.472,925 |
| Infiltración fluvial | 16.346.368,720 |
| Cambio de almacenamiento en cauces | 326.491,267 |
| Cambio de almacenamiento en llanura | 818.517,660 |
| Residuo de la red | **0,315** |

El máximo residuo absoluto por cauce/día es **0,279 m³** y el máximo relativo
es **1,60 × 10⁻⁷**. El estado `CLOSED` exige residuos relativos inferiores a
`10⁻⁵` en el agregado y cada cauce/día; ese umbral es de diagnóstico numérico,
no una tolerancia de ajuste hidrológico. Se validaron 13.505 estados diarios
y 13.468 balances dentro de la ventana.

El residuo parcial de cuenca baja de **1,445 mm a −0,01215 mm** al incorporar
la llanura y las cifras nativas fluviales. La cuenca mantiene
`PARTIAL_ACCOUNTING`: faltan dosel y estados terrestres sin redondeo.
La precisión impresa también explica que el residuo anterior de red
(817.249,537 m³) no sea exactamente igual al cambio recuperado de llanura.

El caudal observado anual sigue siendo **289,423 hm³**. La variante física
conserva PBIAS mensual **−67,297 %** y NSE negativo. El cierre de la red no
resuelve la subestimación observada ni demuestra H1. El siguiente trabajo
es contrastar ET/PET y procedencia meteorológica con evidencia independiente,
revisar pérdidas y preparar calibración/evaluación temporal multianual.

Evidencia versionada:
[south_fork_source_build_2019.json](../research_domain/south_fork_source_build_2019.json).
Incluye seis corridas, comparaciones de reproducción, hashes de código y
artefactos, estados/balances y los dos manifiestos de compilación. El reporte
de longitudes anterior y el experimento publicado v2 conservan su linaje.

## Reproducción local

Desde `from-plant-to-watershed/backend/`, en Linux con CPU compatible con
los paquetes x86_64_v3 del lock y las librerías
Arch/CachyOS y archivos de soporte GCC compatibles registrados en el manifiesto:

```bash
python scripts/fetch_swat_research_sources.py \
  --cache data/baseline-diagnostic-source-build-v1

python scripts/build_swat_research_engine.py \
  --archive data/baseline-diagnostic-source-build-v1/source.tar.gz \
  --lock scripts/swat_research_source.lock.json \
  --toolchain-lock scripts/swat_research_toolchain.lock.json \
  --output data/baseline-diagnostic-source-build-v1/reproduction-new \
  --compiler data/baseline-diagnostic-source-build-v1/toolchain/usr/bin/gfortran \
  --cmake data/baseline-diagnostic-source-build-v1/toolchain/usr/bin/cmake \
  --jobs 2
```

Elegir un directorio de salida nuevo para cada compilación; se rechaza
sobrescribir compilaciones previas. Los mirrors rolling pueden retirar un
paquete: una copia archivada con el mismo SHA-256 satisface el lock. Un cambio
de versión o librerías requiere un nuevo manifiesto y evaluación explícita.

Para repetir la pareja, usar `run_south_fork_baseline_diagnostic.py` con
`--routing-probe`, `--executable` apuntando a `swatplus-research` y nuevos
identificadores/directorios. Añadir `--channel-geometry` y `--routing-graph`
solo al tratamiento, como en la tarea anterior. Este motor no necesita
`--underflow-diagnostic` ni `--zero-channel-kinetics`.

La exportación `inspect_swat_water_path.py` conserva la comparación controlada,
checksums de código y salidas, referencias anteriores mediante
`--engine-reference` y dos manifiestos mediante `--build-reproduction`.
El motor se selecciona por configuración de corrida; la interfaz muestra el
almacenamiento de llanura recuperado y sus límites en el panel científico.

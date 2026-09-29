# Auditoría fase 3.5: sensibilidad del acoplamiento FSPM → SWAT+

## Pregunta y resultado

¿SWAT+ lee los parámetros de maíz que modifica el FSPM y estos alteran el estado vegetal o hidrológico?

**Resultado:** la pareja original de fase 3.4 no demuestra ese efecto. Encontramos una incompatibilidad de lectura en `plants.plt`: el campo entero `days_mat` estaba serializado como `120.00000`. El lector SWAT+ 61.0.2.61 usa lectura Fortran list-directed, detecta solo EOF y no eleva los errores positivos de conversión. La lectura de esa fila puede detenerse en `days_mat` y dejar sin cargar los campos posteriores, incluidos los diez parámetros modificados por el mapper. La pareja original terminó, pero sus outputs hidrológicos, los outputs de yield disponibles y sus contenidos normalizados eran iguales; además, esa configuración no producía `hru_pw_day.txt`.

En 12 workspaces nuevos, aislados y etiquetados `SENSITIVITY_DIAGNOSTIC_ONLY`, renderizamos los valores integrales de `days_mat` como enteros, conservando sus valores numéricos. No cambiamos el proyecto fuente ni los artefactos de fase 3.4. Con esa corrección de serialización idéntica para todos los brazos, el baseline y el brazo de diez parámetros FSPM divergieron en estados de planta y salidas hidrológicas. Ocho probes OAT dieron cambios observables; `ext_co` no produjo respuesta detectable en las salidas disponibles y la altura directa no se puede observar en este build. Esto demuestra sensibilidad computacional del registro `corn` en las copias compatibles. No convierte las salidas diagnósticas en resultado científico final, ni repara retroactivamente la pareja original.

## Inspección del repositorio y artefactos

- HEAD al iniciar: `f2bd12f2eadd416b09b038d908e7db6cc6a6a832`; no había commits posteriores.
- Se inspeccionaron `docs/PHASE_3_4_SCIENTIFIC_AUDIT.md`, `docs/GEMINI_3D_HANDOFF.md` y los scripts de preparación y verificación de fase 3.4.
- Se comprobó la existencia y el manifest/checksum de la variante local `backend/data/phase34-cdl-2019`, los dos workspaces y los artefactos playback antes de usarlos.
- Identidad del par: experimento `phase34-south-fork-cdl-2019-verification`; baseline `phase34-sf19-baseline`; acoplado `phase34-sf19-coupled`; periodo 2019-01-01–2019-12-31; seed 42. El manifest clasifica el caso como `EXPERIMENTAL_CDL_CORN_MAJORITY_MANAGEMENT_NOT_HISTORICAL_RECONSTRUCTION`.
- PostgreSQL local no respondió en `localhost:5432`. No se escribieron filas ni se modificó SQLite de fase 3.4.

## Lectura efectiva del cultivo y parámetros

La evidencia de la cadena se compone de configuración cruzada, salida de manejo y pruebas de intervención. El manifest selecciona 32 HRU con fracción CDL 2019 de maíz ≥ 0.50. En la variante, `hru-data.hru` referencia el landuse experimental; `landuse.lum` lo enlaza con la comunidad y rotación de maíz; `plant.ini` referencia el cultivo; `management.sch` y `lum.dtl` configuran la decisión automática y las operaciones de plantación/cosecha. `plants.plt` contiene el registro `corn`. En el harness instrumentado, `mgt_out.txt` registra operaciones `PLANT` de `corn` para 26 HRU el 15 de mayo y seis HRU el 16 de mayo, y `HARV/KILL` entre el 27 de agosto y el 3 de septiembre. Son eventos de la ejecución diagnóstica con corrección de serialización, no fechas históricas observadas.

La comparación de probes modifica un único campo de la fila `corn` en `plants.plt`, verifica el checksum de cada copia y mantiene iguales forcing, manejo, periodo, outlet, HRU, seed y controles de impresión entre los brazos. Los demás registros vegetales conservan los mismos valores. Al cambiar solo `lai_pot`, `bm_e`, curvas de LAI, `hu_lai_decl` o `rt_dp_max`, SWAT+ produce cambios en salidas de HRU y, para parámetros con vías hidrológicas observables, en ET/percolación. Esta combinación de la fila registrada, el evento de cultivo, los archivos de entrada aislados y la respuesta OAT es la evidencia de uso más fuerte disponible. SWAT+ no imprime el nombre de registro `plants.plt` junto a cada variable de estado, así que no es un trace interno del ejecutable.

La fuente oficial de la versión exacta declara `days_mat` entero en el orden del registro de planta y luego lee la fila mediante una única lectura de lista. El manejador termina solo cuando `iostat < 0`; un error de conversión positivo no se propaga como fallo. La misma fuente de SWAT+ conecta campos de la planta con crecimiento de hojas, biomasa, raíces y comunidad: [lector de `plants.plt`](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_parm_read.f90), [estructura y tipos del registro](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_data_module.f90), [crecimiento foliar](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/pl_leaf_gro.f90), [biomasa](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/pl_biomass_gro.f90), [raíces](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/pl_root_gro.f90) y [comunidad vegetal](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/pl_community.f90). La referencia de formato de entradas y salidas está en [plantas](https://docs.swat.tamu.edu/input-reference/plt/), [configuración `plant.ini`](https://docs.swat.tamu.edu/input-reference/ini/), [impresión](https://docs.swat.tamu.edu/output-reference/) y [archivos de planta y weather](https://docs.swat.tamu.edu/output-reference/aquifer-reservoir-plant/).

## Outputs que existen en esta configuración

| Archivo | Frecuencia y soporte | Variables disponibles / uso | Límite |
|---|---|---|---|
| `hru_pw_day.txt` | Diario; filas por HRU, 365 registros por HRU en este harness | LAI (`lai`), biomasa (`bioms`), incremento y máximo de biomasa, rendimiento, fracciones de estrés, PHU y uptake de N/P (`nplt`, `pplnt`), entre otras | Se activó editando `print.prt` solo en copias. No incluye altura ni profundidad de raíz directas. |
| `mgt_out.txt` | Una fila por operación ejecutada | HRU, fecha, crop y operación `PLANT` / `HARV/KILL` | El original no lo tenía activado; la evidencia de fechas corresponde al harness instrumentado. Son fechas modeladas. |
| `hru_wb_day.txt` | Diario por HRU | `eplant`, ET, percolación, runoff, flujo lateral, precipitación y almacenamiento de agua en suelo | `eplant` y percolación son proxies de respuesta radicular; no miden profundidad de raíz. El almacenamiento se conserva en mm, no se convierte a porcentaje. |
| `basin_wb_day.txt` | Diario de cuenca | ET, runoff, percolación, agua almacenada y balance hídrico | Agregado de cuenca, no estado de una planta. |
| `channel_sd_day.txt` | Diario por canal/outlet | Caudal y variables de calidad impresas | No es una variable vegetal directa. |
| `crop_yld_aa.txt`, `crop_yld_yr.txt` | Resumen de cosecha/anual | MASS y componentes C/N/P por planta/cultivo | La fila no es un estado diario fechado. Se corrigió el parser del harness para respetar el encabezado de dos líneas. |

La configuración SWAT+ disponible no expone altura ni raíz en `hru_pw_day.txt`. La salida diaria de HRU y los proxies hidrológicos no deben presentarse como medición directa de esos estados. La lista de nombres se descubrió en el `files.out` y archivos generados por el ejecutable instalado, y se contrastó con la referencia de salida SWAT+; no se asumieron nombres de archivo no presentes.

## Ventanas y fechas

Hay tres conceptos distintos:

1. **Ventana FSPM aproximada (A):** `2019-04-16` es la primera fecha en que la ventana PHU permite representar el cultivo; `2019-07-24` es la fecha del máximo LAI del FSPM. Son fechas de la trayectoria FSPM aproximada.
2. **Operaciones internas del SWAT+ diagnóstico (B):** `mgt_out.txt` registra plantación de maíz el 15 y 16 de mayo, y cosecha/kill del 27 de agosto al 3 de septiembre de 2019. La emisión de eventos se habilitó solo en copias aisladas.
3. **Eventos agrícolas reales observados (C):** no se aportaron registros observacionales de siembra o cosecha. No se infieren ni reconstruyen fechas históricas.

La diferencia A/B se conserva; la ventana FSPM no se presenta como evento SWAT+ ni como evento observado. La cadena activa usó una regla interna de decisión por temperatura/PHU. La evidencia no demuestra que las operaciones simuladas coincidan con el manejo histórico de los campos.

## Diseño del harness

El runner `backend/scripts/run_phase35_sensitivity_verification.py`:

1. Verifica el manifest de fase 3.4 y sus checksums de entrada.
2. Crea workspaces nuevos por brazo y se niega a sobrescribir el destino.
3. En copias exclusivamente, normaliza 266 representaciones integrales de `days_mat`; conserva valores numéricos.
4. Activa la impresión diaria de `hru_pw` y `mgtout` con el mismo `print.prt`, `file.cio` y `time.sim` en los 12 brazos.
5. Ejecuta SWAT+ real para baseline, el par FSPM y 10 probes OAT en sus respectivos rangos del mapper. Los 12 procesos completaron con `success.fin`.
6. Verifica invariancia de forcing y de manejo. Los checksums del forcing no cambiaron; `management.sch`, `lum.dtl`, HRU, clima, fechas, outlet y los controles de salida coinciden. Cada probe solo cambia el parámetro `corn` indicado en `plants.plt` además de la normalización común.
7. Compara hashes, contenido normalizado, tokens numéricos, filas/fechas, diferencias absolutas/relativas y primer día de divergencia. Las tablas usan la precisión impresa por SWAT+ (tres decimales para las columnas diarias mostradas).
8. Produce el informe local ignorado por Git `backend/data/phase35-sensitivity-verification-v3/phase35-sensitivity-report.json`. Cada brazo y cada parámetro incluyen valores original/FSPM/diagnóstico, rango del mapper, hashes de `plants.plt`, outputs examinados y estadísticas.

La normalización de `days_mat` no cambia el valor del parámetro: corrige solo la representación textual incompatible. Es una adaptación de compatibilidad diagnóstica, no una modificación del proyecto científico original. Los rangos listados abajo son los límites que el mapper aplica y que estas corridas aceptaron; no constituyen calibración ni ranking de importancia.

## Sensibilidad OAT

Todas las diferencias de esta tabla son probe diagnóstico contra baseline normalizado; el código, JSON, hashes y métricas por archivo están en el informe. “Rel.” es máxima diferencia relativa registrada y puede crecer cuando el valor de baseline se aproxima a cero.

| Parámetro | Original → FSPM | Probe diagnóstico [rango aplicado] | Output medido | Filas distintas | Máx. abs. / rel. | Primera divergencia | Clasificación |
|---|---:|---:|---|---:|---:|---|---|
| `lai_pot` | 6.0 → 5.004552 | 10.0 [0.5, 10] | LAI diario; también biomasa | 3372/11680 LAI; 3340/11680 biomasa | LAI 3.997 / 0.692; biomasa 2194.457 / 0.438 | 16–17 mayo | `ACTIVE_AND_SENSITIVE` |
| `frac_hu1` | 0.15 → 0.160188 | 0.05 [0.001, 0.999] | LAI diario | 3369/11680 | 2.016 / 8.923 | 16 mayo | `ACTIVE_AND_SENSITIVE` |
| `lai_max1` | 0.15 → 0.163641 | 0.90 [0.001, 0.999] | LAI diario | 3369/11680 | 4.791 / 165.385 | 16 mayo | `ACTIVE_AND_SENSITIVE` |
| `frac_hu2` | 0.5 → 0.444118 | 0.75 [0.001, 0.999] | LAI diario | 3371/11680 | 1.335 / 1.000 | 16 mayo | `ACTIVE_AND_SENSITIVE` |
| `lai_max2` | 0.95 → 0.864469 | 0.20 [0.001, 0.999] | LAI diario | 3372/11680 | 4.642 / 4.923 | 16 mayo | `ACTIVE_AND_SENSITIVE` |
| `hu_lai_decl` | 0.8 → 0.727933 | 0.98 [0.2, 1.0] | LAI diario; crecimiento de biomasa | 1044/11680 LAI; 518/11680 crecimiento | LAI 1.237 / 0.267; crecimiento 44.143 / 0.125 | 27 julio | `ACTIVE_AND_SENSITIVE` |
| `can_ht_max` | 2.5 → 2.739508 | 20.0 [0.1, 20] | ET vegetal indirecta | 0/11680 | 0 / 0 | — | `OUTPUT_NOT_OBSERVABLE` |
| `rt_dp_max` | 2.0 → 1.200219 | 0.10 [0, 3] | `eplant`; percolación | 1853/11680; 3407/11680 | 6.528 / 1.000; 2.715 / 95.0 | 8 y 10 junio | `ACTIVE_AND_SENSITIVE` |
| `ext_co` | 0.65 → 0.499139 | 1.80 [0, 2] | LAI, biomasa y `eplant` | 0/11680 en cada output | 0 / 0 | — | `ACTIVE_BUT_NO_DETECTABLE_RESPONSE` |
| `bm_e` | 40.0 → 40.106577 | 90.0 [10, 90] | Biomasa diaria; yield MASS | 3372/11680 biomasa; 31/31 MASS | biomasa 31535.097 / 1.025; MASS 14731.664 / 1.017 | 16 mayo; yield 31 diciembre | `ACTIVE_AND_SENSITIVE` |

`ext_co` aparece en la ruta de absorción de radiación de la fuente SWAT+ y se cambió de 0.65 a 1.80 en una corrida de cultivo activo. Sin embargo, LAI, biomasa y ET vegetal impresos no cambiaron en los 11.680 registros. Por eso no se atribuye respuesta a sus valores FSPM y se conserva `ACTIVE_BUT_NO_DETECTABLE_RESPONSE` como resultado observado con una ruta de código configurada, no como prueba de una diferencia de crecimiento. Se mantiene la incertidumbre de ejecución interna porque SWAT+ no imprime el coeficiente leído por HRU.

Para `can_ht_max`, el probe se ejecutó y `eplant` no cambió, pero este build no ofrece una columna de altura vegetal. Una salida indirecta sin cambio no permite descartar cambios de altura internos, por lo que se usa `OUTPUT_NOT_OBSERVABLE`, no `LIKELY_NOT_ACTIVE`.

## Pareja FSPM y redondeo

En las copias normalizadas, la comparación conjunta de los diez valores FSPM con el baseline produjo cambios en 17 variables de salida vegetal y 59 columnas hidrológicas de `basin_wb_day`, `hru_wb_day` y `channel_sd_day`. Entre variables ilustrativas:

| Variable | Filas/celdas distintas | Máx. diferencia absoluta | Primer día |
|---|---:|---:|---|
| `hru_pw_day.lai` | 3353/11680 | 1.180 | 2019-05-16 |
| `hru_pw_day.bioms` | 3372/11680 | 1567.916 | 2019-05-16 |
| `hru_wb_day.eplant` | 1916/11680 | 2.956 | 2019-05-17 |
| `hru_wb_day.perc` | 2260/11680 | 0.098 | 2019-05-23 |
| `basin_wb_day.et` | 176/365 | 0.810 | 2019-05-18 |
| `crop_yld_aa.MASS` | 31/31 | 534.276 | 2019-12-31 |

El último par aplica diez cambios a la vez; esos cambios conjuntos no atribuyen causalidad a cada campo individual. La evidencia causal por campo procede de los probes OAT.

En los artefactos originales de fase 3.4, `basin_wb_day.txt`, `channel_sd_day.txt` y `hru_wb_day.txt` tenían checksums idénticos; el harness confirmó también igualdad de filas y valores normalizados de las salidas disponibles y de los archivos de rendimiento. La impresión `hru_pw_day.txt` no estaba habilitada. Por tanto, no había evidencia de diferencia escondida solo por hashes, formato decimal o fechas agregadas. En los workspaces nuevos, las salidas diarias se compararon después de parsear cada token numérico y su precisión impresa; las diferencias de LAI, biomasa, ET y percolación excedieron el redondeo de tres decimales. La frecuencia diaria y los hashes se mantuvieron constantes entre brazos.

## Registro y consumo por FastAPI

Se implementó `backend/scripts/register_verified_experiment.py`. En modo `--check-only` verificó el manifest, los checksums del proyecto, `success.fin`, checksums de outputs SWAT+, hashes de ambos SQLite playback, IDs y roles compatibles, 365 fechas contiguas, periodo y seed, igualdad de forcing, manejo y configuración compartida, cambio único de `plants.plt`, procedencia real y ausencia de etiquetas fixture/calibrated/observed. Resultado: `ARTIFACTS_VERIFIED_NO_DATABASE_ACCESS` para `phase34-sf19-baseline` y `phase34-sf19-coupled`.

La escritura exige simultáneamente `--database-scope development`, `--apply`, `APP_ENV=development` y URL PostgreSQL loopback. Verifica propietario activo, cuenca correspondiente y escenario neutral, rechaza IDs existentes, y crea los dos rows en una transacción. `--verify-existing` solo lee y compara identidades y hashes. Los registros conservan `experiment_id`, rol, `peer_run_id`, checksums, classification experimental y los tipos de evidencia `REAL_SWAT_PLUS` / `REAL_SWAT_PLUS_COUPLED`. Nunca marca `VALIDATED`, `CALIBRATED`, `HISTORICAL_RECONSTRUCTION` ni `OBSERVED`.

**Estado:** no se ejecutó `--apply`: no hay PostgreSQL escuchando en `localhost:5432`, ni se conoce un propietario y escenario de desarrollo disponibles en otra instancia. Las filas de los IDs anteriores solo están en la SQLite desechable ya excluida de Git; no están registradas en la base usada por el backend normal. No hay IDs accesibles desde la UI todavía. En la corrida previa, el informe de fase 3.4 registra respuestas 200 de FastAPI sobre esa SQLite para availability y playback diario en 16 de abril, 24 de julio y 1 de enero; documenta `SCIENTIFIC_ACTIVE`, `SCIENTIFIC_ACTIVE` y `SCIENTIFIC_FALLOW` respectivamente, con los valores FSPM fechados y las limitaciones, y un 404 para una corrida no perteneciente al propietario. Esa evidencia de SQLite no reemplaza una verificación contra PostgreSQL actual.

No fue necesario cambiar endpoints, tipos TypeScript, `adaptPlaybackVisual()` ni componentes Three.js. Los registros fechados contienen altura, LAI, raíz, biomasa, fenología, transpiración, estrés, precipitación, caudal, muestras estables, IDs HRU, evidencia y limitaciones en las unidades guardadas. También se pasó cada uno de los tres registros reales archivados por el adaptador TypeScript oficial: produjo `SCIENTIFIC_ACTIVE`, `SCIENTIFIC_ACTIVE` y `SCIENTIFIC_FALLOW`; preservó 36 IDs HRU, diez muestras en fechas activas, el estado nulo de plantas fuera de temporada, unidades, evidencia y limitaciones. Para el 16 de abril la respuesta contiene altura ≈0.03378 m, LAI ≈0.14355, raíz ≈0.08903 m y etapa `EMERGENCE`; para el 24 de julio altura ≈2.43704 m, LAI ≈5.00455, biomasa ≈260.85318 g/planta y raíz ≈1.20014 m; el 1 de enero no hay estado vegetal. La humedad FSPM es un supuesto de 24% volumétrico y no se deriva del almacenamiento SWAT+ en mm. La comprobación usó la salida FastAPI guardada de fase 3.4, no una consulta nueva a PostgreSQL.

`field_aggregates` estacional continúa marcado `SEASONAL_MAXIMA_FOR_COUPLING_NOT_A_DATED_FSPM_STATE`. El mapper ahora recibe `CouplingPlantParameterSummary`, un contrato dedicado que excluye distribuciones fechadas de LAI/raíz, estrés, ET, biomasa, humedad y fenología. Los agregados fechados del playback diario no cambiaron; el snapshot legible del resumen conserva la fecha del máximo LAI y no sustituye altura o raíz con máximos de otras fechas. Gemini debe dibujar únicamente el `PlaybackRecord` de la fecha seleccionada.

## Archivos locales, repetición y límites

El harness escribe bajo `backend/data/phase35-sensitivity-verification-vN/`, verifica manifest y checksums y rechaza sobrescribir un directorio existente. Esa salida y los workspaces están excluidos de Git; se versionan solo script, pruebas y documentación. Para una repetición con SWAT+ configurado, desde `backend/`:

```bash
./.venv/bin/python scripts/run_phase35_sensitivity_verification.py \
  --output-root data/phase35-sensitivity-verification-vN
```

Use un `vN` nuevo. El script no conecta a PostgreSQL. El verificador del importador se puede repetir con `--check-only`; para escritura requiere la instancia y los IDs de desarrollo explícitos.

Límites que siguen vigentes:

- La pareja original de fase 3.4 no demuestra que SWAT+ cargó los diez valores modificados; la evidencia positiva se limita a las copias normalizadas de diagnóstico.
- No se dispone de impresión directa de altura, profundidad de raíz ni valor interno de `ext_co` por HRU.
- Los probes y sus salidas se identifican como diagnósticos, no son parámetros científicos finales ni constituyen calibración.
- No hay observaciones de siembra/cosecha para comparar, ni validación contra observaciones.
- PostgreSQL, los endpoints con las filas persistidas y la UI normal siguen pendientes; FastAPI fue comprobado con la SQLite desechable ya producida, no con PostgreSQL en esta fase.
- No se ejecutaron análisis Sobol ni el experimento completo v3, no se modificó SWAT+ fuente, los artefactos históricos v2 ni componentes Three.js, y no se hizo push.

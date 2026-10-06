# Fase 3.4: auditoría y primera ejecución FSPM–SWAT+

> **Registro histórico.** Describe la ejecución de fase 3.4 y sus comprobaciones,
> no el estado operativo actual. La compatibilidad de inputs, los calendarios
> ejecutados, la estimación hídrica y la persistencia PostgreSQL evolucionaron
> después. Véanse [estado actual](../CURRENT_STATE.md),
> [acoplamiento vigente](../FSPM_SWAT_PLUS_COUPLING.md) y
> [auditoría de sensibilidad](PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md).
> Las métricas, hashes y limitaciones originales se conservan como evidencia.

Fecha de verificación: 2026-09-27. Commit de partida: `398c92facda4086eb5636815250a913d2b9e4354`.

## Resultado

Se corrigió la mutación indirecta de estados FSPM fechados, se añadió el preflight obligatorio antes de crear una ejecución acoplada y se centralizó la clasificación de procedencia para `/availability` y `/swat-results`. Se preparó una copia experimental CDL 2019 del proyecto SWAT+ y se ejecutaron SWAT+ baseline y acoplado, además de verificar sus artefactos mediante servicios y endpoints FastAPI con una base SQLite desechable.

Es una primera cadena ejecutada con motor SWAT+ real y una trayectoria generada por el FSPM simplificado. No es calibración, validación observacional, reconstrucción de siembras históricas ni evidencia de acoplamiento bidireccional. La ejecución tuvo lugar con el código local `398c92f+dirty`; sus manifiestos conservan ese `code_version`. El cambio final de la salida de consola del runner ocurrió después y no afectó al cálculo.

## Procedencia agrícola y causa del bloqueo original

La cadena activa del proyecto fuente, comprobada en los archivos SWAT+, es:

```text
hru-data.hru: 36 HRU → agrl_lum
landuse.lum: agrl_lum → agrl_comm + agrl_rot
plant.ini: agrl_comm → agrl
plants.plt: agrl = warm_annual/temp_gro genérico
management.sch: agrl_rot → pl_hv_summer1 agrl
lum.dtl: pl_hv_summer1 usa plant crop y harvest_kill crop
```

El proyecto fuente también contiene un registro de planta `corn` y una tabla `pl_hv_summer1_corn` con acciones específicas `plant corn` / `harvest_kill corn`, pero la cadena de los 36 HRU no los referencia. Por eso la presencia de la planta y tabla no era evidencia de cultivo de maíz activo. El preflight del proyecto fuente reportó `COUPLED_CROP_CONFIGURATION_INVALID`; no se cambiaron sus etiquetas ni se ejecutó ese proyecto como si `agrl` fuera `corn`.

### Variante aislada

El preparador `backend/scripts/prepare_south_fork_cdl_experiment.py` crea una copia nueva y falla si el destino ya existe. Usa composición estática CDL de 2019 con cobertura válida y umbral explícito de fracción de maíz ≥0.50. Selecciona estos 32 HRU:

```text
1, 2, 5–24, 26–27, 29–36
```

Los HRU 3, 4, 25 y 28 permanecen en `agrl`. En la copia, los HRU seleccionados enlazan `corn_lum` → `corn_comm` → `corn_rot` → `pl_hv_summer1_corn`; la tabla de decisión existente se valida por sus acciones de siembra y cosecha de maíz. `plants.plt` y `lum.dtl` de preparación se conservan byte por byte. Los cuatro archivos alterados para construir la variante son `hru-data.hru`, `landuse.lum`, `plant.ini` y `management.sch`. Los hashes de las entradas del proyecto fuente antes y después coinciden.

La selección sigue siendo un experimento hipotético informado por la clase dominante de una imagen anual CDL: no representa rotación plurianual ni confirma eventos de siembra/cosecha. Cambiar `landuse.lum`, comunidad y manejo puede cambiar crecimiento, cobertura, rendimiento, ET, almacenamiento, escorrentía y caudal. Por eso el baseline de la pareja se ejecutó también sobre esa misma variante; la comparación aísla la modificación adicional de parámetros vegetales FSPM, no el impacto de cambiar del manejo `agrl` al de maíz.

El manifiesto local de la copia es `backend/data/phase34-cdl-2019/manifest.json` y su SHA-256 durante la ejecución fue `a2885c60891c0d85689f0449d3b153c0f36814667a0e42372b04ac41012f7d4d`. Documenta IDs, cambios, procedencia CDL, cadena, aproximación PHU y hashes antes/después. Los datos generados están excluidos de Git por `.gitignore`; el preparador y su prueba sí están versionados.

## Flujo de cálculo, variables y persistencia

| Dato | Generación, unidad y frecuencia | Persistencia y recuperación | Límite |
|---|---|---|---|
| Temperatura, lluvia, radiación, humedad relativa y viento | `SwatClimateForcingReader`; archivos diarios de estaciones del proyecto SWAT+, unidades nativas (°C, mm/día, MJ/m²/día, %, m/s) | Checksum de cada forcing en `SimulationRun.provenance`; frame `weather` en artefacto playback DAILY | Media entre estaciones, sin ponderación HRU; no es una observación USGS. CO₂ de FSPM permanece asumido. |
| Planta modelada | `PlantPopulation.step` / FSPM simplificado: altura (m), LAI (m² hoja/m² suelo), biomasa (g/planta), raíces (m), etapa, estrés (fracción), transpiración (mm/día) | Estado agregado fechado y hasta diez muestras en SQLite `twin-playback-v1`; `plant_sample_context` declara población 1000, selección determinista e identidad `SIMULATION_SLOT` | Son estados de una población numérica simplificada, no individuos observados. Solo diez muestras representativas se publican, no las 1000 trayectorias completas. |
| Humedad del FSPM | 24 % volumétrico constante, evidencia `ASSUMED` | Variable diaria con fuente `ASSUMED_CONSTANT_NOT_SWAT_OUTPUT` | No procede de almacenamiento SWAT+; no tiene variación espacial ni realimentación de humedad. |
| Agregados de campo | `PlantToFieldAggregator`: medias y distribuciones calculadas para cada fecha activa | `field` por fecha en sidecar playback | El resumen estacional usado por el mapper marca `SEASONAL_MAXIMA_FOR_COUPLING_NOT_A_DATED_FSPM_STATE`; LAI, altura y raíces conservan fecha de máximo propia. |
| Parámetros vegetales SWAT+ | `SwatPlantParameterMapper`: resumen FSPM actualiza campos compatibles de la entrada de planta corn en `plants.plt` | Workspace SWAT+ acoplado; diff de input y valores originales/nuevos en `provenance.workspace_modifications` | Acoplamiento unidireccional de parámetros vegetales. No se impone ET, estrés, uptake, conductancia ni rendimiento del FSPM a SWAT+ si no hay conversión respaldada. |
| Caudal de salida | Parser SWAT+ `channel_sd`; m³/s, frecuencia nativa de salida | `monthly_outputs` conservando compatibilidad histórica y artefacto playback | Es caudal del outlet; no se copia a HRU. |
| Escorrentía, ET, percolación y agua en suelo | Parser SWAT+ desde `hru_wb` / salidas de cuenca; flujos mm por periodo y almacenamiento en mm | Resultado SWAT normalizado y playback por fecha/resolución; resultados HRU solo si el archivo incluye esa fila | Almacenamiento mm no es porcentaje volumétrico. `TERMS_COMPLETE` no significa cierre del balance. Null no se convierte en cero. |
| Resultados por HRU | Parser conserva los IDs que realmente aparecen en los archivos, con soporte `SWAT_HRU_OUTPUT_UNIT_NO_VERIFIED_POLYGON` | `hru_results` por registro playback | No se realiza asociación HRU→polígono. La estación/outlet no se replica en los HRU. |
| Fenología/temporada FSPM | Ventana aproximada con temperatura y PHU del manejo; fecha exacta de evento no impresa | `crop` diario con `season_id`, `window_status=APPROXIMATE_PLANTING_WINDOW` | No es una fecha de siembra/cosecha observada ni una reproducción completa de condiciones internas SWAT+ (`soil_water`, `year_rot`, etc.). |

Cadena de ejecución:

```text
Solicitud → preflight read-only → validación repetida del ejecutor
→ forcing directo diario → FSPM diario y agregación
→ resumen estacional no fechado → copia SWAT+ aislada + edición documentada de plants.plt
→ ejecutable SWAT+ → parser/normalización por periodo e ID HRU
→ manifests y sidecar SQLite con checksum por artefacto/registro
→ diagnóstico /availability + consulta /playback autenticadas
```

El endpoint de creación ahora rechaza un acoplamiento bloqueado antes de insertar filas o crear artefactos. El ejecutor vuelve a ejecutar preflight, incluida la copia efectiva tras aplicar el mutador. Una solicitud baseline independiente no requiere FSPM.

## Ejecución de verificación

- Periodo: 2019-01-01–2019-12-31 (365 días), salida SWAT+ DAILY.
- Mismo forcing y mismo proyecto variante para los dos brazos; la verificación de hashes reportó que las entradas de workspace difieren solo en `plants.plt`. `simulation.out` difiere por el registro de ejecución.
- SWAT+ devolvió exit code 0 en ambos casos; tiempos reportados por proceso: baseline 35.54 s, coupled 30.01 s.
- Antes: 48.35 GB libres, 2.38 GB de memoria disponible; presupuesto conservador documentado para workspaces/output: 1.96 GB. La carpeta del proyecto fuente medía ~711.9 MB.
- El preflight de variante indicó `READY`, 32 HRU destino, forcing FSPM diario completo y una ventana PHU aproximada. El preflight del proyecto fuente sin variante sigue bloqueado para maíz.
- ID local de relación: `phase34-south-fork-cdl-2019-verification`; identificadores de ejecución local `phase34-sf19-baseline` y `phase34-sf19-coupled`.
- El informe relaciona ambos IDs bajo ese `experiment_id`. El runner ahora también escribe el mismo identificador, los dos IDs de pareja y el rol/peer en `requested_config.swat_plus` y `provenance.experiment` de ambas filas SQLite desechables para cada reproducción; la prueba `test_verification_pair_persists_shared_experiment_id_and_peer_ids` valida esa relación.
- Plant record mapper cambió diez parámetros vegetales en `plants.plt`; por ejemplo, `lai_pot` 6.0 → 5.004551569 m²/m², `can_ht_max` 2.5 → 2.739507989 m, `rt_dp_max` 2.0 → 1.200218822 m. Se registraron los demás valores y el linaje en el reporte. No se cambió el archivo fuente ni se modificaron artefactos v2.
- Las salidas hidrológicas emparejadas fueron idénticas: `basin_wb_day.txt` SHA-256 `cfcb8e4ad70a24d28f9bde89262b78145aa0ff4dbb0542fbe7d1d638d9d7a347`; `channel_sd_day.txt` `3cbbf0dc811f5f48e2e1bd19896c0d0796b80a58acc6a7c752a21ebe44044c26`; `hru_wb_day.txt` `80daa83c2c85915e87625e79d256affe622ebfead972ea54ad0ffbc2132f4a48`. De los 283 archivos por workspace, difieren solo `plants.plt` y `simulation.out`; los resúmenes `basin_crop_yld_yr.txt` también son idénticos. No hay evidencia aquí de respuesta hidrológica a esos cambios de parámetros; se requiere un análisis de sensibilidad/impresión de estado vegetal SWAT+ validado antes de afirmar respuesta.
- `hru_wb_day.txt` conservó 11.680 registros HRU-día que llevan `corn_comm` / `corn_rot` (32 × 365). El resumen de cosecha de cuenca identificó corn, pero el log no imprime la fecha exacta de plantación ni la trayectoria diaria de crecimiento interna de SWAT+; `crop_yld_yr.txt` está solo con encabezado. El playback de planta es el FSPM simplificado, no esa salida interna SWAT+.

El directorio `backend/data/phase34-verification/` contiene el informe completo `phase34-real-engine-report.json`, workspaces, sidecars, salida local de playback y `verification-only.sqlite`; no se versiona. La comprobación de API creó filas solo en esa SQLite desechable: `/availability` clasificó baseline como `SWAT_EXECUTED` sin FSPM y acoplado como `COUPLED_EXECUTED` con resumen, trayectoria, muestras e hidrología disponibles. Las consultas a `/playback` de 2019-04-16, 2019-07-24 y 2019-01-01 devolvieron las fechas exactas, variables y códigos; la tercera no incluyó cultivo ni muestras. Una consulta como usuario no propietario devolvió 404. La configuración PostgreSQL local no respondió y no recibió ninguna fila.

Resultados de playback comprobados:

| Fecha | Estado | Altura | LAI | Biomasa | Raíz | Muestras | Limitación |
|---|---|---:|---:|---:|---:|---:|---|
| 2019-04-16 | activo, `EMERGENCE` | 0.03378 m | 0.14355 m²/m² | 0.0 g/planta | 0.08903 m | 10 | ventana aproximada; humedad 24% `ASSUMED` |
| 2019-07-24 | activo, `REPRODUCTIVE` | 2.43704 m | 5.00455 m²/m² | 260.85318 g/planta | 1.20014 m | 10 | ventana aproximada; humedad 24% `ASSUMED` |
| 2019-01-01 | fuera de temporada | null | null | null | null | 0 | no hay estado vegetal para representar |

Los IDs de las diez muestras se mantuvieron iguales entre primera fecha activa y máxima LAI. Máximo LAI: 24 de julio; máxima altura: 21 de octubre; máxima raíz: 27 de julio. El resumen de máximos que se pasa al mapper no se inserta en registros diarios.

## Defectos cerrados y límites

1. `peak_field` se mutaba después de guardarse en `fspm_days`: los snapshots diarios ahora se copian y el mapper consume un resumen independiente. Las fechas de máximos por variable se conservan. Una prueba coloca máximos de LAI, altura y raíz en fechas diferentes y compara snapshots antes/después.
2. La ruta acoplada ahora hace preflight de los recursos reales y la cadena de cultivo antes de persistir corridas; el ejecutor revalida. La prueba API demuestra cero filas, cero artefactos y cero llamadas al motor si está bloqueada. Baseline conserva su ruta independiente.
3. Un clasificador compartido prioriza `source_kind=HISTORICAL_IMPORT` y el ID exacto legacy `south-fork-final-coupled-2015-2020` por encima de una etiqueta de evidencia heredada `REAL_SWAT_PLUS`. `/availability` y `/swat-results` emiten clase coherente; desconocido no se promueve a ejecución real. No se modificó la fila v2.

Quedan pendientes: insertar corridas verificadas en un PostgreSQL disponible mediante el flujo real de creación; obtener fechas efectivas de siembra/cosecha y salidas de crecimiento SWAT+ con print configuration apropiado; investigar por qué este run no mostró diferencias en outputs al editar los parámetros mapeados; validar calibración/observaciones; probar varios años/rotación real; datos diarios de caudal si solo se imprimen mensual; respuesta de estrés hídrico a agua SWAT+; humedad FSPM espacialmente diferenciada; unión HRU→polígono verificada. No usar fórmulas visuales para completar esas ausencias.

## Pruebas ejecutadas

- Backend unitario/contrato seleccionado: `41 passed, 5 deselected`. Los deseleccionados fueron la prueba SQLite/API del preflight gate, la prueba de disponibilidad/API, la prueba de persistencia con adapter SWAT, y dos escenarios configurados con SWAT local. La suite aislada se ejecutó sin el `tests/conftest.py` que siembra PostgreSQL.
- Backend SQLite/API: `test_blocked_coupled_post_creates_no_runs_or_artifacts` y `test_availability_endpoint_owner_and_filtered_pagination` aprobaron por separado (`2 passed`). Incluyen 404 a usuarios ajenos, clasificación histórica y ausencia de nuevas filas/artefactos en preflight bloqueado.
- Motor auténtico: el runner de fase 3.4 ejecutó SWAT+ baseline y coupled, ambos exit code 0, y comprobó archivos de salida, checksums, entradas emparejadas, artefactos playback y endpoints FastAPI con SQLite temporal. No es una prueba con mock.
- Frontend: `node --experimental-strip-types tests/playback.test.ts` (`19 passed`); `tsc --noEmit` aprobado; ESLint aprobado para los dos tipos TypeScript cambiados y `tests/playback.test.ts`; `next build --webpack` aprobado.
- Python `compileall` y `git diff --check` aprobados. `ruff`, `black` y `mypy` no están instalados; no se declara lint Python.
- Se recopilaron 157 pruebas backend. No se ejecutó la suite completa con la configuración normal porque PostgreSQL local no respondía y el `conftest.py` de esa suite inicializa la base. Las suites seleccionadas no se presentan como ejecución completa.
- No se ejecutó una prueba visual en navegador.

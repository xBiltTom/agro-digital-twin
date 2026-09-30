# Traspaso a Gemini: contrato científico para las tres escalas 3D

## Entrada pública

- `frontend/src/lib/playback-visual-adapter.ts`: `adaptPlaybackVisual(record, {simulationId, simulationName, availability, selectedPlantId})` devuelve `TwinVisualState`. Es puro y no depende de React ni de Three.js.
- `frontend/src/types/playback-availability.ts`: `VisualMode`, `AvailabilityCode`, `SimulationAvailability` y disponibilidad por fecha/resolución. Coincide con `backend/app/schemas/playback_diagnostic.py`.
- `frontend/src/lib/api.ts`: `api.getPlaybackAvailability(id, date?)` consulta `GET /api/v1/simulations/{id}/availability` con los permisos del endpoint playback. `api.getPlayback` obtiene el registro seleccionado.
- `frontend/src/hooks/useTwinPlayback.ts`: expone `availability`, `availabilityLoading`, `record`, `setResolution`, `jumpToDate` y `jumpToFirstCrop`. La página ofrece el botón **Ir al primer cultivo** cuando la resolución seleccionada tiene `first_representable_field`. La búsqueda navega solo a una fecha del manifiesto mediante el índice playback. Si la serie FSPM está en `DAILY` y se seleccionó `MONTHLY`, aparece una indicación para cambiar resolución; no cambia fecha ni resolución automáticamente.
- `frontend/src/lib/playback-navigation.ts`: `firstCropNavigation` decide entre fecha disponible, cambio a `DAILY` o ausencia de cultivo representable. Baselines sin FSPM no muestran la acción.
- `frontend/src/lib/playback-scene.ts`: `sceneFromRecord` conserva las entradas que reciben los componentes 3D actuales y adjunta `scene.visual` con el contrato oficial. `frontend/src/lib/visual-state.ts` mantiene `REFERENCE_MAIZE` exclusivamente como dimensiones ilustrativas; no forma parte de `TwinVisualState`.

## Consulta de una corrida y fecha

Usa `GET /api/v1/simulations?skip=0&limit=100` para elegir una corrida. El servidor limita las filas al usuario actual (excepto roles con acceso administrativo); continúa con `skip` hasta que la página tenga menos elementos que `limit`. No enumeres corridas globalmente ni interpretes un identificador no accesible como existente: FastAPI devuelve 404 fuera del alcance del usuario.

1. Pide `GET /api/v1/simulations/{id}/availability?date=YYYY-MM-DD` para conocer modo, códigos, resoluciones y fechas representables.
2. Pide `GET /api/v1/simulations/{id}/playback?resolution=DAILY&date=YYYY-MM-DD` para estados FSPM diarios, o selecciona explícitamente la resolución SWAT+ mensual/anual disponible. Las consultas por fecha y rango usan el índice SQLite; pagina con `offset`/`limit`.
3. Si la respuesta no incluye el estado pedido, conserva la selección del usuario y presenta el motivo. `first_representable_field` y `first_plant_samples` son fechas guardadas; `jumpToFirstCrop()` es una acción explícita y solo navega a una fecha del artefacto.
4. Si SWAT+ es mensual y FSPM diario, solicita `resolution=DAILY` para la trayectoria y conserva la frecuencia mensual en otra selección/serie. El sidecar diario contiene clima/FSPM y declara que no contiene hidrología diaria.

`GET /api/v1/simulations/{id}/swat-results` entrega resultados SWAT persistidos y su procedencia (`EXECUTED` o `HISTORICAL_IMPORT`) para los gráficos. Una importación histórica conserva periodos y unidades originales; no reconstruyas días desde filas mensuales.

Ejemplo:

```ts
const diagnostic = await api.getPlaybackAvailability(simulationId);
const page = await api.getPlayback(simulationId, { resolution: "DAILY", date: "2020-08-10" });
const visual = adaptPlaybackVisual(page.records[0] ?? null, {
  simulationId, simulationName: run.name, availability: diagnostic,
  selectedPlantId: "test-plant-1",
});
if (visual.mode === "SCIENTIFIC_ACTIVE" && visual.fieldRepresentable) {
  // height/lai conservan value, unit, evidence, source y limitation.
}
const sample = visual.plantSamples.find((plant) => plant.plant_id === selectedPlantId);
// plantSampleContext explica población representada, muestreo e identidad.
```

## Modos y lectura

| Modo | Significado | Cultivo científico |
|---|---|---|
| `SCIENTIFIC_ACTIVE` | El modelo fechado marca cultivo activo; `fieldRepresentable` y `sampleRepresentable` indican por separado si hay altura/LAI de campo o muestra con altura. Puede ser incompleto. | Solo con variables disponibles y maíz compatible. |
| `SCIENTIFIC_FALLOW` | Hay estado fechado y `crop.active=false`. | Ninguno. |
| `HYDROLOGY_ONLY` | Hay hidrología fechada, sin FSPM en esa resolución/corrida. | Ninguno; se puede ofrecer referencia ilustrativa etiquetada. |
| `HISTORICAL_REFERENCE` | Importación v2 sin trayectoria playback v1. Sus resultados persistidos todavía se pueden consultar mediante `/swat-results` y graficar con origen `HISTORICAL_IMPORT`. | Ninguno; los agregados históricos no son una fecha de crecimiento. |
| `DATA_UNAVAILABLE` | Falta estado utilizable, artefacto o integridad. | Ninguno. |

Los códigos estables son `NO_PLAYBACK_ARTIFACT`, `ARTIFACT_UNAVAILABLE`, `ARTIFACT_INVALID`, `SWAT_BASELINE_NO_FSPM`, `HYDROLOGY_ONLY`, `HISTORICAL_REFERENCE`, `OUTSIDE_CROP_SEASON`, `FSPM_STATE_MISSING`, `DATE_NOT_IN_PLAYBACK`, `UNSUPPORTED_CROP_GEOMETRY`, `FIELD_HEIGHT_MISSING`, `FIELD_LAI_MISSING`, `NO_PLANT_SAMPLES`, `SAMPLE_HEIGHT_MISSING`, `SCIENTIFIC_STATE_AVAILABLE`. `stored_fspm_summary_available` requiere una variable FSPM finita con clave reconocida; `stored_fspm_trajectory_available` requiere valores FSPM fechados; `stored_fspm_samples_available` informa muestras individuales persistidas. `fspm_results_available` resume si existe alguno de esos tres tipos y no implica trayectoria. Por resolución, `first_plant_samples` informa la primera fecha con muestras y `first_representable_field` la primera fecha de campo representable. Una corrida ajena responde 404; el diagnóstico no revela su existencia. `selected_date` es opcional; pedir `?date=YYYY-MM-DD` para un diagnóstico puntual. Los intervalos agrícolas tienen `approximate=true` cuando provienen de ventanas PHU, no de eventos de siembra observados.

`TwinVisualState` retiene los `VariableState` completos. `null` significa desconocido y `0` significa cero registrado. `fspmMoisturePercent` es porcentaje volumétrico FSPM y puede tener evidencia `ASSUMED`; `swatSoilWaterMm` es almacenamiento SWAT+ en mm. No hay conversión entre ambos. `plantSamples` contiene solo IDs reales persistidos, con coordenadas locales; `hruIds` contiene IDs de salida y ninguna identidad de polígono. `resolution` es efectiva: los totales mensuales/anuales no son lluvia diaria. La biomasa FSPM es `g/plant`.

`TwinVisualState` también expone `laiDistribution`, `rootDepthDistribution`, `representativePlantCount` y `plantSampleContext`. Cada propiedad variable conserva `value`, `unit`, `evidence`, `source`, `availability` y `limitation`. Si falta LAI pero existe altura, conserva la altura y el LAI nulo.

### Procedencia y frecuencia de las variables

| Variable o escala | Productor y unidades | Frecuencia y persistencia | Límite científico |
|---|---|---|---|
| Altura, LAI, biomasa, raíz, fenología, estrés y transpiración | `PlantPopulation.step` / FSPM simplificado; altura y raíz m, LAI m² hoja/m² terreno, biomasa g/planta, estrés fracción, transpiración mm/día | Por fecha activa; agregado de campo y hasta diez muestras representativas en playback DAILY o `playback_daily_fspm` | Estados modelados simplificados, no observaciones. No convertir raíz desde almacenamiento SWAT+. |
| Distribuciones de LAI y raíz | `PlantToFieldAggregator`; p10/p90/desviación de LAI y p10/p90 de raíz | Por fecha activa en el registro DAILY | Estadísticas de la población modelada; nulos se conservan. |
| IDs de muestra y coordenadas | Población sembrada con seed; IDs y x/y locales en m | Estables como `SIMULATION_SLOT` al reevaluar esa población en la corrida | Diez muestras seleccionadas determinísticamente a través de la población, no un censo de diez plantas observadas. El contexto declara método y conteos. |
| Cultivo, temporada y etapa | Estado FSPM asociado a ventana PHU aproximada del manejo SWAT+ | Fechado DAILY | `APPROXIMATE_PLANTING_WINDOW` no es evento de siembra observado. |
| Humedad FSPM | Entrada constante del FSPM: 24% volumétrico (`ASSUMED`) | DAILY en días de cultivo; ausente fuera de temporada | No procede de SWAT+, no existe retroalimentación de almacenamiento y no tiene variación espacial. |
| Temperatura y precipitación | `SwatClimateForcingReader` desde `weather-sta.cli` y archivos de estación; °C, mm/día; radiación MJ/m²/día y humedad % si existen | Diario; agregado a frecuencia de salida sin crear días | Promedio simple entre estaciones; no ponderado por HRU ni observación USGS. Precipitación faltante es null; cero puede ser real. |
| Caudal de salida | Parser de `channel_sd` SWAT+ o serie observada identificada; m³/s | Frecuencia nativa DAILY/MONTHLY/ANNUAL; observación solo en fechas disponibles | Caudal del outlet; nunca se replica por HRU ni se interpola. |
| Escorrentía, ET, percolación y almacenamiento | Salidas SWAT+ normalizadas; flujos mm/periodo y almacenamiento mm | Frecuencia del artefacto; HRU solo si el archivo trae filas HRU | Almacenamiento en mm no es humedad volumétrica. `TERMS_COMPLETE` indica cobertura temporal de términos, no cierre físico. |
| HRU | IDs realmente impresos por SWAT+ y variables con sus unidades | Frecuencia y fechas presentes en resultados HRU | `polygon_id=null`; no existe unión espacial HRU→polígono verificada. |
| Importación histórica | Resultados persistidos y procedencia importada | Frecuencia original histórica | No es nueva ejecución ni calibración. No reconstruir FSPM ni series diarias. Errores heredados quedan intactos hasta reparación reversible explícita. |

El resumen `total_discharge_hm3` se integra solo desde caudales diarios completos. En salida SWAT+ MONTHLY/ANNUAL o con caudal diario incompleto, el valor queda `null`, `total_discharge_status="NOT_AVAILABLE"` e incluye la causa en `total_discharge_limitation`; el backend no lo deriva multiplicando un promedio de periodos por días. Los informes exportados muestran “No disponible”/celda vacía para ese caso y conservan un cero medido como `0`.

### Modos y casos incompletos

- **A. Hidrología sin FSPM (`HYDROLOGY_ONLY`)**: conserva lluvia, caudal, almacenamiento y HRU presentes. No asigna altura, transpiración o fenología FSPM. La planta de referencia es ilustrativa y debe estar separada de `TwinVisualState`.
- **B. Cultivo activo (`SCIENTIFIC_ACTIVE`)**: usa solo variables de la fecha guardada. `fieldRepresentable` y `sampleRepresentable` se evalúan por separado. Si hay altura y falta LAI, conserva altura y muestra LAI como null.
- **C. Fuera de temporada (`SCIENTIFIC_FALLOW`)**: `crop.active=false`; no mostrar cultivo científico ni arrastrar el último estado vegetal.
- **D. Referencia histórica (`HISTORICAL_REFERENCE`)**: presenta solo variables y periodos persistidos y conserva `HISTORICAL_IMPORT`; no atribuir ejecución, validación v3 ni trayectoria vegetal.
- **E. Datos incompletos (`DATA_UNAVAILABLE`)**: conserva variables disponibles. Los códigos `ARTIFACT_UNAVAILABLE`/`ARTIFACT_INVALID` distinguen persistencia e integridad de una variable no calculada.
- **F. Frecuencias diferentes**: DAILY y MONTHLY son dos series independientes con sus propias resoluciones. No interpolar ni duplicar para sincronizarlas; indica el periodo efectivo de cada una.

## Preflight real y disponibilidad observada

`POST /api/v1/simulations/preflight` es autenticado y no crea corridas. Valida el proyecto exacto de la solicitud, los archivos de control y, para `SWAT_MULTISCALE_COUPLED`, que el cultivo destino esté asociado al manejo de HRU activo, exista forcing FSPM diario y haya una ventana PHU aproximada. Devuelve bloqueos y conteos de componentes/modelos. La estimación mínima de almacenamiento cubre una copia aislada del proyecto SWAT+, no crecimiento de salidas; el runtime depende de periodo y frecuencia.

El proyecto fuente sigue bloqueando el acoplamiento de maíz y debe permanecer así: los 36 HRU usan `agrl_lum` → `agrl_comm` → registro `agrl` → `agrl_rot` → decisión `pl_hv_summer1`, con las acciones genéricas `plant crop` y `harvest_kill crop`. `plants.plt` contiene `corn` y `lum.dtl` contiene `pl_hv_summer1_corn`, pero el proyecto fuente no los enlaza desde esos HRU. La fase 3.4 no cambió el proyecto fuente.

Se preparó y ejecutó una variante aislada de prueba, clasificada como experimento hipotético de manejo y no como reconstrucción histórica ni validación South Fork. El mapa CDL estático 2019 marcó 32 HRU con fracción de maíz ≥ 0.50; los HRU 3, 4, 25 y 28 se dejaron sin cambiar. La variante enlaza solo esos 32 HRU con `corn_lum` → `corn_comm` → `corn_rot` → `pl_hv_summer1_corn`, cuya tabla contiene acciones explícitas de `plant corn` y `harvest_kill corn`. Se conservaron todas las entradas originales en una copia; el manifiesto y los hashes están en `backend/data/phase34-cdl-2019/manifest.json` (directorio local excluido de Git). Las fracciones CDL anuales no son fechas observadas de siembra/cosecha; las ventanas FSPM siguen siendo aproximaciones PHU.

La ejecución real pareada cubrió 2019-01-01 a 2019-12-31, con 365 entradas diarias, semilla 42 y población FSPM modelada de 1000 plantas. El baseline y el acoplado usaron la misma variante CDL, el mismo forcing y el mismo periodo; dentro de sus 283 archivos de trabajo, solo `plants.plt` (parámetros de cultivo) y `simulation.out` difieren. No representa una comparación entre el proyecto original `agrl` y una superficie de maíz: ambos brazos tienen la configuración experimental CDL; el acoplado además recibe parámetros vegetales derivados del resumen FSPM.

Evidencia de la verificación: SWAT+ terminó en ambos brazos con código 0; la comprobación de salida encontró la comunidad esperada en 11.680 HRU-día; los artefactos DAILY tienen 365 registros y pasan checksum; FastAPI local sobre SQLite desechable devolvió disponibilidad y playback; el acceso de un usuario ajeno fue 404. El primer campo y las primeras muestras disponibles son 2019-04-16, con diez IDs estables; el 2019-07-24 hay LAI de campo 5.0046 m²/m² y etapa `REPRODUCTIVE`; 2019-01-01 está fuera de temporada y no tiene estado vegetal. La humedad FSPM de 24% conserva evidencia `ASSUMED` y no viene de SWAT+.

Las salidas hidrológicas `basin_wb_day.txt`, `channel_sd_day.txt` y `hru_wb_day.txt` de la **pareja original** tuvieron checksums idénticos; los archivos de rendimiento de cultivo disponibles también fueron idénticos. Esta igualdad no demuestra sensibilidad a los parámetros FSPM. La auditoría de fase 3.5 encontró que SWAT+ 61.0.2.61 espera un entero en `days_mat`, pero el `plants.plt` de fase 3.4 serializaba `120.00000`; el lector ignora errores positivos de conversión. Además, el `hru_pw_day.txt` vegetal no estaba habilitado. Por tanto, los resultados originales no demuestran que SWAT+ cargó los cambios de planta. Los IDs `phase34-sf19-baseline` y `phase34-sf19-coupled` siguen en la integración SQLite desechable, no en PostgreSQL disponible para la UI. PostgreSQL local no respondió durante esta fase.

### Reproducción del experimento local verificado

Los comandos siguientes fueron ejecutados desde `from-plant-to-watershed/backend` en el entorno donde están las rutas de SWAT+ y CDL configuradas. El preparador rechaza sobrescribir su destino; el runner también rechaza una carpeta de salida existente. Los datos de entrada, salidas, manifests de playback y SQLite se guardan bajo `backend/data/`, excluido de Git:

```bash
PYTHONPATH=. .venv/bin/python scripts/prepare_south_fork_cdl_experiment.py \
  --source-project /home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/project/Scenarios/Default/TxtInOut \
  --cdl-composition /home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/cdl/hru_crop_composition.parquet \
  --cdl-provenance /home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/cdl/hru_crop_provenance.json \
  --destination data/phase34-cdl-2019

PYTHONPATH=. .venv/bin/python scripts/run_phase34_south_fork_verification.py \
  --experiment-bundle data/phase34-cdl-2019 \
  --watershed-metadata /home/bilton/.swatplus_builder/artifacts/south_fork_05451210_2000_2025_retry/delin/watershed_result.json \
  --output-root data/phase34-verification --artifact-root data --timeout-seconds 1800
```

El preparador registra los checksums fuente y de la copia y valida que solo `hru-data.hru`, `landuse.lum`, `plant.ini` y `management.sch` cambien al construir la configuración. El runner ejecuta ambos brazos sobre workspaces separados, verifica hashes de entradas, salidas SWAT+ y sidecars, crea metadatos solo en SQLite temporal e invoca los endpoints FastAPI reales. No registra las corridas en PostgreSQL.

## Fixtures y verificación

`frontend/tests/fixtures/twin-visual-fixtures.json` se genera con los **esquemas Pydantic reales** mediante:

```bash
cd from-plant-to-watershed
backend/.venv/bin/python backend/scripts/generate_visual_fixtures.py
cd frontend
pnpm test
```

Todas las páginas declaran `test_only: true`, `scientific_result: false` y que no son resultados South Fork. `coupled_daily` tiene maíz joven, maíz reproductivo, día sin cultivo, precipitación cero y precipitación desconocida. `baseline` tiene solo hidrología. `historical` no tiene playback. `incomplete` conserva LAI pero deja altura nula. `coupled_monthly` presenta hidrología mensual separada de la trayectoria FSPM diaria de la misma corrida. Las pruebas usan exactamente `PlaybackPage` y `PlaybackRecord`; no insertan nada en PostgreSQL. Para inspección manual, interceptar `GET .../playback` con una página de la fixture en el entorno de pruebas del navegador, como hace `frontend/tests/visual-playback.mjs`. No activar estas páginas mediante el backend de producción.

El generador Pydantic añade distribuciones vegetales, cantidad de población y método de muestreo. No conectes las fixtures a la base productiva ni las presentes como una ejecución South Fork.

## Hallazgos de la base configurada (auditoría solo lectura, 2026-09-24)

La auditoría de solo lectura de la base PostgreSQL configurada encontró seis corridas de dos propietarios. Una línea base `SWAT_STANDARD_BASELINE` dispone de 365 registros diarios íntegros (2018), hidrología y 36 IDs HRU; no tiene cultivo/FSPM. Una importación South Fork v2 tiene resultados históricos agregados sin manifiesto v1. Otras cuatro corridas carecen de manifiesto v1. Ninguna de esas seis filas contiene una trayectoria FSPM diaria acoplada accesible. La verificación local 2019 descrita arriba es una nueva ejecución real del motor, pero no una fila de esa base. La lista API pagina por propietario y el cliente consume todas las páginas de 100.

La importación histórica existente presenta indicadores de cinco defectos heredados: percolación fija 142.50, cierre cero no calculado, humedad derivada de `soil_water_mm/10`, biomasa etiquetada `kg/m²` pese al esquema `g/plant`, y etiqueta de calibración pese al informe v2 (`NOT_OPTIMIZED`, ningún parámetro ajustado). `backend/scripts/populate_swat_simulations.py` hace auditoría de solo lectura por defecto y ya no crea estos valores en futuras importaciones. La reparación de la fila existente **no se ejecuta automáticamente**. Procedimiento reversible: exportar JSON completo de la fila y hashes v2, identificar el ID en la auditoría, preparar un parche de campos JSON con valores `null` y claves de razón, revisar el diff, ejecutar una transacción explícita con copia de seguridad y verificar de nuevo; conservar rollback documentado. No editar los archivos v2.

## Reparación local de playback — 2026-09-29

Se comprobó el PostgreSQL local antes de modificarlo. La corrida `09dd581d-e2ac-44d8-b3c0-3e641301ec92` (SWAT+ estándar, 2018) conservaba 365 salidas hidrológicas y un sidecar SQLite cuyo SHA-256 y 365 fechas coincidían con el manifiesto; `playback_frames` no tenía filas. Se respaldó `digitaltwin` en `/tmp/opencode/digitaltwin-before-twin3d-repair.dump` y se migró el sidecar verificado a 365 frames JSONB `DAILY`. La corrida sigue siendo baseline y no contiene cultivo ni FSPM.

El bundle local `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2` superó la verificación de los 20 artefactos y del archivo comprimido. Se registró con el script existente como `phase234-sf-2019-v2`, asignado al propietario local de desarrollo: 365 frames diarios, 36 HRUs y 37 canales. No se volvió a ejecutar SWAT+.

Después de la reparación, `/availability` y `/playback` informan `AVAILABLE` para ambas corridas. En 2018 el playback es hidrológico (`SWAT_STANDARD_BASELINE`, sin FSPM); en 2019-07-15 la corrida acoplada devuelve cultivo activo, LAI, 70 muestras, 36 HRUs y 37 canales. El visor debe respetar el `simId` de la URL, elegir inicialmente la resolución con trayectoria FSPM cuando exista, y distinguir un manifiesto inválido de la ausencia histórica de playback.

## Alcance de Gemini

Trabajar solo en representación 3D: geometrías, mallas, animación, materiales, iluminación, cámara y calidad gráfica. Consumir `TwinVisualState` o `scene.visual` y sus códigos; no cambiar FastAPI, importadores, FSPM, SWAT+, contratos o datos históricos. No convertir `null` en cero; no inferir lluvia de escorrentía, estrés de ET, humedad porcentual de mm, ni polígonos a partir del índice HRU. Separar toda planta de referencia de los resultados científicos. Los componentes actuales muestran referencia cuando `scene === null`, incluso mientras se carga un registro; decidir visualmente cómo distinguir espera de `HISTORICAL_REFERENCE`/`DATA_UNAVAILABLE`. No interpretar las 1.014 instancias del campo como plantas individuales simuladas. La integración HRU→polígono y la ejecución v3 quedan para fases posteriores.

Hallazgos visuales pendientes (no modificados por Codex): `FieldPlotMesh3D.tsx` altera las sondas contextuales en +2.5 y −2.8 puntos porcentuales; requieren etiqueta ilustrativa o una variable espacial real, que el backend no proporciona. `PlantModel3D.tsx` usa 1.4 mm/día de transpiración para la planta de referencia; no es un resultado FSPM. `WatershedMesh3D.tsx` usa 5 m³/s como respaldo para animar el río cuando caudal es null; el efecto ambiental puede continuar como decoración, pero una animación presentada como impulsada científicamente debe detenerse o quedar indeterminada sin caudal. `SoilGridsStratigraphyCutout` usa 24% cuando falta humedad y la red de canales fija un factor óptico: son parámetros visuales, no sensores o humedad medida. Mantén claramente separados los efectos atmosféricos decorativos de los impulsados por una variable científica.

## Actualización confirmada de fase 3.5

La causa más probable de la igualdad original se identificó en la lectura de `plants.plt`: `days_mat` aparece como `120.00000`, aunque SWAT+ 61.0.2.61 lo declara `INTEGER`; su lector no eleva un I/O status positivo de conversión. Se verificó sin tocar el proyecto fuente ni los artefactos originales: en 12 workspaces nuevos, solo se cambió la representación textual integral de `days_mat` a entero de forma idéntica; el forcing, las fechas, el manejo, HRU, outlet y controles se mantuvieron invariantes. Se habilitaron `hru_pw_day.txt` y `mgt_out.txt` en esas copias. Los eventos internos de maíz fueron 26 plantaciones el 2019-05-15, seis el 2019-05-16 y cosechas/kill del 2019-08-27 al 2019-09-03. Son fechas de la ejecución de diagnóstico, no observaciones históricas.

La comparación baseline vs FSPM en esas copias mostró cambios en LAI, biomasa, ET/percolación y otras salidas vegetales/hidrológicas. Ocho probes OAT detectaron sensibilidad; `ext_co` no produjo una diferencia impresa y no hay altura directa en las salidas. Toda esa corrida está marcada `SENSITIVITY_DIAGNOSTIC_ONLY`, no es resultado científico final ni calibración. El informe completo, valores/rangos, hashes y diferencias está en [docs/PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md](PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md) y en la salida local ignorada `backend/data/phase35-sensitivity-verification-v3/`.

El resultado de fase 3.5 no cambia los datos fechados de playback. Para crecimiento, Gemini debe consumir solo `PlaybackRecord` de la fecha solicitada a través de `adaptPlaybackVisual()` → `TwinVisualState`. No uses `field_aggregates` para reconstruir una fecha: el resumen de fase 3.4 conserva la etiqueta `SEASONAL_MAXIMA_FOR_COUPLING_NOT_A_DATED_FSPM_STATE`, porque máximos de LAI, altura y raíz pueden venir de fechas distintas. El mapper ahora usa `CouplingPlantParameterSummary` dedicado y un snapshot diario legible conserva una fecha coherente; la distribución diaria de playback permanece como estaba.

Se añadió un importador explícito y transaccional `backend/scripts/register_verified_experiment.py`. Su `--check-only` verificó el manifest y los artefactos reales. No se hizo `--apply`: no había PostgreSQL de desarrollo disponible, así que no existen aún IDs accesibles para la UI. La SQLite desechable de fase 3.4 registra respuestas de FastAPI 200 para availability y playback del 2019-04-16 (`SCIENTIFIC_ACTIVE`), 2019-07-24 (`SCIENTIFIC_ACTIVE`) y 2019-01-01 (`SCIENTIFIC_FALLOW`), y 404 para una corrida fuera del propietario; esa prueba previa no representa una comprobación contra PostgreSQL actual.

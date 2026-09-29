# Fases 2, 3 y 4 — estado diario South Fork 2019

## Resultado operativo

La ejecución corregida `phase234-sf-2019-v2` usa el proyecto experimental South Fork 2019 de la Fase 1. Su manifiesto está en `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/manifest.json`. Conserva 365 fechas, 36 HRU y 37 canales por fecha. El maíz FSPM representa siete calendarios de manejo de 32 HRU y publica hasta 70 slots de plantas por día. Los slots son plantas simuladas representativas, no observaciones. `phase234-sf-2019-v1` permanece identificado como ejecución anterior a la corrección.

El endpoint existente es `GET /api/v1/simulations/phase234-sf-2019-v2/playback?date=2019-07-15&resolution=DAILY`. Exige la autenticación y el alcance de propietario habituales. La respuesta usa `PlaybackPage` v1 y contiene un `PlaybackRecord` con `field`, `plant_samples`, `hru_results`, `channel_results`, `hydrology` y `weather`. Un ejemplo completo capturado desde FastAPI está en `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/playback_api_example_2019-07-15.json`.

## Acoplamiento hídrico

En cada iteración, el runner lee `sw_ave` diario de `hru_wb_day` para cada HRU de maíz. `hru-data.hru` enlaza la HRU con su perfil `soils.sol`. En [SWAT+ 61.0.2.61 `soil_phys_init.f90`](https://github.com/swat-model/swatplus/blob/61.0.2.61/src/soil_phys_init.f90), `sol_st` y `sol_fc` excluyen el agua al punto de marchitez (`wp`). Por tanto, `sw_ave` no es humedad volumétrica total. El adaptador calcula `f = sw_ave / Σ(AWC_capa × espesor_capa)`; estima el agua radicular por capa como `WP_capa + f × AWC_capa` y pondera por el espesor dentro de la profundidad radicular FSPM. A `sw_ave = 0`, la estimación coincide con WP; a `sw_ave = Σ(AWC × espesor)`, coincide con capacidad de campo. También reproduce los límites de densidad, AWC y porosidad de esa inicialización. Los grupos de calendario usan la media ponderada por área HRU y fracción CDL de maíz. El FSPM recibe esa humedad y esos umbrales al calcular estrés, transpiración, absorción, LAI y biomasa.

Los umbrales proceden del código de inicialización de la misma versión del ejecutable. La salida diaria no proporciona el agua de cada capa.

La proyección a la zona radicular supone una fracción de agua disponible uniforme en el perfil; por eso `estimated_soil_moisture_vol_percent`, `estimated_root_zone_water_mm` y `estimated_plant_available_fraction` llevan evidencia `DERIVED` y una limitación explícita. Son estimaciones operativas, no medidas ni estados SWAT+ por capa. Cada HRU conserva su almacenamiento y estimación individual; las plantas de un grupo usan condiciones hídricas ponderadas del grupo. Las HRU con el mismo calendario pueden tener suelos distintos y la población FSPM no resuelve esas diferencias dentro del grupo.

El flujo ejecuta SWAT+ para obtener el calendario inicial, calcula FSPM con el agua de esa salida, mapea el contrato estacional a `plants.plt` en una copia aislada y repite SWAT+. Acepta la corrida cuando coinciden los eventos de manejo por HRU y el máximo cambio del almacenamiento promedio diario de todas las HRU entre iteraciones es de 0,1 mm o menor. La corrida v2 convergió en dos iteraciones acopladas; el último máximo fue 0,001 mm. SWAT+ conserva sus propias ecuaciones de transpiración e hidrología. No se escriben los valores diarios FSPM de ET o estrés directamente en SWAT+.

## Contrato para Gemini

Cada `VariableState` entrega `value`, `unit`, `availability`, `evidence`, `source` y, cuando procede, `limitation`. `MODELLED_SWAT_PLUS` identifica resultados de SWAT+, `SIMPLIFIED_FSPM` estados de la población vegetal, `DERIVED` conversiones y agregados, y `ASSUMED` entradas supuestas. Un valor ausente queda en `null` con `NOT_AVAILABLE`.

`plant_samples[*].calendar_id` y `hru_ids` enlazan cada slot representativo con su calendario y HRU. `hru_results[*].hru_id`, `gis_id` y `calendar_id` preservan identificadores del proyecto; `crop.active` cambia con las fechas ejecutadas de siembra y cosecha. `channel_results[*].channel_id` y `gis_id` preservan las claves de `channel_sd_day`. `polygon_id` y `geometry_id` quedan nulos porque no hay una vinculación verificada de los resultados con polígonos o geometrías de canal. El caudal está en m3/s y el almacenamiento de canal en m3; no se publica nivel ni profundidad de río. El adaptador visual existente expone directamente `hruStates` y `channelStates` sin calcular procesos científicos.

El `watershed_id` del artefacto publicado usa el identificador externo estable `05451210`; el registro de `simulation_runs` conserva por separado el UUID de la cuenca local. `watershed_code` mantiene el mismo identificador externo para que un despliegue con otros UUID pueda recuperar el mismo artefacto.

FastAPI lee `playback_frames` en PostgreSQL: clave `(simulation_id, resolution, date)`, `payload` JSONB completo y SHA-256 por frame. La migración `009_playback_frames.sql` crea esa tabla y el índice temporal. `SimulationRun.provenance.playback` conserva catálogo, periodo y procedencia, pero no duplica frames. `backend/scripts/register_phase234_south_fork_2019.py` importa v1 y v2 de forma idempotente tras verificar los IDs existentes y los checksums. Los archivos `playback.sqlite.gz`, CSV, logs y manifiestos siguen versionados como respaldo; FastAPI no los lee durante consultas normales.

## Comprobaciones

- El manifiesto v2 marca `COMPLETED`, 365 frames, 36 HRU y 37 canales por fecha, siete calendarios y 32 HRU de maíz. La convergencia SWAT+/FSPM está declarada; no hay advertencias graves de integridad.
- FastAPI sobre PostgreSQL devolvió HTTP 200 para 15 de enero, 15 de mayo, 15 de julio, 30 de agosto, 15 de septiembre y 15 de diciembre. La siembra activa muestras el 15 de mayo; septiembre y diciembre no presentan plantas FSPM. Disponibilidad y paginación funcionaron con las lecturas SQLite bloqueadas. Una consulta HTTP a Uvicorn del endpoint del 15 de julio respondió 200; después de detener e iniciar de nuevo el proceso, playback y disponibilidad volvieron a responder 200.
- El 15 de julio v2 tiene 70 muestras, 36 HRU y 37 canales. La humedad FSPM derivada es 29,2263 vol%, el estrés FSPM 0,0442, la biomasa 167,6516 g/planta, la transpiración 2,3156 mm/día y el caudal de salida 0,3202 m3/s. v1 conserva sus resultados previos (16,5867 vol%, estrés 0,5877 y caudal 0,3172 m3/s).
- La migración JSONB, las inserciones idempotentes, el conflicto de checksum, la paginación y la reconexión se comprobaron en `digitaltwin_test_playback`, una base aislada dentro de la instancia local. Los frames v1 y v2 se registraron en `digitaltwin` sin cambiar los datos previos de v1.
- La suite completa del backend terminó con 183 pruebas aprobadas y cuatro omitidas; las 20 pruebas del adaptador frontend y `tsc --noEmit` aprobaron. Las comprobaciones PostgreSQL se ejecutaron con los scripts `verify_playback_store_isolated_pg.py` y `verify_phase234_postgres.py`.

## Límites para la representación

La meteorología fuente no tiene origen documentado en el proyecto. El escenario de manejo proviene de CDL 2019 y no reconstruye operaciones observadas. La aproximación hídrica depende de la hipótesis de perfil uniforme; la lectura diaria no permite gradientes de humedad por capa ni una profundidad hidráulica de canal. Las fechas de manejo son eventos simulados con resolución diaria. La vegetación FSPM se emite solo dentro del intervalo siembra a cosecha; los resultados hidrológicos continúan todo el año.

# Fases 2, 3 y 4 — estado diario South Fork 2019

## Resultado operativo

La corrida `phase234-sf-2019-v1` usa el proyecto experimental South Fork 2019 de la Fase 1. Su manifiesto está en `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v1/manifest.json`. Conserva 365 fechas, 36 HRU y 37 canales por fecha. El maíz FSPM está activo 112 días entre el 15 de mayo y el 3 de septiembre; representa siete calendarios de manejo de 32 HRU y publica hasta 70 slots de plantas por día. Los slots son plantas simuladas representativas, no observaciones.

El endpoint existente es `GET /api/v1/simulations/phase234-sf-2019-v1/playback?date=2019-07-15&resolution=DAILY`. Exige la autenticación y el alcance de propietario habituales. La respuesta usa `PlaybackPage` v1 y contiene un `PlaybackRecord` con `field`, `plant_samples`, `hru_results`, `channel_results`, `hydrology` y `weather`. Un ejemplo completo generado desde el sidecar indexado está en `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v1/playback_example_2019-07-15.json`.

## Acoplamiento hídrico

En cada iteración, el runner lee `sw_ave` diario de `hru_wb_day` para cada HRU de maíz. `hru-data.hru` enlaza la HRU con su perfil `soils.sol`. El espesor del perfil convierte almacenamiento en mm a una media volumétrica: `theta [%] = sw_ave [mm] / dp_tot [mm] × 100`. Cada capa aporta punto de marchitez estimado por la convención SWAT+ `0.40 × clay[%] × bd / 100`, capacidad de campo `WP + AWC` y porosidad `1 − bd / 2.65`. La profundidad radicular FSPM delimita el volumen accesible y pondera los umbrales por espesor de capa. Los grupos de calendario usan la media ponderada por área HRU y fracción CDL de maíz. El FSPM recibe esa humedad y esos umbrales al calcular estrés, transpiración, absorción, LAI y biomasa.

Las definiciones de `sw_ave`, `dp_tot`, `awc` y los umbrales se contrastaron con la [referencia oficial de balance hídrico](https://docs.swat.tamu.edu/output-reference/water-balance/), la [estructura de `soils.sol`](https://swatplus.gitbook.io/io-docs/introduction-1/soils/soils.sol) y la [teoría de agua del suelo SWAT+](https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-2-hydrology/chapter-2-3-soil-water/2-3.1-soil-structure).

La salida diaria SWAT+ no contiene agua por capa. La proyección de la humedad media del perfil a la zona radicular supone distribución uniforme con la profundidad; por eso `estimated_soil_moisture_vol_percent`, `estimated_root_zone_water_mm` y `estimated_plant_available_fraction` llevan evidencia `DERIVED` y una limitación explícita. Son estimaciones operativas, no medidas ni estados SWAT+ por capa. Cada HRU conserva su almacenamiento y estimación individual; las plantas de un grupo usan condiciones hídricas ponderadas del grupo. Las HRU con el mismo calendario pueden tener suelos distintos y la población FSPM no resuelve esas diferencias dentro del grupo.

El flujo ejecuta SWAT+ para obtener el calendario inicial, calcula FSPM con el agua de esa salida, mapea el contrato estacional a `plants.plt` en una copia aislada y repite SWAT+. Acepta la corrida cuando coinciden los eventos de manejo por HRU y el máximo cambio del almacenamiento promedio diario de todas las HRU entre iteraciones es de 0,1 mm o menor. La corrida aceptada necesitó cuatro iteraciones; el último máximo fue 0,003 mm. SWAT+ conserva sus propias ecuaciones de transpiración e hidrología. No se escriben los valores diarios FSPM de ET o estrés directamente en SWAT+.

## Contrato para Gemini

Cada `VariableState` entrega `value`, `unit`, `availability`, `evidence`, `source` y, cuando procede, `limitation`. `MODELLED_SWAT_PLUS` identifica resultados de SWAT+, `SIMPLIFIED_FSPM` estados de la población vegetal, `DERIVED` conversiones y agregados, y `ASSUMED` entradas supuestas. Un valor ausente queda en `null` con `NOT_AVAILABLE`.

`plant_samples[*].calendar_id` y `hru_ids` enlazan cada slot representativo con su calendario y HRU. `hru_results[*].hru_id`, `gis_id` y `calendar_id` preservan identificadores del proyecto; `crop.active` cambia con las fechas ejecutadas de siembra y cosecha. `channel_results[*].channel_id` y `gis_id` preservan las claves de `channel_sd_day`. `polygon_id` y `geometry_id` quedan nulos porque no hay una vinculación verificada de los resultados con polígonos o geometrías de canal. El caudal está en m3/s y el almacenamiento de canal en m3; no se publica nivel ni profundidad de río. El adaptador visual existente expone directamente `hruStates` y `channelStates` sin calcular procesos científicos.

El `watershed_id` del artefacto publicado usa el identificador externo estable `05451210`; el registro de `simulation_runs` conserva por separado el UUID de la cuenca local. `watershed_code` mantiene el mismo identificador externo para que un despliegue con otros UUID pueda recuperar el mismo artefacto.

El archivo `playback.sqlite.gz` queda versionado junto con las tablas y el manifiesto. `PlaybackArtifactStore` verifica SHA-256 del comprimido y del SQLite restaurado y reconstruye el sidecar local si falta. El registro en la tabla existente `simulation_runs` se hace con `backend/scripts/register_phase234_south_fork_2019.py`, proporcionando IDs existentes de propietario, cuenca South Fork y escenario neutral. No crea tablas ni endpoints nuevos.

## Comprobaciones

- El manifiesto marca `COMPLETED`, 365 días de cuenca, 13.140 filas HRU de agua, 13.140 filas HRU de planta y 13.505 filas de canal. No declara advertencias graves de integridad.
- Se recorrieron los 365 frames: fechas únicas, 36 HRU y 37 canales por día, plantas ausentes fuera del cultivo, y relación `calendar_id`/`hru_ids` en todas las muestras activas.
- FastAPI devolvió HTTP 200 y un frame para 1 de enero, 14, 15 y 16 de mayo, 15 de julio, 27 de agosto, 4 de septiembre y 31 de diciembre. El 14 de mayo y el 4 de septiembre no tienen plantas FSPM; el 15 y 16 de mayo activan cuatro y siete grupos respectivamente.
- El 15 de julio la respuesta tiene 70 muestras, 36 HRU y 37 canales. La humedad FSPM derivada es 16,5867 vol%, el estrés FSPM 0,5877 y el caudal de salida 0,3172 m3/s. Son resultados simulados del escenario experimental.
- `pytest` en los componentes de suelo, FSPM, playback y acoplamiento: 50 aprobadas. `tsc --noEmit`: correcto. Pruebas del adaptador frontend: 20 aprobadas, incluida la carga del JSON real. Se restauró también el sidecar completo a partir del comprimido versionado y se consultó el 15 de julio.

## Límites para la representación

La meteorología fuente no tiene origen documentado en el proyecto. El escenario de manejo proviene de CDL 2019 y no reconstruye operaciones observadas. La aproximación hídrica depende de la hipótesis de perfil uniforme; la lectura diaria no permite gradientes de humedad por capa ni una profundidad hidráulica de canal. Las fechas de manejo son eventos simulados con resolución diaria. La vegetación FSPM se emite solo dentro del intervalo siembra a cosecha; los resultados hidrológicos continúan todo el año.

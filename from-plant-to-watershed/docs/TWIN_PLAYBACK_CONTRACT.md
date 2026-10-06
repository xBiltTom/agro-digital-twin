# Contrato temporal y representación — `twin-playback-v1`

Contrato vigente de FastAPI, PostgreSQL y visor 3D. La versión del esquema no
es la versión del experimento científico; véase [estado actual](CURRENT_STATE.md).

## 1. API y acceso

Todos los endpoints requieren autenticación. Las corridas se filtran por dueño,
salvo `SUPERADMIN`; una corrida fuera del alcance responde 404.

| Endpoint | Uso |
| --- | --- |
| `GET /api/v1/simulations?skip=0&limit=100` | Catálogo paginado de corridas accesibles. |
| `GET /api/v1/simulations/{id}/availability` | Origen, resoluciones, disponibilidad FSPM y primeras fechas representables; acepta `?date=YYYY-MM-DD`. |
| `GET /api/v1/simulations/{id}/playback` | Estados fechados, catálogo de variables, procedencia y limitaciones. |
| `GET /api/v1/simulations/{id}/swat-results` | Resultados SWAT+ persistidos y origen ejecutado/importado. |

Parámetros de playback:

- `date=YYYY-MM-DD` **o** intervalo inclusivo `start=...&end=...`.
- `resolution=DAILY|MONTHLY|ANNUAL`; sin selección usa la frecuencia principal.
- `offset` desde 0 y `limit` entre 1 y 500, por defecto 100.

La respuesta `PlaybackPage` incluye `artifact_status`, `simulation_status`,
`available_resolutions`, `total`, `records`, `variables`, `provenance` y
`limitations`. Una corrida sin artefacto entrega cero registros y
`NOT_AVAILABLE`; un artefacto inválido o un fallo de integridad produce 503.
Ausencia de datos e integridad fallida son estados distintos.

## 2. Persistencia

`playback_frames` almacena el payload JSONB completo y SHA-256 por
`(simulation_id, resolution, date)`. La migración
`backend/migrations/009_playback_frames.sql` crea la tabla y el índice temporal.
`SimulationRun.provenance.playback` contiene periodo, catálogo y linaje, sin
duplicar los frames; puede existir `playback_daily_fspm` para otra resolución.

FastAPI consulta PostgreSQL y verifica el checksum de los frames leídos.
La clave única evita duplicados y una importación idempotente comprueba que el
contenido existente coincida. `PlaybackArtifactStore` se conserva como lector
de archivos SQLite comprimidos para importación/recuperación, no para consultas
normales de la API.

Herramientas de recuperación, desde `backend/`:

- `scripts/register_phase234_south_fork_2019.py`: verifica e importa un bundle
  South Fork 2019 completado. Argumentos en [estado actual](CURRENT_STATE.md).
- `scripts/backfill_playback.py RUN_ID`: publica playback de una línea base
  SWAT+ ya persistida a partir de datos recuperables. No ejecuta SWAT+ ni crea
  trayectoria FSPM para un acoplado histórico.
- `scripts/backfill_playback.py RUN_ID --repair-legacy-sidecar`: migra un sidecar
  baseline verificado si todavía no hay frames PostgreSQL. Rechaza una serie
  parcial existente; conserva el manifiesto anterior.

Las importaciones no corrigen retrospectivamente cálculos o etiquetas
científicas de filas antiguas. Una reparación requiere conservar el contenido
previo y documentar exactamente qué cambió.

## 3. Estructura y evidencia

`PlaybackRecord` conserva simulación, fecha, resolución, tipo de corrida,
cuenca, código externo, outlet, soporte espacial y estos grupos:

| Grupo | Contenido |
| --- | --- |
| `weather` | Forcing disponible con unidad y procedencia. |
| `crop` | Actividad, cultivo, etapa y fuente del calendario. |
| `field` | Agregados FSPM de la fecha, incluida fracción de área activa cuando existe. |
| `plant_samples` | Slots representativos persistidos, IDs y variables individuales. |
| `plant_sample_context` | Población, conteo capturado, método e identidad `SIMULATION_SLOT`. |
| `hydrology` | Resultados de cuenca y caudal outlet; observación solo si se enlaza explícitamente. |
| `hru_results` | IDs HRU, GIS, calendario y variables de salida/estimadas. |
| `channel_results` | IDs canal/GIS y variables impresas de caudal, volumen y temperatura. |

Cada `VariableState` lleva `value`, `unit`, `availability`, `evidence`, `source`
y `limitation` opcional. **`null` significa desconocido; `0` es un cero registrado.**
Una variable ausente lleva `NOT_AVAILABLE` en disponibilidad y evidencia.

Evidencias permitidas: `OBSERVED`, `MODELLED_SWAT_PLUS`, `SIMPLIFIED_FSPM`,
`SIMPLIFIED_HYDROLOGY`, `DERIVED`, `ASSUMED`, `SYNTHETIC`, `NOT_AVAILABLE`.
Se clasifican por variable: un mismo frame puede mezclar estados modelados,
estimaciones, observaciones y entradas supuestas.

- `soil_water_mm`: almacenamiento SWAT+ por encima de WP, en mm, para el
  perfil/soporte declarado.
- `field.soil_moisture_vol_percent`: humedad FSPM en porcentaje volumétrico.
  En South Fork corregido es `DERIVED`; sin agua HRU diaria puede ser `ASSUMED`.
  No es `soil_water_mm / 10` ni se multiplica de nuevo por 100.
- `hydrology.evapotranspiration_mm`: ET hidrológica de SWAT+ o motor simplificado.
  `field.actual_transpiration_mm_day` es transpiración FSPM, otra variable.
- Biomasa FSPM: g/planta; biomasa HRU SWAT+: kg/ha cuando se imprime.
- Caudal: m³/s. Almacenamiento de canal: m³. No hay nivel/profundidad inferidos.

`plant_samples[*].calendar_id` y `hru_ids` enlazan muestras con sus grupos.
`x_m/y_m` son coordenadas locales de población, no geográficas.
`polygon_id` y `geometry_id` siguen nulos hasta verificar la unión espacial.
Un GIS ID conservado no equivale a tener esa unión.

## 4. Tiempo, cobertura y temporadas

Los registros se alinean por fecha/periodo y clave espacial, no por posición
en una lista. Se rechazan duplicados y fechas inválidas; los faltantes
permanecen ausentes, sin interpolación ni reconstrucción de días históricos.

En mensual/anual, el primer día identifica el periodo. `date` devuelve el
periodo que contiene esa fecha; un intervalo incluye periodos solapados.
Forcing acumulado en un fragmento solicitado no se presenta como mes completo.
Los flujos mm se agregan según periodo; temperatura y caudal medio conservan
su semántica de promedio y las observaciones declaran cobertura.

Una corrida acoplada de frecuencia mensual/anual puede ofrecer además `DAILY`
con FSPM/forcing y **sin hidrología diaria**. Son series independientes:
no se duplican ni interpolan resultados mensuales para animar días.

La ruta vigente usa eventos ejecutados de siembra/cosecha; las corridas
anteriores con `APPROXIMATE_PLANTING_WINDOW` conservan esa limitación. Fuera de
temporada no se arrastra el último estado vegetal: `crop.active=false`, campo
sin cultivo y muestras vacías. Durante cosecha escalonada se conservan solo
grupos/muestras activos y la fracción de área activa.

`total_discharge_hm3` solo se integra desde caudales diarios completos.
Con frecuencia gruesa o cobertura insuficiente queda nulo con estado/razón.
`water_balance.status=TERMS_COMPLETE` expresa cobertura de términos, no cierre
físico del balance. `code_version` añade `+dirty` para cambios locales no
confirmados; los manifiestos y hashes mantienen el linaje de cada corrida.

## 5. Entrada oficial del frontend

| Archivo en `frontend/src/` | Responsabilidad |
| --- | --- |
| `hooks/useTwinPlayback.ts` | Disponibilidad, paginación/caché, reproducción, selección de resolución y navegación por fecha. |
| `lib/playback-visual-adapter.ts` | `adaptPlaybackVisual()` puro; devuelve `TwinVisualState` con unidades, evidencia y límites. |
| `lib/playback-scene.ts` | `sceneFromRecord()` y puntos de gráfica desde el mismo registro. |
| `lib/playback-navigation.ts` | Primera fecha representable y resolución preferida según disponibilidad guardada. |
| `types/playback.ts` | Contrato `PlaybackPage`/`PlaybackRecord`. |
| `types/playback-availability.ts` | Modos y códigos del diagnóstico. |
| `lib/visual-state.ts` | Dimensiones ilustrativas `REFERENCE_MAIZE`, separadas de datos científicos. |

La URL `/twin-3d?simId=...` respeta la corrida solicitada si es accesible.
Sin ID, el visor prioriza `phase234-sf-2019-v2` cuando está en el catálogo.
Inicialmente prefiere la resolución con trayectoria FSPM; no inventa una fecha
de cultivo. **Ir al primer cultivo** es una acción explícita basada en el
manifiesto. Las peticiones de una selección anterior se invalidan/cancelan.
El timeline avanza por índice de registro real; las gráficas usan la página
cargada y conservan brechas nulas.

| Modo visual | Significado |
| --- | --- |
| `SCIENTIFIC_ACTIVE` | Cultivo fechado activo con campo o muestra representable; puede ser incompleto. |
| `SCIENTIFIC_FALLOW` | El registro declara cultivo inactivo. No significa datos desconocidos. |
| `HYDROLOGY_ONLY` | Hidrología fechada sin FSPM representable. |
| `HISTORICAL_REFERENCE` | Importación histórica sin trayectoria playback; gráficos persistidos y contexto estático. |
| `DATA_UNAVAILABLE` | Falta estado utilizable o hay un problema de disponibilidad/integridad. |

`fieldRepresentable` y `sampleRepresentable` se evalúan por separado. Los
códigos distinguen falta de artefacto, artefacto inválido, ausencia de muestras,
altura/LAI faltantes, cultivo incompatible y fecha fuera de temporada.

## 6. Reglas de representación 3D

- Usar únicamente el `PlaybackRecord` seleccionado, no `field_aggregates`
  estacionales ni fórmulas científicas dentro de Three.js.
- Lluvia animada solo con precipitación **DAILY**, disponible y positiva.
  Cero apaga partículas; mensual/anual muestra acumulados sin tormentas diarias.
- Planta individual solo con muestra persistida compatible. Su altura, raíces
  y etapa provienen de esa muestra; si desaparece tras cosecha no se sustituye
  silenciosamente por el promedio del campo.
- Las 1.014 instancias del campo son decorativas, gobernadas por agregados y
  fracción de área activa; los marcadores con ID son muestras persistidas.
- LAI/estrés modulan geometría/color como transformaciones gráficas. Hojas,
  nervaduras, mazorca y raíces laterales no son mallas botánicas validadas.
- El terreno y la red de South Fork son contexto espacial con relieve
  ilustrativo. Un clic en sector no identifica una HRU; no asociar por índice.
- El outlet no se replica como caudal de cada canal. Los valores por canal
  proceden de `channel_results`; sin sección hidráulica no se calcula nivel.
- Viento, materiales y movimiento ambiental deben distinguirse de efectos
  impulsados por variables persistidas. Sin variable no se fabrica un sensor.
- Para otras cuencas no atribuir geometría South Fork. En modo histórico,
  la referencia planta/parcela es estática y explícitamente ilustrativa.

## 7. Verificación

Desde `frontend/`, `pnpm test` verifica el adaptador, navegación, frecuencias,
integridad de identidades y casos South Fork/fixtures. `tests/visual-playback.mjs`
usa Playwright para interceptar la API con fixtures y capturar las tres escalas;
requiere Next.js iniciado y Chromium disponible. Puede configurarse con
`PLAYWRIGHT_MODULE`, `CHROMIUM_PATH` y `VISUAL_OUTPUT_DIR`.

`backend/scripts/generate_visual_fixtures.py` genera fixtures con los esquemas
Pydantic reales. Llevan `test_only` y no son resultados científicos.
Una prueba visual o de contrato no valida la fisiología ni el caudal frente a
observaciones.

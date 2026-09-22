# Contrato temporal del gemelo — `twin-playback-v1`

## Inventario y alcance

| Fuente | Disponibilidad anterior | Estado de reproducción |
|---|---|---|
| SWAT+ `records` normalizados | Fechados en `monthly_outputs` incluso cuando la frecuencia era diaria; el nombre histórico se conserva | Caudal, escorrentía, ET, percolación y almacenamiento de suelo por periodo real `DAILY`, `MONTHLY` o `ANNUAL` |
| SWAT+ `hru_results` | Fechados en `hru_aggregates.results` | Por identificador `hru_unit` verificable en la salida; sin identidad de polígono asumida |
| SWAT+ estaciones de forcing directo | Archivos diarios `weather-sta.cli`/`*.pcp`/`*.tmp`; opcionalmente `*.slr`/`*.hmd` | Fechas explícitas, media aritmética entre estaciones como resumen de cuenca; no equivale a observación USGS ni a ponderación HRU |
| FSPM acoplado | Estados diarios calculados pero descartados salvo máximos y muestra final | Nuevas corridas capturan agregado diario y hasta 10 plantas reales con IDs estables; no reconstruible para corridas antiguas |
| Hidrología/FSPM simplificados | `SimulationResult` diario y agregados/muestra solo finales | Nuevas corridas capturan agregado y muestra diaria; forcing sintético clasificado `SYNTHETIC` |
| USGS | Observaciones por fecha en el registro de datos; validación mensual separada | Si se enlazan a una corrida, `observed_streamflow_m3s` conserva la fecha y evidencia `OBSERVED`; para SWAT+ mensual/anual se promedia solo los días observados disponibles, indicando su cobertura; nunca rellena fechas ausentes |
| South Fork v2 | Informe y datasets históricos | Intactos. Este contrato no los reetiqueta ni los promueve como playback completo |

El runner South Fork v3 conserva su exportación propia; no se ha ejecutado ni validado completamente. Este contrato no declara resultados v3 nuevos.

## API y almacenamiento

`GET /api/v1/simulations/{id}/playback` requiere autenticación y que el usuario sea dueño de la corrida o `SUPERADMIN`. Parámetros: `date=YYYY-MM-DD` **o** `start=YYYY-MM-DD&end=YYYY-MM-DD`, `offset` desde 0 y `limit` entre 1 y 500 (100 por defecto). `resolution=DAILY|MONTHLY|ANNUAL` permite elegir una frecuencia disponible; sin él se devuelve la frecuencia SWAT+ principal. Una corrida acoplada con salida SWAT+ mensual/anual ofrece además `DAILY` con FSPM y forcing, dejando la hidrología diaria en `null`. `available_resolutions` informa las opciones. Responde `simulation_status` (`PENDING`, `RUNNING`, `FAILED`, `COMPLETED`), `artifact_status`, frecuencia efectiva, total filtrado, registros, catálogo de variables, procedencia y limitaciones. Una corrida histórica sin artefacto responde `NOT_AVAILABLE` y cero registros, sin representar ceros científicos. Una falla de integridad/archivo responde 503.

Cada corrida nueva publica un sidecar SQLite inmutable por ID en `DATA_ARTIFACT_ROOT/playback/v1`, con índice de fecha y checksum SHA-256 por registro. Una corrida acoplada con SWAT+ mensual/anual añade el sidecar `playback/v1/fspm-daily`. En `SimulationRun.provenance.playback` y, cuando proceda, `playback_daily_fspm`, quedan los manifiestos con `schema_version`, nombre, checksum del archivo completo, intervalo, frecuencia, catálogo, configuración, semilla, versión del código y procedencia. PostgreSQL conserva los manifiestos, no otra copia de miles de estados de plantas. La consulta de un día usa el índice, no carga la serie completa. El directorio debe persistir y compartirse entre procesos FastAPI.

`code_version` añade `+dirty` si hay cambios locales sin confirmar; una ejecución científica publicable requiere conservar también el commit final y los insumos versionados.

`backend/scripts/backfill_playback.py RUN_ID`, ejecutado desde `backend`, publica un sidecar **solo** para una línea base SWAT+ terminada y ya persistida. No ejecuta SWAT+, no sintetiza FSPM, y deja el forcing en `null` si el workspace aislado original no existe. Rechaza corridas acopladas históricas porque su trayectoria diaria fue descartada. No modifica los informes o artefactos South Fork v2.

## Semántica de fechas, variables y evidencia

Cada registro lleva `simulation_id`, fecha ISO 8601, `resolution`, `run_type`, `watershed_id` (clave de la base de datos), `watershed_code`, `outlet_unit` cuando se configuró, soporte espacial, grupos `weather`, `crop`, `field`, `plant_samples`, `hydrology` y `hru_results`. Cada variable lleva `value`, `unit`, `evidence`, `source`, `availability` y, cuando corresponde, `limitation`. Valores ausentes son `null` con `NOT_AVAILABLE`; `0` solamente aparece cuando el modelo o forcing lo registra como cero. Evidencias: `OBSERVED`, `MODELLED_SWAT_PLUS`, `SIMPLIFIED_FSPM`, `SIMPLIFIED_HYDROLOGY`, `DERIVED`, `ASSUMED`, `SYNTHETIC`, `NOT_AVAILABLE`. La clasificación se hace por variable; una fecha puede mezclar forcing derivado de estaciones, hidrología SWAT+ y humedad FSPM asumida.

Los archivos meteorológicos conservan el día del año original, incluidos años bisiestos. Se rechazan fechas duplicadas, días inválidos y la falta de temperatura/precipitación en cualquier estación directa; el acoplado exige también solar y humedad relativa. Viento y PET directos se exponen si están completos; variables secundarias incompletas de una línea base permanecen `null`. Los registros SWAT+ se alinean por `period`, FSPM por fecha calculada y observaciones por fecha observada; nunca por longitud/posición. Si falta una salida SWAT+ para un periodo solicitado, se conserva el periodo con hidrología `null` y una limitación. Mensual/anual se etiqueta con su frecuencia efectiva; precipitación y radiación se suman en el periodo disponible y temperatura/humedad relativa se promedian. El primer día del mes/año identifica el periodo, incluso si la solicitud comienza a mitad del mismo. El total meteorológico puede abarcar solo el fragmento solicitado del periodo; no se presenta como mes/año completo.

El lector no reconstruye series generadas internamente por el generador climático de SWAT+ (`sim`/WGN). En una línea base, la meteorología no recuperable queda ausente; un acoplado requiere forcing directo completo para poder justificar su FSPM. Si el workspace SWAT+ efectivo cambia el forcing respecto del leído por el FSPM, la publicación acoplada se rechaza en vez de atribuir a ambos modelos entradas diferentes.

El proveedor normalizado externo anterior rellenaba solar, humedad relativa y CO₂ ausentes con valores de metadatos o valores por defecto del modelo. Ese comportamiento de entrada existente se conserva para no cambiar corridas simplificadas, pero ahora cada variable rellenada se marca `ASSUMED` en playback, con la limitación correspondiente. No se presenta como observación del archivo climático.

`soil_water_mm` significa almacenamiento de agua SWAT+ en milímetros. `field.soil_moisture_vol_percent` significa humedad volumétrica FSPM en porcentaje; en el acoplado South Fork sigue siendo la constante **asumida** del 24 %, no una observación ni una conversión de SWAT+. `hydrology.evapotranspiration_mm` proviene de SWAT+ o del modelo hidrológico simplificado; `field.actual_transpiration_mm_day` proviene del FSPM. Sin perfil, capas y correspondencia espacial/temporal validados, no se transforma `soil_water_mm` en humedad volumétrica.

El cultivo acoplado se marca activo únicamente dentro de las ventanas calculadas por PHU; fuera de ellas, `crop.active=false`, `field={}` y `plant_samples=[]`. `window_status=APPROXIMATE_PLANTING_WINDOW` declara que siembra/cosecha no son eventos SWAT+ observados. Una línea base SWAT+ deja `crop=null` y no contiene estados FSPM. La corrida simplificada no dispone todavía de un calendario explícito de siembra/cosecha y declara esa limitación.

Las coordenadas `x_m`/`y_m` de las muestras de plantas son relativas a la cuadrícula de población simulada; no son coordenadas geográficas. La identidad de polígono HRU sigue siendo `null` hasta documentar una correspondencia espacial comprobable.

Ejemplo abreviado de **fixture determinista**, no resultado South Fork:

```json
{
  "schema_version": "twin-playback-v1",
  "simulation_id": "run-1",
  "simulation_status": "COMPLETED",
  "artifact_status": "AVAILABLE",
  "resolution": "DAILY",
  "available_resolutions": ["DAILY"],
  "total": 1,
  "offset": 0,
  "limit": 1,
  "records": [{
    "schema_version": "twin-playback-v1",
    "simulation_id": "run-1",
    "date": "2020-02-29",
    "resolution": "DAILY",
    "run_type": "SWAT_STANDARD_BASELINE",
    "watershed_id": "basin",
    "watershed_code": null,
    "outlet_unit": null,
    "spatial_support": "WATERSHED_OUTLET_AND_BASIN",
    "weather": {"precipitation_mm": {"value": 2.0, "unit": "mm/day", "evidence": "DERIVED", "source": "SWAT station basin mean", "availability": "AVAILABLE", "limitation": null}},
    "crop": null,
    "field": {},
    "plant_samples": [],
    "hydrology": {"soil_water_mm": {"value": null, "unit": "mm", "evidence": "NOT_AVAILABLE", "source": "SWAT+ normalized output", "availability": "NOT_AVAILABLE", "limitation": "No recorded value"}},
    "hru_results": [],
    "availability": {"weather": "AVAILABLE", "field": "NOT_AVAILABLE", "plant_samples": "NOT_AVAILABLE", "hydrology": "NOT_AVAILABLE", "hru_results": "NOT_AVAILABLE"},
    "limitations": ["SWAT+ has no normalized output for this period; hydrological values are null"]
  }],
  "variables": {},
  "provenance": {"fixture": true},
  "limitations": []
}
```

La respuesta real incluye las demás variables meteorológicas e hidrológicas, con valores `null` cuando faltan, y el catálogo correspondiente. El ejemplo muestra un día bisiesto sin salida SWAT+, precisamente para ilustrar que una laguna no equivale a cero.

## Instrucciones para la fase 3

1. Consultar `/api/v1/simulations/{id}/playback` por fecha/intervalo y paginar. Usar `resolution` y `availability` antes de animar; una muestra de planta no equivale al promedio de campo.
2. Para lluvia usar `weather.precipitation_mm.value`, respetando su unidad y su evidencia. Eliminar la precipitación derivada de escorrentía/caudal.
3. Para crecimiento usar `field.lai`, `field.height_m`, `field.root_depth_m`, `field.biomass_g_plant` y `crop.active`; para plantas individuales usar solo `plant_samples` con sus IDs estables. Eliminar estados maduros persistentes fuera de temporada.
4. Para estrés y transpiración usar `field.water_stress` y `field.actual_transpiration_mm_day` cuando existan. Eliminar los proxies `1 - SWAT_ET/5.8` y `SWAT_ET * 0.78`.
5. Eliminar la multiplicación heredada `soil_moisture_vol * 100`. `field.soil_moisture_vol_percent.value` ya es porcentaje volumétrico. `hydrology.soil_water_mm` es almacenamiento en mm; no sustituye esa humedad.
6. Usar `hydrology.streamflow_m3s`, `runoff_mm`, `evapotranspiration_mm`, `percolation_mm` y `soil_water_mm` para el soporte de cuenca. Usar `hru_results` únicamente como HRU identificada por la salida SWAT+; falta un mapa verificado HRU→polígono.

Continúan pendientes la retroalimentación física SWAT+→FSPM, las fechas de manejo ejecutadas, la ponderación estación→HRU, la georreferenciación comprobada de HRUs y la validación observacional de los estados vegetales. Este contrato prepara los datos; no sincroniza todavía el visor 3D.

# Traspaso a Gemini: contrato científico para las tres escalas 3D

## Entrada pública

- `frontend/src/lib/playback-visual-adapter.ts`: `adaptPlaybackVisual(record, {simulationId, simulationName, availability, selectedPlantId})` devuelve `TwinVisualState`. Es puro y no depende de React ni de Three.js.
- `frontend/src/types/playback-availability.ts`: `VisualMode`, `AvailabilityCode`, `SimulationAvailability` y disponibilidad por fecha/resolución. Coincide con `backend/app/schemas/playback_diagnostic.py`.
- `frontend/src/lib/api.ts`: `api.getPlaybackAvailability(id, date?)` consulta `GET /api/v1/simulations/{id}/availability` con los permisos del endpoint playback. `api.getPlayback` obtiene el registro seleccionado.
- `frontend/src/hooks/useTwinPlayback.ts`: expone `availability`, `availabilityLoading`, `record`, `setResolution`, `jumpToDate` y `jumpToFirstCrop`. La página ofrece el botón **Ir al primer cultivo** cuando la resolución seleccionada tiene `first_representable_field`. La búsqueda navega solo a una fecha del manifiesto mediante el índice playback. Si la serie FSPM está en `DAILY` y se seleccionó `MONTHLY`, aparece una indicación para cambiar resolución; no cambia fecha ni resolución automáticamente.
- `frontend/src/lib/playback-navigation.ts`: `firstCropNavigation` decide entre fecha disponible, cambio a `DAILY` o ausencia de cultivo representable. Baselines sin FSPM no muestran la acción.
- `frontend/src/lib/playback-scene.ts`: `sceneFromRecord` conserva las entradas que reciben los componentes 3D actuales y adjunta `scene.visual` con el contrato oficial. `frontend/src/lib/visual-state.ts` mantiene `REFERENCE_MAIZE` exclusivamente como dimensiones ilustrativas; no forma parte de `TwinVisualState`.

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

## Fixtures y verificación

`frontend/tests/fixtures/twin-visual-fixtures.json` se genera con los **esquemas Pydantic reales** mediante:

```bash
cd backend
venv/bin/python scripts/generate_visual_fixtures.py
cd ../frontend
npm test
```

Todas las páginas declaran `test_only: true`, `scientific_result: false` y que no son resultados South Fork. `coupled_daily` tiene maíz joven, maíz reproductivo, día sin cultivo, precipitación cero y precipitación desconocida. `baseline` tiene solo hidrología. `historical` no tiene playback. `incomplete` conserva LAI pero deja altura nula. `coupled_monthly` presenta hidrología mensual separada de la trayectoria FSPM diaria de la misma corrida. Las pruebas usan exactamente `PlaybackPage` y `PlaybackRecord`; no insertan nada en PostgreSQL. Para inspección manual, interceptar `GET .../playback` con una página de la fixture en el entorno de pruebas del navegador, como hace `frontend/tests/visual-playback.mjs`. No activar estas páginas mediante el backend de producción.

## Hallazgos de la base configurada (auditoría solo lectura, 2026-09-24)

Se encontraron seis corridas de dos propietarios. Una línea base `SWAT_STANDARD_BASELINE` dispone de 365 registros diarios íntegros (2018), hidrología y 36 IDs HRU; no tiene cultivo/FSPM. Una importación South Fork v2 tiene resultados históricos agregados sin manifiesto v1. Otras cuatro corridas carecen de manifiesto v1. No hay trayectoria FSPM diaria accesible en esa base. La lista API antes paginaba 50 corridas globales y el cliente filtraba después; ahora el servidor filtra por propietario y el cliente consume todas las páginas de 100.

La importación histórica existente presenta indicadores de cinco defectos heredados: percolación fija 142.50, cierre cero no calculado, humedad derivada de `soil_water_mm/10`, biomasa etiquetada `kg/m²` pese al esquema `g/plant`, y etiqueta de calibración pese al informe v2 (`NOT_OPTIMIZED`, ningún parámetro ajustado). `backend/scripts/populate_swat_simulations.py` hace auditoría de solo lectura por defecto y ya no crea estos valores en futuras importaciones. La reparación de la fila existente **no se ejecuta automáticamente**. Procedimiento reversible: exportar JSON completo de la fila y hashes v2, identificar el ID en la auditoría, preparar un parche de campos JSON con valores `null` y claves de razón, revisar el diff, ejecutar una transacción explícita con copia de seguridad y verificar de nuevo; conservar rollback documentado. No editar los archivos v2.

## Alcance de Gemini

Trabajar solo en representación 3D: geometrías, mallas, animación, materiales, iluminación, cámara y calidad gráfica. Consumir `TwinVisualState` o `scene.visual` y sus códigos; no cambiar FastAPI, importadores, FSPM, SWAT+, contratos o datos históricos. No convertir `null` en cero; no inferir lluvia de escorrentía, estrés de ET, humedad porcentual de mm, ni polígonos a partir del índice HRU. Separar toda planta de referencia de los resultados científicos. Los componentes actuales muestran referencia cuando `scene === null`, incluso mientras se carga un registro; decidir visualmente cómo distinguir espera de `HISTORICAL_REFERENCE`/`DATA_UNAVAILABLE`. No interpretar las 1.014 instancias del campo como plantas individuales simuladas. La integración HRU→polígono y la ejecución v3 quedan para fases posteriores.

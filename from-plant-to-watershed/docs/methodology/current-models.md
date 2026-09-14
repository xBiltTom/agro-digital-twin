# Modelos actualmente implementados

## Estado científico

La aplicación ejecuta un pipeline **DEMO** reproducible. Sus componentes son
`SyntheticClimateProvider`, `SimplifiedPlantModel` y `SimplifiedHydrologyModel`.
No ejecuta SWAT+, no descarga NEX-GDDP-CMIP6, no contiene un FSPM completo y no
ha sido calibrada. Puede calcular métricas contra observaciones alineadas, pero
ello es `DEMONSTRATION_ONLY`, no una validación formal ni evidencia para H0/H1.

## Observaciones separadas del modelo

Fase C incorpora `UsgsStreamflowProvider` y un registry de datos para conservar
una serie USGS RAW, checksum SHA-256, normalización diaria en m³/s, QC y un
producto mensual derivado. Esta infraestructura no modifica parámetros, inputs
ni resultados de `SimplifiedHydrologyModel`; no constituye calibración ni
validación. La matriz de candidatas permanece preliminar: no hay todavía una
cuenca elegible congelada.

## SimplifiedPlantModel

Modelo algebraico diario de una planta representativa expresado como lámina de
agua equivalente sobre el campo. ET0 usa la aproximación de Turc ya presente en
el prototipo. La transpiración potencial es `ET0 × Kc × factor_CO2`; la
transpiración real añade una respuesta por humedad tipo Feddes y un factor de
acceso radicular `min(1, profundidad_raíz / 120 cm)`.

Entradas: temperatura (°C), radiación (MJ m⁻² día⁻¹), humedad relativa (%),
humedad volumétrica (%) y CO₂ (ppm). Flujos: mm día⁻¹. El dominio validado por
software exige umbrales de humedad ordenados, radiación no negativa y humedad
relativa entre 0 y 100%.

No modela órganos, arquitectura tridimensional, fenología, carbono ni raíces por
capa. `PlantPopulation` ejecuta una población determinista de hasta 10 000
instancias del modelo simplificado con variabilidad acotada en Kc, profundidad
radicular y humedad; no convierte el modelo en un FSPM. Los proxies de savia,
potencial foliar y conductancia son
salidas ilustrativas del modelo simplificado, no observaciones.

## SyntheticClimateProvider

Genera tiempo diario estacional pseudoaleatorio con `random.Random(seed)`. La
misma seed y controles producen la misma serie. `temp_anomaly_c` desplaza la
temperatura y `precip_factor` escala la intensidad; un factor cero produce
precipitación cero. Toda serie lleva `evidence_type=SYNTHETIC`.

No usa archivos, GCM, miembros, calendarios CMIP, bias correction, estaciones
ni observaciones. Los nombres SSP de catálogo sólo inspiran perturbaciones demo;
no convierten la serie en CMIP6.

## SimplifiedHydrologyModel

Modelo conceptual agregado con escorrentía SCS-CN, almacén de suelo y almacén
subterráneo. No ejecuta SWAT+. Para cada día:

```text
P + I = Qsuperficial + ETreal + Qbase + Δ(Ssuelo + Sgw) + residual
```

La percolación es una transferencia interna de suelo a groundwater y no se
cuenta como salida del sistema. Todos los términos del balance son mm/día salvo
los almacenamientos (mm); el caudal convierte `(Qsuperficial + Qbase)` a m³/s
mediante área de cuenca. No existen mínimos de groundwater ni de caudal. El
residual diario y acumulado se exponen y se prueba con tolerancia de `1e-9 mm`.

Supuestos principales: cuenca lumped, timestep diario, perfil de 1000 mm,
capacidad de campo 32%, saturación 44%, percolación lineal 0.45 y recesión de
baseflow 0.045. `FieldToHRUCoupler` produce tres `COARSE_HRU_PROXY` ponderados
por área y expone las entradas de campo; no representa HRUs, cauces, routing
físico, calibración ni SWAT+.

## Configuración, unidades y provenance

`RunConfig` es inmutable y distingue configuración solicitada de efectiva.
Rechaza claves desconocidas. Parámetros soportados: `base_kc`,
`max_root_depth_cm`, `curve_number`, `initial_soil_moisture_vol` e
`irrigation_mm_per_day`. La antigua `irrigation_efficiency` se rechaza porque no
existe un plan de manejo al cual aplicarla.

Cada corrida persiste seed, snapshots ligeros de cuenca/escenario,
implementaciones/versiones, clasificación, unidades, soporte espacial/temporal,
timestamps y error estructurado. `datasets=[]` significa que no se usó ningún
dataset, no que su provenance sea desconocida.

`PlantToFieldAggregator` conserva medias, desviaciones estándar y percentiles de
la población completa y sólo persiste una muestra representativa. La utilidad
`litres_per_plant_day_to_mm_day` establece explícitamente que 1 L m⁻² equivale a
1 mm y valida área/volumen.

## Cadena futura

```text
Plant population (SIMPLIFIED)
  ↓ PlantToField (DERIVED)
Field aggregate
  ↓ FieldToHRU (COARSE_HRU_PROXY)
HRU proxy
  ↓
SimplifiedHydrologyModel (SIMPLIFIED)
  ↓
ValidationEngine (DEMONSTRATION_ONLY when USGS aligns)

`SwatPlusAdapter` y `Cmip6FileProvider` existen como contratos de integración;
su capability es `NOT_AVAILABLE` o `READY_FOR_ARTIFACT` hasta recibir sus
artefactos/configuración reales.
```

La selección verificable completa de watershed/gauge, CMIP6, validación
estadística y evaluación de H0/H1 pertenecen a fases posteriores.

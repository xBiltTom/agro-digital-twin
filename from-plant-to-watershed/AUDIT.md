# Auditoria del estado actual

Fecha de auditoria: 2026-09-07. Alcance: inspeccion estatica de `/backend`, `/frontend` y el prototipo local bajo `/prototypes/from-plant-to-watershed_-multi-scale-digital-twin`. La ruta solicitada `/prototypes/ai-studio-mvp` no existe en este checkout. El prototipo esta sin versionar (`git status`: `?? prototypes/`); no debe confundirse con una implementacion incluida en `HEAD`.

## Dictamen

El repositorio contiene un backend FastAPI y frontend Next.js funcionales para una demostracion persistente, pero no una plataforma cientifica multiescala validada. El flujo actual calcula un modelo ecohidrologico conceptual con clima sintetico; no ejecuta SWAT+, no adquiere NEX-GDDP-CMIP6 y no implementa la cadena Planta -> Campo -> HRU -> SWAT+.

El prototipo AI Studio es una referencia visual y de interaccion. Sus datos, trabajos, conectores, WebSocket, Celery, Redis, resultados de validacion y arquitectura backend son simulados o literales de TypeScript. No se deben migrar como evidencia ni como implementacion de produccion.

## Respuestas a las verificaciones requeridas

| Verificacion | Hallazgo |
|---|---|
| Ejecuta SWAT+ | No. `backend/app/services/swat_hydrology.py` implementa `SWATHydrologyEngine`, un modelo propio agregado con SCS-CN, deposito de suelo, deposito subterraneo y conversion a caudal. No hay ejecutable, proyecto, archivos de entrada/salida ni adaptador SWAT+. |
| Accede a NASA NEX-GDDP-CMIP6 | No. `DownscaledClimateEngine` genera estacionalidad, ruido y lluvia aleatoria. No hay NetCDF, GCM, miembro, descarga, extraccion, calendario CMIP ni bias correction. |
| El modelo de planta es FSPM | No. `IndividualPlantPhysiologyModel` es un modelo algebraico simplificado de ET/transpiracion/estres. No representa arquitectura de organos, carbono, crecimiento, fenologia, extraccion por capas ni poblacion de plantas. |
| Existe escala de campo explicita | No. Hay ORM de HRU/subcuenca y una parcela 3D, pero no 1000 plantas, densidad, posiciones, agregacion espacial, ni resultados de campo. |
| Existe Field -> HRU | No. El orquestador usa el area total de cuenca y constantes; no itera HRUs, fracciones de area, especies, CN o subcuencas. |
| Metricas cientificas usan observaciones reales | No en backend. Son resumentes de la simulacion. En AI Studio, NSE/RMSE/PBIAS, caudales y rendimiento provienen de arrays hardcodeados sin provenance acreditada. |
| El frontend distingue DEMO vs REAL | No de forma suficiente. Presenta modelo simplificado, forcing sintetico, visores procedurales y perturbaciones locales con etiquetas que pueden sugerir SWAT, CMIP6, IoT o AI reales. |

## Estado de los componentes

### Backend y scientific core

| Componente | Archivo/modulo | Tipo real | Que afirma representar | Que representa realmente | Riesgo | Accion recomendada |
|---|---|---|---|---|---|---|
| Planta | `services/plant_model.py`, `IndividualPlantPhysiologyModel` | SIMPLIFIED_SCIENTIFIC_MODEL | Fisiologia individual/Feddes/FSPM | Demanda de ET, factor de estres y proxies de savia, potencial y conductancia sobre humedad media | Se presenta como planta individual sin arquitectura ni escalamiento; raiz maxima no influye | Conservar para CI/demo como `SimplifiedPlantModel`; documentar unidades y limites; reemplazar progresivamente por interfaz `PlantModel` |
| Hidrologia | `services/swat_hydrology.py`, `SWATHydrologyEngine` | SIMPLIFIED_SCIENTIFIC_MODEL | SWAT/balance hidrologico | SCS-CN y dos depositos propios | No es SWAT+; minimo de agua subterranea y caudal minimo crean agua; no hay cierre de masa | Renombrar a `SimplifiedHydrologyModel`; corregir balance antes de reutilizar; crear futuro `SwatPlusAdapter` separado |
| Clima | `services/climate_engine.py`, `DownscaledClimateEngine` | SYNTHETIC_DATA_PROVIDER | Downscaled/CMIP6 | Generador pseudoaleatorio estacional | Escenarios denominados CMIP6 sin datos CMIP6; precipitacion nominal no controla la serie | Conservar como `SyntheticClimateProvider`; crear futuro `NexGddpCmip6Provider` |
| Acoplamiento | `services/twin_coupling_engine.py`, `TwinCouplingEngine` | SIMPLIFIED_SCIENTIFIC_MODEL | Gemelo multiescala | Planta representativa y suelo agregado de cuenca, con persistencia ORM | Core depende de SQLAlchemy; no hay campo, HRU ni snapshots reproducibles | Separar ejecucion pura de persistencia; sustituir por orquestador que llame transformaciones explicitas |
| Entidades espaciales | `models/watershed.py` | INFRASTRUCTURE | Cuenca, subcuenca, HRU, especie | Catalogo ORM con relaciones | Los atributos no participan en la simulacion; sin geometria PostGIS/CRS | Conservar modelo catalogo; versionar/snapshot y activar solo cuando el modelo los consuma |
| Corridas/resultados | `models/simulation.py` | INFRASTRUCTURE | Escenarios y resultados | Persistencia SQL de corrida y dias | Sin semilla, snapshots, commit, datos, log, error, estados completos ni unicidad por dia | Evolucionar a manifiesto inmutable de corrida |
| Seeder | `services/seed_service.py` | DEMO | Datos iniciales/observado/SSP | Parametros y metadatos definidos en codigo | Etiqueta "Observado 1985-2014" alimenta clima sintetico y calendario 2026 | Aislar como fixtures demo; no tratar como catalogo cientifico |
| Reportes | `services/report_service.py` | INFRASTRUCTURE | Informe cientifico | PDF/DOCX/XLSX reales sobre resultados ORM | Conclusiones de riego, resiliencia y conservacion no estan respaldadas | Mantener exportacion; bloquear narrativa cientifica hasta provenance y validacion |
| WebSocket | `api/v1/twin_ws.py` | INFRASTRUCTURE | Estado de gemelo en tiempo real | Reproduce resultados ya guardados | No es telemetria ni progreso; no autentica | Etiquetar como playback o reemplazar por eventos de job autenticados |
| Validacion/ML | backend completo | UNKNOWN | Integracion ML/validacion | No se localizo pipeline ejecutable | No afirmar ML ni validacion | Implementar despues de observaciones y protocolo independiente |

No se identifico un componente cientifico `REAL_INTEGRATION` para SWAT+, NEX-GDDP-CMIP6, USGS, USDA NASS, CHIRPS, SoilGrids o Landsat.

### Riesgos tecnicos y cientificos observados

1. **P0: resultados no validos por no conservacion de masa.** El minimo de almacenamiento subterraneo y el caudal minimo en `swat_hydrology.py` introducen agua sin fuente. No publicar ni comparar caudales hasta cerrar balances diarios y acumulados.
2. **P0: atribucion falsa de SWAT+, CMIP6, FSPM y observaciones.** Nombres y textos exceden la implementacion. Separar etiquetas `synthetic`, `simplified`, `illustrative`, `observed` y `derived` en API, UI y reportes.
3. **P0: reproducibilidad no garantizada.** La semilla se deriva de `hash(sim_run.id)`, depende del proceso y no se persiste. No hay snapshots de configuracion, cuenca, HRU, escenario ni version del codigo.
4. **P0: riego y parametros expuestos no afectan al modelo.** `irrigation_efficiency` y `parameters` se almacenan pero el orquestador no los consume. Diferencias entre corridas pueden atribuirse falsamente al manejo cuando provienen de distinta semilla.
5. **P0: ET0 y estres sin trazabilidad metodologica.** La formula difiere de la documentacion y contiene conversiones no justificadas; la respuesta tipo Feddes es discontinua y no usa potencial matricial ni perfil radicular.
6. **P1: no hay escala de campo ni mapping Campo -> HRU.** La existencia de tablas HRU no constituye una simulacion espacial. Faltan conversion de unidades, ponderacion de areas y agregacion temporal.
7. **P1: clima sintetico etiquetado como historico/SSP.** No hay GCM, miembro, periodo, bias correction ni control de calendario. No comparar hipotesis H0/H1 con este forcing.
8. **P1: validacion demo y estadistica no apta para evidencia.** AI Studio tiene arrays sin provenance, Sobol fijo, KS incorrecto, bootstrap sin semilla y reportes con metricas fijas. No migrar calculos cientificos a TypeScript.
9. **P1: leakage y comparacion no reproducible.** No hay separacion temporal/espacial de calibracion y validacion; observaciones y simulaciones demo coexisten como literales.
10. **P1: identificadores geograficos no verificados.** El prototipo asocia `USGS-05464500` a Walnut Creek/Ames, pero el identificador corresponde a Cedar River at Cedar Rapids. HUC, gauge y geometria requieren fuente y version independientes.
11. **P2: informes con afirmaciones no condicionales.** Los reportes declaran eficacia de riego, resiliencia o conservacion de masa sin evidencia almacenada.
12. **P2: operacion y seguridad.** Registro publico puede solicitar roles privilegiados; tests hacen `drop_all` sobre la DB configurada; WS no autentica; ejecuciones pueden permanecer `RUNNING` al fallar.

## Reproducibilidad y provenance

El sistema actual conserva UUID, usuario, fechas de creacion, referencias mutables a cuenca/escenario, una parte de los resultados diarios y KPIs. Esto no basta para repetir una corrida.

| Requisito | Estado actual | Gap |
|---|---|---|
| `simulation_id`, autor y fecha | Parcialmente persistido | Faltan `started_at`, `finished_at`, intento y transiciones |
| Configuracion y parametros efectivos | JSON solicitado | Se ignora en ejecucion; no hay schema, hash ni snapshot |
| Semilla y RNG | No persistidos | `hash()` no es estable entre procesos |
| Cuenca, HRUs y especies usadas | Solo FK catalogo | No hay snapshot/version ni evidencia de uso |
| Datasets, versiones y checksums | Ausente | No se distingue observado, sintetico, derivado ni demo |
| Escenario climatico/manejo | FK mutable | No hay GCM, miembro, periodo, correccion ni plan de manejo efectivo |
| Version de codigo/entorno | Ausente por corrida | Falta commit, versiones de motor, dependencias y esquema |
| Logs, errores y eventos | Ausente por corrida | Sin error estructurado, logs ni correlacion |
| Outputs y metricas | Filas diarias/KPIs parciales | Falta checksum, unidades, estados internos y resultados por unidad espacial |

El manifiesto minimo futuro por corrida debe incluir: identificadores, configuracion solicitada y efectiva, snapshots de dominio, datasets/checksums, seed, versiones, calendario/timestep, logs/errores, outputs/checksum, metricas y estado de validacion.

## Frontend existente frente a prototipo

El frontend actual ya tiene autenticacion, catalogos, creacion/listado de simulaciones, resultados REST, playback WS, escena 3D, graficas y descarga de reportes. No debe sustituirse masivamente por la SPA Vite.

| Componente AI Studio | Estado actual en AI Studio | Accion | Destino Next.js | Backend requerido | Riesgo |
|---|---|---|---|---|---|
| `ThreeDPlantViewer` | Three.js procedural y props locales | Integrar parcialmente, reescribiendo contrato y lifecycle | Extender `components/3d/PlantModel3D.tsx` o visor aislado client-only | Estado temporal de planta, arquitectura o marca ilustrativa, unidades/provenance | Geometria no FSPM; fugas GPU, escalas inconsistentes |
| Campo de `ThreeDPlantViewer` | 980 instancias aleatorias | No migrar como agregacion; reutilizar solo tecnica visual | `FieldPlotMesh3D.tsx` | Distribucion de campo/plantas o agregado declarado | Confundir variacion visual con 1000 plantas simuladas |
| `WatershedGisViewer` | SVG con HRUs y red inventados | Portar inspector; reescribir mapa GIS | Nueva ruta/modulo GIS dentro de dashboard | GeoJSON/COG, CRS, HRU, capas, estacion validada | No es georreferenciado; gauge/HUC incorrectos |
| `SimulationOrchestrator` | Timers, logs y job local falsos | Portar UX de formulario/progreso; reescribir todo el flujo | Evolucion de `simulations/page.tsx` | Simulacion/job, estado, progreso, eventos, errores | Presentar Celery/SWAT/QDM como reales |
| `ValidationLab` | Estadisticas TS sobre fixtures | Portar layout; backend debe producir metricas | Nueva pagina de validacion cuando exista protocolo | Observaciones, series alineadas, baseline, metricas Python, CIs | Sobol fijo, KS defectuoso, leakage |
| `DataIngestionModule` | Timers y contadores aleatorios | Portar tarjetas de estado; reescribir conectores | Nueva pagina datasets al implementar ingesta | Dataset/job/provenance/errores | Simular descarga y bias correction |
| `ReportGenerator` | PDF/XLSX/HTML `.doc` cliente con cifras fijas | Conservar backend real de reportes, no este motor | Mejorar `reports/page.tsx` | Artefactos asociados a corrida y validacion | Cifras fijas y formato Word no real |
| `ArchitectureViewer` | Strings de Python/Docker | Descartar como implementacion | Documentacion futura basada en repositorio real | Ninguno | Copiar infraestructura ficticia/insegura |
| `ApiExplorer` | Respuestas con timeout | Descartar | OpenAPI real o cliente generado | OpenAPI | Contratos ficticios |
| `mockScientificData.ts` | Fixtures y textos "Authentic/Ground Truth" | Mantener solo fixtures aislados/renombrados | `frontend` test fixtures, no UI productiva | Ninguno | Datos sin provenance presentados como reales |

### Duplicacion detectada

| Capacidad | AI Studio | Implementacion canonica actual | Decision |
|---|---|---|---|
| Login, roles, perfil | Estado/claims mock | FastAPI + Next.js reales | Conservar actual; no portar mock |
| Simulacion | Timer local | POST FastAPI y resultados persistidos | Conservar actual; refactorizar contrato despues |
| Estado temporal | Intervalos locales | REST/WS playback | Consolidar en una fuente de corrida; no duplicar |
| Planta/campo/cuenca 3D | Three.js procedural | React Three Fiber actual | Reutilizar ideas visuales, no dos renderers equivalentes |
| Graficas/validacion | SVG/arrays locales | Recharts para resultados; sin validacion real | Mantener Recharts; validacion futura desde Python |
| Reportes | Cliente con constantes | Backend PDF/DOCX/XLSX | Mantener backend y corregir contenido |
| API/arquitectura | Strings y timeouts | FastAPI/OpenAPI reales | Descartar prototipo |

## Matriz de API: existente y gaps

| Necesidad UI | Endpoint existente | Estado | Accion propuesta |
|---|---|---|---|
| Catalogo de cuencas/HRUs | `GET /simulations/watersheds/all` | Reutilizable, contrato mejorable | Normalizar como `GET /watersheds` y detalle; mantener lectura inicialmente |
| Catalogo de escenarios | `GET /simulations/scenarios/all` | Reutilizable, sin version/origen | Normalizar como `GET /scenarios`, declarar `synthetic` o fuente/version |
| Crear corrida | `POST /simulations` | Incompleto: bloquea HTTP y acepta parametros inertes | Mantener recurso; validar `RunConfig`, persistir manifiesto; usar 202 solo al desacoplar ejecucion |
| Listar/detallar corrida | `GET /simulations`, `GET /simulations/{id}` | Reutilizable | Incluir configuracion efectiva, provenance, progreso, error y estado tipado |
| Resultados | `GET /simulations/{id}/results?limit=` | Incompleto | Cursor/offset, 404 coherente, unidades, series espaciales y versiones |
| Playback | `WS /twin/ws/{id}` | Demo/reproduccion, sin auth | Etiquetar como playback y autenticar; reemplazar por eventos de corrida si hay worker |
| Progreso y jobs | Ninguno | Faltante | Incorporar en el recurso simulacion: estado, `completed_days`, `total_days`, timestamps, error; no crear `jobs` separado aun |
| Cancelacion | Ninguno | Faltante condicionado | `POST /simulations/{id}/cancel` solo con ejecucion cooperativa real |
| Datasets | Ninguno | Faltante para integracion real | `POST /datasets`, `GET /datasets/{id}` y registro de ingesta cuando se implemente adquisicion |
| Validacion | Ninguno | Faltante | `POST /simulations/{id}/validation` y lectura asociada, solo tras tener observaciones/protocolo |
| Reportes | `GET /reports/download/...`, historial | Reutilizable pero semantica riesgosa | Exigir corrida completa/provenance; conservar un endpoint de descarga inicialmente |
| Proyectos | Ninguno | No prioritario | Agregar solo al requerir agrupacion/ACL de experimentos |

No se recomienda introducir simultaneamente recursos redundantes `experiments`, `runs`, `jobs` y `simulations`. Para el alcance actual, una simulacion debe ser el experimento y, cuando aplique, su unidad de ejecucion.

## Estructura objetivo propuesta

La propuesta conserva directorios canonicos y evita una reorganizacion cosmetica. El cambio esencial es separar core cientifico puro de FastAPI, ORM y workers.

```text
backend/
  app/                         # FastAPI, ORM, routers, application services
    api/v1/
    application/               # crear corrida, persistir, reportar, publicar eventos
    infrastructure/            # SQLAlchemy, archivos, proveedores externos, workers
    models/ schemas/
  scientific_core/             # sin FastAPI, ORM, Redis, Celery ni DB
    contracts/                 # PlantModel, FieldModel, ClimateProvider, HydrologyModel
    plant/                     # simplified y futura implementacion FSPM
    field/                     # poblacion, agregacion espacial/temporal
    coupling/                  # PlantToField, FieldToHRU, unidades/provenance
    hydrology/                 # simplified y adapter SWAT+
    climate/                   # synthetic y adapter NEX-GDDP-CMIP6
    validation/                # metricas, Sobol, bootstrap, KS, Wilcoxon
  tests/
    scientific_core/           # balances, unidades, determinismo, referencias
    integration/               # API, DB, adaptadores externos con fixtures
frontend/
  src/
    app/(dashboard)/
    components/                # UI y visualizaciones, no calculo cientifico
    features/                  # simulations, validation, datasets, gis si crecen
    lib/api.ts
    types/
prototypes/
  ai-studio-mvp/               # referencia aislada, fixtures declarados demo
docs/
  methodology/                 # protocolos, unidades, fuentes, seleccion de cuencas
  adr/                         # decisiones de arquitectura y contratos
```

`scientific_core` se justifica porque actualmente `TwinCouplingEngine` mezcla modelos, SQLAlchemy y commits. No se propone PostGIS, TimescaleDB, Redis o Celery hasta que una necesidad ejecutable los justifique; PostgreSQL/PostGIS sera apropiado al incorporar geometria y consultas espaciales reales.

## Evidencia principal

- Modelos: `backend/app/services/plant_model.py`, `swat_hydrology.py`, `climate_engine.py`, `twin_coupling_engine.py`.
- Dominio/API: `backend/app/models/{watershed,simulation}.py`, `backend/app/api/v1/{simulations,twin_ws,reports}.py`.
- UI actual: `frontend/src/app/(dashboard)/{simulations,twin-3d,reports}/page.tsx`, `frontend/src/components/3d/`.
- Prototipo: `prototypes/from-plant-to-watershed_-multi-scale-digital-twin/src/{components,services,data}/`.

La auditoria no ejecuta SWAT+, descarga de datasets, ni validacion externa. La ausencia se refiere al codigo y artefactos inspeccionados.

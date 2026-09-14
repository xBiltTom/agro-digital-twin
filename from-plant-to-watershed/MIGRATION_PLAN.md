# Plan de migracion hacia el gemelo digital multiescala

## Principios y limite de esta fase

Este plan no asume que H1 sea verdadera. La comparacion futura entre baseline SWAT+ y gemelo acoplado debe usar mismo forcing, periodo, unidades, watershed/gauge, protocolo de calibracion y particion de evaluacion.

Los modelos actuales simplificados pueden seguir sirviendo para desarrollo, demostracion offline y CI, pero deben declararse por tipo y no llamarse SWAT+, FSPM o CMIP6 reales. El prototipo AI Studio fue retirado el 2026-09-08 tras la migracion de las ideas visuales necesarias; no es fuente cientifica ni backend.

## Que conservar, refactorizar y retirar despues

| Area | Conservar | Refactorizar | Retirar posteriormente |
|---|---|---|---|
| Frontend Next.js | Layout, auth, cliente API, formularios, Recharts, React Three Fiber, escenas por escala, descargas | Etiquetas de evidencia, URLs REST/WS, accesibilidad, estados de error, contratos tipados/runtime, unificar resultados | Fallbacks que aparentan datos, shocks locales no persistidos y KPIs hardcodeados |
| Backend FastAPI | ORM, auth/RBAC tras corregir seguridad, catalogos, resultados, exportacion, OpenAPI | Ejecutor desacoplado del ORM, lifecycle, validacion de input, manifests, WS autenticado | Seed y narrativas que se presenten como observadas/validadas |
| Modelos simplificados | Clima, planta e hidrologia para CI/offline | Renombrar, documentar unidades, cerrar balances, semilla explicita, contratos puros | Uso publico de nombres SWAT+/CMIP6/FSPM si no se implementan |
| Prototipo AI Studio retirado | Ningun artefacto ejecutable | Las ideas visuales relevantes ya se reimplementaron en Next.js | Timers, `mockScientificData`, ApiExplorer, ArchitectureViewer como codigo, roles/tokens mock, cifras y conclusiones fijas |

## Contratos cientificos objetivo

Los contratos se definen en Python dentro de `scientific_core`, con serializacion en la capa de aplicacion. La UI consume resultados; no implementa calculos cientificos principales.

| Contrato | Responsabilidad | Entradas/salidas verificables |
|---|---|---|
| `PlantModel` | Estado individual y fisiologia | forcing, suelo por capa, parametros; organos/LAI/raiz/transpiracion/estres/unidades |
| `FieldModel` | Poblacion y variabilidad espacial | estados de plantas, posiciones/densidad/suelo; agregados y distribuciones de campo |
| `PlantToFieldAggregator` | Conversion explicita Planta -> Campo | volumen/planta a lamina/campo; area, densidad, metodo, incertidumbre |
| `FieldToHRUCoupler` | Mapping Campo -> HRU | campos/HRUs/geometria; ponderacion, conversion de unidades, agregacion temporal y provenance |
| `HydrologyModel` | Hidrologia intercambiable | forcing e inputs HRU; flujos/almacenamientos con balance y unidades |
| `SwatPlusAdapter` | Integracion SWAT+ real futura | proyecto/inputs/version ejecutable/logs/outputs y errores; nunca esconder conversiones |
| `ClimateProvider` | Forcing versionado | cobertura, unidades, calendario, source/provenance; puede ser `SyntheticClimateProvider` o NEX |
| `ValidationEngine` | Evaluacion en Python | series alineadas, protocolo, metricas, CIs, pruebas, resultados indefinidos explicitos |
| `SimulationOrchestrator` | Ordena ejecucion reproducible | manifiesto inmutable, eventos, outputs y estado; sin formulas ni dependencias ORM en core |

Cada variable intercambiada debe llevar unidad, soporte espacial, resolucion temporal, metodo de agregacion, valor faltante y provenance. Las transformaciones se registran como artefactos: Planta -> Campo -> HRU -> SWAT+.

## Fases recomendadas

### Fase 0: correcciones de integridad y rotulado

Dependencia: ninguna. Objetivo: impedir afirmaciones cientificas o de seguridad falsas antes de extender la UI.

1. Corregir escalamiento de roles, WS sin autenticacion y fixture de tests destructivo.
2. Etiquetar toda salida como `SIMPLIFIED`, `SYNTHETIC`, `DEMO`, `ILLUSTRATIVE`, `OBSERVED` o `DERIVED` segun corresponda.
3. Retirar o condicionar afirmaciones de SWAT+, NEX, IoT, AI, conservacion de masa, riego eficaz y validacion.
4. Deshabilitar controles cuyos parametros no se ejecuten, incluido riego, o hacerlos visibles como no implementados.
5. Corregir URLs configurables REST/health/WS y errores/fallbacks que presenten datos ficticios.

Criterio de salida: ninguna pantalla o reporte presenta datos sinteticos, modelo simplificado o fixture como observacion, integracion externa o resultado validado.

### Fase A: consolidacion de UI en Next.js

Dependencia: Fase 0. Objetivo: elevar UX sin duplicar aplicaciones ni reconstruir logica falsa del prototipo retirado.

1. Consolidar patrones visuales de tarjetas, progreso, inspector y tabs directamente en componentes Next.js.
2. Mantener la fuente de datos en `frontend/src/lib/api.ts`; no importar `mockScientificData.ts` en rutas productivas.
3. Adaptar visualizador de planta como client-only y declarar si su geometria es ilustrativa.
4. Conservar React Three Fiber actual como renderer canonico; no introducir un segundo stack Three.js salvo una justificacion concreta.
5. No construir GIS, ingesta o laboratorio de validacion funcional hasta que existan contratos backend.

Criterio de salida: nueva UI reutiliza endpoints actuales sin prometer datasets, workers o resultados inexistentes.

### Fase B: refactor del scientific core y reproducibilidad

Dependencia: Fase 0; puede avanzar en paralelo con A. Objetivo: hacer el modelo conceptual testeable y honestamente nombrado.

1. Extraer modelos puros de `TwinCouplingEngine`; el core no importa FastAPI, SQLAlchemy ni ORM.
2. Renombrar modelos simplificados y documentar ecuaciones, referencias, unidades, supuestos y dominio de validez.
3. Introducir `RunConfig` validado, semilla explicita persistida, estados iniciales y snapshots de parametros.
4. Implementar tests de determinismo, limites, conversiones, balance diario/acumulado y parametros que realmente afecten salidas.
5. Corregir creacion de agua, ET0/estados fisicos y narrativa de reportes antes de cualquier interpretacion.

Criterio de salida: una misma configuracion y seed reproduce los mismos outputs, el balance cierra o explica intercambios externos, y cada parametro expuesto tiene efecto o se rechaza.

### Fase C: observaciones y seleccion verificable de watershed/gauge

Dependencia: Fase B. Objetivo: establecer dominio Corn Belt y provenance antes de calibrar o validar.

1. Definir protocolo metodologico de seleccion de cuencas: >=60% agricultura, >=20 anos de caudal diario, exclusion de reservorios y criterios de calidad.
2. Registrar watershed, CRS, HRUs, estaciones USGS, area de drenaje y fuente/version geometrica. Verificar IDs contra fuentes oficiales; no reutilizar fixtures del prototipo.
3. Incorporar datasets observacionales como recursos versionados: USGS, USDA NASS, CHIRPS, SoilGrids y Landsat/USGS, segun se implementen.
4. Añadir unidades, cobertura, control de calidad, checksums, licencias y trazabilidad de transformaciones.
5. Definir separacion temporal y, cuando corresponda, espacial de calibracion/validacion antes de ajustar parametros.

Criterio de salida: cada serie usada tiene fuente, version, unidad, cobertura, control de calidad y asociacion verificable a watershed/gauge.

### Fase D: baseline SWAT+ real

Dependencia: Fase C. Objetivo: construir el comparador H0 antes del modelo acoplado.

1. Implementar `SwatPlusAdapter` con proyecto SWAT+, version de ejecutable, inputs generados, logs, errores y outputs archivados.
2. Hacer explicitamente testeables conversiones, generacion/modificacion de inputs y extraccion de outputs.
3. Calibrar y validar baseline con datos observados bajo protocolo congelado; registrar parametros y periodos.
4. No reemplazar el modelo simplificado: conservarlo como modo offline/test identificado.

Criterio de salida: una corrida baseline SWAT+ es repetible desde manifiesto, ejecuta software real y se valida contra observaciones independientes.

### Fase E: FSPM y agregacion de campo

Dependencia: Fases B y C. Objetivo: crear una escala Planta -> Campo cientificamente explicita.

1. Seleccionar e implementar progresivamente modelo de planta con alcance declarado; no etiquetarlo FSPM pleno antes de cubrir arquitectura/estado requeridos.
2. Modelar poblacion aproximada de 1000 plantas con posiciones, propiedades de suelo y variabilidad reproducible.
3. Implementar agregacion espacial y temporal con conversiones de litros/planta/dia a mm/dia, densidad, area y incertidumbre.
4. Persistir outputs por planta/muestra representativa y por campo sin forzar el frontend a cargar datos masivos.

Criterio de salida: existe transformacion auditada Planta -> Campo con unidades, ponderaciones, seed y tests de conservacion/agregacion.

### Fase F: acoplamiento Campo -> HRU -> SWAT+

Dependencia: Fases D y E. Objetivo: implementar el componente central sin ocultarlo en servicios genericos.

1. Definir mapping campo/HRU basado en geometria, uso de suelo, periodos y cobertura; tratar campos parciales y multiples.
2. Convertir ET, infiltracion, estres, raiz y variables derivadas al contrato de entrada de SWAT+ con unidades y agregacion temporal explicitadas.
3. Generar/modificar inputs SWAT+, ejecutar adaptador y extraer outputs por HRU/subcuenca/cauce.
4. Registrar provenance de cada transformacion, incluidas reglas de asignacion y versiones.
5. Probar casos sinteticos de area/unidades y corridas de integracion controladas.

Criterio de salida: se puede inspeccionar y repetir toda la cadena Plant -> Field -> HRU -> SWAT+, con cada conversion verificable.

### Fase G: NEX-GDDP-CMIP6 y correccion de sesgo

Dependencia: Fases C y D; F es recomendable para escenarios acoplados. Objetivo: forcing climatico verificable.

1. Implementar `NexGddpCmip6Provider` separado de descarga, preprocessing, almacenamiento, bias correction y forcing generation.
2. Soportar SSP2-4.5 y SSP5-8.5 con GCM, miembro, periodo, calendario, variable, grilla y archivo identificados.
3. Definir y validar bias correction usando solo ventanas permitidas por el protocolo; no usar validacion para ajustar.
4. Conservar el proveedor sintetico para CI/demo con marca explicita.

Criterio de salida: cada forcing CMIP6 tiene artefactos, hashes, metodo de correccion, parametros, cobertura y controles de unidades/calendario.

### Fase H: validacion, sensibilidad e incertidumbre

Dependencia: Fases C, D y segun objetivo E-G. Objetivo: implementar evidencia en Python, no en componentes TS.

1. Implementar RMSE, NSE y PBIAS hidrologicos; RMSE y R2 de rendimiento, con validacion de alineacion/unidades y casos indefinidos.
2. Implementar KS correctamente sin interpretar no-rechazo como identidad; Wilcoxon con hipotesis, empates, dependencia y alternativa declaradas.
3. Ejecutar Sobol real sobre parametros FSPM: transpiracion, profundidad maxima de raiz y LAI, con diseno muestral, seed, N y outputs archivados.
4. Aplicar bootstrap apropiado para series temporales y CI 95% de rendimiento bajo SSP5-8.5, con unidad de remuestreo justificada.
5. Exponer resultados, no formulas, a la UI junto con protocolo y provenance.

Criterio de salida: metricas y pruebas son artefactos reproducibles de Python asociados a datasets, protocolo, corrida y version.

### Fase I: evaluacion formal de H0/H1

Dependencia: Fases D, F, G y H. Objetivo: comparacion controlada, no una demostracion visual.

1. Congelar watershed/gauges, periodo, forcing, calibracion, baseline y digital twin acoplado.
2. Ejecutar comparacion equivalente y preespecificada para RMSE mensual de escorrentia y variabilidad espacial de rendimiento.
3. Reportar resultados, incertidumbre, tests y limitaciones; H1 se acepta solo si evidencia el umbral definido y el protocolo lo respalda.

Criterio de salida: informe reproducible que puede rechazar H1 y conserva todos los artefactos necesarios para auditoria.

## Dependencias entre fases

```text
Fase 0 -> Fase A
Fase 0 -> Fase B -> Fase C -> Fase D -> Fase F -> Fase G -> Fase H -> Fase I
                                  \-> Fase E -/
```

No se debe adelantar Fase F antes de disponer de baseline SWAT+ y campo explicito. No se debe declarar CMIP6 real antes de Fase G ni resultados H0/H1 antes de Fase I.

## API minima por etapa

| Etapa | Accion de API | Motivo |
|---|---|---|
| 0-B | Mejorar `POST/GET /simulations` y resultados existentes | Configuracion efectiva, seed, estados, errores, provenance y paginacion sin expandir superficie |
| C | Añadir `datasets` cuando exista ingesta real | Registrar fuente, cobertura, unidades, checksum, licencia y QC |
| D-F | Extender detalle de simulacion y resultados espaciales | Mostrar modelo, artefactos, HRU/campo y transformaciones asociadas |
| H | Añadir validacion asociada a una simulacion | Una accion/recurso de validacion que reciba dataset, variable, periodo y protocolo |
| Cuando haya worker real | Estado/eventos y cancelacion de simulacion | Progreso y cancelacion cooperativa, no timers simulados |

La UI necesita: proyectos solo cuando haya agrupacion/ACL real; cuencas/HRUs, escenarios, simulaciones, progreso, resultados, datasets, validacion y reportes solo cuando sus recursos tengan trazabilidad. No se implementara un CRUD completo de cada entidad por anticipacion.

## Condiciones de no migracion

No portar a produccion desde AI Studio:

- `mockScientificData.ts` como dataset, incluidos gauge/HUC y series de caudal/rendimiento.
- Timers como ingestion, Celery, Redis, WebSocket o progreso.
- Strings de `ArchitectureViewer` y `ApiExplorer` como backend/API/documentacion operativa.
- Sobol hardcodeado, KS actual, p-values/conclusiones fijas o bootstrap del navegador como validacion.
- PDF/XLSX/HTML Word con cifras fijas o formato anunciado distinto del generado.
- Claims/tokens/roles locales como autorizacion.

## Verificacion requerida al cerrar cada fase

| Tipo | Requisito |
|---|---|
| Ciencia | Pruebas de unidades, balance, casos limite, determinismo y referencia donde aplique |
| Datos | Fuente, version, licencia, checksum, cobertura, QC y lineage |
| Reproducibilidad | Manifiesto de corrida, seed, snapshots, commit/version de motor y outputs verificables |
| UI | Etiqueta de provenance, estado de disponibilidad/error y coherencia con API/reporte |
| Seguridad | Autorizacion backend, WS autenticado, DB de tests aislada y sin credenciales demo en produccion |
| Comparacion | Calibracion/validacion separadas, forcing equivalente y baseline congelado |

Este documento es un plan. No autoriza migracion masiva de UI, nuevos endpoints, SWAT+ ni CMIP6 hasta revision explicita.

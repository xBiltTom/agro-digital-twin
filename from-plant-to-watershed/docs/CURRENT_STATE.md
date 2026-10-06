# Estado actual del proyecto

Revisión documental: **2026-10-06**. Describe el código y los artefactos del
repositorio; la disponibilidad de servicios locales se comprueba al ejecutarlos.
La [ficha técnica](../project_framework.md) conserva el alcance de investigación.

## 1. Implementación y evidencia

| Componente | Estado y alcance |
| --- | --- |
| Plataforma | FastAPI, Next.js, autenticación/RBAC, catálogo y reportes multiformato. |
| Motor hidrológico | SWAT+ real 61.0.2.61; nueva receta de investigación desde fuente, con reproducción binaria local. |
| Planta | `SIMPLIFIED_FSPM`: poblaciones deterministas con variabilidad paramétrica, no un FSPM botánico completo validado. |
| Calendario | Siembra/cosecha por HRU desde `mgt_out.txt`; eventos modelados, no operaciones agrícolas observadas. |
| Agua SWAT+ → FSPM | Estimación de humedad radicular desde `sw_ave` y `soils.sol`, bajo hipótesis de fracción de agua disponible uniforme en el perfil. |
| Planta → SWAT+ | Diez parámetros del registro vegetal `corn` en `plants.plt`; SWAT+ mantiene sus propias ecuaciones de agua y cultivo. |
| Persistencia | Frames JSONB PostgreSQL con clave temporal y SHA-256. |
| Visor | Tres escalas y estados fechados; mallas anatómicas y terreno ilustrativos/contextuales. |
| Diagnóstico observacional | Tres variantes estándar 2019 con lectura de caudal corregida; la pareja acoplada requiere su propia comparación. |
| Recorrido del agua | 37 cauces delineados con almacenamiento independiente de llanura y cierre numérico de red; balance de cuenca todavía parcial. |
| Meteorología / ET | Auditoría gridMET y comparación externa 2019; detecta rellenos de calendario y discrepancias de lluvia/viento en warm-up. |
| Descargas SWAT+ | CSV de registros y JSON con configuración, procedencia, métricas y cobertura desde Simulaciones e Informes. |
| CMIP6 / rendimiento | Sin proyecciones CMIP6 normalizadas en el experimento publicado ni validación de rendimiento a escala HRU/cuenca. |

## 2. Experimentos que conviven

| Identificador | Uso | Interpretación |
| --- | --- | --- |
| `south-fork-final-v1` | `research_domain/final_report.json` | Resultado archivado del antiguo contrato de tres máximos vegetales. |
| `south-fork-final-v2` | `research_domain/final_report_v2.json`; `/reports/final-scientific` | Experimento anterior publicado, evaluación USGS 2018–2020; H1 no respaldada, mejora mensual 0 %. |
| `phase1-sf-2019-v3` | Bundle de ejecución 2019 | Calendarios ejecutados y inputs compatibles, todavía con humedad FSPM constante asumida. |
| `phase234-sf-2019-v1` | Bundle diario anterior | Anterior a la corrección de interpretación del almacenamiento SWAT+. |
| `phase234-sf-2019-v2` | Bundle diario corregido y selección preferida del visor cuando es accesible | Gemelo planta–suelo–agua experimental, no calibración ni nueva prueba de H1. |
| `sf19-diag-v1-reference` | Ejecución estándar diaria registrada en PostgreSQL | Referencia de desarrollo: RMSE mensual 9,533 m³/s; NSE −0,961. |
| `sf19-diag-v1-tile-probe` | Activación experimental de drenaje en maíz | Genera drenaje, pero carece de conexión `til` en las unidades de ruteo. |
| `sf19-diag-v2-tile-routed` | Misma activación y conexión `til` al canal | RMSE mensual 8,914 m³/s; NSE −0,715; referencia todavía insuficiente. |
| `sf19-flow-v1-reference` | Referencia repetida con lectura corregida de hidrogramas | RMSE mensual 8,574 m³/s; NSE −0,587; volumen 100,420 hm³. |
| `sf19-flow-v1-tile-probe` | Drenaje sin conexión, con lectura corregida | Drenaje fuera del recorrido; residuo parcial 64,224 mm. |
| `sf19-trace-v3-tile-routed` | Drenaje conectado y lectura corregida | RMSE mensual 7,776 m³/s; NSE −0,305; volumen 103,553 hm³. |
| `sf19-geom-v1-geom-routed` | Longitudes delineadas con binario original | `FAILED`: SIGFPE en calidad del agua durante warm-up. |
| `sf19-geom-v2-geom-routed` | Intento de cinética con entradas cero | `FAILED`: underflow en sedimentos; varias entradas cero se sustituyen por valores predeterminados. |
| `sf19-geom-ctrl-v1-tile-routed` | Control con copia diagnóstica que permite underflow | Reproduce volumen y métricas de la variante artificial conectada; 365 frames. |
| `sf19-geom-v3-geom-routed` | Longitudes delineadas y misma copia diagnóstica | RMSE mensual 8,081 m³/s; NSE −0,409; volumen 94,460 hm³; 365 frames. |
| `sf19-src-ctrl-v1-tile-routed` / `sf19-src-v1-geom-routed` | Primera pareja desde fuente | Reproduce caudales y recupera almacenamiento; build anterior con rutas absolutas. |
| `sf19-src-ctrl-v2-tile-routed` | Control con receta reproducible desde fuente | Reproduce el control anterior; 365 frames. |
| `sf19-src-v2-geom-routed` | Longitudes delineadas y receta reproducible | Reproduce caudales anteriores; residuo de red 0,315 m³, cuenca parcial −0,01215 mm; 365 frames. |

Dashboard y reportes consultan el experimento final v2. El visor prioriza el
gemelo diario corregido, salvo que se indique una corrida accesible mediante
`?simId=`. Esa diferencia de linaje debe permanecer explícita.

El [diagnóstico 2019](BASELINE_DIAGNOSTIC_2019.md) documenta las tres nuevas
corridas, las intervenciones y el siguiente trabajo físico. Cada corrida tiene
365 frames persistidos; la comparación incluye 12 meses completos y conserva
86 valores USGS estimados. Este avance evalúa el baseline estándar, sin FSPM/ML.

El [recorrido del agua](WATER_PATH_DIAGNOSTIC_2019.md) identificó después un
error del reporte de canales artificiales. Las tres variantes `sf19-flow-*` y
`sf19-trace-v3-*` conservan valores originales y normalizados; sus comparaciones
son consistentes entre sí. Las métricas de `sf19-diag-*` corresponden a la lectura
anterior y no deben mezclarse con ellas al atribuir mejoras físicas.

La [recuperación de longitudes](CHANNEL_GEOMETRY_DIAGNOSTIC_2019.md) añade
212,637 km de cauces derivados del DEM. La pareja controlada cambia únicamente
`len` entre inputs trazables; los términos terrestres siguen idénticos. El
ruteo físico de aquella etapa incluye almacenamiento y pérdidas, con balance
parcial por ausencia del estado de llanura. El ejecutable diagnóstico cambia solamente
la trampa de underflow de una copia del binario auditado; no es una versión
oficial; aquella etapa dejó pendiente fijar el motor para el paper.

La [compilación desde fuente](SWAT_SOURCE_BUILD_2019.md) fija después el commit,
herramientas y política de underflow, y obtiene ejecutables idénticos desde dos
directorios independientes. La pareja definitiva reproduce las series diarias
anteriores. Su salida independiente recupera 0,819 hm³ de cambio de llanura,
con cierre numérico de la red y contabilidad de cuenca todavía parcial.
Las métricas USGS siguen mostrando una referencia insuficiente; no se evaluó H1.

La [auditoría meteorológica](METEOROLOGY_DIAGNOSTIC_2019.md) contrasta los mismos
inputs con caché gridMET y nuevas descargas. En 2019 las conversiones coinciden
dentro del redondeo; el warm-up contiene cinco cierres de año interpolados,
192 valores de lluvia de 2011 y 328 valores de viento de 2015 distintos de la
referencia gridMET recuperada. ET SWAT+ suma 834,971 mm frente a 683,073 mm de
TerraClimate, que es otro modelo y no una medición. PET difiere según el producto
de referencia; la comparación no justifica una reducción global de PET.
Ambas corridas en pglocal tienen la auditoría completa, su revisión anterior
conservada y sus 365 frames originales. El panel científico expone comparaciones
y alertas; las futuras corridas agregan weather por área de HRU.

## 3. Gemelo South Fork 2019 corregido

Bundle: `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/`.
`manifest.json` y `run_status.json` conservan los checksums y las comprobaciones:

- Estado `COMPLETED`, 365 fechas y 20 artefactos catalogados.
- 36 HRU y 37 canales por fecha; outlet GIS `153`.
- 32 HRU de maíz y siete calendarios; 1.000 plantas FSPM por grupo.
- Hasta diez slots representativos por grupo y fecha, hasta 70 muestras activas.
- Siembra modelada el 15/16 de mayo; cosechas/kill del 27 de agosto al 3 de septiembre.
- Dos iteraciones acopladas; máximo cambio final de `sw_ave` de 0,001 mm,
  por debajo de la tolerancia de 0,1 mm, con calendarios coincidentes.
- El proyecto fuente permaneció sin cambios.

En el frame del **2019-07-15** se documentan humedad FSPM estimada de
29,2263 vol%, estrés 0,0442, biomasa 167,6516 g/planta, transpiración
2,3156 mm/día y caudal outlet de 0,3202 m³/s. Son estados modelados/derivados.

Ese caudal pertenece al bundle archivado; requiere auditoría con hidrogramas
nativos ante el hallazgo del reporte de canales artificiales. El nuevo diagnóstico
no modifica retrospectivamente este gemelo ni el reporte científico publicado.

La verificación operativa previa registró v1 y v2 en PostgreSQL y comprobó
playback autenticado, reconexión y consultas sin lector SQLite. También migró
el playback de una línea base 2018 sin FSPM. El acceso depende del propietario
y de los datos registrados en cada despliegue, no solo de tener el bundle.

Para consultar la corrida:

```text
GET /api/v1/simulations/phase234-sf-2019-v2/availability
GET /api/v1/simulations/phase234-sf-2019-v2/playback?date=2019-07-15&resolution=DAILY
```

Para importar el bundle en una instalación preparada, desde `backend/`, con
IDs existentes de propietario, South Fork y escenario neutral:

```bash
python scripts/register_phase234_south_fork_2019.py \
  data/phase1-south-fork-2019/results/phase234-sf-2019-v2 \
  --owner-id UUID_USUARIO --watershed-id UUID_CUENCA --scenario-id UUID_ESCENARIO
```

El importador verifica los artefactos y el contenido repetido. No ejecuta SWAT+.

Para una nueva ejecución del flujo diario de 2019, desde `backend/`, con
proyecto experimental y ejecutable disponibles:

```bash
python scripts/run_phase1_south_fork_2019.py \
  --run-id south-fork-2019-nueva-ejecucion \
  --project /ruta/al/proyecto-experimental \
  --executable /ruta/al/ejecutable/swatplus \
  --output-root data/phase1-south-fork-2019 \
  --warmup-years 19 --plant-count 1000 --seed 42
```

El script conserva el nombre histórico de fase 1, pero usa el runner acoplado
actual. El periodo visible está fijado a 2019; escribe CSV, playback comprimido,
logs y manifiesto. Rechaza sobrescribir un run ID existente. La nueva ejecución
tiene su propio linaje y no se registra automáticamente como reporte de H1.

## 4. Límites científicos relevantes

- **Dominio:** un piloto en South Fork; no validación cruzada multicuenca.
- **Manejo:** CDL 2019 estático informa una variante experimental; no
  reconstruye rotaciones ni operaciones históricas observadas.
- **Meteorología:** la auditoría de las referencias 2019 identifica gridMET y
  reconstruye sus conversiones; registra anomalías de calendario/caché en el
  warm-up. Las etiquetas de procedencia de bundles anteriores se conservan;
  los contrastes externos de ET son comparaciones entre modelos.
- **Humedad:** estimación de zona radicular, no humedad diaria medida por capa.
  Las plantas de un calendario reciben condiciones ponderadas del grupo.
- **Acoplamiento:** el resumen de los grupos actualiza un único registro `corn`;
  no transmite una parametrización vegetal distinta por HRU. ET, uptake y
  estrés diarios FSPM no se imponen a SWAT+.
- **Geometría:** `polygon_id` y `geometry_id` permanecen nulos. Los IDs GIS no
  prueban por sí solos una unión con las mallas del frontend.
- **Planta 3D:** hojas, raíces laterales y órganos son geometría ilustrativa;
  las 1.014 instancias del campo no son 1.014 trayectorias individuales.
- **ML:** los bundles mensuales versionados son sintéticos; el pronóstico diario
  sobre playback aprende de simulación y no demuestra mejora contra USGS.

## 5. Siguiente etapa de investigación

1. Corregir el forcing de warm-up en una variante trazable: cierres de año,
   lluvia de 2011 y viento de 2015. Comparar contra la referencia preservada
   bajo el mismo motor, geometría, parámetros y observaciones; después revisar
   partición ET, pérdidas fluviales y alcance espacial antes de calibrar.
2. Comparar baseline/acoplado con caudal consistente contra USGS, manteniendo
   proyecto, forcing, warm-up, periodo, outlet, motor y controles comunes.
3. Extender a varios años y separar desarrollo/calibración de evaluación para
   el caudal medio mensual del outlet en m³/s, fijado en la reformulación;
   estimar incertidumbre teniendo en cuenta dependencia temporal.
4. Publicar el nuevo experimento con su propio linaje y conectar comparación,
   reportes y visor a la misma evidencia.

El runner `run_final_south_fork.py` todavía calcula FSPM con humedad constante
asumida. Ejecutarlo no evalúa por sí solo toda la ruta hídrica actual.

## 6. Verificación de software

En la revisión de 2026-10-05 se ejecutaron:

- `venv/bin/python -m pytest -q tests` desde backend: **185 aprobadas, 4 omitidas**.
- `pnpm test` desde frontend: **31 aprobadas**.
- `pnpm exec tsc --noEmit --incremental false`: aprobado.

Son comprobaciones de software de aquella revisión; no incluyeron un nuevo
experimento SWAT+, evaluación USGS ni inspección visual en navegador. Las
corridas científicas del 2026-10-06 se documentan en las secciones anteriores;
en la tarea de longitudes no se ejecutaron suites de tests.
En la tarea posterior desde fuente se compilaron dos ejecutables idénticos,
se ejecutaron cuatro corridas científicas en pglocal y se compiló TypeScript
sin errores. No se ejecutaron suites de tests ni inspección visual en navegador.
En la auditoría meteorológica se inspeccionaron las corridas existentes,
se contrastaron productos externos y se compiló Python/TypeScript sin errores.
Los hashes de procedencia, métricas, caudales y frames permanecieron idénticos
después de adjuntar el diagnóstico a pglocal. No se ejecutaron nuevas simulaciones,
suites de tests ni inspección visual en navegador.

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
| Experimento multianual | `sf-multi-v1`: particiones congeladas, búsqueda física 12/12 y 96 meses pareados A/B publicados; referencia exploratoria por PBIAS. |
| ML observacional | `sf-ml-v1`: búsqueda igual de seis candidatos C/D; Ridge α = 10 seleccionado en VALIDATION, pesos/scalers TRAIN congelados y bundles registrados en pglocal. TEST evaluado sin reajuste. |
| Evaluación reservada | `sf-test-v1`: 60 meses TEST, diez publicaciones y 3.652 frames; bootstrap pareado 12 meses/2.000 réplicas. H1 no respaldada, también al excluir estimados. |
| Agua SWAT+ → FSPM | Estimación de humedad radicular desde `sw_ave` y `soils.sol`, bajo hipótesis de fracción de agua disponible uniforme en el perfil. |
| Planta → SWAT+ | Diez parámetros del registro vegetal `corn` en `plants.plt`; SWAT+ mantiene sus propias ecuaciones de agua y cultivo. |
| Persistencia | Frames JSONB PostgreSQL con clave temporal y SHA-256. |
| Visor | Tres escalas y estados fechados; mallas anatómicas y terreno ilustrativos/contextuales. |
| Diagnóstico observacional | Tres variantes estándar 2019 con lectura de caudal corregida; la pareja acoplada requiere su propia comparación. |
| Recorrido del agua | 37 cauces delineados con almacenamiento independiente de llanura y cierre numérico de red; balance de cuenca todavía parcial. |
| Meteorología / ET | Auditoría gridMET y comparación externa 2019; anomalías del warm-up corregidas en una variante controlada, ET y acuíferos diagnosticados. |
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
| `sf19-phys-ctrl-v1-reference` | Control con código actual sobre inputs físicos preparados | Reproduce exactamente los 365 caudales de la referencia; 365 frames. |
| `sf19-phys-fix-v1-reference` | Misma física y clima de warm-up corregido | RMSE mensual 8,079 m³/s; NSE −0,408; volumen 94,520 hm³; 365 frames. |
| `sf-multi-v1-cal-10` | Mejor candidato en CALIBRATION 2005–2012 | RMSE mensual 4,718 m³/s; NSE 0,649; PBIAS −40,605 %. Falla el criterio de sesgo; exploratorio. |
| `sf-ml-v1-c` / `sf-ml-v1-d` | Bundles residuales observacionales en PostgreSQL | RMSE de desarrollo VALIDATION 2,978 / 2,990 m³/s; no decisión de H1. |
| `sf-test-v1` | A/B/C/D en TEST 2021–2025, dataset `sf-test-v1-monthly` | RMSE A/B/C/D 3,695 / 3,579 / 2,749 / 4,517 m³/s. Reducción D/A −22,239 %, IC95 absoluto [−3,286; +1,871] m³/s; H1 no respaldada. |

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

La [entrega 1](PHYSICAL_REFERENCE_DELIVERY_1.md) corrige 1.062 registros de clima
del warm-up en una copia y ejecuta control/corrección en pglocal. El clima 2019
permanece idéntico; el volumen apenas aumenta 0,060 hm³. La referencia está
diagnosticada para iniciar calibración multianual de desarrollo, bajo manejo y
máscara de drenaje fijos; todavía no está calibrada ni validada. La mayor parte
de `esoil` ocurre con LAI bajo; el aporte acuífero es pequeño. El motor fija
`perco=0,1` en HRU drenadas y excluye esas HRU del ajuste de `perco` por calibración.
La red corregida cierra con residuo 1,686 m³; el balance de cuenca sigue parcial.

La [entrega 2](MULTIYEAR_EXPERIMENT_DELIVERY_2.md) fija después 12 candidatos
y separa CALIBRATION 2005–2012, TRAIN 2013–2017, VALIDATION de desarrollo
2018–2020 y TEST reservado 2021–2025. El ganador mejora el ajuste, pero falla
|PBIAS| ≤ 30 %: no es una referencia validada. B utiliza el contrato vegetal
derivado en 2010 y congelado antes de TRAIN/VALIDATION. La nueva copia corrige
también los cierres climáticos de 2020/2024; no se consultan resultados TEST.
Las 16 publicaciones A/B y la derivación vegetal 2010 tienen 6.209 frames
diarios en pglocal. CSV/Parquet, esquema y linaje están versionados y registrados
como dataset `sf-multi-v1-monthly-ab`: 192 filas, 96 meses pareados. Las 16
auditorías nativas cierran numéricamente la red; la contabilidad de cuenca sigue
parcial. En VALIDATION, RMSE A/B es 4,007/3,921 m³/s; son métricas de desarrollo.

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
- **ML:** los bundles históricos de runoff son sintéticos. Los nuevos C/D aprenden
  residuos contra USGS con predictores modelados; la inferencia mensual es retrospectiva.
  D queda ligeramente detrás de C en desarrollo y empeora su RMSE puntual
  frente a A en TEST. H1 no respaldada; C tiene menor RMSE puntual pero
  PBIAS +44,616 % e intervalo C/A que incluye cero.
  El pronóstico diario sobre playback aprende de simulación.

## 5. Siguiente etapa de investigación

El trabajo se organiza en cinco entregas; las cuatro primeras están completadas:

1. **Referencia física — completada:** corrección controlada del warm-up,
   reproducción, ET, suelos, drenaje, acuíferos, pérdidas fluviales y área.
2. **Experimento multianual — completado:** protocolo/particiones y escenario
   agrícola fijos; calibración acotada 12/12, calendarios por temporada y contrato
   vegetal 2010 congelado. Publicación A/B anual y exportaciones fechadas.
   Referencia exploratoria por incumplimiento de sesgo.
3. **ML — completada:** residual y alineación temporal reparados; protocolo ML,
   seis candidatos iguales por brazo, selección C/D exclusivamente en VALIDATION.
   Pesos TRAIN, referencias simples y artefactos congelados en pglocal.
   Véase [entrega 3](ML_RESIDUAL_DELIVERY_3.md).
4. **Evaluación de H1 — completada:** TEST 2021–2025, referencias TRAIN,
   bootstrap temporal pareado y sensibilidad a estimados. H1 no respaldada;
   no se retocaron pesos ni criterios. Véase [entrega 4](TEST_EVALUATION_DELIVERY_4.md).
5. **Gemelo funcional y paper — siguiente:** creación/ejecución/consulta/descarga sobre
   PostgreSQL, comparación/reportes/visor con el mismo linaje y paquete del artículo.

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
En la entrega 1 se ejecutaron dos corridas científicas en pglocal, con 365 frames
cada una, y se cotejaron reproducción diaria, corrección climática y balances.
La revisión de procesos lee los outputs y el código fuente del motor fijado.
En la entrega 2 se completaron 29 corridas científicas en pglocal: 12 candidatos,
una derivación vegetal y 16 publicaciones A/B. Se revisaron cobertura, soporte
USGS pareado, hashes, contrato vegetal congelado y 16 balances nativos.
Tres casos puros existentes de calendario/agregación/playback pasaron por
invocación directa, sin cargar el fixture SQLite temporal. Los módulos Python
modificados compilan; no se ejecutó la suite completa ni inspección del navegador.
En la entrega 3 se ajustaron doce candidatos sobre TRAIN y se seleccionaron C/D
por VALIDATION. Se cotejaron 96 inferencias por brazo entre entrenamiento,
bundle del laboratorio y backend; se registraron dos modelos externos y 17
artefactos en la misma base pglocal. No se ejecutó una suite de tests ni se
inspeccionó el navegador. En esa entrega TEST permaneció reservado.
En la entrega 4 se publicaron diez corridas A/B TEST con 3.652 frames y diez
auditorías nativas; las redes cierran numéricamente y el balance de cuenca
sigue clasificado como parcial. Se exportaron pares/predicciones mensuales,
se generaron 2.000 réplicas por variante y se registraron 12 artefactos en
`sf-test-v1-monthly`. El runner reutilizó los resultados congelados sin nuevas
consultas de caudal, corridas o evaluación. Los módulos añadidos compilan;
no se ejecutó una suite de tests ni se inspeccionó el navegador.

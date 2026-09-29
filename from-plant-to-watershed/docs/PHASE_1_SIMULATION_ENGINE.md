# Fase 1 — Motor de simulación multiescala

## Alcance

Esta fase pone en funcionamiento la ruta existente entre el FSPM simplificado y el ejecutable real SWAT+ para el proyecto experimental South Fork 2019. No cambia resultados archivados, no modifica el proyecto fuente, no calibra parámetros y no presenta el experimento CDL como reconstrucción histórica. No se modificó el frontend.

## Auditoría del estado anterior

Se revisaron los contratos del parser y el adaptador SWAT+, el acoplamiento en TwinCouplingEngine, las clases existentes PlantPopulation y PlantToFieldAggregator, los datasets de South Fork y los documentos de auditoría de las fases 3.4 y 3.5. La fase 3.5 ya había comprobado con copias instrumentadas que el formato decimal de los campos enteros podía interrumpir la lectura de plants.plt sin impedir que el ejecutable produjera algunos resultados. En ese estado, no había una prueba suficiente de que los diez parámetros FSPM llegaran al registro activo de maíz.

El origen de compatibilidad revisado es la etiqueta exacta SWAT+ 61.0.2.61 y su ejecutable local. La estructura Fortran de planta declara como enteros days_mat y mat_yrs (el encabezado de datos usa yrs_mat); la lectura de plants.plt usa una lectura list-directed. La comunidad vegetal carga plants_com y rot_yr_ini como enteros. Los lectores de manejo cargan los contadores de operaciones automáticas y programadas, y mes y día como enteros. time.sim y el primer registro de print.prt también contienen campos enteros. El código de compatibilidad valida estas columnas y formatos antes de iniciar cada proceso y corrige únicamente tokens decimales que sean matemáticamente enteros en la copia de trabajo.

Referencias de la versión exacta: [tipos de planta](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_data_module.f90), [lector plants.plt](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/plant_parm_read.f90), [lector de comunidad vegetal](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/readpcom.f90), [lector de management.sch](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/mgt_read_mgtops.f90), [lector de operaciones](https://raw.githubusercontent.com/swat-model/swatplus/61.0.2.61/src/read_mgtops.f90) y [documentación SWAT+ de management.sch](https://swatplus.gitbook.io/io-docs/introduction-1/landuse-and-management/management.sch).

### Componentes y frecuencias

| Componente existente | Salidas que realmente proporciona | Frecuencia y escala |
|---|---|---|
| FSPM SIMPLIFIED_FSPM, PlantPopulation | Altura, LAI, raíces, biomasa, fenología, transpiración y estrés por estado vegetal; agregados del dosel/campo | Paso diario durante cada calendario activo; plantas representativas de un modelo determinista |
| SWAT+ hru_pw_day | LAI, biomasa, rendimiento, crecimiento de biomasa, estrés de agua/aireación/temperatura/N/P/salinidad y fracción PHU si la columna está impresa | Diario por HRU |
| SWAT+ hru_wb_day | Precipitación, runoff, ET y componentes disponibles, percolación y almacenamiento inicial/promedio/final de agua en suelo | Diario por HRU |
| SWAT+ basin_wb_day | Términos de balance hídrico disponibles | Diario agregado a cuenca |
| SWAT+ channel_sd_day | flo_out y otros campos impresos disponibles | Diario por canal |
| SWAT+ mgt_out.txt | Operaciones, cultivo, HRU y fecha realmente ejecutados | Evento por HRU |

SWAT+ no imprime altura ni profundidad de raíces en la tabla vegetal de esta configuración. La fase 3.5 no podía proporcionar esos estados directamente desde hru_pw_day. El FSPM sí los calcula como estados del modelo simplificado. No se atribuyen esas variables de FSPM a SWAT+.

El proyecto local backend/data/phase34-cdl-2019/project tiene 32 HRU con evidencia CDL 2019 válida para la fracción de maíz. Es un caso experimental de manejo derivado de CDL con mayoría de maíz, no una reconstrucción histórica. La fracción CDL proviene del manifiesto adyacente; los pesos espaciales se calculan como área HRU por fracción de maíz.

## Cambios implementados

### Lectura segura de SWAT+

backend/app/services/swat_input_compatibility.py valida days_mat, yrs_mat, plt_cnt, rot_yr_ini, numb_ops, numb_auto, mes/día de operaciones, time.sim y el registro de control de print.prt. Si un campo es entero decimal exacto, por ejemplo 120.00000, lo escribe como 120 solo después de crear una copia aislada. Rechaza valores fraccionarios, no finitos, mal formados o archivos con esquema inesperado. Registra antes/después, archivo y línea, hashes, versión fuente y evidencia de que el valor numérico no cambió. No cambia parámetros científicos.

backend/app/services/swat_plus_adapter.py valida los recursos y archivos de clima declarados antes de crear la ejecución; prepara cada proyecto SWAT+ en un workspace nuevo; programa allí el periodo, calentamiento y salidas diarias; limpia solo outputs obsoletos de esa copia; normaliza y vuelve a validar los campos enteros; aplica el mapper solo dentro de la copia; verifica success.fin actual y outputs generados después del inicio. Todo error de copia, preparación, ejecución, marcador de éxito o lectura se registra como FAILED.

### Calendario y clima compartidos

backend/app/services/swat_executed_calendar.py convierte PLANT y HARV/KILL de mgt_out.txt en calendarios por HRU. No aplana las fechas distintas. Para reducir ejecuciones FSPM, agrupa HRU solo cuando coinciden las fechas de plantación y cosecha, y guarda HRU, peso y fechas de cada grupo.

backend/app/services/executed_calendar_fspm.py ejecuta una población FSPM por grupo de fechas, con forcing diario de las estaciones asignadas en hru.con.wst. Usa Tmax/Tmin para temperatura media, precipitación, radiación solar y humedad relativa en las unidades que consume el FSPM. El agregado de campo pondera área HRU por fracción CDL de maíz. CO2=400 ppm y humedad volumétrica constante de 24% son supuestos explícitos del FSPM. SWAT+ conserva su propio almacenamiento de agua en mm.

backend/app/services/swat_coupled_runner.py hace primero una ejecución real de SWAT+ para obtener los eventos. Después ejecuta FSPM, mapea el contrato estacional en una copia, repite SWAT+ y verifica que la firma por HRU de siembra/cosecha coincida con el calendario usado por FSPM. La ejecución solo se acepta tras convergencia. También compara el forcing diario efectivo de la copia SWAT+ con el forcing FSPM para las HRU y fechas utilizadas.

El mapper conserva el mecanismo existente y modifica únicamente el registro de la planta objetivo en plants.plt. El resumen estacional dedicado mapea LAI y su curva, altura máxima, profundidad radicular máxima limitada por el perfil de suelo cuando existe, ext_co y bm_e. No escribe ET, escorrentía, almacenamiento, uptake ni estrés en SWAT+.

### Datos de salida

backend/app/services/swat_plus_parser.py normaliza variables y unidades, conserva filas por HRU/planta/canal/evento, distingue almacenamiento inicial/promedio/final, reconoce m3/s y no completa variables ausentes. Rechaza fechas o claves espaciales duplicadas y reporta cobertura de cada variable.

backend/app/services/playback_builder.py integra variables disponibles por escala en playback. No inventa altura/raíz SWAT+, no convierte mm de almacenamiento a humedad volumétrica ni convierte caudal a profundidad.

backend/scripts/run_phase1_south_fork_2019.py ejecuta el mismo flujo normal y exporta tablas CSV fechadas y un manifiesto con unidades, escala, fuente, clasificación, hashes y cobertura. Los proyectos de ejecución se almacenan bajo backend/data/phase1-south-fork-2019/workspaces y se excluyen de Git; los artefactos reducidos de resultados quedan bajo results.

## Calendario de manejo y sincronización

La auditoría de fase 3.5, usando las salidas instrumentadas existentes, encontró 32 HRU de maíz: 26 eventos PLANT el 15 de mayo de 2019 y seis el 16 de mayo. Las fechas HARV/KILL difieren entre HRU: 27 de agosto (2), 28 de agosto (7), 29 de agosto (6), 30 de agosto (11), 31 de agosto (2), 1 de septiembre (3) y 3 de septiembre (1). También aparecen eventos de cultivos no maíz que no entran al calendario FSPM de maíz.

Son operaciones ejecutadas simuladas, no observaciones. La ruta normal vuelve a obtenerlas de mgt_out.txt y produce grupos con cada pareja de fechas distinta. Si varias HRU tienen las mismas fechas, sus plantas FSPM se agrupan para reducir cálculo, pero no se les asigna un día representativo diferente al que ejecutó SWAT+. El evento se aplica a la fecha completa porque la salida no contiene un instante intradiario.

## Reproducción y resultados de South Fork 2019

Comando usado desde la raíz del repositorio: backend/venv/bin/python backend/scripts/run_phase1_south_fork_2019.py --run-id phase1-sf-2019-v3

Configuración: ejecutable local SWAT+ 61.0.2.61; periodo visible 2019-01-01 a 2019-12-31; impresión diaria; calentamiento de 19 años desde 2000 con nyskip=19; seed 42; 1,000 plantas representativas por calendario FSPM; outlet channel GIS 153. El calentamiento produce estados hidrológicos previos, pero no añade fechas al periodo FSPM ni a las tablas visualizadas.

Estado inicial: preflight READY, 32 HRU de cultivo activo, 532 tokens que requieren normalización textual segura y 2.85 GB como límite inferior para cuatro copias aisladas. La primera ejecución de calendario terminó con código 0, success.fin actual y outputs basin_wb_day, channel_sd_day, hru_wb_day, hru_pw_day y mgt_out.txt. El registro contiene las correcciones por archivo/línea, su antes/después y hashes.

El primer intento del runner FSPM quedó marcado FAILED antes del segundo SWAT+: el agregado omitía dos rasgos estáticos que consume el mapper. El error y su traceback permanecen en el run_status.json local del intento phase1-sf-2019-v1, dentro del área ignorada. El agregado se corrigió y se añadió una prueba; la ejecución aceptada usa un ID nuevo.

Ejecución aceptada: phase1-sf-2019-v3; manifest status COMPLETED; el fingerprint del contenido del proyecto original coincide antes y después. SWAT+ y FSPM cubren del 1 de enero al 31 de diciembre con 365 fechas. El calendario converge en una iteración acoplada. El forcing efectivo de la copia SWAT+ coincide con el forcing FSPM en las 365 fechas y variables comprobadas. Se aplicaron diez actualizaciones al registro corn de plants.plt: lai_pot, frac_hu1, lai_max1, frac_hu2, lai_max2, hu_lai_decl, can_ht_max, rt_dp_max, ext_co y bm_e.

Se hicieron dos ejecuciones completas consecutivas con el mismo proyecto, parámetros, fechas y seed (v2 para verificar el acoplamiento y v3 para validar la exportación final). Los checksums de los outputs SWAT+ acoplados y los hashes de las trayectorias FSPM por grupo y las muestras vegetales coinciden. v3 conserva una sola columna date y amplía el parser/exportación de canales con storage, entrada/salida y estado térmico impresos por SWAT+.

Después de completar v3 se añadieron al paquete de resultados los dos informes de compatibilidad que ya existían en sus workspaces aislados y se normalizaron los finales de línea de los CSV exportados; no se volvió a ejecutar SWAT+ ni se alteraron valores o series. Cada informe detalla 532 normalizaciones exactas de enteros en `plants.plt`, con valores numéricos y parámetros científicos preservados. El manifiesto conserva el fingerprint capturado durante la ejecución y separa el fingerprint del runner actualizado para exportación reproducible. `run_status.json` deja constancia de esta actualización del manifiesto.

El calendario ejecutado tiene siete grupos de fechas entre 32 HRU: siembra el 15 de mayo para 26 HRU y el 16 de mayo para seis; cosecha/kill entre el 27 de agosto y el 3 de septiembre en siete fechas. La salida contiene 72 eventos de manejo (incluye otros cultivos), 365 filas de cuenca, 13,140 filas de balance HRU, 13,140 filas de estado vegetal HRU y 13,505 filas de 37 canales. El FSPM produce 365 registros fechados; hay 112 días con al menos una cohorte activa entre el 15 de mayo y el 3 de septiembre, 754 filas calendario-día y 7,540 estados de slots representativos (10 capturas por cada población de 1,000 y día activo).

Las cinco series hidrológicas diarias requeridas están completas: precipitación, escorrentía generada, evapotranspiración, agua del suelo y caudal. El parser no registró advertencias por fecha duplicada, periodos ausentes, unidades inesperadas, valores no finitos ni flujos negativos. Las sumas impresas de la cuenca para 2019 son 1,080.817 mm de precipitación, 108.086 mm de escorrentía generada, 849.866 mm de ET y 121.339 mm de percolación. El caudal medio diario del canal outlet 153 es 1.96379674 m3/s; el almacenamiento de agua en suelo varía entre 262.534 y 447.499 mm. Son resultados de esta corrida experimental, no una comparación observacional.

Durante los días activos, el agregado FSPM varía de 0.0916 a 5.0032 m2/m2 de LAI, de 0.0517 a 2.6319 m de altura, de 0.0939 a 1.2002 m de profundidad radicular y de 0 a 380.270 g/planta de biomasa estimada. La humedad FSPM permanece en 24 vol% como supuesto; el estrés es constante porque la humedad simplificada también lo es. Este estado no se presenta como retroalimentación de SWAT+.

Artefactos en backend/data/phase1-south-fork-2019/results/phase1-sf-2019-v3/:

- manifest.json y run_status.json: versión ejecutable, hashes, warmup, convergencia, integridad y catálogo de variables.
- basin_daily.csv, hru_daily.csv, plant_hru_daily.csv y channel_daily.csv: salidas SWAT+ reales a cada escala.
- management_events.csv y executed_hru_calendar.csv: eventos modelados y calendario final por HRU.
- climate_daily.csv: forcing diario usado, con origen de datos marcado sin verificar.
- fspm_field_daily.csv y fspm_calendar_group_daily.csv: estados agregados fechados.
- fspm_plant_samples_daily.csv: estados de slots FSPM representativos, no individuos observados.
- calendar.json, coupling_iterations.json, parameter_mapping.json y fspm_provenance.json.
- calendar-baseline-input-compatibility.json y coupled-final-input-compatibility.json: registro íntegro de correcciones de formato para cada copia ejecutada de SWAT+.

El manifiesto final cataloga 18 artefactos con checksum, tamaño, columnas, escala, procedencia y campos temporales cuando corresponden.

manifest.json cataloga tablas y registros con checksum, columnas, escala, procedencia y campos temporales; cada variable indica unidad, escala, fuente, frecuencia/fecha y clasificación SIMULATED, DERIVED o ASSUMED. También registra el SHA-256 de los archivos fuente del motor usados en el runner, parser, acoplamiento, FSPM y playback. El forcing meteorológico se marca SOURCE_UNVERIFIED porque el manifiesto del proyecto no permite afirmar si son observaciones, reanálisis u otra fuente. Los parámetros heterogéneos y coordenadas de slots FSPM se clasifican ASSUMED; los estados calculados, SIMULATED; y los agregados ponderados, DERIVED. Si una columna no está disponible, queda ausente/parcial en vez de generarse mediante sustitución sintética. Un fallo deja run_status.json como FAILED con excepción y traceback.

## Variables y escalas disponibles para fase 2

| Escala/interfaz | Variables disponibles | Unidades o límites |
|---|---|---|
| Planta FSPM, por fecha y grupo de calendario | LAI, altura, profundidad y distribución de raíz, biomasa/rendimiento estimados, hojas, etapa fenológica, GDD, cobertura, transpiración, uptake y estrés; posición y parámetros de cada slot | m, cm, m2/m2, g/planta, mm/día, fracción y degC día según variable; slot representativo del modelo |
| Campo FSPM agregado, por fecha | Altura media, LAI y distribución, raíces y distribución, biomasa/rendimiento, ET/transpiración, estrés, cobertura, fracción de área activa y etapa | Valores derivados del FSPM ponderados por grupo de calendario/área maíz; humedad = supuesto constante 24 vol% |
| HRU SWAT+ diario | Precipitación, runoff, ET y componentes, percolación, agua de suelo inicial/promedio/final; LAI, biomasa, rendimiento, PHU y factores de estrés si aparecen en hru_pw_day | Agua en mm; flujos de agua en mm/día; LAI m2/m2; biomasa/rendimiento kg/ha; factores como fracciones |
| Canal SWAT+ diario | Área contribuyente, volúmenes de precipitación/evaporación/seepage, almacenamiento de agua, inflow y flo_out, temperatura del agua; se exportan todos los canales y su GIS ID | Área ha; volúmenes/storage m3 por paso diario; caudales m3/s; temperatura degC. No son profundidad ni nivel |
| Cuenca SWAT+ diaria | Precipitación, runoff, ET, percolación, almacenamiento y salida de canal seleccionada cuando exista cobertura | mm o mm/día por columna; caudal m3/s |
| Eventos/calendario por HRU | PLANT y HARV/KILL, cultivo y fecha simulados; pares de fechas que forman cohortes FSPM | Día ISO, HRU, cultivo y operación |
| Forcing diario de HRU asignadas | Temperatura, precipitación, radiación, humedad relativa; viento/PET si hay archivos; CO2 | degC, mm/día, MJ/m2/día, %, m/s, mm/día, ppm; origen meteorológico sin declarar en manifest del proyecto |

Para la interacción planta-suelo-agua, los inputs estáticos originales relacionan hru.con (área, latitud/longitud, elevación y estación wst) con hru-data.hru (topografía, hidrología, perfil soil, manejo y soil-plant initialization). soils.sol contiene número de capas nly, grupo hidrológico, profundidad total dp_tot, profundidades dp por capa, densidad bd, agua disponible awc, conductividad soil_k, carbono, textura, roca, albedo, erodabilidad, salinidad y pH cuando están definidos. hru_wb_day imprime estados agregados sw_init, sw_final, sw_ave y sw_300 en mm; no se configuró una serie temporal de humedad por capa. chandeg.con da IDs GIS, área contribuyente y enlaces/topología; channel-lte.cha enlaza parámetros de canal. channel_sd_day da flo_stor en m3 y caudales, pero esos archivos no justifican una conversión a nivel/profundidad sin geometría hidráulica de sección.

Interfaces listas para consumo:

| Interfaz | Entrada | Resultado disponible |
|---|---|---|
| SwatOutputParser(...).parse(run_directory, start_date, end_date) | Copia de TxtInOut ejecutada y periodo | SwatParsedOutput: records, hru_results, plant_results, channel_results, management_events, cobertura/unidades y archivos origen |
| SwatExecutedCropCalendar.from_events(events, *, crop, start_date, end_date, hru_weights) | Eventos parseados de mgt_out.txt y pesos HRU | Calendarios y grupos por fecha; consulta group_for_hru(hru_id) |
| run_fspm_on_executed_calendar(*, project, calendar, start_date, end_date, plant_count, seed) | Calendario SWAT+, proyecto y forcing | Estados FSPM diarios por grupo/campo, muestras de plantas, clima y procedencia |
| run_coupled_swat_with_executed_calendar(adapter, config, *, target_crop, fspm_crop, plant_count, seed) | Contrato SwatPlusRunConfig | Corrida acoplada, outputs SWAT+, calendario, estados FSPM, parámetros escritos y comprobación de convergencia |
| PlaybackFrame de playback_builder.py | Registros SWAT+ y estado FSPM fechados | Frame para una fecha con field, hydrology y listas de HRU/canales/plantas cuando existan |
| Manifiesto fase 1 y tablas CSV | run_id y fecha/campo espacial | Catálogo de unidades, clasificación, disponibilidad, checksums y valores por fecha/escala |

La fase 2 puede seleccionar una fecha y resolver estados de campo, planta representativa, HRU y canal sin mezclar sus escalas.

La humedad FSPM debe seguir identificándose como asumida mientras no se conecten estados SWAT+ por capa con la profundidad/propiedades de soils.sol y una conversión física válida a humedad volumétrica de zona radicular. El almacenamiento SWAT+ en mm se conserva como variable distinta. El caudal en m3/s y el almacenamiento del canal en m3 tampoco se convierten a nivel o profundidad sin una sección hidráulica válida.

## Pruebas

La prueba unitaria nueva cubre normalización sin cambio de valor científico, rechazo de campos fraccionarios, calendario distinto por HRU, forcing ponderado por estación/área/CDL, retención de rasgos FSPM para el mapper, una fecha canónica en exportación, canal con storage/caudales sin conversión a profundidad y prohibición de crear altura SWAT+ o humedad porcentual desde almacenamiento mm. También se ejecutan las pruebas de parser, preflight, copia aislada, control de success.fin, playback y registro de deltas.

Resultado final: 52 passed, 6 deselected entre los cinco archivos de prueba relevantes; py_compile pasó para runner y servicios. Las seis pruebas no ejecutadas son tres tests API/persistencia con base de datos y tres tests de integración API que duplican la ejecución SWAT real del runner o dependen de entorno. El fixture global de base de datos no terminó de inicializarse localmente, por lo que el estado de esas pruebas es NOT_EXECUTED. El runner completo FSPM/SWAT+ sí se ejecutó aparte con recursos locales y no requiere PostgreSQL.

## Limitaciones que siguen abiertas

- El proyecto de fase 3.4 es experimental y no representa manejo histórico validado.
- El origen de los archivos meteorológicos no está identificado en el manifiesto local; se conservan sin alterarlos y su categoría se marca SOURCE_UNVERIFIED.
- El FSPM existente no recibe retroalimentación de humedad de suelo SWAT+; conserva su supuesto de 24 vol%.
- La altura y la raíz son estados calculados por el FSPM, no salidas disponibles de SWAT+ en la tabla hru_pw.
- El acoplamiento es un contrato de parámetros vegetales de una dirección (FSPM hacia plants.plt); no sustituye hidrología SWAT+ ni integra agua bidireccional.
- No se presenta RMSE ni se intenta optimizar ajuste científico.

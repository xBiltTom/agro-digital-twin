# Entrega 2 — Experimento multianual South Fork

Fecha: **2026-10-06**. Experimento: `sf-multi-v1`. Corridas y playback en
**pglocal / digitaltwin**, con el mismo propietario, cuenca y escenario neutral
que las entregas anteriores. Las referencias históricas permanecen archivadas.
Entrega completada: 29 corridas, 6.209 frames diarios y cuatro artefactos
registrados en el dataset `sf-multi-v1-monthly-ab`.

## 1. Protocolo y exposición previa

El [protocolo v1](../research_domain/south_fork_multiyear_protocol_v1.json)
se copió al directorio de ejecución antes de iniciar la búsqueda. Fija:

| Partición | Años | Uso |
| --- | --- | --- |
| WARMUP | 2000–2004 | Inicialización de la calibración. |
| CALIBRATION | 2005–2012 | Selección de parámetros físicos: 96 meses. |
| TRAIN | 2013–2017 | Futuro ajuste de modelos residuales: 60 meses. |
| VALIDATION | 2018–2020 | Selección de desarrollo: 36 meses. |
| TEST | 2021–2025 | Reservado hasta la entrega 4. |

2018–2020 ya se exploraron en experimentos históricos; VALIDATION no es ciega.
También existió exposición previa a 2015–2017 y a la cobertura/QC del archivo
USGS completo. No se encontraron evaluaciones de resultados 2021–2025 en los
reportes experimentales o las corridas inventariadas; esto no demuestra ausencia
de exposición fuera del repositorio. Esta entrega no consulta ni exporta sus
caudales observados.

Se fija D vs A como contraste primario, RMSE mensual, caudal corregido
`max(0, Q_física + residual)`, bootstrap circular pareado de bloques de 12 meses,
2.000 réplicas, semilla 42 e intervalo del 95 %. H1 requerirá un intervalo de
reducción de RMSE enteramente positivo. La familia de ML, features, presupuestos
iguales C/D y fórmulas concretas de las referencias simples se fijarán antes
de entrenar en la entrega 3. Aquí H1 sigue **NOT_EVALUATED**.

## 2. Física, clima y calibración acotada

Se conserva el motor desde fuente, commit
`77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d`, y SHA-256 del ejecutable
`56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d`.
La copia de entrada hereda la corrección climática de la entrega 1 y corrige
224 registros adicionales del 31 de diciembre de 2020 y 2024 contra la caché
gridMET archivada. Reparar meteorología de 2024 no usa resultados de caudal
de TEST. Los manifiestos conservan valores anteriores/nuevos, recibos y hashes.

ESCO, profundidad mínima del acuífero somero para retorno y tiempo del drenaje
son ajustes exploratorios; no estimaciones hidráulicas locales observadas.
Se mantienen suelos, geometría, área, cobertura del drenaje, PET y `perco`.
Este motor impone `perco=0,1` en HRU drenadas y las excluye de su calibración.
El uso del suelo de maíz CDL 2019 y la máscara experimental de tile drainage
permanecen fijos: no se reconstruyen rotaciones agrícolas históricas.

La primera etapa cruza ESCO `{0,05; 0,5; 0,95}` y `flo_min` `{3; 5; 8}` m,
con `t_fc=24` h. La segunda conserva ESCO/flo_min del primer ganador y prueba
`t_fc={6; 12; 48}` h. Criterio: menor RMSE mensual CALIBRATION, desempate por ID.
Se ejecutaron **12/12 candidatos** en PostgreSQL, con 96 outputs mensuales
por candidato; el playback se reserva a las publicaciones diarias finales.

| Candidato | ESCO | flo_min (m) | t_fc (h) | RMSE (m³/s) | NSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 0,05 | 3 | 24 | 4,996 | 0,606 |
| 02 | 0,05 | 5 | 24 | 4,982 | 0,609 |
| 03 | 0,05 | 8 | 24 | 4,729 | 0,647 |
| 04 | 0,5 | 3 | 24 | 7,886 | 0,019 |
| 05 | 0,5 | 5 | 24 | 7,734 | 0,057 |
| 06 | 0,5 | 8 | 24 | 7,602 | 0,089 |
| 07 | 0,95 | 3 | 24 | 8,389 | −0,110 |
| 08 | 0,95 | 5 | 24 | 8,247 | −0,073 |
| 09 | 0,95 | 8 | 24 | 8,136 | −0,044 |
| **10** | **0,05** | **8** | **6** | **4,718** | **0,649** |
| 11 | 0,05 | 8 | 12 | 4,721 | 0,649 |
| 12 | 0,05 | 8 | 48 | 4,748 | 0,645 |

El ganador `sf-multi-v1-cal-10` tiene **PBIAS −40,605 %**. Cumple NSE ≥ 0,
pero incumple el límite predefinido de |PBIAS| ≤ 30 %. Se conserva como
**BUDGET_EXHAUSTED_EXPLORATORY_REFERENCE**. No se amplía el presupuesto ni se
declara una referencia validada. Que los parámetros seleccionados estén en
los extremos del rango también limita su interpretación física.

## 3. Calendarios y contrato vegetal

El lector conserva todas las temporadas completas por HRU, empareja los eventos
de siembra y cosecha y rechaza secuencias incompletas o solapadas. La
[auditoría nativa multianual](../research_domain/south_fork_executed_calendar_multiyear_v1.json)
recupera 44 grupos y ocho temporadas 2005–2012 en cada una de las 32 HRU de maíz.
Las firmas de convergencia incluyen todas las temporadas; la población FSPM
se reinicia por temporada con 1.000 plantas/grupo y semilla 42.

Los agregados diarios usan los grupos del año correspondiente. El alcance
publicado es maíz con una temporada anual completa; no se extiende el contrato
a rotaciones o a cultivos con temporadas que cruzan años.

La corrida `sf-multi-v1-b-parameters-2010` deriva los diez parámetros vegetales
en el año 2010, preseleccionado dentro de CALIBRATION. El resumen congelado tiene
LAI potencial 5,028, altura máxima 2,631 m y raíz máxima 1,200 m. Es un contrato
modelado simplificado: 2010 no fue demostrado como año representativo ni se
validó la morfología con observaciones. TRAIN/VALIDATION no regeneran ese resumen.

La ponderación efectiva de esta copia usa **área de HRU de maíz**. No hay un
manifiesto adyacente con fracciones CDL por HRU, por lo que no se aplican
ponderaciones fraccionales de cobertura. El uso del suelo estático sí proviene
del escenario preparado con CDL; ambas cosas se distinguen en la procedencia.

## 4. Parejas A/B y exportaciones

A es SWAT+ estándar; B comparte sus parámetros físicos y reemplaza únicamente
el registro vegetal `corn` de `plants.plt` mediante el resumen FSPM congelado.
Cada año 2013–2020 se publica por separado, pero el motor vuelve a simular desde
2000 con los inputs congelados de su brazo. No reinicia almacenes el 1 de enero
del año publicado. Esa coordinación reduce memoria manteniendo el historial.

IDs: `sf-multi-v1-a-{año}` y `sf-multi-v1-b-{año}`. El linaje coteja inputs,
meteorología completa, warm-up, fechas y outputs nativos. B sigue la ruta
operativa de acoplamiento y publica estados diarios FSPM con agua SWAT+; fijar
el contrato vegetal evita ajustar sus parámetros con años de evaluación.

La corrección de anotaciones del playback conserva la temporada conocida en
HRU inactivas. Solo actualiza `crop` y `calendar_id` antes nulos de estas nuevas
corridas; guarda hashes anterior/posterior y comprueba que el resto del payload
permanezca idéntico. Los frames históricos 2019 no se reescriben.

El paquete mensual tiene **192 filas = 96 meses pareados × 2 brazos**, no 192
observaciones independientes. CSV, Parquet, esquema y linaje se versionan en
`research_domain/multiyear_v1/` y se registran como artefactos derivados en
pglocal. El [reporte de la entrega](../research_domain/south_fork_multiyear_delivery_2_v1.json)
conserva selección, métricas, IDs y hashes.

- Q observado y Q físico usan exactamente los mismos días USGS aprobados.
  Cobertura mínima mensual 90 %; A/A,e se incluyen y se cuentan los estimados.
- El 20 de agosto de 2017 está ausente: ese mes usa 30/31 días para ambos Q.
  No hay imputación. Clima y estados modelados siguen usando el mes completo.
- El residual es `Q_obs − Q_física`. Las variables derivadas del target/QC
  observacional no deben entrar como predictores.
- Flujos en mm se suman; estados y clima se promedian. Percolación no se
  presenta como infiltración. Humedad de perfil procede de `sw_ave`.
- A tiene FSPM nulo. B tiene cero de estructura/transpiración cuando todo el
  cultivo está inactivo, estrés nulo y columnas de disponibilidad/actividad.
  Raíz, biomasa y transpiración FSPM son medias de los grupos activos;
  LAI incorpora el área de maíz inactiva. No equivalen a ET de toda la cuenca.
- El predictor con clima/estado del mes completo es retrospectivo, no un
  pronóstico anterior al mes. La comparación excluyendo USGS estimado queda
  para la evaluación secundaria con soporte común recalculado.

Las métricas TRAIN/VALIDATION se conservan en el reporte como diagnóstico de
desarrollo. Los balances de red son comprobaciones numéricas; la contabilidad
de cuenca permanece parcial y no valida por sí misma la hidrología.

| Partición/brazo | Meses | RMSE (m³/s) | NSE | PBIAS (%) |
| --- | ---: | ---: | ---: | ---: |
| TRAIN A | 60 | 5,747 | 0,134 | −48,088 |
| TRAIN B | 60 | 5,644 | 0,165 | −46,447 |
| VALIDATION A | 36 | 4,007 | 0,699 | −29,336 |
| VALIDATION B | 36 | 3,921 | 0,711 | −28,027 |

El menor sesgo de VALIDATION no reabre el criterio de aceptación fallido en
CALIBRATION. Son resultados de desarrollo; no prueban H1 ni validan fisiología.

## 5. Ejecución y siguiente entrega

Desde `backend/`, con la fuente física, cachés y ejecutable disponibles:

```bash
venv/bin/python scripts/run_south_fork_multiyear.py --phase all
venv/bin/python scripts/package_south_fork_multiyear.py
```

El runner reutiliza IDs completos compatibles y rechaza IDs incompletos o
incompatibles. No sobreescribe una corrida fallida ni crea otra base de datos.
Los workspaces/logs pesados quedan en `data/baseline-diagnostic-multiyear-v1/`.
El paquete versionado permite leer los datos sin volver a ejecutar SWAT+.

El playback usa la API existente, con autenticación del propietario:

```text
GET /api/v1/simulations/sf-multi-v1-b-2013/playback?date=2013-07-15&resolution=DAILY
```

Se compilaron los módulos Python modificados y pasaron tres casos puros
existentes de calendario, agregación FSPM y variables HRU del playback, invocados
directamente sin cargar el fixture SQLite temporal. Los hashes del paquete y
el esquema común CSV/Parquet se cotejaron con el reporte. No se ejecutó la
suite completa ni inspección del navegador. La unificación de creación, comparación, reportes
y visor corresponde a la entrega 5.

La **entrega 3** preparará residual y alineación temporal, fijará features y
búsquedas comparables C/D, entrenará solo en TRAIN y seleccionará en VALIDATION.
La referencia con sesgo pendiente debe acompañar todo resultado posterior:
una mejora ML contra ella no demuestra fisiología válida ni cierre hídrico.

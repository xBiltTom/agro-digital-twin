# Reformulación experimental — From Plant to Watershed

**Versión:** 0.1 · **Fecha:** 2026-10-06.
**Estado:** orientación acordada; protocolo pendiente de congelar antes de la
evaluación final. Este documento no declara nuevas corridas ni resultados.

## 1. Relación con la ficha original

[project_framework.md](project_framework.md) conserva la ficha técnica del
profesor y el tema de investigación. Este documento complementa su ejecución
con un alcance viable para el primer artículo: **planta–suelo–cuenca, SWAT+,
modelo vegetal simplificado y aprendizaje automático**.

Para próximas iteraciones:

- La ficha original define la dirección temática y las extensiones deseadas.
- Esta reformulación define la pregunta experimental y las decisiones del primer
  estudio. No debe interpretarse el alcance completo de la ficha como implementado.
- [CURRENT_STATE.md](docs/CURRENT_STATE.md) describe código, experimentos y límites
  operativos; los contratos de [acoplamiento](docs/FSPM_SWAT_PLUS_COUPLING.md) y
  [playback](docs/TWIN_PLAYBACK_CONTRACT.md) definen las interfaces existentes.
- Toda modificación de hipótesis, target, particiones o comparadores se registra
  con fecha y motivo; después de observar TEST no se redefine el protocolo para
  favorecer un resultado.

## 2. Problema y contribución buscada

SWAT+ ya representa crecimiento vegetal e hidrología. La pregunta no es si
puede añadirse una planta 3D, sino **qué valor añadido aporta una representación
vegetal externa y una corrección ML a la simulación hidrológica**.

Se investigará ese valor mediante comparaciones controladas contra caudal USGS,
separando el aporte del FSPM simplificado del aporte del ML. El gemelo permite
ejecutar, almacenar y explorar los estados por escala y fecha; su apariencia
gráfica no constituye evidencia de precisión física.

La novedad debe establecerse mediante revisión bibliográfica. No se adopta sin
evidencia la afirmación de que no existen frameworks relacionados. Hay
antecedentes de vegetación/hidrología y calibración con teledetección; la
contribución debe precisar mecanismo, diseño de ablación, reproducibilidad y
condiciones donde la integración resulta útil o limitada.

## 3. Objetivo y alcance del primer artículo

**Objetivo general:** desarrollar y evaluar un framework multiescala que integre
un modelo vegetal simplificado, SWAT+ y una corrección hidrológica mediante ML,
para representar la dinámica planta–cuenca y evaluar el caudal en una cuenca
agrícola.

Objetivos específicos:

1. Preparar un experimento reproducible con clima, suelo, manejo y observaciones
   trazables, manteniendo las condiciones compartidas entre comparadores.
2. Generar estados vegetales e hidrológicos fechados mediante SWAT+–FSPM.
3. Entrenar y seleccionar en el laboratorio un modelo de corrección de caudal.
4. Evaluar el sistema físico e híbrido en años independientes y cuantificar
   diferencias, incertidumbre y límites.
5. Integrar las predicciones ML en la plataforma conservando por separado el
   resultado físico y el asistido, con sus unidades y procedencia.

El primer estudio será una **evaluación retrospectiva multianual en South Fork
Iowa River, USGS 05451210**. Una sola cuenca permite un estudio de caso temporal,
no demostrar generalización espacial a todo el Corn Belt.

La salida primaria será el **caudal medio mensual del outlet en m³/s**, distinto
de la escorrentía superficial en mm. Los cálculos físicos y el playback pueden
seguir siendo diarios; la corrección mensual no se interpolará para fabricar
estados diarios. El uso de clima/estados del mes completo es propio de esta
evaluación retrospectiva, no de un pronóstico emitido antes de ese mes.

El sistema se describe como gemelo orientado a simulación y reproducción de
estados. Monitoreo en tiempo real, asimilación operacional y pronóstico con
meteorología futura son extensiones que requieren contratos distintos.

## 4. Hipótesis y preguntas secundarias

Sea A el SWAT+ estándar y D el sistema SWAT+–FSPM asistido por ML. Definimos:

```text
ΔRMSE = RMSE_A − RMSE_D
mejora_relativa = 100 × (RMSE_A − RMSE_D) / RMSE_A
```

La mejora relativa queda indefinida si RMSE_A es cero.

- **H0:** el sistema completo no reduce el RMSE del caudal medio mensual frente
  a SWAT+ estándar en los años de evaluación independientes (ΔRMSE ≤ 0).
- **H1:** el sistema completo reduce ese RMSE (ΔRMSE > 0).

Se retira del primer protocolo la exigencia no justificada de **≥15 %** y la
promesa conjunta de mejor rendimiento espacial. Se reportan efecto absoluto,
relativo e incertidumbre; una diferencia positiva puntual no basta para afirmar
una mejora robusta. La regla inferencial y cualquier umbral de relevancia
práctica deben justificarse antes de evaluar TEST.

Preguntas secundarias:

1. ¿Qué diferencia produce el FSPM sin ML?
2. ¿Qué diferencia produce ML sobre cada configuración física?
3. ¿La información vegetal aporta valor adicional al sistema asistido por ML?
4. ¿Cambian las conclusiones por año, temporada o tratamiento de valores USGS
   estimados, definidos antes del análisis correspondiente?

Si se consigue LAI independiente, se añade una evaluación vegetal secundaria
con calidad, escala y periodos explícitos. Mejorar el caudal no valida por sí
solo raíces, estrés, biomasa ni fisiología.

## 5. Diseño de comparación y atribución

| Brazo | Configuración | Función |
| --- | --- | --- |
| A | SWAT+ estándar | Referencia física con parámetros vegetales tabulados. |
| B | SWAT+–FSPM simplificado | Efecto del acoplamiento sin ML. |
| C | SWAT+ estándar + corrección ML | ML sin acoplamiento FSPM. |
| D | SWAT+–FSPM + corrección ML | Sistema completo. |

- **D vs A:** contraste primario del sistema completo.
- **B vs A:** efecto del acoplamiento físico evaluado.
- **C vs A y D vs B:** aporte de las correcciones ML.
- **D vs C:** aporte total de la integración vegetal bajo configuraciones
  híbridas comparables; no identifica por sí solo cada mecanismo individual.

Una ablación adicional, con/sin features vegetales sobre el mismo brazo físico,
puede aislar su valor predictivo para ML. Los contrastes secundarios se
identifican como tales y no se promueven retrospectivamente a resultado primario.

Compartir cuenca, forcing, fechas, outlet, warm-up, esquema de manejo, controles
de impresión y compatibilidad de inputs. Comparar sobre las mismas fechas
válidas. La variante experimental CDL debe ser común a los brazos: comparar
maíz acoplado contra manejo genérico distinto confundiría los efectos.

Primero revisar/calibrar una referencia razonable usando solo el periodo de
desarrollo. Para aislar el acoplamiento, conservar parámetros hidrológicos
compartidos entre A/B. C/D necesitan presupuestos de búsqueda, familias de
algoritmos y reglas de selección comparables. Todo cambio de manejo o de
parametrización se registra, no se oculta como efecto del FSPM.

## 6. Papel obligatorio del laboratorio ML

`agro-digital-twin-st` es el laboratorio de preparación, entrenamiento,
comparación y exportación del modelo campeón. `from-plant-to-watershed` es su
consumidor para inferencia y persistencia. El ML participa en una función
hidrológica concreta; no necesita sustituir toda la planta, HRU y red de canales.

El aprendizaje residual propuesto es:

```text
Entrenamiento: residuo = Q_observado − Q_físico
Inferencia:    Q_híbrido = Q_físico + residuo_predicho
```

Q_físico corresponde al brazo A o B. Q_observado solo construye el objetivo y
evalúa las predicciones; el modelo no puede necesitar el caudal observado del
periodo objetivo para inferir su corrección. Cualquier uso de observaciones
rezagadas implica otro contrato operacional y debe declararse.

Definir antes de entrenar target observado, nombre/unidad del caudal físico de
referencia, features, resolución, historia necesaria y política de faltantes.
Los targets actuales con descripción de caudal *simulado* no se reutilizan como
observado cambiando solo la etiqueta. Infiltración y percolación tampoco son
intercambiables.

Seleccionar modelos e hiperparámetros con TRAIN/VALIDATION o validación temporal
interna; usar TEST una vez con la configuración fijada. Preprocesadores y
transformaciones aprendidas se ajustan solo en TRAIN durante la selección.
Comparar candidatos
sobre fechas comunes, especialmente si las ventanas temporales eliminan filas.
La arquitectura profunda no es obligatoria: complejidad y recursos se justifican
por cantidad de años/muestras, desempeño y estabilidad.

El bundle conserva modelo, preprocesador, schema, métricas, dataset, split,
procedencia y limitaciones. El campeón es específico del target y evaluación,
no un modelo universal del gemelo.

Entrenar con resultados simulados produce un surrogate, no validación contra
observaciones. La ruta principal elegida aquí es corrección observacional; la
aceleración con surrogate queda como línea posterior. La corrección estadística
no se reinyecta automáticamente en el balance físico de SWAT+: ambos resultados
se publican separados y se declara que el caudal corregido no garantiza cierre
del balance de masa.

## 7. Datos y sustituciones metodológicas

| Elemento original | Uso en el primer estudio |
| --- | --- |
| Caudal USGS | Mantener como observación primaria; conservar calificadores, gaps y cobertura. |
| CHIRPS | Sustituir por gridMET para Iowa, documentando extracción y conversiones. |
| SoilGrids | Usar gNATSGO/bases de suelo SWAT+ con procedencia y propiedades verificadas. |
| Landsat histórico 1984–2023 | Usar CDL de los años evaluados cuando se modele manejo histórico; alternativamente declarar un escenario de manejo fijo. |
| FSPM completo parametrizado en campo | FSPM simplificado con supuestos explícitos y validación vegetal secundaria cuando haya evidencia. |
| USDA NASS de rendimiento | Posponer validación espacial hasta contar con observaciones y correspondencia de escala defendibles. CDL no es rendimiento observado. |
| CMIP6 downscaled | Extensión posterior; +2 °C/−15 % de lluvia son perturbaciones controladas, no proyecciones CMIP6. |
| Validación multicuenca | Comenzar con estudio de caso temporal; añadir cuencas solo cuando datos y proyectos sean verificables. |

Base comprobada en la revisión de 2026-10-06:

- USGS South Fork: 9.496 valores diarios, 2000–2025, un día ausente y calificadores
  de estimación que requieren análisis explícito. Hay longitud temporal para
  diseñar particiones, pero no 26 años de manejo histórico reconstruido.
- 25 puntos meteorológicos de rejilla y 125 archivos diarios 2000–2025 de la
  copia experimental coinciden por hash con el proyecto fuente. Sus metadatos
  externos identifican gridMET; `soils.sol` coincide y el constructor identifica
  gNATSGO/bases de referencia. Integrar ese linaje en el manifiesto científico.
- CDL disponible para 2019; falta historia anual para afirmaciones de rotación.
- No se identificaron datasets vegetales independientes ni CMIP6 normalizado
  en las carpetas de datos revisadas.
- Boone/TREC son material complementario: faltan 17 archivos de temperatura
  declarados en el proyecto Boone y su hash USGS necesita reconciliarse con el
  assessment. No cuentan aún como validación espacial completada.

Para LAI considerar MODIS MCD15A3H (500 m, compuesto de cuatro días), con filtros
de calidad, máscara de cultivos y agregación compatible. Es una estimación
satelital, no LAI medido de individuos. Si se usa para ajuste, reservar periodos
independientes para evaluación. La adquisición puede aportar una prueba de
proceso, sin convertirse en requisito para iniciar el protocolo hidrométrico.

## 8. Evaluación y reproducibilidad

- **Métrica primaria:** RMSE del caudal medio mensual, m³/s, en TEST.
- **Complementarias:** MAE, NSE, KGE y PBIAS, con fórmula/signo/versiones
  documentados; diagnóstico diario separado del contraste primario.
- Agregar observaciones y simulaciones con soporte temporal compatible;
  declarar cobertura y rechazar meses insuficientes según regla previa. No
  imputar observaciones para mejorar una métrica.
- Estimar incertidumbre de diferencias emparejadas respetando dependencia
  temporal, por ejemplo con bootstrap por bloques. Fijar longitud de bloque,
  número de réplicas y regla de decisión antes de TEST, según los datos.
- KS es diagnóstico de distribución, no validación de la secuencia temporal.
  Wilcoxon no se aplica a un único RMSE por modelo y requiere revisar sus
  supuestos antes de usar errores mensuales como muestras independientes.
- Sensibilidad: comenzar con intervenciones y/o Morris; Sobol requiere rangos,
  diseño y ejecuciones suficientes. No equiparar los probes OAT existentes con
  una sensibilidad global completada.
- Conservar inputs, hashes, manifiestos, versiones, seeds, configuración,
  particiones, predicciones y errores por periodo. Un registro diario repetido
  entre escenarios no constituye una nueva observación independiente.

Es preferible un resultado negativo o de efecto limitado bien explicado a
optimizar hasta alcanzar la H1. No rechazar H0 no demuestra equivalencia;
afirmar no inferioridad requiere margen y contraste definidos previamente.

## 9. Ajustes de implementación previos a las corridas finales

1. Revisar el baseline y sus errores, incluyendo forcing, outlet, agua/ET,
   parametrización y representación del drenaje subsuperficial cuando proceda.
2. Adaptar el calendario a múltiples temporadas o coordinar años con condiciones
   iniciales/warm-up explícitos: el contrato actual exige una temporada por HRU.
3. Crear exportación desde estados fechados de la ruta SWAT+ actual. El exportador
   mensual existente está orientado a la ruta simplificada y reutiliza agregados
   de LAI/raíces de toda la corrida; no usarlo como evolución mensual científica.
4. Manejar cultivo inactivo y variables ausentes sin defaults sintéticos ni
   eliminación automática de todas las features vegetales. Cero biológico y
   dato desconocido son distintos; fijar una estrategia por variable.
5. Construir el target residual observado, armonizar sus contratos entre proyectos
   y habilitarlo en el laboratorio con fuentes observacionales compatibles.
6. Corregir selección del campeón: hoy el trainer general y el experimento diario
   utilizan métricas de TEST para elegirlo; deben elegir en validación.
7. Integrar inferencia externa en SWAT+ real: hoy esa rama retorna antes del
   bloque ML de la ruta simplificada. Publicar resultado físico y asistido sin
   sobrescribir outputs originales ni fabricar playback diario desde meses.

El reporte publicado `south-fork-final-v2` y el bundle diario
`phase234-sf-2019-v2` pertenecen a experimentos distintos. Sus resultados no
se promueven a este protocolo. Los bundles mensuales sintéticos y el pronóstico
diario sobre simulación tampoco constituyen evidencia de la nueva H1.

## 10. Orden de trabajo y decisiones abiertas

**Secuencia:** revisión bibliográfica y de datos → congelación de protocolo →
baseline y exportación → entrenamiento/selección → evaluación independiente →
integración y redacción.

Antes de evaluar, fijar y versionar:

- Años exactos de warm-up, calibración, TRAIN, VALIDATION y TEST; presupuesto
  de búsqueda, variables y tratamiento de temporadas.
- Manejo anual reconstruido o escenario fijo, alcance del CDL y cuenca/outlet.
- Regla de cobertura/QC, tratamiento de USGS estimado y métricas comunes.
- Diseño inferencial, contraste primario y análisis secundarios/ablaciones.
- Referencias y novedad; disponibilidad de LAI y función en ajuste/evaluación.

Los años ya examinados para depuración o parametrización no se describen como
una evaluación ciega intacta. Elegir un holdout no utilizado o declarar
honestamente el carácter exploratorio; un preregistro nuevo no borra análisis
anteriores. OSF puede registrar el protocolo antes de la evaluación final.

El primer artículo no promete rendimiento espacial, generalización multicuenca,
proyecciones CMIP6 ni recomendaciones de política operacional. Puede incluir
escenarios controlados como exploración, sin presentar la corrección ML fuera
de su dominio de entrenamiento como una respuesta fisiológica validada.

La meta editorial es un artículo reproducible y defendible, con evaluación
independiente y límites claros. Una revista indexada en Scopus es una aspiración;
alcance, indexación y cuartil se verifican al elegir la revista. La reformulación
no garantiza aceptación ni exige obtener un resultado positivo.

**Título de trabajo:** *Evaluación de un framework multiescala planta–cuenca con
corrección hidrológica mediante aprendizaje automático en una cuenca agrícola*.

## Referencias iniciales para continuar la revisión

- [Alemayehu et al. (2017): crecimiento vegetal mejorado en SWAT](https://doi.org/10.5194/hess-21-4449-2017).
- [Rane y Jayaraj: calibración multiobjetivo con ET y LAI](https://doi.org/10.1007/s13762-022-04293-7).
- [Documentación SWAT+: dosel y altura](https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-5-land-cover-plant/optimal-growth/potential-growth/canopy-cover-and-height).
- [Catálogo MODIS MCD15A3H](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD15A3H).
- [Catálogo gridMET](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_GRIDMET).

Estos antecedentes orientan la revisión; no constituyen todavía un análisis
exhaustivo del estado del arte ni prueba de novedad.

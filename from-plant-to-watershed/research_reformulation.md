# Reformulación experimental — From Plant to Watershed

**Versión:** 0.2 · **Fecha:** 2026-10-06.
**Estado:** orientación acordada; protocolo pendiente de congelar antes de la
evaluación final. Esta revisión incorpora lectura de código, artefactos locales
y antecedentes bibliográficos; no declara nuevas corridas ni evaluación de H1.

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

SWAT+ ya representa crecimiento vegetal e hidrología. La pregunta experimental
es: **¿qué valor adicional aporta una parametrización vegetal informada por un
modelo simplificado al caudal mensual simulado con SWAT+, antes y después de
aplicar una corrección mediante aprendizaje automático?**

Se investigará ese valor mediante comparaciones controladas contra caudal USGS,
separando el aporte del FSPM simplificado del aporte del ML. El gemelo permite
ejecutar, almacenar y explorar los estados por escala y fecha; su apariencia
gráfica no constituye evidencia de precisión física.

La contribución buscada es cuantificar el aporte incremental de la información
vegetal mediante comparaciones controladas, explicar la respuesta física y
publicar datos, configuraciones y predicciones reproducibles. La plataforma
permite ejecutar y explorar esa evidencia; su implementación es un entregable
de software, mientras que la contribución científica depende del experimento.

La novedad debe establecerse mediante revisión bibliográfica. Existen
antecedentes de vegetación/hidrología, calibración con teledetección y corrección
residual de SWAT+ mediante ML; [Yang et al. (2026)](https://doi.org/10.5194/hess-30-4271-2026)
emplean meteorología y estados físicos para aprender residuos de caudal.
La integración general SWAT+–ML tiene antecedentes. La revisión debe precisar
qué diferencia introducen nuestro mecanismo vegetal, las ablaciones y las
condiciones de evaluación, sin afirmar prioridad o ausencia de trabajos
relacionados antes de completar el estado del arte.

### Alcance físico del acoplamiento disponible

La ruta actual agrupa HRU por calendario ejecutado, calcula poblaciones vegetales
representativas y resume sus rasgos para modificar diez parámetros de un único
registro `corn` en `plants.plt`. Los grupos comparten esa parametrización;
SWAT+ conserva sus ecuaciones de crecimiento y balance hídrico. ET, absorción
de agua y estrés diarios del FSPM no se imponen directamente a SWAT+.

La afirmación defendible es una parametrización vegetal externa compartida,
informada por estados representativos y retroalimentación hídrica aproximada.
La transmisión de parámetros distintos por HRU, la fisiología individual
validada y el seguimiento de plantas observadas requieren contratos y evidencia
adicionales. El artículo debe explicar esta agregación al interpretar sus
resultados y cualquier afirmación de representación espacial.

## 3. Objetivo y alcance del primer artículo

**Objetivo general:** desarrollar y evaluar un framework multiescala reproducible
que integre SWAT+, una parametrización vegetal basada en un modelo simplificado
y corrección residual mediante ML, cuantificando sus aportes al caudal medio
mensual de South Fork Iowa River.

Objetivos específicos:

1. Preparar datos trazables y una referencia hidrológica diagnosticada, con
   reglas de calidad, manejo, warm-up y particiones temporales explícitas.
2. Ejecutar los brazos físicos A/B bajo condiciones compartidas y exportar
   estados vegetales e hidrológicos fechados con unidades y procedencia.
3. Entrenar las correcciones C/D y seleccionar sus modelos exclusivamente en
   validación, conservando contratos y predicciones reproducibles.
4. Comparar los cuatro brazos en periodos reservados, cuantificando diferencias,
   incertidumbre temporal y límites del aporte vegetal y del ML.
5. Entregar un gemelo funcional para usuarios autenticados: configurar y ejecutar
   corridas, consultar estados por fecha y escala, contrastar caudales observados
   y simulados, y descargar resultados con unidades, cobertura y procedencia.
   La disponibilidad de cada salida debe corresponder a la frecuencia ejecutada.

Evidencia de cumplimiento: dataset y protocolo versionados; manifiestos y
exportaciones A/B; bundles C/D con registro de selección; y tablas de errores,
contrastes e incertidumbre. Los objetivos se cumplen al producir y evaluar
esa evidencia, aunque el efecto resulte nulo o negativo. La integración en la
plataforma conservará por separado resultados físicos y asistidos, con sus
unidades y procedencia, como entregable de software del mismo estudio.
El objetivo funcional requiere un recorrido completo desde la creación hasta
la descarga sobre PostgreSQL; una visualización aislada no acredita su cumplimiento.

Primer avance: [diagnóstico de la referencia South Fork 2019](docs/BASELINE_DIAGNOSTIC_2019.md).
Las corridas de desarrollo detectaron drenaje sin enlace vegetal y sin conexión
de ruteo; sus intervenciones no sustituyen una máscara histórica observada ni
la evaluación independiente de los brazos A/B/C/D.

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

Este cambio es documental: `ValidationEngine.compare()` todavía aplica el
umbral de 15 % y declara `NOT_FORMAL_HYPOTHESIS_TEST`. El nuevo evaluador debe
implementar la regla inferencial fijada para este protocolo, conservando las
etiquetas históricas de los experimentos anteriores bajo sus propias versiones.

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
| B | SWAT+ con parametrización vegetal informada por FSPM simplificado | Efecto físico vegetal sin ML. |
| C | SWAT+ estándar + corrección ML | ML sin acoplamiento FSPM. |
| D | B + corrección ML | Sistema completo. |

- **D vs A:** contraste primario del sistema completo.
- **B vs A:** efecto del acoplamiento físico evaluado.
- **C vs A y D vs B:** aporte de las correcciones ML.
- **D vs C:** aporte total de la integración vegetal bajo configuraciones
  híbridas comparables; no identifica por sí solo cada mecanismo individual.

B vs A y D vs C son necesarios para sustentar una conclusión sobre el aporte
vegetal. Una mejora D vs A puede explicarse principalmente por ML. Si C y D
tienen desempeños similares, reportar el tamaño y la incertidumbre de esa
diferencia; concluir ausencia de evidencia suficiente no demuestra equivalencia.

Una ablación adicional, con/sin features vegetales sobre el mismo brazo físico,
puede aislar su valor predictivo para ML. Los contrastes secundarios se
identifican como tales y no se promueven retrospectivamente a resultado primario.

Añadir referencias de bajo costo: climatología mensual calculada en TRAIN y
una corrección estadística sencilla del caudal físico, ajustada en desarrollo.
Fijar antes de TEST su fórmula, hiperparámetros y política de caudales negativos.
Permiten evaluar si la complejidad vegetal y ML aporta valor frente a métodos
simples, usando el mismo soporte temporal que los cuatro brazos.

Compartir cuenca, forcing, fechas, outlet, warm-up, esquema de manejo, controles
de impresión y compatibilidad de inputs. Comparar sobre las mismas fechas
válidas. La variante experimental CDL debe ser común a los brazos: comparar
maíz acoplado contra manejo genérico distinto confundiría los efectos.

Primero diagnosticar y, cuando la configuración física sea defendible, calibrar
la referencia usando solo el periodo de desarrollo y un presupuesto acotado.
Documentar criterios de aceptación y limitaciones antes de TEST. Una corrección
ML puede compensar errores físicos; su mejora de caudal no demuestra que esos
procesos estén representados correctamente. Para aislar el acoplamiento,
conservar parámetros hidrológicos compartidos entre A/B. C/D necesitan
presupuestos de búsqueda, familias de
algoritmos y reglas de selección comparables. Todo cambio de manejo o de
parametrización se registra, no se oculta como efecto del FSPM.

### Diagnóstico prioritario de South Fork

El reporte histórico `south-fork-final-v2` registra NSE mensual −0,6746 y PBIAS
−79,5795 % para 2018–2020. Es evidencia de una referencia con errores importantes
en aquel experimento; la ruta diaria corregida necesita su propia evaluación.

En el proyecto experimental local `backend/data/phase34-cdl-2019/project/`
existe `tiledrain.str`, pero los registros de `landuse.lum` tienen `tile=null`.
La presencia del archivo no acredita activación del drenaje. Un estudio previo
de South Fork documentó drenaje artificial extensivo y su importancia para el
balance hídrico ([Green et al., estudio hidrológico](https://www.ars.usda.gov/ARSUserFiles/36627/Green%20ASABE%20413.pdf)).
Esto justifica revisar la representación del proceso; todavía no prueba que
explique por sí solo los errores del proyecto actual.

El diagnóstico debe cubrir forcing y conversiones, activación y aportes del
drenaje cuando correspondan, ET/PET, almacenamiento y aportes subterráneos,
routing, outlet y consistencia del balance hídrico. Toda reparación física
común se aplica a A/B y se registra antes de atribuir diferencias al FSPM.

## 6. Papel obligatorio del laboratorio ML

`agro-digital-twin-st` es el laboratorio de preparación, entrenamiento,
comparación y exportación del modelo campeón. `from-plant-to-watershed` es su
consumidor para inferencia y persistencia. El ML participa en una función
hidrológica concreta; no necesita sustituir toda la planta, HRU y red de canales.

El aprendizaje residual propuesto es:

```text
Entrenamiento: residuo = Q_observado − Q_físico
Inferencia:    Q_híbrido = Q_físico + residuo_predicho
Evaluación:   comparar Q_híbrido con Q_observado en las mismas fechas
```

Q_físico corresponde al brazo A o B. Q_observado solo construye el objetivo y
evalúa las predicciones; el modelo no puede necesitar el caudal observado del
periodo objetivo para inferir su corrección. Cualquier uso de observaciones
rezagadas implica otro contrato operacional y debe declararse.

Conservar Q_observado, Q_físico y residuo como columnas distintas y con la misma
unidad m³/s. El caudal físico necesario para reconstruir la predicción mantiene
su valor original aunque también se escale una copia como feature. Cualquier
recorte de caudal negativo u otra transformación de la predicción se fija antes
de TEST y se aplica de forma consistente durante selección, evaluación e
inferencia.

Definir antes de entrenar target observado, nombre/unidad del caudal físico de
referencia, features, resolución, historia necesaria y política de faltantes.
Los targets actuales con descripción de caudal *simulado* no se reutilizan como
observado cambiando solo la etiqueta. Infiltración y percolación tampoco son
intercambiables.

Seleccionar modelos e hiperparámetros con TRAIN/VALIDATION o validación temporal
interna; usar TEST una vez con la configuración fijada. Preprocesadores y
transformaciones aprendidas se ajustan solo en TRAIN durante la selección.
Comparar candidatos sobre fechas comunes, especialmente si las ventanas
temporales eliminan filas. Alinear objetivo, caudal físico y predicción por sus
claves temporales y espaciales; truncar vectores por longitud no garantiza esa
alineación. Iniciar con una corrección sencilla y RF/SVR/XGBoost bajo un
presupuesto comparable. La arquitectura profunda requiere justificar
complejidad y recursos por cantidad de años/muestras, desempeño y estabilidad.

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

- USGS South Fork: 9.496 valores diarios, 2000–2025; falta el 2017-08-20.
  De los registros, 2.653 tienen calificadores `A,e` (27,94 %) y 6.843 tienen
  `A`. Fijar tratamiento de valores estimados y análisis de sensibilidad antes
  de evaluar; su eliminación puede cambiar la cobertura y composición estacional.
  Hay longitud temporal para diseñar particiones, pero no 26 años de manejo
  histórico reconstruido.
- 25 puntos meteorológicos de rejilla y 125 archivos diarios 2000–2025 de la
  copia experimental coinciden por hash con el proyecto fuente. Sus metadatos
  externos identifican gridMET; `soils.sol` coincide y el constructor identifica
  gNATSGO/bases de referencia. Integrar ese linaje en el manifiesto científico.
- CDL disponible para 2019; falta historia anual para afirmaciones de rotación.
- El bundle corregido `phase234-sf-2019-v2` contiene 365 fechas de 2019; el LAI
  FSPM está disponible en 112 días y ausente en 253. La disponibilidad estacional
  requiere políticas explícitas por variable al construir features mensuales.
- No se identificaron datasets vegetales independientes ni CMIP6 normalizado
  en las carpetas de datos revisadas.
- Boone/TREC son material complementario: faltan 17 archivos de temperatura
  declarados en el proyecto Boone y su hash USGS necesita reconciliarse con el
  assessment. No cuentan aún como validación espacial completada.

El intervalo completo 2000–2025 aporta como máximo 312 meses antes de warm-up,
exclusiones y particiones. Las HRU, plantas numéricas y escenarios no multiplican
las observaciones independientes del caudal del outlet. El tamaño efectivo
también depende de la autocorrelación; justificar con estas restricciones la
complejidad de los modelos y la precisión de los intervalos de incertidumbre.

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
- Usar una máscara común de fechas y valores válidos para todos los brazos y
  referencias. Registrar cantidad de meses y años, exclusiones y cobertura por
  partición, además de errores emparejados y resultados por año/temporada.
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

1. Diagnosticar el baseline: forcing y unidades, outlet, agua/ET, routing y
   drenaje subsuperficial. Revisar `tile=null` en el proyecto experimental y
   justificar su configuración con fuentes y evidencia de ejecución. Calibrar
   solo después del diagnóstico, usando desarrollo y presupuesto registrado.
2. Adaptar el calendario a múltiples temporadas o coordinar años con condiciones
   iniciales/warm-up explícitos: el contrato actual exige una temporada por HRU.
3. Crear exportación desde estados fechados de la ruta SWAT+ actual. El exportador
   mensual existente está orientado a la ruta simplificada y reutiliza agregados
   de LAI/raíces de toda la corrida; no usarlo como evolución mensual científica.
   Corregir los cargadores que publican `percolation_mm` como `infiltration_mm`;
   conservar nombre, unidad y significado de cada variable física.
4. Manejar cultivo inactivo y variables ausentes sin defaults sintéticos ni
   eliminación automática de todas las features vegetales. Cero biológico y
   dato desconocido son distintos; fijar una estrategia por variable.
5. Construir el target residual observado, armonizar sus contratos entre proyectos
   y habilitarlo en el laboratorio con fuentes observacionales compatibles.
6. Reparar la evaluación residual en `src/core/training/trainer.py` del
   laboratorio: en modelos tradicionales, `y_true_eval` ya contiene el caudal
   total y vuelve a sumar el baseline. En secuencias, conservar el baseline en
   unidades físicas antes de escalar features y alinear objetivos/baselines
   de VALIDATION y TEST con las fechas de cada ventana. Ambas rutas deben
   comparar caudal reconstruido con el objetivo observado original.
7. Corregir selección del campeón: hoy el trainer general y el experimento diario
   utilizan métricas de TEST para elegirlo; deben elegir en validación sobre
   fechas comunes, según la métrica fijada por el protocolo.
8. Integrar inferencia externa en SWAT+ real: hoy esa rama retorna antes del
   bloque ML de la ruta simplificada. Publicar resultado físico y asistido sin
   sobrescribir outputs originales ni fabricar playback diario desde meses.
9. Versionar el evaluador de los cuatro brazos, referencias simples y contraste
   primario con incertidumbre temporal. Retirar el umbral heredado de 15 % de la
   nueva regla de decisión y conservar las interpretaciones históricas por versión.

El reporte publicado `south-fork-final-v2` y el bundle diario
`phase234-sf-2019-v2` pertenecen a experimentos distintos. Sus resultados no
se promueven a este protocolo. Los bundles mensuales sintéticos y el pronóstico
diario sobre simulación tampoco constituyen evidencia de la nueva H1.

## 10. Orden de trabajo y decisiones abiertas

**Secuencia:** revisión bibliográfica, auditoría de datos y de años utilizados →
diagnóstico físico con desarrollo → congelación de protocolo y contratos →
reparación del pipeline residual y preparación multianual → calibración A y
corridas/exportación A/B → entrenamiento/selección C/D y referencias simples →
evaluación reservada → integración y redacción.

La primera tarea es revisar activación del drenaje y balance hídrico, junto con
reparar la evaluación residual. La decisión de escalar a varias temporadas se
apoya en una referencia diagnosticada y contratos correctos de unidades y fechas.
El acceso a TEST para desarrollo queda excluido de esta secuencia.

Antes de evaluar, fijar y versionar:

- Años exactos de warm-up, calibración, TRAIN, VALIDATION y TEST; presupuesto
  de búsqueda, variables y tratamiento de temporadas.
- Manejo anual reconstruido o escenario fijo, alcance del CDL y cuenca/outlet.
- Regla de cobertura/QC, tratamiento de USGS estimado y métricas comunes.
- Fórmulas de las referencias simples, manejo de cultivo inactivo/faltantes,
  features C/D, política de caudales negativos y selección del campeón.
- Diseño inferencial, contraste primario y análisis secundarios/ablaciones;
  longitud de bloque, réplicas y regla de decisión de incertidumbre.
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
parametrización vegetal simplificada y corrección residual del caudal mediante
aprendizaje automático en South Fork Iowa River*.

### Registro de revisión

- **2026-10-06 · v0.1:** delimitación del primer artículo a una cuenca, caudal
  mensual, cuatro comparadores y corrección residual observacional; retiro del
  umbral obligatorio de 15 % y de las promesas espaciales/CMIP6.
- **2026-10-06 · v0.2:** precisión de pregunta y objetivos medibles, alcance de
  parametrización vegetal compartida, referencias simples, diagnóstico de
  drenaje/balance hídrico, conteos USGS y disponibilidad vegetal, reparaciones
  residuales y alineación temporal, actualización del evaluador y antecedentes
  SWAT+–ML. Motivo: contrastar la propuesta con código, artefactos y literatura
  antes de congelar el protocolo. Se conserva D vs A como contraste primario;
  los años, reglas de calidad y diseño inferencial siguen pendientes de fijar.

## Referencias iniciales para continuar la revisión

- [Alemayehu et al. (2017): crecimiento vegetal mejorado en SWAT](https://doi.org/10.5194/hess-21-4449-2017).
- [Rane y Jayaraj: calibración multiobjetivo con ET y LAI](https://doi.org/10.1007/s13762-022-04293-7).
- [Yang et al. (2026): SWAT+ con corrección ML de residuos en un framework de balance hídrico](https://doi.org/10.5194/hess-30-4271-2026).
- [Green et al.: evaluación hidrológica de SWAT y drenaje artificial en South Fork Iowa](https://www.ars.usda.gov/ARSUserFiles/36627/Green%20ASABE%20413.pdf).
- [Documentación SWAT+: dosel y altura](https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-5-land-cover-plant/optimal-growth/potential-growth/canopy-cover-and-height).
- [Catálogo MODIS MCD15A3H](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD15A3H).
- [Catálogo gridMET](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_GRIDMET).

Estos antecedentes orientan la revisión; no constituyen todavía un análisis
exhaustivo del estado del arte ni prueba de novedad.

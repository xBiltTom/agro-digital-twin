# Reformulación experimental — From Plant to Watershed

**Versión:** 0.6 · **Fecha:** 2026-10-06.
**Estado:** protocolo multianual v1 congelado antes de calibrar; búsqueda física
de 12 candidatos terminada y 96 meses pareados A/B publicados. La referencia seleccionada
incumple el criterio de sesgo y permanece exploratoria. C/D seleccionados en
VALIDATION mediante búsqueda ML comparable; pesos TRAIN y referencias simples
congelados. TEST 2021–2025 evaluado sin reajuste; **H1 no respaldada** por el
intervalo de reducción RMSE D/A. Flujo funcional de usuarios y paquete del
paper integrados; las cinco entregas técnicas están completadas.

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
El [seguimiento del recorrido del agua](docs/WATER_PATH_DIAGNOSTIC_2019.md)
identificó además un error del reporte de canales artificiales y corrigió su
lectura con volúmenes nativos. Antes de calibrar A/B se deben recuperar longitudes
reales y comprobar el ruteo físico; cerrar conexiones y corregir la lectura
no acredita desempeño hidrológico ni evaluación de H1.
La [recuperación de longitudes de cauces](docs/CHANNEL_GEOMETRY_DIAGNOSTIC_2019.md)
completó una comparación controlada de desarrollo: 212,637 km delineados,
ruteo físico y menor volumen outlet, con NSE todavía negativo. Una copia
diagnóstica del binario permitió underflow sin cambiar rutinas del modelo;
aquella tarea dejó pendiente fijar un motor reproducible y completar la
contabilidad fluvial antes del experimento A/B del paper.
La [etapa posterior desde fuente](docs/SWAT_SOURCE_BUILD_2019.md) completó esa
receta y recuperó el almacenamiento de llanura: red cerrada numéricamente,
cuenca todavía parcial y métricas USGS idénticas. Esa etapa dejó pendiente
revisar la referencia física antes de calibrar A/B.
La [auditoría meteorológica posterior](docs/METEOROLOGY_DIAGNOSTIC_2019.md)
reconstruye gridMET y contrasta ET/PET con productos externos. Identifica cinco
cierres de año interpolados y discrepancias de lluvia de 2011 y viento de 2015
en el warm-up. Esa auditoría requirió una variante corregida y una comparación
controlada antes de estudiar sensibilidad o calibrar. TerraClimate aporta ET
modelada; su comparación no acredita validación observacional de ET ni H1.

La [entrega 1](docs/PHYSICAL_REFERENCE_DELIVERY_1.md) completa esa corrección y
revisión: 1.062 registros de warm-up reparados, control que reproduce exactamente
365 caudales anteriores y variante corregida con 94,520 hm³ frente a 289,423 hm³
USGS. La corrección climática no resuelve la subestimación. ET con baja cobertura
y escaso aporte acuífero son prioridades para calibración; las pérdidas netas
fluviales y la diferencia de área tienen una magnitud menor que el déficit.
El motor fija `perco=0,1` en HRU drenadas y no permite ajustar allí `perco` mediante
su selector de calibración. La referencia queda preparada para **iniciar**
calibración multianual de desarrollo bajo un escenario agrícola fijo y declarado;
no está calibrada ni validada. Los años adicionales requieren revisar sus cierres
climáticos. Se conservan la geometría física, el motor y los experimentos previos.

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
  gNATSGO/bases de referencia. La auditoría meteorológica ya integra las
  conversiones y alertas de calendario/caché en las referencias de pglocal;
  el linaje de suelos requiere su propia revisión.
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
6. **Implementado en entrega 3:** evaluación residual en
   `src/core/training/trainer.py`: observado tabular sin segunda suma del
   baseline; secuencias con baseline físico separado del escalado y alineado
   a la fecha objetivo. El experimento C/D mensual usa el contrato corregido.
7. **Implementado en entrega 3:** trainer general y experimento diario seleccionan
   por RMSE de VALIDATION. La nueva búsqueda C/D usa fechas comunes y el
   presupuesto/métrica congelados; no accede a TEST.
8. Integrar inferencia externa en SWAT+ real: hoy esa rama retorna antes del
   bloque ML de la ruta simplificada. Publicar resultado físico y asistido sin
   sobrescribir outputs originales ni fabricar playback diario desde meses.
9. **Implementado en entrega 4:** evaluador de los cuatro brazos, referencias
   TRAIN y contraste primario con bootstrap temporal pareado. La nueva regla
   usa IC95 de reducción RMSE, sin umbral de 15 %; los resultados históricos
   conservan su interpretación por versión. H1 no respaldada en TEST.

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

La entrega 1 de referencia física está completada. La
[entrega 2](docs/MULTIYEAR_EXPERIMENT_DELIVERY_2.md) fija protocolo y particiones,
preparación multianual, calibración acotada y exportación fechada A/B.
La [entrega 3](docs/ML_RESIDUAL_DELIVERY_3.md) completa la selección C/D en
VALIDATION y congela modelos y referencias simples en pglocal.
La [entrega 4](docs/TEST_EVALUATION_DELIVERY_4.md) completa TEST 2021–2025 y la
decisión inferencial, con sensibilidad a estimados y resultados congelados.
Las **cinco entregas técnicas están completadas**, incluido el flujo de usuarios
y el paquete del paper. La [entrega 5](docs/FUNCTIONAL_TWIN_DELIVERY_5.md)
documenta ejecución propia A/B, ML mensual, comparación y descargas.
La decisión de escalar a varias temporadas se apoya en una referencia
diagnosticada y contratos correctos de unidades y fechas.
TEST ya está evaluado y no se reutilizará para ajustar este experimento.

El [protocolo v1](research_domain/south_fork_multiyear_protocol_v1.json) fija
WARMUP 2000–2004, CALIBRATION 2005–2012, TRAIN 2013–2017, VALIDATION 2018–2020
y TEST 2021–2025. VALIDATION ya fue explorada y se declara de desarrollo.
Fija escenario agrícola estático, QC/cobertura, cultivo inactivo/faltantes,
presupuesto físico de 12 candidatos y regla inferencial con bloques de 12 meses,
2.000 réplicas e intervalo del 95 %. La derivación vegetal usa 2010 y se congela
antes de publicar TRAIN/VALIDATION; no se recalcula por año de evaluación.

La selección física alcanza NSE mensual 0,649 y RMSE 4,718 m³/s en CALIBRATION,
pero PBIAS −40,605 % incumple |PBIAS| ≤ 30 %. Se conserva exploratoria sin
ampliar el presupuesto. La futura mejora ML contra esta referencia no bastará
para afirmar validación física o fisiológica.

La [entrega ML](docs/ML_RESIDUAL_DELIVERY_3.md) fija seis candidatos iguales por
brazo, 14 features C y 21 D, StandardScaler ajustado solo en TRAIN y selección
por RMSE del caudal corregido en VALIDATION. Ambos ganadores son Ridge α = 10;
RMSE de desarrollo C 2,978 y D 2,990 m³/s frente a A 4,007. D no supera C en
estos años. La climatología y corrección afín se ajustaron solo en TRAIN y se
congelaron junto con los bundles. Estos resultados no deciden H1 ni demuestran
valor fisiológico adicional. La inferencia es retrospectiva con inputs del mes
completo; el contraste D/C combina referencia física y features diferentes.

La entrega 4 evalúa 60 meses TEST con 1.826 días aprobados, incluidos 578
estimados. RMSE A/B/C/D: 3,695/3,579/2,749/4,517 m³/s. Reducción D/A −22,239 %;
IC95 absoluto [−3,286; +1,871] m³/s: **H1 no respaldada**. Excluir estimados
reduce el soporte a 36 meses y mantiene la misma decisión. C tiene menor
RMSE puntual, pero su IC95 C/A incluye cero y PBIAS +44,616 %. No se cambia el
contraste primario a C ni se ajustan pesos después de observar TEST.

El flujo funcional y el [borrador del paper](research_domain/paper_v1/manuscript.md)
exponen la decisión, el linaje y sus límites. No se usó LAI observado para
ajuste o evaluación fisiológica. Las referencias verificadas delimitan los
antecedentes; la revisión exhaustiva, autoría y preparación editorial son
trabajo posterior del equipo.

Los años ya examinados no se describen como una evaluación ciega intacta.
TEST 2021–2025 ahora es conocido: futuras modificaciones de modelo requieren
otro holdout independiente o una declaración explícita de desarrollo.
Un preregistro nuevo no borra análisis anteriores. Este experimento conserva
sus recibos locales previos a la ejecución; no se afirma un preregistro OSF.

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
- **2026-10-06 · v0.3:** protocolo multianual v1 y particiones congelados,
  presupuesto de 12 candidatos, calendario por temporada y contrato vegetal
  derivado en 2010. La referencia ganadora falla el criterio predefinido de
  sesgo; se conserva exploratoria y TEST permanece reservado.
- **2026-10-06 · v0.4:** protocolo ML congelado antes del ajuste, reparación de
  reconstrucción residual/alineación y selección exclusivamente en VALIDATION.
  C/D Ridge α = 10, referencias simples y pesos TRAIN congelados; registro en
  pglocal y paridad de inferencia. TEST y H1 continúan pendientes.
- **2026-10-06 · v0.5:** diez publicaciones TEST A/B y 60 meses evaluados con
  C/D y referencias TRAIN congelados. Bootstrap circular pareado de 12 meses,
  2.000 réplicas, sin umbral de 15 %. H1 no respaldada; sensibilidad sin
  estimados conserva la decisión sobre 36 meses. No se reoptimiza después
  de TEST ni se reemplaza el contraste primario por C.

- **2026-10-06 · v0.6:** flujo funcional de reproducción histórica A/B con ML
  mensual opcional, comparación TEST actual, descargas y paquete del paper
  registrados en pglocal. B 2021 propio completado con 365 frames y 12
  predicciones D. H1 sigue no respaldada; no se reentrenaron bundles.

## Referencias iniciales para continuar la revisión

- [Alemayehu et al. (2017): crecimiento vegetal mejorado en SWAT](https://doi.org/10.5194/hess-21-4449-2017).
- [Rane y Jayaraj: calibración multiobjetivo con ET y LAI](https://doi.org/10.1007/s13762-022-04293-7).
- [Yang et al. (2026): Disentangling the key drivers of water balance in Central Asia’s Lake Balkhash: A relative contribution assessment](https://doi.org/10.5194/hess-30-4271-2026).
- [Green et al.: evaluación hidrológica de SWAT y drenaje artificial en South Fork Iowa](https://www.ars.usda.gov/ARSUserFiles/36627/Green%20ASABE%20413.pdf).
- [Documentación SWAT+: dosel y altura](https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-5-land-cover-plant/optimal-growth/potential-growth/canopy-cover-and-height).
- [Catálogo MODIS MCD15A3H](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD15A3H).
- [Catálogo gridMET](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_GRIDMET).

Estos antecedentes orientan la revisión; no constituyen todavía un análisis
exhaustivo del estado del arte ni prueba de novedad.

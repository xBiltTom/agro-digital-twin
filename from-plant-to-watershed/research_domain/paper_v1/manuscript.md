# Evaluación mensual de un gemelo digital planta–cuenca con parametrización vegetal simplificada y corrección residual en South Fork Iowa River

**Borrador de trabajo · 6 de octubre de 2026.** Autoría, afiliaciones y revista se completarán por el equipo. Los resultados corresponden al experimento congelado `sf-test-v1`; no se han reajustado modelos después de consultar TEST.

## Resumen

Se evaluó un framework funcional de investigación que integra SWAT+, una parametrización vegetal derivada de un FSPM simplificado y aprendizaje automático residual para caudal mensual en South Fork Iowa River. Se compararon SWAT+ estándar (A), SWAT+ parametrizado con FSPM (B), A con ML (C) y B con ML y variables FSPM (D). La búsqueda física se limitó a 12 candidatos sobre 2005–2012; la referencia seleccionada no superó el criterio de sesgo de calibración y se conservó exploratoria. Ambos modelos residuales fueron Ridge con α = 10, seleccionados en VALIDATION 2018–2020 y ajustados exclusivamente en TRAIN 2013–2017. TEST 2021–2025 incluyó 60 meses pareados. Los RMSE A/B/C/D fueron 3,695/3,579/2,749/4,517 m³/s. La reducción D frente a A fue −0,822 m³/s (−22,239 %), con IC95 [−3,286; +1,871] m³/s mediante bootstrap pareado circular de bloques de 12 meses y 2.000 réplicas. H1 no recibió respaldo; excluir caudales estimados mantuvo la decisión sobre 36 meses. La plataforma permite ejecución, consulta de estados diarios y descarga de evidencia. Su funcionamiento no demuestra validez fisiológica ni conservación hídrica de las predicciones ML.

**Palabras clave:** SWAT+, gemelo digital experimental, FSPM simplificado, regresión residual, evaluación temporal, resultados negativos.

## 1. Introducción y contribución delimitada

Mejorar la descripción vegetal de un modelo hidrológico y corregir estadísticamente sus errores son intervenciones con alcances distintos. Alemayehu et al. estudiaron un módulo de crecimiento modificado para vegetación tropical y su evaluación mediante LAI y balance hídrico; el ámbito difiere del maíz de South Fork. [Artículo original, 2017](https://hess.copernicus.org/articles/21/4449/2017/).

Existen antecedentes que combinan modelos relacionados con SWAT+ y corrección ML. Yang et al. integraron SEGSWAT+, corrección de errores y un marco Budyko para estudiar los cambios del balance del lago Balkhash. Por tanto, combinar SWAT+ y ML no constituye por sí solo una afirmación de novedad. [Artículo original, 2026](https://hess.copernicus.org/articles/30/4271/2026/).

La contribución de este estudio es un experimento reproducible de cuatro variantes, con contratos temporales y de unidades explícitos, una interfaz de investigación funcional y una evaluación reservada que admite resultados negativos. No se afirma prioridad mundial ni una revisión bibliográfica exhaustiva. La pregunta es si D reduce el RMSE mensual frente a A bajo la receta y el manejo experimental fijados. H1 requiere que el IC95 de esa reducción sea estrictamente positivo.

## 2. Materiales y métodos

### 2.1 Dominio, observaciones y particiones

El dominio corresponde a South Fork Iowa River, estación USGS **05451210**. WARMUP abarca 2000–2004, CALIBRATION 2005–2012, TRAIN 2013–2017, VALIDATION 2018–2020 y TEST 2021–2025. VALIDATION había sido explorada y se declara de desarrollo. El registro previo a TEST es un recibo local, no un preregistro público independiente. El uso de suelo y la máscara experimental de maíz/drenaje se fijaron con CDL 2019; no se reconstruyeron rotaciones históricas.

Se admitieron observaciones aprobadas A y A,e, normalizando el separador de calificadores. Se rechazaron valores ausentes, negativos o no finitos; no se imputó caudal. Cada mes requiere al menos 90 % de días pareados. Q observado y físico se promedian sobre exactamente las mismas fechas aprobadas. Las variables explicativas climáticas y de proceso utilizan el mes calendario completo. En TEST hubo 1.826 días aprobados, de los cuales 578 fueron estimados A,e. La sensibilidad excluye esos días antes de agregar y conserva la cuadrícula original de 60 meses, con 36 meses elegibles y 24 excluidos. Este filtrado cambia la composición estacional.

### 2.2 Referencia física y contrato planta–cuenca

La receta SWAT+ desde fuente y su ejecutable se congelaron por SHA-256. Se exploraron 12 combinaciones físicas; la seleccionada usa ESCO = 0,05, umbral de acuífero somero flo_min = 8 m y t_fc de drenaje = 6 h. En CALIBRATION, RMSE = 4,718 m³/s, NSE = 0,649 y PBIAS = −40,605 %. Al incumplir |PBIAS| ≤ 30 %, se etiquetó `BUDGET_EXHAUSTED_EXPLORATORY_REFERENCE` y no se amplió el presupuesto.

B aplica a `plants.plt` diez parámetros vegetales derivados de la temporada preespecificada 2010. Ese contrato se mantiene constante en todos los años de evaluación. La humedad radicular del FSPM se deriva del almacenamiento SWAT+ y del suelo bajo una fracción uniforme de agua disponible en el perfil. El calendario usa eventos modelados por HRU; los estados de planta no son mediciones fisiológicas independientes. SWAT+ conserva sus propias ecuaciones hídricas y vegetales. Los inputs A/B difieren únicamente en `plants.plt` después de las intervenciones controladas.

Las publicaciones anuales reproducen la historia desde 2000; no reinician almacenamientos cada año. Solo se exponen los días del año solicitado. Los diagnósticos nativos muestran cierre numérico de la red, pero la contabilidad de cuenca sigue siendo parcial; un residuo pequeño no demuestra contabilidad completa.

### 2.3 Corrección residual y comparadores

La respuesta ML es el residuo mensual Qobs − Qphys. La salida es max(0, Qphys + residuo estimado), en m³/s. C usa 14 variables comunes: caudal físico, precipitación, temperatura, radiación, humedad, viento, ET, PET, percolación, drenaje, escorrentía, agua del perfil y seno/coseno del mes. D añade siete variables de planta: LAI, profundidad radicular, biomasa por planta, transpiración, estrés, fracción activa y fracción con estrés disponible. Las agregaciones FSPM ponderan superficies reales de HRU de maíz; no se dispone de ponderación fraccional CDL independiente.

Para cultivo inactivo, LAI, raíz, biomasa y transpiración tienen cero conocido; estrés permanece ausente. Se codifica estrés ausente como cero acompañado de su fracción de disponibilidad. Esta codificación no equivale a medir ausencia de estrés. Los faltantes estructurales de features se rechazan.

Cada brazo contó con seis candidatos y el mismo presupuesto. Pesos y escaladores se ajustaron solo en TRAIN; ambos seleccionados fueron Ridge α = 10. No se reajustaron en TRAIN+VALIDATION ni en TEST. La climatología mensual y las correcciones afines A/B se ajustaron únicamente en TRAIN. Los inputs abarcan el mes completo, por lo que las salidas son retrospectivas y no pronósticos adelantados. D frente a C cambia simultáneamente referencia física y features; no es una ablación pura de valor vegetal.

### 2.4 Métricas, incertidumbre y decisión

Se empleó el evaluador canónico del repositorio para RMSE, MAE, NSE, PBIAS y KGE modificado con cociente de coeficientes de variación. PBIAS es positivo cuando la simulación excede la observación. Se usa ΔRMSE = RMSE(A) − RMSE(D), positivo si D mejora.

El contraste principal usa bootstrap circular pareado de bloques móviles de 12 meses, cinco bloques por réplica truncados a 60 meses, 2.000 réplicas, semilla 42 y percentiles bilaterales al 95 %. La misma secuencia de meses se aplica a ambos errores. Las máscaras de elegibilidad se aplican después del muestreo, evitando cerrar huecos en la sensibilidad. H1 se respalda solo si el límite inferior absoluto es mayor que cero y todas las réplicas están definidas. No se aplica un umbral arbitrario de 15 %. Los contrastes secundarios son descriptivos y no se ajustaron por multiplicidad.

## 3. Resultados

### 3.1 Evaluación temporal

Las métricas completas de TRAIN, VALIDATION, TEST y sensibilidad se entregan en `metrics.csv`; la tabla siguiente corresponde al TEST principal.

| Variante | RMSE (m³/s) | MAE (m³/s) | NSE | KGE | PBIAS (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 3,695 | 2,154 | 0,268 | 0,434 | −32,087 |
| B | 3,579 | 2,087 | 0,313 | 0,479 | −28,626 |
| C | 2,749 | 1,997 | 0,595 | 0,424 | +44,616 |
| D | 4,517 | 2,588 | −0,094 | 0,219 | +65,501 |

**Figura 1:** hidrograma mensual observado y A/B/C/D, `figures/monthly-test.png`. Las predicciones muestran una corrección con sesgo positivo en C/D pese al menor RMSE puntual de C.

**Figura 2:** reducciones de RMSE e intervalos pareados, `figures/contrasts.png`. D/A: −0,822 m³/s, IC95 [−3,286; +1,871]; la decisión es **H1 no respaldada**. El intervalo que incluye cero tampoco demuestra empeoramiento significativo.

C/A presenta reducción puntual de 25,598 %, pero su intervalo absoluto [−0,397; +2,199] incluye cero. No se reemplaza el contraste primario por C después de conocer TEST. B/A mejora puntualmente 3,133 %, con intervalo descriptivo [0,011; 0,226] m³/s; esto no constituye una validación confirmatoria de fisiología.

### 3.2 Sensibilidad y funcionamiento

Sin estimados, RMSE A/B/C/D es 4,419/4,251/2,782/5,384 m³/s sobre 36 meses. La reducción D/A es −0,965 m³/s, IC95 [−4,482; +2,857], manteniendo H1 no respaldada. Las diferencias de soporte impiden interpretar esta sensibilidad como el mismo conjunto anual completo.

Se publicaron diez corridas físicas TEST A/B, 3.652 frames diarios y predicciones C/D mensuales. La plataforma registra corridas del usuario, expone estado de ejecución, consulta física y visor, compara el experimento global y descarga artefactos. La geometría anatómica y el terreno son ilustrativos; los identificadores GIS no demuestran un mapeo poligonal completo ni plantas observadas. La corrección mensual no se distribuye artificialmente sobre los días ni modifica el playback físico.

## 4. Discusión y límites

El resultado negativo delimita el rendimiento del contrato congelado en una cuenca y bajo un escenario agrícola estático. El sesgo de calibración y la diferencia entre señales físicas y residuales condicionan la interpretación. Menor error de salida no implica procesos internos correctos ni balance de agua conservado por la corrección ML.

No se incorporó LAI observado a ajuste o evaluación: el LAI empleado es modelado. Una futura evaluación vegetal requiere datos independientes, controles de calidad y correspondencia espacial/temporal explícita. ET/PET externos usados en diagnósticos no se presentan como mediciones fisiológicas de referencia en este experimento.

La selección usa solo 60 meses TRAIN y 36 VALIDATION de desarrollo; la dependencia temporal y el limitado TEST de 60 meses deben acompañar cualquier conclusión. Los contrastes secundarios no tienen control de multiplicidad. D/C no identifica causalmente el aporte de features FSPM. No se demostraron generalización multicuenca, rendimiento espacial, CMIP6 ni recomendaciones operacionales. La plataforma es un gemelo digital experimental de estados modelados y reproducción histórica; no se demostró asimilación operativa en tiempo real.

TEST ya es conocido. Toda revisión del modelo deberá contar con otro holdout independiente o declararse como desarrollo. Repetir la receta congelada en la interfaz no crea evidencia confirmatoria adicional.

## 5. Conclusiones

El sistema implementa un flujo funcional y trazable de planta–cuenca, inferencia mensual y evidencia descargable. Bajo la comparación reservada fijada, D no demuestra reducción robusta de RMSE frente a A. La sensibilidad conserva esa conclusión. El aporte defendible es el diseño reproducible, la evaluación explícita de sus límites y la publicación del resultado negativo, sin confundir capacidad de uso con validación física o fisiológica.

## Disponibilidad de datos y código

El ZIP contiene protocolos, reportes congelados, series mensuales, bootstrap, esquemas, linaje, bundles C/D y recetas de análisis. `reproduce.md` detalla dependencias, comprobaciones y los inputs externos requeridos para reproducir SWAT+ y persistencia. Los proyectos SWAT+, ejecutable, grillas meteorológicas y la base PostgreSQL completa son dependencias locales separadas; no se afirma que este ZIP las incluya. No contiene credenciales. La referencia a TEST en metadatos de registro es posterior y no altera los pesos ni metadatos congelados originales.

## Referencias verificadas para este borrador

- Alemayehu, T., van Griensven, A., Woldegiorgis, B. T., y Bauwens, W. (2017). *An improved SWAT vegetation growth module and its evaluation for four tropical ecosystems*. Hydrology and Earth System Sciences, 21, 4449–4467. [doi:10.5194/hess-21-4449-2017](https://hess.copernicus.org/articles/21/4449/2017/).
- Yang, R., Wu, J., Gan, G., y Guo, R. (2026). *Disentangling the key drivers of water balance in Central Asia's Lake Balkhash: A relative contribution assessment*. Hydrology and Earth System Sciences, 30, 4271–4292. [doi:10.5194/hess-30-4271-2026](https://hess.copernicus.org/articles/30/4271/2026/).

Estas referencias contextualizan las intervenciones; la revisión completa, autoría, declaraciones y formato editorial se prepararán antes de enviar el artículo.

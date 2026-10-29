# Propuesta para el artículo: v2 exploratoria

## Métodos

Se amplió la calibración física con nueve combinaciones de ESCO (0,01, 0,025 y 0,05) y flo_min (8, 10 y 12 m), con t_fc=6 h. Se simuló desde 2000 y se calificó solo 2005–2012 frente a caudales diarios USGS aprobados, incluyendo estimados, sin imputación. Se fijaron antes de ejecutar NSE ≥ 0 y |PBIAS| ≤ 30 % como criterios conjuntos de aceptación; de no cumplirlos ningún candidato, se seleccionó exploratoriamente el menor |PBIAS|.

Con la referencia seleccionada se derivaron parámetros vegetales FSPM para 2010 y se congelaron antes de las simulaciones anuales. El diseño cruzó la física A/B con 14 predictores comunes o estos más siete vegetales. Los estados de A se calcularon pasivamente con su propio calendario y humedad SWAT+, sin transferir sus parámetros vegetales; B recibió la parametrización congelada. Las cuatro correcciones residuales usaron Ridge α=10, escaladores y ajustes solo en 2013–2017, y caudal corregido truncado a cero. El estrés ausente se codificó con un indicador de disponibilidad; se conservaron los ceros de cultivo inactivo. Las variables del mes completo producen estimaciones retrospectivas.

Se evaluaron todos los brazos en fechas comunes, con cobertura diaria mensual mínima del 90 %, y se incluyeron climatología y correcciones afines ajustadas en TRAIN. Los intervalos de ΔRMSE se obtuvieron por bootstrap circular pareado de 2000 réplicas, semilla 42 y bloques de 3, 6, 12 y 24 meses, aplicando la elegibilidad tras el remuestreo del calendario completo. Se repitió el análisis excluyendo registros A,e y recalculando medias y soporte. Los contrastes factoriales y su interacción son descriptivos, sin ajuste por multiplicidad. TEST 2021–2025 ya era conocido y se considera exploratorio.

## Resultados

Ninguno de los nueve candidatos cumplió ambos criterios físicos. La referencia exploratoria seleccionada alcanzó RMSE 4,271 m³/s, NSE 0,712, KGE′ 0,618 y PBIAS −33,958 %, frente a 4,718 m³/s, 0,649, 0,541 y −40,605 % en la referencia original. El contrato modelado derivado en 2010 tuvo LAI potencial 5,028, altura máxima 2,633 m y raíz máxima 1,200 m.

En TEST conocido, el RMSE fue 3,044 y 2,933 m³/s para A y B físicas; 2,652 y 3,806 para A14 y A21; y 2,635 y 3,584 para B14 y B21. Añadir variables vegetales dio ΔRMSE de −1,153 m³/s en A y −0,949 en B; con bloques de 12 meses, los intervalos descriptivos fueron [−2,388; −0,054] y [−1,957; −0,089], respectivamente. La interacción fue 0,205 [−0,038; 0,434] m³/s. Tras excluir A,e, quedaron 36 meses elegibles y los intervalos correspondientes fueron [−3,210; −0,068], [−2,665; −0,119] y [−0,059; 0,556]. Cada intervalo utilizó 2000 réplicas válidas. Estos resultados no establecen efectos causales generales.

## Limitaciones

La referencia sigue incumpliendo el criterio físico de sesgo. La nueva comparación no es independiente porque TEST ya fue examinado. Se usaron una cuenca, manejo y drenaje experimentales y estados vegetales modelados sin validación fisiológica independiente. La corrección residual no asegura conservación hídrica. La serie de cinco años limita el bootstrap, especialmente con bloques de 24 meses; los intervalos de múltiples comparaciones son descriptivos y pueden cambiar con el tamaño de bloque.

## Disponibilidad de datos y código

Se preparó localmente un paquete con inputs físicos, observaciones USGS, protocolos, hashes, contratos, código, modelos, predicciones, métricas e intervalos. El análisis y entrenamiento residuales se reprodujeron en una carpeta limpia utilizando el entorno existente; los nueve candidatos de calibración y las trece parejas físicas anuales también se reprodujeron desde carpetas limpias con el mismo entorno y ejecutable. Una instalación independiente no se ha ensayado. Las observaciones USGS pueden revisarse; se conserva la instantánea identificada por hash. La licencia del código propio y las condiciones de distribución pública de los insumos integrados requieren decisión y revisión de los autores; no se afirma publicación externa.

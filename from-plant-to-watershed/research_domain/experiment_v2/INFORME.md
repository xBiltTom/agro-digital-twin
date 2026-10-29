# Informe de ejecución v2

## Clasificación

| Tarea | Estado | Evidencia y límites |
|---|---|---|
| Auditoría, rama y protocolo | COMPLETADA | Commit 397257ebb9b12cf33f2e29e004480246d773cc90; `PROTOCOLO.md` fijado antes de la búsqueda v2. |
| Búsqueda física | COMPLETADA | Nueve candidatos reales, parámetros, métricas, predicciones y selección en `calibracion.csv` y `runs/`. |
| Aceptación de la referencia física | BLOQUEADA | Ningún candidato del presupuesto cumple el límite absoluto de PBIAS de 30 %. Se retiene únicamente como exploratoria; una nueva búsqueda exige otro protocolo y no garantiza aceptación. |
| Derivación y congelación vegetal | COMPLETADA | `frozen_plant_contract_v2.json`, derivación 2010, semilla 42, 1000 plantas/grupo; convergencia en dos iteraciones. |
| Simulaciones anuales y factorial | COMPLETADA | 2013–2025, A y B diarios; FSPM de A pasivo sobre su propia salida; A14, A21, B14, B21 y A/B físicos. |
| Evaluación y bootstrap | COMPLETADA | 60 meses TEST elegibles en primario y 36 al excluir A,e; 2000 réplicas por bloque, 3/6/12/24 meses, índices comunes, máscara después del muestreo; contrastes descriptivos sin ajuste por multiplicidad. |
| Reproducción de análisis y modelos | COMPLETADA | Carpeta limpia con mismos insumos y entorno existente; cinco CSV idénticos y recálculo independiente de 36 filas de métricas. No se probó instalación limpia de dependencias. |
| Reproducción física completa | COMPLETADA | En carpetas limpias se repitieron los nueve candidatos, la derivación vegetal y las 13 parejas anuales. Coincidieron 864 caudales de calibración y 4.748 días por brazo; el análisis completo volvió a producir los mismos CSV. Se usaron el ejecutable y entorno existentes, no una instalación limpia de dependencias. |
| Licencias y publicación | BLOQUEADA | Los autores deben elegir licencia para el código propio y confirmar permisos y créditos de datos integrados antes de distribuirlos. La investigación local no depende de esa decisión. |

## Física

La referencia original tuvo RMSE 4,718285, NSE 0,648924, KGE′ 0,541496 y PBIAS −40,604751 %. La regla previa seleccionó v2-cal-02 (ESCO 0,01; flo_min 10 m; t_fc 6 h), RMSE 4,271337, NSE 0,712286, KGE′ 0,618364 y PBIAS −33,958292 %. El sesgo incumple la aceptación. Para cada valor de ESCO los escenarios flo_min 10 y 12 m dieron resultados idénticos dentro de esta búsqueda, lo cual no demuestra inoperancia global. Los parámetros son exploratorios, no mediciones locales.

El contrato de 2010 contiene LAI potencial 5,028221, altura 2,632671 m y raíz 1,200219 m. Son estados modelados no validados por observaciones fisiológicas. El contrato se congeló antes de las simulaciones anuales y del ajuste residual.

## Factorial retrospectivo

Sobre TEST conocido y 60 meses elegibles:

| Configuración | RMSE (m³/s) | NSE | PBIAS (%) |
|---|---:|---:|---:|
| A física | 3,044 | 0,503 | −14,507 |
| B física | 2,933 | 0,539 | −11,169 |
| A14 | 2,652 | 0,623 | 49,362 |
| A21 | 3,806 | 0,224 | 62,746 |
| B14 | 2,635 | 0,628 | 49,462 |
| B21 | 3,584 | 0,312 | 61,216 |

La convención es ΔRMSE=RMSE(referencia)−RMSE(configuración). Con bloques de 12 meses, el efecto de añadir vegetación en A fue −1,153 m³/s [−2,388; −0,054] y en B fue −0,949 [−1,957; −0,089]; 2000 réplicas válidas. La diferencia de esos efectos, B menos A, fue 0,205 [−0,038; 0,434]. Al excluir A,e, quedaron 36 meses y los efectos fueron −1,766 [−3,210; −0,068] y −1,465 [−2,665; −0,119], interacción 0,301 [−0,059; 0,556]. Son comparaciones internas exploratorias, no pruebas de causalidad. Los intervalos son descriptivos y no ajustados por múltiples contrastes. Con bloques de 24 meses hay pocos bloques efectivamente independientes; las conclusiones dependen de la longitud de la serie y del bloque.

Todos los resultados, incluido MAE y KGE′, los cuatro bloques y referencias climatológica y afines están en `metricas_v2.csv` y `contrastes_v2.csv`. `comparacion_metricas_v2.csv` compara las configuraciones homólogas originales y nuevas; A21 no existía originalmente. El valor `nan` para estrés en cultivo inactivo representa ausencia, se codifica 0 solo para Ridge junto con fracción de disponibilidad. Estructura y transpiración de cultivo inactivo son ceros biológicos; se rechazan ausencias estructurales. Las variables mensuales completas son retrospectivas, no pronósticos adelantados.

## Ejecución y comprobaciones

La primera ejecución de 2013, 2018 y 2022 se detuvo por una comprobación de hash equivocada: el adaptador normaliza la copia de inputs. Se conservaron los mensajes en `ejecucion_errores.log`; se verificaron hashes de outputs, transferencia congelada, calendario y convergencia antes de recuperar esas salidas y recalcular FSPM. El hash de A se comparó antes/después de mutación en la copia normalizada y el original se comprobó inalterado. Se detuvo una corrida duplicada de 2025 y se completó otra en una copia independiente. Se verificaron fechas y climatología idénticas A/B, valores finitos, estrés y ceros biológicos en los 13 años. La rama incluye series diarias compactas; el archivo local de inputs físicos no se redistribuye hasta revisar sus condiciones y los outputs nativos voluminosos se descartaron; sus hashes individuales no se han conservado para todos los años.

## Decisiones y datos que aportarían los autores

1. Elegir una licencia autorizada para código propio; verificar condiciones de distribución y créditos de Boone CDL y derivados antes de publicar.
2. Aportar si existen rotaciones, manejo, drenaje y observaciones independientes de vegetación o un periodo realmente no examinado. No son requisitos para ejecutar los cálculos realizados; permitirían contrastar los supuestos o evaluar de forma independiente.
3. Para verificar portabilidad a otra instalación, reconstruir el ejecutable con la cadena de compilación fijada e instalar las dependencias; esa instalación independiente no se ha ensayado. No se ha demostrado que falten inputs esenciales en este espacio de trabajo.

La reproducción física limpia inicial falló antes de iniciar SWAT+ por una ruta simbólica no resuelta; el detalle está en `reproduccion_error_ruta.log`. Se corrigió la resolución de la ruta y se ejecutó íntegramente. Se interrumpió una copia duplicada de 2025; la corrida independiente de ese año terminó y coincidió. El recibo `reproduccion_fisica_limpia.json` contiene hashes y resultados por año.

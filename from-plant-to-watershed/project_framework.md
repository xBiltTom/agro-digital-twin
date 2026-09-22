# From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models with SWAT Hydrology and Downscaled Climate Projections

## Problema
Los gemelos digitales agrícolas operan a escala de metro o hectárea, pero las decisiones de política hídrica y adaptación climática requieren comprensión a escala de cuenca hidrográfica. No existe un framework que conecte el gemelo de una planta de maíz individual con el modelo hidrológico de una cuenca completa y las proyecciones climáticas.

## Objetivo
Desarrollar un gemelo digital multi-escala que acople un modelo funcional-estructural de planta (FSPM) con SWAT+ (hidrología de cuenca) y proyecciones climáticas descendentes (CMIP6), permitiendo simular el efecto de prácticas de manejo a nivel de planta sobre el balance hídrico regional.

## Hipótesis
* **$H_0$:** El acoplamiento planta-cuenca no mejora la predicción de escorrentía vs. SWAT+ con parámetros de cultivo promedio. 
* **$H_1$:** El twin multi-escala reduce el RMSE de escorrentía mensual en $\geq 15\%$ con mejor representación de la variabilidad espacial de rendimiento.

## Metodología
* **Módulo 1: Datos:** USDA NASS (rendimiento por condado), SoilGrids 2.0 (suelo), CHIRPS (precipitación), Landsat (uso de suelo, serie histórica 1984–2023), CMIP6 (proyecciones SSP2-4.5 y SSP5-8.5, downscaled con bias correction).
* **Módulo 2: Arquitectura multi-escala:** 
  * **Nivel 1 (planta):** modelo FSPM simplificado (maíz, 3D, arquitectura de raíces y canopeo) parametrizado con datos de campo. 
  * **Nivel 2 (campo):** agregación de 1000 plantas con variabilidad espacial (USDA BARC). 
  * **Nivel 3 (cuenca):** SWAT+ con HRUs (Hydrologic Response Units) informadas por los outputs del Nivel 2 (ET, infiltración, escorrentía). 
  * **Nivel 4 (clima):** forzantes de CMIP6 downscaled.
* **Módulo 3: Validación:** validación cruzada espacial (cuencas de entrenamiento vs. test). Comparación contra SWAT+ estándar (parámetros de cultivo tabulados).
* **Módulo 4: Escenarios:** 
  * (a) aumento de temperatura $+2^\circ\text{C}$
  * (b) reducción de precipitación del $15\%$
  * (c) adopción de agricultura de conservación (siembra directa)
  * (d) cambio de maíz a sorgo.
* **Módulo 5: Impacto:** proyección de rendimiento bajo cambio climático, disponibilidad hídrica de cuenca, recomendaciones de política de uso de suelo.

## Pruebas estadísticas
* **KS:** Para validar distribución de escorrentía simulada vs. observada (USGS streamflow gauges).
* **Comparación:** Wilcoxon signed-rank para RMSE de escorrentía (twin multi-escala vs. SWAT+ estándar).
* **Sensibilidad:** Método de Sobol para identificar qué parámetros del FSPM (tasa de transpiración, profundidad radicular máxima, área foliar) más afectan la escorrentía de cuenca.
* **Predictiva:** RMSE, NSE (Nash-Sutcliffe Efficiency), PBIAS para escorrentía mensual; RMSE, $R^2$ para rendimiento.
* **Bootstrap:** IC $95\%$ para rendimiento proyectado bajo SSP5-8.5.

## Protocolo
* **Tipo:** Simulación basada en modelos con validación hidrométrica.
* **DAG:** $\text{CO}_2$ + Temperatura + Precipitación $\rightarrow$ Crecimiento de planta $\rightarrow$ ET + Infiltración $\rightarrow$ Escorrentía $\rightarrow$ Disponibilidad hídrica. Manejo agrícola modula cada flecha.
* **Población:** Cuencas hidrográficas agrícolas del Corn Belt de EE.UU. con datos de USGS $\geq 20$ años.
* **Inclusión:** Cuencas con $\geq 60\%$ de área agrícola, datos de caudal diarios, datos de uso de suelo Landsat. 
* **Exclusión:** Cuencas con presas mayores que alteren el régimen.
* **Pre-registro:** OSF.
* **Ética:** Datos públicos. Consideración de impacto en comunidades rurales aguas abajo.
* **Timeline:** 
  * Meses 1–3: revisión + datos. 
  * Meses 4–7: calibración FSPM + SWAT+. 
  * Meses 8–11: acoplamiento multi-escala. 
  * Meses 12–14: validación. 
  * Meses 15–17: redacción.

## Datasets
USDA NASS, CHIRPS, SoilGrids 2.0, Landsat (USGS), CMIP6 (NASA NEX-GDDP).

## Revistas
* **Agricultural Systems** (CiteScore ~9.0, afinidad: modelado de sistemas + escalabilidad)
* **Remote Sensing of Environment** (CiteScore ~16.0, afinidad: teledetección + series temporales)
* **Science of the Total Environment** (CiteScore ~12.5, afinidad: impacto ambiental + cuencas)
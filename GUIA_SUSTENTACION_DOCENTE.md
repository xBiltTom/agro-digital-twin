# 🎓 Guía Maestra para la Sustentación con el Docente
## Proyecto: *From Plant to Watershed — Gemelo Digital Agrícola Multiescala*
**Asignatura:** Ingeniería de Software II — Ciclo VIII  

---

## 📌 1. Resumen Ejecutivo del Proyecto (Speech de 30 segundos)

> *"Profesor, nuestro proyecto resuelve un problema crítico en la agricultura moderna y la gestión del agua: los gemelos digitales tradicionales operan aislados a nivel de metro o parcela, sin entender el impacto en la cuenca hidrográfica completa, mientras que los modelos de cuenca tradicionales ignoran la fisiología de la planta.*  
> *Nosotros desarrollamos una **plataforma de software multiescala** que conecta la fisiología individual de una planta de maíz (**FSPM**), la dinámica del suelo en parcela (**HRUs**) y la hidrología de cuenca completa (**SWAT+** con 36 subcuencas reales en Iowa), integrando un **Visor 3D interactivo** y un **Copiloto de IA con LangChain** que traduce millones de datos numéricos en decisiones concretas de política hídrica y manejo agronómico."*

---

## 🏛️ 2. Las 4 Escalas del Gemelo Digital (El Núcleo del Software)

Explícale al profesor que el sistema no es un simple dashboard, sino una **cadena causal jerárquica de 4 niveles**:

```text
[Nivel 4: Clima & Escenarios] ──► Aumento +2°C / Reducción -15% lluvia / Siembra directa / Sorgo
              │
              ▼
[Nivel 1: Micro / Planta FSPM] ──► 1,000 plantas de maíz, dinámica de GDD, LAI foliar, raíces de 1.2 m, estrés Feddes
              │
              ▼
[Nivel 2: Meso / Parcela HRU]  ──► Humedad volumétrica del suelo (0-100 cm), curva número SCS-CN, infiltración
              │
              ▼
[Nivel 3: Macro / Cuenca SWAT+]──► 36 subcuencas hidrológicas, 37 ríos/canales, aforo USGS 05451210 (South Fork Iowa)
```

1. **Micro (Planta Individual - FSPM simplificado):**
   * Modela 1,000 plantas de maíz representativas con variación paramétrica poblacional.
   * Modela el crecimiento foliar (LAI), profundidad de raíces activas ($1.20\text{ m}$), transpiración y función de estrés hídrico de Feddes ($\alpha$).
2. **Meso (Parcela / Comunidad HRU):**
   * Agregación estadística de las plantas en unidades de respuesta hidrológica (*HRU*).
   * Balance hídrico del suelo en horizontes superficiales ($0-30\text{ cm}$) y profundos ($30-100\text{ cm}$).
3. **Macro (Cuenca Hidrográfica SWAT+):**
   * Implementado sobre la cuenca real **South Fork Iowa River** (`USGS 05451210`, $560.89\text{ km}^2$, condados de Hamilton y Hardin, Iowa, EE. UU.).
   * Delineación hidrográfica real: **36 subcuencas** y red fluvial de **37 canales de afluencia** que desembocan en la estación hidrométrica de New Providence.
4. **Clima y Escenarios de Cambio Climático:**
   * Evalúa los 4 escenarios de la investigación: $+2^\circ\text{C}$ de temperatura, $-15\%$ de precipitación, adopción de siembra directa (`no-till / zerotill`) y sustitución de maíz por sorgo granífero (`grsg`).

---

## 🤖 3. El Módulo de Inteligencia Artificial y LangChain

### ¿Qué problema resuelve este módulo?
Un motor de simulación como SWAT+ genera miles de datos numéricos diarios ($Q=58.06\text{ m}^3/\text{s}$, $ET=133.1\text{ mm}$, $\text{precipitación}=1092.9\text{ mm}$, $\theta=32.8\%$).  
Para un funcionario de cuenca o un agricultor, **los números y gráficos fríos no dicen directamente qué decisiones tomar**.  
El módulo de IA automatiza el **Módulo 5 de la investigación (Impacto y Políticas de Cuenca)**: toma el balance numérico de la simulación y genera un **diagnóstico biológico comprensible y recomendaciones prácticas de manejo agrícola**.

### ¿Cuál es el rol técnico de LangChain?
LangChain actúa como el **orquestador y puente de ingeniería** entre nuestro backend FastAPI y los Modelos de Lenguaje Grande (LLMs):

1. **Salida Estructurada Garantizada (*Schema Enforcement*):**
   * Sin LangChain, un LLM responde texto libre o prosa desordenada.
   * LangChain fuerza al modelo a responder un **JSON estricto** validado con Pydantic (`executive_summary`, diagnóstico en las 3 escalas `micro_scale_plant`, `meso_scale_field`, `macro_scale_watershed`, `climate_resilience_assessment` y `policy_recommendations`). La interfaz de React/Next.js lo consume directamente sin romperse jamás.
2. **Independencia del Proveedor (*Vendor-Agnostic*):**
   * La arquitectura está desacoplada. Hoy podemos usar Google Gemini (`gemini-2.5-flash`), mañana OpenAI (`gpt-4o-mini`), o un modelo local sin costo como Llama 3 con Ollama, **sin cambiar ni una sola línea del código de negocio**.
3. **Inyección de Contexto Científico y Control de Alucinaciones:**
   * Empaqueta las métricas reales y el contexto hidrográfico de Iowa dentro de un prompt de sistema blindado. La IA **no inventa números**: si un dato no está en el balance de la corrida, lo reporta con honestidad científica en las limitaciones.
4. **Alta Disponibilidad y Resiliencia (Motor de Contingencia):**
   * Si en plena sustentación no hay internet, no hay saldo en la API o no se configuró clave, **el sistema no falla**. Se activa automáticamente un **motor experto científico determinista** que analiza los ratios de escorrentía y humedad y devuelve el mismo formato JSON en 200 ms.

---

### 📂 Archivos clave de la implementación:
* **Servicio Backend:** [`backend/app/services/ai_insights.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/backend/app/services/ai_insights.py)
* **Endpoints API:** `GET /api/v1/simulations/{id}/ai-insights` y `POST /api/v1/simulations/{id}/ai-insights` en [`simulations.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/backend/app/api/v1/simulations.py).
* **Esquema Pydantic:** [`AIInsightsResponse` en `schemas/simulation.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/backend/app/schemas/simulation.py).
* **Componente Frontend:** [`AIInsightsCard.tsx`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/frontend/src/components/simulations/AIInsightsCard.tsx) en [`simulations/page.tsx`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/frontend/src/app/(dashboard)/simulations/page.tsx).
* **Prueba Unitaria:** [`test_ai_insights.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESIÓN-O1/gemelos-digitales/from-plant-to-watershed/backend/tests/test_ai_insights.py).

---

## 🌐 4. El Visor 3D Multiescala (`/twin-3d`)

Si el profesor te pide ver el gemelo digital en 3D:
* **Tecnología:** React Three Fiber (Three.js sobre React 19 / Next.js 16).
* **Geometría Real GIS:** No son cubos aleatorios ni terrenos sintéticos. Los polígonos corresponden a los **GeoPackages reales de la delineación SWAT+** (`subbasins.gpkg`, `channels.gpkg`, `watershed_result.json` de Iowa).
* **Interacción:**
  * **Escala Macro:** Muestra la cuenca completa ($560.89\text{ km}^2$), la divisoria topográfica iluminada, las 36 subcuencas coloreadas según el cultivo dominante (maíz, soya, rotación, franja riparia), la red de 37 canales con agua en movimiento y la estación de aforo USGS 05451210 en New Providence con caseta, panel solar y telemetría de caudal.
  * **Clic en cualquier subcuenca:** La cámara hace zoom cinemático hacia la escala **Meso (Parcela)**.
  * **Escala Micro:** Permite observar el modelo fisiológico tridimensional de la planta de maíz individual.

---

## 🧪 5. El Subproyecto de Machine Learning (`agro-digital-twin-st`)

Si el profesor pregunta por la carpeta `agro-digital-twin-st`:
* Es el **Laboratorio de IA y Modelos Sustitutos (*Surrogate Models*)** desarrollado bajo la metodología **CRISP-DM** en Streamlit.
* **Modelos entrenados:** Random Forest, XGBoost, SVR, CNN-LSTM y **LSTM Autoencoder + Random Forest** (Modelo Campeón, $NSE = 0.9861$, $RMSE = 2.58\text{ mm}$).
* **Rigor anti-fuga de datos (*Leak-Free*):** Ventanas temporales 3D `(samples, timesteps, features)` aisladas por cuenca/HRU y particiones temporales estrictas (Train 65%, Val 15%, Test 20%).
* **Pruebas Estadísticas:** Wilcoxon signed-rank, Kolmogorov-Smirnov, Bootstrap IC 95% y análisis de sensibilidad de Sobol.
* **Desacoplamiento:** Exporta paquetes autocontenidos (`ModelBundle`) que FastAPI consume en producción sin depender de Streamlit.

---

## 🎯 6. Guion Recomendado para la Presentación (4 Minutos)

### Minuto 1: Planteamiento del Problema
1. Abre el navegador en `http://localhost:3000`.
2. Explica que la plataforma conecta desde la célula de la planta hasta la desembocadura de la cuenca hidrográfica para responder a los retos del cambio climático.

### Minuto 2: El Gemelo 3D de Iowa
1. Ve a la ruta **`/twin-3d`**.
2. Muestra la cuenca de South Fork Iowa River: explica que los 36 polígonos y los 37 canales fluviales provienen de datos geoespaciales reales de SWAT+.
3. Pasa el cursor por las subcuencas para mostrar el tooltip interactivo y haz clic en una para hacer zoom a la escala Meso.

### Minuto 3: Simulaciones y el Copiloto con LangChain
1. Ve a la ruta **`/simulations`**.
2. Selecciona una simulación de la lista en la izquierda.
3. Señala la tarjeta superior: **"Diagnóstico Científico & Recomendaciones de Política (IA)"**.
4. Muestra cómo LangChain sintetizó el balance de masa (1092.9 mm de lluvia, 283.1 mm de escorrentía, 58.06 m³/s de caudal).
5. Cambia entre las pestañas **Micro (Planta)**, **Meso (Parcela)** y **Macro (Cuenca)** para mostrar la coherencia multiescala.
6. Muestra las recomendaciones concretas de manejo (siembra directa, zonas riparias, rotación a sorgo).
7. Pulsa el botón **Regenerar** para demostrar que la respuesta se actualiza dinámicamente.

### Minuto 4: Arquitectura de Software y Código
1. Menciona que el backend sigue principios de **Clean Architecture**: el núcleo científico (`scientific_core`) es Python puro sin dependencias web, mientras que FastAPI y Next.js gestionan la persistencia y la interfaz.

---

## ❓ 7. Preguntas Típicas del Docente y Cómo Responderlas

#### P1: "¿Por qué usaron LangChain en lugar de llamar directamente a la API de OpenAI o Gemini con `fetch` o `requests`?"
> **Respuesta:** *"Porque LangChain nos aporta tres ventajas de ingeniería de software: primero, **salidas estructuradas consistentes** mediante validación de esquemas JSON, evitando que un cambio en la prosa del LLM rompa el frontend; segundo, **independencia de proveedor (*vendor-agnostic*)**, permitiéndonos alternar entre Gemini, OpenAI o modelos locales con solo cambiar una variable de entorno; y tercero, **gestión de resiliencia**, interceptando errores de red o cuota para activar automáticamente nuestro motor experto de respaldo sin interrumpir la experiencia de usuario."*

#### P2: "¿La Inteligencia Artificial es la que calcula el caudal o la evapotranspiración?"
> **Respuesta:** *"No, profesor. Los cálculos biofísicos y el balance de masa los resuelven estrictamente los modelos físicos deterministas (**SWAT+**, **FSPM** y las ecuaciones de conservación de agua). La física nunca debe delegarse a un LLM porque los modelos de lenguaje sufren alucinaciones numéricas. El rol de LangChain es **interpretativo y de síntesis**: lee las salidas de los modelos físicos y las traduce a conclusiones científicas y recomendaciones de política hídrica."*

#### P3: "¿Qué pasa si en plena sustentación se cae internet o no hay crédito en la API del LLM?"
> **Respuesta:** *"El sistema es tolerante a fallos por diseño. En `ai_insights.py` implementamos un **motor heurístico científico de contingencia**. Si LangChain detecta que no hay API key o no hay conexión, ejecuta el análisis biofísico localmente usando reglas de balance hídrico y entrega exactamente el mismo esquema JSON en menos de 200 ms."*

#### P4: "¿Los polígonos de la cuenca 3D son generados al azar?"
> **Respuesta:** *"No. Provienen de la delineación hidrológica oficial de la cuenca **South Fork Iowa River (código hidrológico USGS 05451210)**, extraída de los archivos GeoPackage (`subbasins.gpkg` y `channels.gpkg`) generados por SWAT+. Cada una de las 36 subcuencas tiene su área real calculada en kilómetros cuadrados y su clasificación de cultivo según el Cropland Data Layer (CDL) de USDA."*

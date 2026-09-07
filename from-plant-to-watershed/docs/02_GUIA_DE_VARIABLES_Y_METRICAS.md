# 02. Guía de Variables, Métricas y Valores del Sistema

Esta guía es el **diccionario de referencia** para entender exactamente qué significa cada número, gráfico, barra y etiqueta visible en el sistema, en qué unidades se mide y cuáles son los rangos óptimos y de alerta.

---

## 📊 1. Diccionario de Variables Biofísicas e Hidrológicas

### 💧 1. Caudal en el Exutorio del Río ($Q$ / Streamflow)
- **¿Qué es?**: El volumen total de agua que pasa por el punto más bajo de la cuenca (el río en el exutorio) en cada segundo.
- **Unidad de medida**: Metros cúbicos por segundo ($\text{m}^3/\text{s}$). *(Nota: $1\text{ m}^3/\text{s} = 1000\text{ litros por segundo}$)*.
- **Interpretación**:
  - `0.5 - 3.0 m³/s`: **Caudal de Estiaje / Seco** (época seca o sequía).
  - `3.0 - 12.0 m³/s`: **Caudal Normal / Régimen Base** (condiciones óptimas de la cuenca).
  - `12.0 - 25.0 m³/s`: **Crecida Moderada** (después de lluvias en la sierra).
  - `> 25.0 m³/s`: **Crecida Extrema / Alerta de Inundación** (tormentas torrenciales o evento El Niño).

---

### 🌱 2. Humedad Volumétrica del Suelo ($\theta$ / Soil Moisture)
- **¿Qué es?**: El porcentaje del volumen de suelo que está ocupado por agua líquida en la zona radicular activa ($0 - 100\text{ cm}$).
- **Unidad de medida**: Porcentaje volumétrico ($\%$ o $\text{cm}^3\text{ agua}/\text{cm}^3\text{ suelo} \times 100$).
- **Puntos Críticos del Suelo**:
  - `θ < 12%`: **Punto de Marchitez Permanente (PMP)**. La fuerza de succión del suelo es tan alta que las raíces no pueden extraer agua; la planta muere si se mantiene.
  - `12% - 20%`: **Déficit Hídrico**. La planta activa mecanismos de defensa (cierre de estomas).
  - `20% - 34%`: **Zona de Agua Fácilmente Asimilable (Capacidad de Campo - CC)**. Rango ideal para frutales y hortalizas.
  - `> 40%`: **Saturación / Asfixia Radicular**. Los poros del suelo se llenan de agua y falta oxígeno para las raíces.

---

### 🍂 3. Índice de Estrés Hídrico del Cultivo ($CWSI$ / Crop Water Stress Index)
- **¿Qué es?**: Un indicador normalizado adimensional de $0.0$ a $1.0$ que mide el grado de sed y sufrimiento hídrico de la planta.
- **Fórmula**: $\text{CWSI} = 1 - \frac{T_{act}}{T_{pot}}$
- **Interpretación y Códigos de Color en el Sistema**:
  - `0.00 - 0.25` 🟢 **Óptimo / Sin Estrés**: La planta transpira al 100% de su capacidad. Follaje verde esmeralda y ramas erguidas.
  - `0.25 - 0.55` 🟡 **Estrés Moderado**: Cierre parcial de estomas para ahorrar agua. Follaje verde-lima, leve reducción de fotosíntesis.
  - `0.55 - 1.00` 🔴 **Estrés Crítico / Severo**: Cierre estomático total, marchitez física de hojas (color amarillo/marrón) y detención del crecimiento de frutos.

---

### 🌿 4. Transpiración Real de la Planta ($Tr$ / Actual Transpiration)
- **¿Qué es?**: La cantidad de agua que las raíces absorben del suelo y que las hojas evaporan a la atmósfera a través de sus estomas durante el proceso de fotosíntesis en un día.
- **Unidad de medida**: Milímetros por día ($\text{mm}/\text{d}$). *(Nota: $1\text{ mm} = 1\text{ litro de agua por } \text{m}^2 \text{ de cultivo}$)*.
- **Rangos normales**:
  - `0.0 - 1.0 mm/d`: Muy baja (días fríos, noche o planta en sequía extrema).
  - `2.5 - 4.5 mm/d`: Normal para palto Hass adulto en clima templado.
  - `> 5.5 mm/d`: Muy alta (días calurosos y soleados con suficiente agua en suelo).

---

### ☀️ 5. Evapotranspiración de Referencia ($ET_0$ / Potential Evapotranspiration)
- **¿Qué es?**: La "sed de la atmósfera". Representa la cantidad máxima de agua que el sol, el calor, el viento y la sequedad del aire demandarían de una superficie vegetal estándar con agua infinita.
- **Unidad de medida**: Milímetros por día ($\text{mm}/\text{d}$).
- **Cálculo**: Ecuación de **Penman-Monteith FAO-56** / Método de **Turc** en función de la temperatura y radiación solar incidente.

---

### 🪵 6. Velocidad del Flujo de Savia en el Xilema (*Sap Flow Velocity*)
- **¿Qué es?**: La velocidad física a la que el agua con nutrientes asciende por los vasos conductores microscópicos (xilema) dentro del tronco del árbol, desde las raíces hasta las ramas más altas.
- **Unidad de medida**: Centímetros por hora ($\text{cm}/\text{h}$).
- **Interpretación**:
  - `0.0 - 3.0 cm/h`: Noche o estrés hídrico extremo (árbol "dormido").
  - `8.0 - 16.0 cm/h`: Flujo normal diurno en días soleados.
  - `> 20.0 cm/h`: Flujo máximo durante olas de calor con riego óptimo.

---

### 🌧️ 7. Precipitación Diaria ($P$ / Precip)
- **¿Qué es?**: Altura de agua de lluvia acumulada sobre el terreno en 24 horas.
- **Unidad de medida**: Milímetros ($\text{mm}$).
- **Escala de Intensidad**:
  - `0 mm`: Día despejado / seco.
  - `1 - 5 mm`: Llovizna leve.
  - `10 - 25 mm`: Lluvia moderada / buena para recarga de acuíferos.
  - `> 40 mm`: **Tormenta Torrencial** (dispara escorrentía rápida y riesgo de huaycos en quebradas).

---

### ⛰️ 8. Escorrentía Superficial ($Q_{surf}$)
- **¿Qué es?**: La porción del agua de lluvia que no logra infiltrarse en el suelo debido a pendientes pronunciadas o saturación, y resbala sobre la superficie hacia quebradas y ríos.
- **Unidad de medida**: Milímetros acumulados ($\text{mm}$).
- **Cálculo**: Método de la **Curva Número (SCS-CN)** del USDA adaptado por SWAT.

---

### 💧 9. Percolación Profunda ($w_{seep}$)
- **¿Qué es?**: El agua que logra atravesar toda la zona radicular (más allá de los $100\text{ cm}$ de profundidad) y continúa descendiendo por gravedad para recargar los acuíferos subterráneos de la cuenca.
- **Unidad de medida**: Milímetros ($\text{mm}$).

---

### 🌊 10. Volumen Total Descargado por la Cuenca
- **¿Qué es?**: La suma de todo el volumen de agua fluvial que ha salido por el río de la cuenca a lo largo de los días simulados.
- **Unidad de medida**: Hectómetros cúbicos ($\text{hm}^3$). *(Nota: $1\text{ hm}^3 = 1,000,000\text{ m}^3 = 1\text{ billón de litros}$)*.

---

## 🌍 2. Guía de Escenarios Climáticos CMIP6

El sistema permite simular el futuro del clima bajo las rutas socioeconómicas compartidas (**Shared Socioeconomic Pathways - SSP**) del 6º Informe del IPCC:

| Escenario | Nombre | Anomalía Térmica | Factor de Lluvia | Significado en la Simulación |
| :--- | :--- | :---: | :---: | :--- |
| **HISTORICAL** | Línea Base Histórica | $+0.0\text{ °C}$ | $1.00$ ($100\%$) | Clima promedio histórico de la cuenca Santa Eulalia - Rímac. |
| **SSP1-2.6** | Sostenibilidad y Mitigación | $+0.8\text{ °C}$ | $1.05$ ($+5\%$) | Escenario optimista con bajas emisiones y mayor estabilidad en caudales. |
| **SSP2-4.5** | Trayectoria Media / Estabilización | $+1.5\text{ °C}$ | $0.90$ ($-10\%$) | Escenario intermedio: aumento de demanda evaporativa y menor lluvia invernal. |
| **SSP5-8.5** | Alta Dependencia Fósil | $+3.2\text{ °C}$ | $0.75$ ($-25\%$) | **Escenario extremo**: severas olas de calor, sequías prolongadas y alto riesgo de estrés vegetal crónico. |

---

## 📌 3. Tabla Resumen de Alertas Rápidas

| Métrica | Icono | Estado Verde (Óptimo) | Estado Amarillo (Precaución) | Estado Rojo (Crítico) |
| :--- | :---: | :---: | :---: | :---: |
| **Caudal ($Q$)** | 🌊 | $3.0 - 12.0\text{ m}^3/\text{s}$ | $1.0 - 3.0$ o $12.0 - 25.0\text{ m}^3/\text{s}$ | $< 0.8$ o $> 25.0\text{ m}^3/\text{s}$ |
| **Humedad ($\theta$)** | 💧 | $22\% - 35\%$ | $15\% - 22\%$ o $35\% - 40\%$ | $< 12\%$ (Marchitez) o $> 42\%$ |
| **Estrés ($CWSI$)** | 🍂 | $0.00 - 0.25$ | $0.25 - 0.55$ | $> 0.55$ |
| **Transpiración ($Tr$)** | 🌿 | $2.5 - 5.0\text{ mm/d}$ | $1.0 - 2.5\text{ mm/d}$ | $< 0.8\text{ mm/d}$ |
| **Flujo de Savia** | 🪵 | $8.0 - 18.0\text{ cm/h}$ | $4.0 - 8.0\text{ cm/h}$ | $< 2.0\text{ cm/h}$ |

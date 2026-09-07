# 03. Modelos Científicos y Fórmulas Matemáticas

Este documento contiene las ecuaciones diferenciales y empíricas que gobiernan el motor biofísico del gemelo digital, implementadas en [`plant_model.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/from-plant-to-watershed/backend/app/services/plant_model.py), [`swat_hydrology.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/from-plant-to-watershed/backend/app/services/swat_hydrology.py) y [`climate_engine.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/from-plant-to-watershed/backend/app/services/climate_engine.py).

---

## 🌊 1. Ecuación General del Balance Hídrico SWAT

El modelo hidrológico SWAT (**Soil and Water Assessment Tool**) opera bajo el principio de **conservación estricta de masa de agua**:

$$SW_t = SW_{0} + \sum_{i=1}^t \left( R_{day} + I_{irr} - Q_{surf} - E_a - w_{seep} - Q_{gw} \right)$$

Donde para cada paso de tiempo diario $t$:
- $SW_t$: Contenido final de agua en el suelo ($\text{mm}$).
- $SW_0$: Contenido inicial de agua en el suelo ($\text{mm}$).
- $R_{day}$: Precipitación diaria ($\text{mm}$).
- $I_{irr}$: Riego suministrado en la parcela ($\text{mm}$).
- $Q_{surf}$: Escorrentía superficial calculada por Curva Número ($\text{mm}$).
- $E_a$: Evapotranspiración real del sistema ($\text{mm}$).
- $w_{seep}$: Percolación profunda hacia el acuífero ($\text{mm}$).
- $Q_{gw}$: Flujo de retorno de aguas subterráneas / caudal base ($\text{mm}$).

---

## ⛰️ 2. Escorrentía Superficial (Método de la Curva Número SCS)

La escorrentía superficial en las laderas de la cuenca se modela mediante la metodología del **USDA Natural Resources Conservation Service (SCS)**:

$$Q_{surf} = \begin{cases} 
\frac{\left( R_{day} - I_a \right)^2}{R_{day} - I_a + S} & \text{si } R_{day} > I_a \\
0 & \text{si } R_{day} \le I_a
\end{cases}$$

Donde:
- $I_a = 0.2 \cdot S$: Abstracción inicial (intercepción por hojas y retención en micro-depresiones).
- $S$: Máxima retención potencial del suelo ($\text{mm}$), calculada a partir del número de curva $CN$:

$$S = \frac{25400}{CN} - 254$$

### Ajuste Dinámico por Humedad Antecedente (AMC)
El valor de $CN$ no es estático; se ajusta dinámicamente según la humedad previa del suelo:
- **AMC I (Suelo Seco)**: $CN_1 = CN_2 - \frac{20(100 - CN_2)}{100 - CN_2 + \exp(2.533 - 0.0636(100 - CN_2))}$
- **AMC III (Suelo Húmedo)**: $CN_3 = CN_2 \cdot \exp(0.00673(100 - CN_2))$

---

## 🌿 3. Fisiología de la Planta y Modelo de Absorción Radicular de Feddes

### A. Demanda Evaporativa Potencial ($ET_0$ y $T_{pot}$)
La evapotranspiración de referencia se calcula mediante la formulación de **Turc** (calibrada para valles interandinos):

$$ET_0 = 0.013 \cdot \left(\frac{T_{mean}}{T_{mean} + 15}\right) \cdot \left( R_s \cdot 23.8846 + 50 \right)$$

La transpiración potencial del cultivo es función de su coeficiente de cultivo fenológico $K_c$:

$$T_{pot} = K_c \cdot ET_0$$

---

### B. Función de Reducción de Feddes ($\alpha(\theta)$)
Las raíces no absorben agua a tasa potencial si el suelo está muy seco o saturado. Feddes (1978) modela el factor de reducción $\alpha \in [0, 1]$ mediante una función continua por tramos:

$$\alpha(\theta) = \begin{cases} 
0 & \text{si } \theta \le \theta_{wp} \quad \text{(Punto de Marchitez Permanente)} \\
\frac{\theta - \theta_{wp}}{\theta_{crit} - \theta_{wp}} & \text{si } \theta_{wp} < \theta < \theta_{crit} \quad \text{(Zona de Estrés Hídrico)} \\
1.0 & \text{si } \theta_{crit} \le \theta \le \theta_{fc} \quad \text{(Rango Óptimo de Capacidad de Campo)} \\
\frac{\theta_{sat} - \theta}{\theta_{sat} - \theta_{fc}} & \text{si } \theta_{fc} < \theta \le \theta_{sat} \quad \text{(Asfixia por Exceso de Agua)} \\
0 & \text{si } \theta > \theta_{sat}
\end{cases}$$

La transpiración real del árbol es entonces:

$$T_{act} = \alpha(\theta) \cdot T_{pot}$$

---

### C. Velocidad del Flujo de Savia en el Xilema
El volumen diario transpirado debe fluir a través del área transversal del xilema activo ($A_{xylem}$) durante las horas de luz solar ($t_{luz} \approx 10\text{ h}$):

$$v_{sap} = \frac{T_{act} \cdot A_{canopy}}{A_{xylem} \cdot t_{luz}} \quad \left[\frac{\text{cm}}{\text{h}}\right]$$

---

### D. Índice de Estrés Hídrico del Cultivo ($CWSI$)
Mide la fracción de transpiración no satisfecha debido al cierre estomático:

$$CWSI = 1 - \frac{T_{act}}{T_{pot}} = 1 - \alpha(\theta)$$

- Si $\alpha = 1 \implies CWSI = 0$ (Planta sin estrés).
- Si $\alpha = 0 \implies CWSI = 1$ (Cierre estomático total / sequía crítica).

---

## 🌊 4. Tránsito Hidrológico Fluvial (Caudal en Exutorio $Q$)

El caudal total en la salida de la cuenca ($m^3/s$) integra la escorrentía rápida superficial con la respuesta lenta del acuífero (caudal base):

$$Q(t) = \left( \frac{Q_{surf} \cdot \text{Área}}{86400} \right) + Q_{gw}(t)$$

Donde el caudal base de aguas subterráneas sigue una ley de recesión exponencial de Boussinesq:

$$Q_{gw}(t) = Q_{gw}(t-1) \cdot e^{-\alpha_{gw} \Delta t} + w_{seep} \cdot (1 - e^{-\alpha_{gw} \Delta t})$$

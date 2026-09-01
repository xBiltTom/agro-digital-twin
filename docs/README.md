# 📚 Documentación Oficial del Sistema: Gemelo Digital AP-3
## *From Plant to Watershed: A Multi-Scale Digital Twin Framework*

Bienvenido a la documentación técnica y científica de la plataforma de **Gemelo Digital 3D Multiescala**. Este compendio está diseñado para explicar en detalle la arquitectura del sistema, el significado de cada variable mostrada, las fórmulas biofísicas empleadas y la guía de uso de cada módulo.

---

## 🗺️ Índice de Documentos

| Documento | Descripción |
| :--- | :--- |
| **[01. Arquitectura y Funcionamiento General](01_ARQUITECTURA_Y_FUNCIONAMIENTO.md)** | Explica cómo se comunican el Backend (FastAPI), Frontend (Next.js), Base de Datos y el Motor 3D (Three.js/R3F), y cómo funciona el acoplamiento multiescala. |
| **[02. Guía de Variables, Métricas y Valores](02_GUIA_DE_VARIABLES_Y_METRICAS.md)** | **Diccionario completo de cada valor en pantalla**: qué significa $Q$, $\theta$, $Tr$, $ET_0$, $CWSI$, flujo de savia, unidades, rangos normales, óptimos y de alerta. |
| **[03. Modelos Científicos y Fórmulas](03_MODELOS_CIENTIFICOS_Y_FORMULAS.md)** | Fundamentos matemáticos: balance hidrológico SWAT, Curva Número SCS, función de absorción radicular de Feddes ($\alpha$), Penman-Monteith y escenarios CMIP6. |
| **[04. Guía de Usuario y Manual de Módulos](04_GUIA_DE_USUARIO_Y_MODULOS.md)** | Manual operativo paso a paso: cómo correr simulaciones, interpretar gráficos, usar el visor 3D, exportar reportes (PDF, Word, Excel) y gestionar roles/usuarios. |

---

## 💡 Concepto Central en 1 Minuto

El sistema responde a una pregunta clave:
> **"¿Cómo impacta el cambio climático global y la gestión de agua en toda una cuenca hidrográfica sobre la salud y productividad de una sola planta en una parcela agrícola (y viceversa)?"**

Para responder esto, el sistema conecta 3 escalas de manera continua:
1. **Macro (Cuenca SWAT)**: Ríos, lluvias, escorrentías en montañas y recarga de acuíferos ($km^2$).
2. **Meso (Parcela Agrícola HRU)**: Suelo estratificado en horizontes ($0-100\text{ cm}$), riego por goteo y sensores IoT ($ha$).
3. **Micro (Planta Individual)**: Absorción de agua en raíces (Feddes), transporte en xilema (savia) y transpiración foliar ($cm$).

```
[Forzamiento CMIP6: Lluvia / Temp / CO2]
                │
                ▼
┌──────────────────────────────────────────────┐
│  MACRO: Cuenca SWAT (Río, Escorrentía, DEM) │
└──────────────────────┬───────────────────────┘
                       │ Disponibilidad hídrica
                       ▼
┌──────────────────────────────────────────────┐
│  MESO: Parcela HRU (Horizontes de Suelo, IoT)│
└──────────────────────┬───────────────────────┘
                       │ Humedad volumétrica θ
                       ▼
┌──────────────────────────────────────────────┐
│  MICRO: Planta 3D (Feddes, Xilema, CWSI)     │
└──────────────────────────────────────────────┘
```

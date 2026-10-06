# Gemelos digitales — From Plant to Watershed

Proyecto de Ingeniería de Software II para investigar el acoplamiento entre
planta, campo e hidrología de cuenca.

## Puntos de entrada

- **[Ficha técnica de investigación](from-plant-to-watershed/project_framework.md):**
  problema, objetivos, hipótesis y metodología que guían la investigación.
- **[Plataforma FastAPI + Next.js](from-plant-to-watershed/README.md):** instalación
  y operación del sistema principal.
- **[Estado actual](from-plant-to-watershed/docs/CURRENT_STATE.md):** capacidades
  implementadas, versiones de experimentos y trabajo científico pendiente.
- **[Índice técnico](from-plant-to-watershed/docs/README.md):** contratos, datos y
  evidencia histórica.
- **[Laboratorio ML en Streamlit](agro-digital-twin-st/README.md):** entrenamiento,
  inferencia y procedencia de los modelos auxiliares.
- **[Guía de sustentación](GUIA_SUSTENTACION_DOCENTE.md):** recorrido demostrable
  y alcance de las afirmaciones.

## Estado resumido

El gemelo diario experimental South Fork 2019 usa SWAT+ real y un FSPM
simplificado, con calendarios ejecutados y retroalimentación hídrica aproximada.
El reporte de hipótesis publicado sigue siendo el experimento anterior
`south-fork-final-v2`, con `H1_NOT_SUPPORTED`. Son resultados de versiones
distintas; la nueva ruta todavía necesita su propia comparación contra USGS.

La prioridad de investigación es evaluar observacionalmente el acoplamiento
actual. Los contratos documentan por separado estados simulados, observaciones,
estimaciones y supuestos.

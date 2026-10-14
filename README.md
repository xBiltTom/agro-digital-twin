# Gemelos digitales — From Plant to Watershed

Proyecto de Ingeniería de Software II para investigar el acoplamiento entre
planta, campo e hidrología de cuenca.

## Puntos de entrada

- **[Ficha técnica de investigación](from-plant-to-watershed/project_framework.md):**
  problema, objetivos, hipótesis y metodología que guían la investigación.
- **[Reformulación experimental](from-plant-to-watershed/research_reformulation.md):**
  alcance del primer artículo, hipótesis, comparadores y papel del modelo ML.
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

El MVP operativo usa `phase234-sf-2019-v2`: 365 fechas, 36 HRUs, 37 canales,
estados FSPM y playback persistido en PostgreSQL. FastAPI es el origen de los
datos temporales que consume el visor Next.js. El inicio integrado y la
importación están documentados en la [plataforma](from-plant-to-watershed/README.md).

La evaluación observacional `sf-test-v1` es un experimento distinto (2021–2025)
y conserva `H1_NOT_SUPPORTED`. No es una validación científica del bundle 2019.
La geometría 3D es contextual, el FSPM es simplificado y la calibración
hidrológica sigue pendiente.

La prioridad de investigación es evaluar observacionalmente el acoplamiento
actual. Los contratos documentan por separado estados simulados, observaciones,
estimaciones y supuestos.

Para probar el bundle sin ejecutar de nuevo SWAT+, comenzar por
[Inicio integrado con Docker Compose](from-plant-to-watershed/README.md#inicio-integrado-con-docker-compose).

# Documentación técnica y científica

La [ficha técnica de investigación](../project_framework.md) establece el
tema original. La [reformulación experimental](../research_reformulation.md)
delimita el primer estudio y las decisiones que deben fijarse antes de evaluar.
Los documentos de esta carpeta describen lo implementado y la evidencia disponible.

## Documentación vigente

| Documento | Contenido |
| --- | --- |
| [Estado actual](CURRENT_STATE.md) | Capacidades, corridas de referencia, límites y siguiente etapa científica. |
| [Diagnóstico de referencia 2019](BASELINE_DIAGNOSTIC_2019.md) | Corridas en PostgreSQL, comparación USGS, drenaje/ruteo y exportaciones. |
| [Recorrido del agua 2019](WATER_PATH_DIAGNOSTIC_2019.md) | Error de reporte, volúmenes nativos, balances y límites de los canales artificiales. |
| [Longitudes de cauces 2019](CHANNEL_GEOMETRY_DIAGNOSTIC_2019.md) | Delineación, fallos de underflow, pareja controlada y balance parcial con ruteo físico. |
| [Motor desde fuente y almacenamiento 2019](SWAT_SOURCE_BUILD_2019.md) | Receta reproducible, estados de llanura, balances nativos y reproducción en pglocal. |
| [Meteorología y ET/PET 2019](METEOROLOGY_DIAGNOSTIC_2019.md) | Conversiones gridMET, anomalías del warm-up, comparaciones externas y agregación por HRU. |
| [Entrega 1: referencia física](PHYSICAL_REFERENCE_DELIVERY_1.md) | Warm-up corregido en pglocal, comparación controlada, ET/suelos/drenaje/acuíferos y decisión para calibración. |
| [Reporte científico publicado](FINAL_REPORT.md) | Resultado v2, separación respecto al gemelo diario y reproducción del runner final. |
| [Acoplamiento FSPM–SWAT+](FSPM_SWAT_PLUS_COUPLING.md) | Calendarios ejecutados, feedback hídrico aproximado y mapeo de parámetros. |
| [Contrato de playback y representación](TWIN_PLAYBACK_CONTRACT.md) | API, PostgreSQL, evidencia, frecuencias y consumo del visor 3D. |
| [Integración SWAT+ real](SWAT_PLUS_REAL_INTEGRATION.md) | Adaptador y prueba de referencia oficial del motor. |
| [Selección de cuencas](methodology/watershed-selection-protocol.md) | Criterios del dominio y condiciones para validación espacial. |
| [USGS y control de calidad](methodology/usgs-streamflow.md) | Descarga diaria, unidades, cobertura y agregación mensual. |
| [Registro de datos](methodology/observational-data.md) | Observaciones, artefactos, procedencia y proveedores pendientes. |
| [ADR 001: núcleo científico](adr/001-pure-scientific-core.md) | Frontera entre lógica científica, integración y persistencia. |

Instalación: [README de la plataforma](../README.md).
Interfaz: [README del frontend](../frontend/README.md).
ML: [README del laboratorio](../../agro-digital-twin-st/README.md).

## Evidencia histórica

Las auditorías se conservan porque explican por qué un proceso SWAT+ terminado
y un checksum de entrada distinto no bastaban para demostrar acoplamiento:

- [Fase 3.4](audits/PHASE_3_4_SCIENTIFIC_AUDIT.md): pareja original, cadena de
  cultivo y salidas idénticas.
- [Fase 3.5](audits/PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md): incompatibilidad de
  `days_mat` y sensibilidad en copias instrumentadas.

Sus estados de base de datos, fechas aproximadas y límites corresponden a
aquellas ejecuciones; no deben usarse como descripción del runtime actual.

## Cómo interpretar versiones

- **`south-fork-final-v2`:** experimento publicado por la API de reportes.
- **`phase234-sf-2019-v2`:** gemelo diario corregido, con feedback hídrico
  aproximado; es otro experimento.
- **`twin-playback-v1`:** versión del esquema temporal, no del experimento.
- **`south-fork-final-v3`:** destino del runner final si se ejecuta; no hay un
  reporte v3 publicado en el repositorio revisado.

No deducir equivalencia entre esos identificadores por compartir el sufijo `v2`.

# 📚 Documentación Técnica y Científica: From Plant to Watershed

Repositorio y base de conocimiento técnico-científica del framework **From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models with SWAT Hydrology and Downscaled Climate Projections**.

---

## 🗺️ Índice de Documentación Vigente

| Documento | Enfoque | Descripción |
| :--- | :--- | :--- |
| **[Marco Metodológico Oficial](../project_framework.md)** | Científico / General | Hipótesis $H_0/H_1$, módulos 1 al 5, protocolos de inclusión/exclusión, pruebas estadísticas y revistas diana. |
| **[Reporte Final del Piloto South Fork](FINAL_REPORT.md)** | Validación Experimental | Evaluación hidrológica en South Fork Iowa River (`USGS 05451210`), baseline vs acoplado, y escenarios climáticos (+2°C, -15% precipitación, no-till, sorgo). |
| **[Acoplamiento FSPM → SWAT+](FSPM_SWAT_PLUS_COUPLING.md)** | Modelado Multiescala | Contratos de acoplamiento de variables de dosel/raíz a nivel de comunidad vegetal (v2.1.1), mapeo a `plants.plt` y balance hídrico. |
| **[Integración Real SWAT+](SWAT_PLUS_REAL_INTEGRATION.md)** | Infraestructura y Reproducibilidad | Verificación del ejecutable SWAT+ oficial (Linux x86_64 rev 61/62), preparación de workspaces y validación de outputs. |
| **[ADR 001: Pure Scientific Core](adr/001-pure-scientific-core.md)** | Arquitectura de Software | Desacoplamiento estricto del motor científico en `scientific_core` frente a frameworks web (FastAPI, SQLAlchemy). |
| **[Protocolo de Selección de Cuencas](methodology/watershed-selection-protocol.md)** | Metodología Espacial | Criterios objetivos de selección en el Corn Belt: $\geq 60\%$ área agrícola, $\geq 20$ años de caudal diario USGS, cribado de presas NID y verificación CDL. |
| **[USGS Streamflow & QC](methodology/usgs-streamflow.md)** | Datos Observacionales | Normalización de caudales diarios (parámetro 00060), conversión de unidades a $\text{m}^3/\text{s}$, flags de calidad y linaje. |
| **[Observational Data Registry](methodology/observational-data.md)** | Provenance y Checksums | Gestión de artefactos de datos, hashes SHA-256 y trazabilidad de datasets. |

---

## 🏛️ Flujo Multiescala Implementado

El framework acopla jerárquicamente cuatro escalas biofísicas:

1. **Nivel 1 (Micro / Planta)**: FSPM determinista de 1,000 plantas con variación paramétrica intra-poblacional (LAI dinámico, arquitectura de raíces, transpiración).
2. **Nivel 2 (Meso / Parcela - HRU)**: Agregación de comunidad vegetal, balance en zona radicular e intercambio de agua en suelo.
3. **Nivel 3 (Macro / Cuenca)**: SWAT+ sobre la cuenca hidrográfica South Fork Iowa River con 36 subcuencas hidrológicas y 37 canales fluviales enrutados al aforo `USGS 05451210`.
4. **Nivel 4 (Clima)**: Forzamientos meteorológicos y escenarios de perturbación climática y de manejo agronómico.

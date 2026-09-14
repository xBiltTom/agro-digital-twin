# USGS daily streamflow

`UsgsStreamflowProvider` recupera el producto USGS Daily Values para descarga
media (`parameterCd=00060`, `statCd=00003`). Conserva los bytes originales como
artefacto `RAW`, calcula SHA-256, normaliza observaciones diarias `OBSERVED` y
mantiene una agregación mensual `DERIVED` separada.

La respuesta fuente expresa descarga en `ft3/s`; la normalización usa la
conversión explícita y probada `m3/s = ft3/s × 0.028316846592`. Un promedio
mensual es **mean discharge** en m3/s, no volumen mensual. Un volumen futuro
debe ser otra variable y aplicar integración temporal explícita.

QC registra duplicados, fechas desordenadas, faltantes, negativos, gaps,
cobertura, período y años efectivos. Los valores problemáticos se preservan con
su estado; no se rellenan ni eliminan silenciosamente. Los meses bajo el umbral
de cobertura quedan `included=false` y sin promedio.

Fuente y documentación oficial: https://waterservices.usgs.gov/docs/dv-service/daily-values-service-details/

## Lineage

`USGS station → JSON RAW + SHA-256 → parser versionado → m3/s → QC → daily OBSERVED → monthly DERIVED`.

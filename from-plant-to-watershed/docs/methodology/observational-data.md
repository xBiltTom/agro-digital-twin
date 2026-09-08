# Datos observacionales y registry

`Dataset` describe proveedor, variable, unidad, resolución, soporte espacial,
período, referencia, licencia, evidencia y QC. `DatasetArtifact` referencia el
archivo almacenado y su SHA-256. `StreamflowObservation` mantiene observaciones
normalizadas por fecha, estación, unidad original, valor original, valor m3/s y
calificador de calidad.

Los artefactos se almacenan bajo `data/raw/` y `data/processed/`; Git ignora su
contenido. Los manifests y metadata conservan URL, checksum, versión de parser,
período y QC para reproducibilidad sin versionar series masivas.

Contratos futuros, aún `NOT_IMPLEMENTED`: USDA NASS (yield a nivel county y su
incompatibilidad espacial con watershed), CHIRPS (precipitación gridded),
SoilGrids (propiedades de suelo) y Landsat Collection 2 (cobertura/productos).
No se presenta ninguno como ingerido.

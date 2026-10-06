# Registro de datos, observaciones y procedencia

`Dataset` describe proveedor, variable, unidad, resolución, soporte espacial,
período, referencia, licencia, evidencia y QC. `DatasetArtifact` referencia el
archivo almacenado y su SHA-256. `StreamflowObservation` mantiene observaciones
normalizadas por fecha, estación, unidad original, valor original, valor m3/s y
calificador de calidad.

Los artefactos observacionales usan `data/raw/` y `data/processed/`; los
manifiestos conservan URL, checksum, versión de parser, periodo y QC.
Las series masivas suelen quedar fuera de Git. Los bundles reducidos del
gemelo bajo `backend/data/phase1-south-fork-2019/results/` sí tienen artefactos
versionados y sus propios manifiestos: no confundir ambos mecanismos.

## Fuentes y estados

| Fuente | Estado relevante |
| --- | --- |
| USGS Daily Values | Proveedor implementado, RAW con hash, observación normalizada m³/s y QC; agregación mensual DERIVED separada. |
| CDL 2019 | Composición estática utilizada para la variante experimental y pesos HRU; no operaciones de manejo observadas ni rotación histórica. |
| Clima del proyecto SWAT+ | Forcing disponible; el bundle diario reciente no documenta suficientemente el origen meteorológico y conserva `SOURCE_UNVERIFIED`. |
| Suelos del proyecto SWAT+ | Inputs `soils.sol` utilizados por el motor y la estimación radicular; no prueban ingestión del proveedor SoilGrids. |
| USDA NASS | Contrato de proveedor pendiente en `dataset_contracts.py`; el reporte final marca validación LIMITED por falta de crosswalk county→HRU/cuenca. |
| CHIRPS, SoilGrids, Landsat | Contratos planificados `NOT_IMPLEMENTED` en el registry; no declararlos ingeridos por existir sus nombres en la ficha técnica. |
| CMIP6 | Soporte de archivos/configuración no equivale a dataset disponible; sin artefactos normalizados en el experimento publicado. |

Los estados SWAT+/FSPM son salidas modeladas, no observaciones. La humedad
radicular estimada se marca DERIVED y los inputs asumidos conservan ASSUMED.
Un escenario de +2 °C o −15 % de lluvia no se etiqueta como proyección CMIP6.

Detalles: [USGS y QC](usgs-streamflow.md),
[selección de cuencas](watershed-selection-protocol.md) y
[estado actual](../CURRENT_STATE.md).

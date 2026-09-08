# Artefactos de datos del MVP

El MVP no descarga ni inventa datasets. Un investigador registra un archivo local situado bajo `DATA_ARTIFACT_ROOT` mediante `POST /api/v1/datasets/register-artifact`. El registro conserva proveedor, fuente, versión, cobertura, unidad, QC, metadata, tamaño y SHA-256.

Fuentes previstas: USGS (caudal diario), USDA NASS (rendimiento anual de maíz), CHIRPS (precipitación), SoilGrids (perfil estático), Landsat (cobertura preparada) y NEX-GDDP-CMIP6 (CSV diario normalizado). Para CMIP6 el metadata debe declarar escenario, GCM, miembro, período, calendario, unidades y método de corrección de sesgo.

Una corrida selecciona artefactos como `CONTEXT_ONLY` hasta que exista un adaptador de forcing compatible. El único forcing ejecutable incluido por defecto es `SYNTHETIC`; esta distinción aparece en el manifiesto y en los reportes.

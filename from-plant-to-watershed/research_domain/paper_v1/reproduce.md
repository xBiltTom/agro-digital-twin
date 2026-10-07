# Reproducción y disponibilidad

## Alcance del paquete

El ZIP preserva las tablas y resultados congelados, bundles C/D con sus pesos y escaladores, protocolos, recibos, esquemas, linaje y recetas. `archive-manifest.json` proporciona SHA-256 de cada archivo incluido. El manifiesto junto al ZIP incluye su checksum. El manuscrito es un borrador que requiere autoría y revisión editorial antes de envío.

El paquete permite inspeccionar la evidencia publicada y reproducir el análisis mensual desde las series. No incluye la base PostgreSQL completa, el proyecto SWAT+ ni los archivos pesados de forcing. La reproducción física exige esas dependencias locales, su procedencia y los hashes de los manifiestos de las entregas 1–4. Ninguna receta crea una base temporal.

## Entorno

Desde `from-plant-to-watershed/backend`, usar el venv del proyecto y la base **pglocal digitaltwin**, configurada por `DATABASE_URL`. El usuario local necesita acceso al socket `/run/postgresql`. No compartir `.env`. Consultar versiones exactas de análisis/figuras en `software.json`; Matplotlib es una dependencia del empaquetado, no del motor de producción.

```bash
venv/bin/pip install -r requirements-paper.txt
venv/bin/python scripts/package_south_fork_paper.py --register
```

El empaquetador verifica el reporte y todos los artefactos TEST, genera tablas y figuras y registra `sf-paper-v1`. No ajusta modelos ni cambia las publicaciones TEST. Puede regenerar el paquete del borrador; los originales congelados permanecen separados.

## Reproducción física del usuario

Requiere `data/baseline-diagnostic-multiyear-v1/selected-project`, `parameter-manifest.json`, `frozen-plant-contract.json` y el ejecutable `data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research`, además de la cuenca, escenario neutro, observaciones y bundles ya registrados en pglocal. El perfil verifica el ejecutable y los parámetros. La interfaz **Simulaciones → Ejecutar una reproducción propia** permite seleccionar año 2021–2025, brazo A/B y ML mensual C/D. Cada corrida pertenece al usuario autenticado; el informe agregado es visible para usuarios autenticados.

La ejecución se realiza en un proceso independiente; no requiere Redis ni una cola nueva. Las salidas físicas diarias se conservan aun si falla el posprocesamiento ML mensual. Los logs locales están en `data/south-fork-user-v1/<id>.log`. Si se interrumpe el servicio, el proceso hijo puede continuar mientras el host siga funcionando. Una terminación del host puede dejar una corrida PENDING/RUNNING: el operador debe comprobar el log y los procesos antes de marcarla FAILED; no relanzar una corrida parcialmente escrita.

Para ejecutar una corrida pendiente cuyo proceso no llegó a iniciarse:

```bash
venv/bin/python scripts/run_south_fork_profile.py --run-id ID_DE_LA_CORRIDA_PENDIENTE
```

Para crear y ejecutar desde CLI con un usuario existente:

```bash
venv/bin/python scripts/run_south_fork_profile.py --owner UUID_DEL_USUARIO --year 2025 --arm B
```

No reutiliza un ID TEST ni altera su resultado. Las corridas anuales vuelven a procesar desde 2000; su coste excede un año de simulación. No se ofrece cancelación ni recuperación automática tras apagar el host.

## Recetas científicas previas

Con sus inputs ya instalados, las recetas versionadas originales documentan preparación, calibración, exportación y evaluación:

```bash
venv/bin/python scripts/run_south_fork_multiyear.py --help
venv/bin/python scripts/package_south_fork_multiyear.py --help
venv/bin/python scripts/run_south_fork_ml.py
venv/bin/python scripts/run_south_fork_test.py
```

Las recetas ML/TEST reconocen artefactos completos y compatibles para reutilizarlos; no borrar outputs para forzar reajuste. TEST ahora es conocido. Una modificación de modelo necesita otro holdout o una declaración explícita de desarrollo.

La construcción del ejecutable se documenta en `docs/SWAT_SOURCE_BUILD_2019.md` y las entregas previas. Consultar también los locks `scripts/swat_research_source.lock.json` / `scripts/swat_research_toolchain.lock.json`.

## Interpretación

H1 no respaldada; no significa demostrar empeoramiento significativo. La referencia física falló su criterio de sesgo. C/D son correcciones retrospectivas de caudal mensual, no pronósticos adelantados ni balances físicos conservativos. LAI y estados FSPM son modelados; no se empleó LAI observado para validar fisiología. El archivo histórico 2018–2020 continúa disponible, pero la decisión actual procede de TEST 2021–2025.

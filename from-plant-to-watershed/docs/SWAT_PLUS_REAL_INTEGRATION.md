# Integración SWAT+ real y prueba de referencia

El runtime requiere un ejecutable y proyecto SWAT+ locales. El adaptador está
en `backend/app/services/swat_plus_adapter.py`; la ruta South Fork actual usa
SWAT+ **61.0.2.61** y se describe en
[acoplamiento FSPM–SWAT+](FSPM_SWAT_PLUS_COUPLING.md).

La ejecución oficial **62.0.0 / Osu_1hru** documentada abajo es una prueba de
integración anterior, no el experimento de South Fork ni su calibración.
Los hashes se conservan para identificar exactamente esa evidencia.

## Ejecución de referencia verificada

- Engine: official `swat-model/swatplus` Linux x86_64 release `62.0.0`.
- Release archive SHA-256:
  `d0244e0ef07289ccb0fcf1a69bfef53ffb16f7dbc464b827f0143f26bde333f9`.
- Extracted executable SHA-256:
  `5d30a2d255f6c0d49e8456835523156b85b0d204334bd27d8f461994bacbe8b6`.
- Input project: official `refdata/Osu_1hru` (one HRU, 10 ha) from
  `https://github.com/swat-model/swatplus.git`, commit
  `cb442f7c05fc3bfc34349c446010f452d2737ca0`.
- Deterministic project-tree manifest SHA-256:
  `6c4a3f7a371302b5e5432b213c2e6894b976295ba210407b79faf6e7a2175f4a`.

Periodo: `2010-01-01` a `2010-12-31`, salida diaria y cero años de warm-up,
seleccionados dentro del rango del proyecto. No son constantes del runtime.

## Reproducir la prueba de referencia

Preparar el release y el proyecto de la revisión citada. Desde
`from-plant-to-watershed/`, con el entorno backend activado:

```bash
SWAT_PLUS_EXECUTABLE=/absolute/path/swatplus-62.0.0-gnu-lin_x86_64-Rel \
SWAT_PLUS_PROJECT_DIR=/absolute/path/swatplus/refdata/Osu_1hru \
SWAT_PLUS_WORKING_DIRECTORY=/tmp/swat-api-real-workspaces \
SWAT_PLUS_INTEGRATION_START=2010-01-01 \
SWAT_PLUS_INTEGRATION_END=2010-12-31 \
SWAT_PLUS_INTEGRATION_OUTPUT_FREQUENCY=DAILY \
pytest -q backend/tests/test_swat_plus_adapter.py -m integration -k real_swat_baseline_api
```

Se selecciona solo la prueba baseline: la integración acoplada necesita un
proyecto con cultivo/manejo compatibles y no se infiere de este caso de una HRU.

## Garantías del adaptador actual

- Preflight de recursos, archivos declarados y cadena de cultivo cuando procede.
- Copia aislada antes de editar `time.sim`, `print.prt` y entradas acopladas.
- Validación/normalización de tokens enteros sin cambiar valores científicos.
- Limpieza de outputs obsoletos solo en la copia, proceso con timeout y
  comprobación de `success.fin` actual.
- Parser por fecha, unidad espacial y unidades impresas; cobertura y faltantes
  explícitos, sin sustitución hidrológica sintética ante fallo.
- Configuración efectiva, hashes de input/output y modificaciones en provenance.

Un proceso exitoso demuestra ejecución. La sensibilidad se comprueba por
intervenciones y salidas; el ajuste científico exige observaciones. Véanse
[auditoría de sensibilidad](audits/PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md) y
[reporte publicado](FINAL_REPORT.md).

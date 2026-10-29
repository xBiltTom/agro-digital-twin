# Experimento v2: paquete de trabajo

Base Git `397257ebb9b12cf33f2e29e004480246d773cc90`, rama `experiment/south-fork-repro-v2`. `PROTOCOLO.md` se escribió antes de ejecutar las nueve corridas. Nada se publicó ni se alteraron las salidas originales.

## Reproducción mensual y del modelo B14: probada

Desde la raíz del repositorio, con Python 3.12.3, numpy 2.4.2, pandas 2.3.3, scikit-learn 1.9.0 y joblib 1.5.2:

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/analisis_mensual.py
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/verificar_metricas.py
```

Se copiaron únicamente ambos scripts y sus cuatro CSV/JSON de entrada a una jerarquía nueva en `/tmp`; se ejecutaron con el venv existente. Los tres CSV de predicciones, métricas y contrastes coincidieron byte a byte; el recálculo independiente en biblioteca estándar comprobó 32 filas. No se probó instalación limpia de dependencias. `modelo_B14.joblib` contiene Ridge y StandardScaler ajustados de nuevo exclusivamente con TRAIN; C y D son predicciones congeladas originales, no se volvieron a entrenar. El archivo joblib debe cargarse únicamente desde una fuente confiable.

Las entradas necesarias, versionadas en el repositorio, son `multiyear_v1/monthly-ab.csv`, `test_v1/monthly-ab.csv`, `test_v1/monthly-predictions.csv` y `agro-digital-twin-st/artifacts/south_fork_monthly_residual_v1/{protocol.json,development-predictions.csv}`. Los bundles originales C/D y los escaladores están en ese mismo directorio. Versiones exactas adicionales: `../paper_v1/software.json`. El análisis B14 es una ampliación exploratoria **sobre las físicas originales**, no una evaluación de la nueva calibración.

## Reproducción física

La copia local `forcing_inputs.tar.gz`, excluida de GitHub mientras se revisan las condiciones de distribución, contiene los 198 inputs del proyecto corregido previo a calibración, incluidos meteorología, suelos, cobertura y manejo; `forcing_inputs_sha256.json` contiene hashes individuales cotejados antes del empaquetado. `runs/v2-cal-*/parameter-manifest.json` documenta las transformaciones y `result.json` conserva todas las predicciones de calibración y métricas; `calibracion.csv` resume los nueve. El ejecutable local usado es `backend/data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research` SHA-256 `56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d`. Fuente, patches, herramienta y receta: `../../docs/SWAT_SOURCE_BUILD_2019.md`, `../../backend/scripts/swat_research_source.lock.json`, `../../backend/scripts/swat_research_toolchain.lock.json` y `../../../licenses/`. El binario depende del runtime compilado local y no se incluye en este subpaquete. La fuente y runtime de investigación no son una versión oficial sin modificaciones.

Para repetir la búsqueda se requiere el checkout completo, el entorno del backend y el ejecutable indicado, extraer el archivo de inputs en `backend/data/baseline-diagnostic-multiyear-v1/forcing-project` en una copia limpia y comprobar cada hash del JSON, y la instantánea USGS versionada indicada abajo. Luego ejecutar:

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/calibrar.py
```

Este comando se ejecutó en el entorno original. La siguiente comprobación ejecutada en una carpeta temporal limpia extrajo y verificó los 198 inputs y reprodujo exactamente los 96 caudales de v2-cal-02 con el entorno y ejecutable existentes:

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/verificar_fisica.py
```

Se repitió después toda la física en carpetas limpias con el entorno y ejecutable existentes; no se ensayó una instalación nueva de dependencias. No debe ejecutarse sobre una carpeta con resultados incompatibles: el script reutiliza `result.json` existentes. La derivación FSPM, nueve candidatos y todas las parejas A/B se repitieron en esta máquina desde copias limpias; no se probó otra instalación. No confundir la reproducción de nueve calibraciones con la reproducción de todas las simulaciones anuales.

## Procedencia y condiciones de uso

Observaciones: instantánea USGS `data/raw/usgs/05451210_2000-01-01_2025-12-31.json`, SHA-256 `5d63af30789bf2f970bfafdea9b8151271b5c96bc30601fe856b7a369df42a3d`, estación 05451210, 00060, estadística 00003, consulta registrada el 2026-09-07. La consulta y calificadores están en el JSON; una descarga nueva puede diferir porque USGS revisa sus datos. Se retienen A y A,e; valores en ft³/s multiplicados por 0,028316846592. [USGS: créditos y dominio público](https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted); [revisión de datos](https://water.usgs.gov/data/disclaimer.html).

Clima: gridMET corregido, [documentación y condiciones del proveedor](https://www.climatologylab.org/gridmet.html); manifiestos de corrección y detalle de archivos en `backend/data/baseline-diagnostic-multiyear-v1/forcing-manifest.json` y `docs/PHYSICAL_REFERENCE_DELIVERY_1.md`. Fuente de proyecto Boone CDL: `backend/scripts/fetch_figshare_swat_inputs.py`, archivo Figshare `57107195`, subdirectorio `Boone_CDL_20250629/Scenarios/Default/TxtInOut/`; documentación de modificaciones en las entregas físicas. Las condiciones específicas de redistribución de este derivado integrado no se han verificado íntegramente: el archivo de inputs es un respaldo local para la investigación y no se incluye en la rama publicada. Verificar derechos y créditos de todos los componentes antes de redistribuirlo.

SWAT+ usa LGPL-2.1 según `licenses/SWATPLUS-NOTICE.md`, que no se extiende automáticamente al código propio. No se encontró licencia autorizada para el código propio; autores deben escogerla. No se incluyen credenciales ni configuración .env.

## Continuación factorial v2 completada

Se ejecutó `simular_v2.py` para 2013–2025 desde las entradas físicas empaquetadas, con referencia v2-cal-02 y el contrato 2010 de `frozen_plant_contract_v2.json`. El código utiliza el adaptador y acoplamiento originales del backend. Cada año comienza a simular en 2000; B transfiere el contrato fijo y A utiliza la corrida estándar como base, y ejecuta FSPM en modo pasivo usando calendario y agua de A. El archivo vegetal de A se comprueba antes/después de la mutación sobre la copia normalizada, y su fuente se verifica sin modificaciones. El output `annual/` contiene el agua y clima diarios, los estados y las huellas de cada par; no incluye todas las salidas nativas descartadas. Ver `INFORME.md` para el error inicial, la recuperación auditada y la interrupción de una corrida duplicada.

Comando de reproducción secuencial desde la raíz del repositorio (preparado; las corridas reales se ejecutaron en subconjuntos, no mediante esta invocación completa):

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/simular_v2.py 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
```

Comandos de comprobación y análisis ejecutados:

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/verificar_anuales.py
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/factorial_v2.py
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/verificar_metricas.py --v2
```

El primer comando reutiliza resultados anuales y contrato existentes: para una repetición física hay que usar un checkout/carpeta de resultados limpia y preservar los originales, con el ejecutable y bibliotecas descritos arriba. En esta ejecución se usaron seis directorios independientes mediante la variable opcional `SOUTH_FORK_V2_WORK`; no se requiere base de datos. La recuperación comprueba el hash de outputs nativos, aplica nuevamente el contrato y verifica convergencia; una interrupción puede dejar una carpeta de workspace incompatible que deberá conservarse o moverse antes de reintentar. El fallo por hash normalizado ocurrió durante el posprocesamiento, no se trata como corrida satisfactoria hasta los controles de recuperación.

Para comprobar análisis sin ejecutar SWAT+, copiar `annual/`, los tres scripts de verificación/análisis, `frozen_plant_contract_v2.json`, `metricas_disponibles.csv`, el JSON de observaciones USGS y el `protocol.json` original respetando su jerarquía de repositorio. Se probó en una carpeta temporal limpia con el venv existente: `mensual_v2.csv`, `predicciones_v2.csv`, `metricas_v2.csv`, `contrastes_v2.csv` y `comparacion_metricas_v2.csv` coincidieron byte a byte; además, el recálculo independiente verificó las 36 filas de métricas. Los cuatro `modelo_v2_*.joblib` incluyen su escalador y Ridge. El análisis y TEST son retrospectivos y exploratorios. Se repitió también el recorrido físico completo desde carpetas limpias con el entorno existente; otra instalación de software no se ha probado.

## Comprobación física completa en carpeta limpia

Se repitieron los nueve candidatos, la derivación de 2010 y los 13 años: 864 caudales mensuales de calibración y 4.748 valores diarios por brazo coincidieron exactamente. Con las salidas repetidas, los cinco CSV de análisis volvieron a coincidir byte a byte. El resumen vegetal coincidió exactamente; su archivo JSON tiene otro hash porque registra rutas diferentes. El recibo `reproduccion_fisica_limpia.json` y `comparar_fisica_limpia.py` documentan la comparación. La primera preparación con enlace simbólico falló antes de SWAT+; el error quedó en `reproduccion_error_ruta.log` y se corrigió resolviendo el directorio backend.

La copia limpia se creó en `/tmp` con `simular_v2.py`, `PROTOCOLO.md`, `forcing_inputs.tar.gz` y `forcing_inputs_sha256.json`, un enlace al backend existente y la instantánea USGS. Se ejecutó `simular_v2.py --derive-only` y luego grupos de años con `SOUTH_FORK_V2_WORK` distintos; la búsqueda se ejecutó con `calibrar.py` apuntando a los inputs extraídos. La comparación se ejecutó con:

```bash
from-plant-to-watershed/backend/venv/bin/python from-plant-to-watershed/research_domain/experiment_v2/comparar_fisica_limpia.py RUTA_DEL_DIRECTORIO_EXPERIMENTAL_LIMPIO
```

Se reutilizaron el Python y ejecutable de investigación existentes; no se ha establecido reproducibilidad entre sistemas o compiladores diferentes.

## Archivo físico no distribuido en la rama

`forcing_inputs.tar.gz` permanece solo en el equipo local porque no se han verificado íntegramente los derechos de redistribución del proyecto integrado. Para ejecutar la física desde un clon, los autores deben proporcionar esa copia exacta o completar su reconstrucción a partir de las fuentes y manifiestos descritos arriba. Su SHA-256 es `acc4fa365e6f493212f170c7b71153136dc51b903c50680136c5c44b72e33f1f`; cada uno de los 198 archivos debe coincidir además con `forcing_inputs_sha256.json`. Las recetas de descarga originales, correcciones de clima y transformación de parámetros están referenciadas arriba, pero una reconstrucción íntegra desde fuentes remotas sin la copia local no se ha probado.

# Figuras y tablas científicas

Las exportaciones reproducen el estilo de `figuras/` con los artefactos del
experimento publicado `sf-test-v1`. Son operaciones de lectura: no ejecutan
SWAT+, no entrenan modelos y no reescriben `paper_v1` ni sus manifiestos.

## Acceso desde la plataforma

- **Reportes y Evidencia → Figuras y tablas científicas:** los ocho elementos,
  con vista previa y descarga individual.
- **Simulación y Acoplamiento → Figuras y tablas científicas:** resultados TEST
  y configuración del experimento publicado. La corrida seleccionada en el
  módulo no cambia estas exportaciones; la interfaz lo indica explícitamente.
- **Catálogo de Datos y ML → Figuras y tablas del protocolo temporal:** tabla
  y diagrama de particiones.

Todos los elementos admiten PNG a 300 dpi, SVG y PDF vectoriales. Las cinco
tablas también admiten CSV UTF-8 con BOM. Las vistas previas usan el PNG del
mismo generador que las descargas y conservan fondo blanco en ambos temas.

## Elementos y procedencia

| ID de exportación | Referencia | Fuente |
| --- | --- | --- |
| `monthly-hydrograph` | Figura 5, hidrograma | `test_v1/monthly-predictions.csv` |
| `performance` | Tabla 5, métricas en filas y A/B/C/D en columnas | Informe TEST congelado |
| `contrasts-plot` | Figura 6, puntos e IC 95 % | Contrastes del informe TEST |
| `contrasts` | Tabla 6, diferencias, mejora e intervalos | Contrastes del informe TEST |
| `temporal-partition` | Figura 4, etapas del protocolo | Protocolo multianual congelado |
| `partitions` | Tabla 4, fechas, meses y usos | Protocolo y textos explicativos |
| `plant-mapping` | Tabla 2, diez parámetros vegetales | Contrato vegetal congelado de 2010 y definiciones |
| `experimental-design` | Tabla 3, brazos A/B/C/D | Definiciones del experimento, comprobadas contra los brazos registrados |

Se comprueba el SHA-256 del informe contra el manifiesto TEST, del protocolo
contra el informe, y de las predicciones contra el manifiesto. El contrato
vegetal se reconstruye del objeto `frozen_plant_contract` de la entrega 2 y se
comprueba contra el hash del contrato original registrado en TEST; no requiere
el proyecto SWAT+ instalado. La ausencia o alteración de una fuente impide
exportar el elemento afectado y devuelve HTTP 503.

Las fechas son las reales: WARMUP 2000–2004, CALIBRATION 2005–2012, TRAIN
2013–2017, VALIDATION 2018–2020 y TEST 2021–2025. Se muestran cinco etapas.

Los cuatro resultados admiten `PRIMARY` y `EXCLUDE_ESTIMATED`. La sensibilidad
conserva las 60 posiciones del calendario y deja huecos en los meses no elegibles
(36 meses elegibles en los artefactos actuales). Las otras cuatro exportaciones
son independientes de esa selección.

ΔRMSE significa RMSE(referencia) − RMSE(candidato). Los intervalos son los
bootstrap por bloques ya registrados; no se recalculan al exportar. Los
contrastes secundarios son descriptivos y no ajustados por multiplicidad.
KGE corresponde a la variante modificada del sistema y PBIAS a simulado menos
observado. Los valores negativos y la inclusión de cero se conservan.
La tabla vegetal incorpora los valores y distingue parámetros base sin calibrar.

## API y ejecución

Todas las rutas requieren usuario activo autenticado:

```text
GET /api/v1/research/south-fork/exports
GET /api/v1/research/south-fork/exports/{id}/{png|svg|pdf|csv}?variant=PRIMARY
```

Los archivos se generan en memoria, con renderizado Matplotlib serializado
por proceso para proteger su estado global. La ruta síncrona usa el thread pool
de FastAPI. No se añade ninguna migración ni persistencia. Matplotlib 3.10.8
se incluye en `backend/requirements.txt`; hay que instalar las dependencias y
reiniciar el backend para usar el generador en una instalación existente.

## Verificación reproducible

Desde `backend/`:

```bash
MPLCONFIGDIR=/tmp/scientific-exports-mpl venv/bin/python -m pytest -q tests/test_scientific_exports.py tests/test_reports.py tests/test_swat_reports.py
```

Desde `frontend/`, con frontend y API ejecutándose y una **base desechable**
con el usuario de prueba estándar:

```bash
pnpm exec tsc --noEmit --incremental false
VISUAL_BASE_URL=http://localhost:3000 SCIENTIFIC_API_URL=http://localhost:8000/api/v1 pnpm test:scientific-exports
```

El test de navegador valida las ocho vistas previas, los cuatro formatos de
descarga, la sensibilidad, el error recuperable, reapertura, móvil y los
elementos de cada módulo. Admite `CHROMIUM_PATH` y `VISUAL_OUTPUT_DIR`.

Verificación local del 2026-10-20: 28 pruebas backend de exportaciones/reportes
y 35 pruebas frontend del visor aprobadas; TypeScript y ESLint de los archivos
nuevos aprobados. Pasaron el recorrido de navegador de esta función contra API
real con base temporal y las regresiones existentes de Reportes y catálogo de
Simulaciones. Se inspeccionaron los ocho PNG y capturas móvil/escritorio.
Los 26 artefactos e implementaciones comprobados contra los manifiestos TEST
y del paper conservaron sus hashes. No se ejecutó la suite completa del backend
ni se publicaron cambios en un despliegue.

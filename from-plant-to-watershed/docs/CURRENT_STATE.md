# Estado actual del proyecto

Revisión documental: **2026-10-05**. Describe el código y los artefactos del
repositorio; la disponibilidad de servicios locales se comprueba al ejecutarlos.
La [ficha técnica](../project_framework.md) conserva el alcance de investigación.

## 1. Implementación y evidencia

| Componente | Estado y alcance |
| --- | --- |
| Plataforma | FastAPI, Next.js, autenticación/RBAC, catálogo y reportes multiformato. |
| Motor hidrológico | SWAT+ real; South Fork usa la versión 61.0.2.61. |
| Planta | `SIMPLIFIED_FSPM`: poblaciones deterministas con variabilidad paramétrica, no un FSPM botánico completo validado. |
| Calendario | Siembra/cosecha por HRU desde `mgt_out.txt`; eventos modelados, no operaciones agrícolas observadas. |
| Agua SWAT+ → FSPM | Estimación de humedad radicular desde `sw_ave` y `soils.sol`, bajo hipótesis de fracción de agua disponible uniforme en el perfil. |
| Planta → SWAT+ | Diez parámetros del registro vegetal `corn` en `plants.plt`; SWAT+ mantiene sus propias ecuaciones de agua y cultivo. |
| Persistencia | Frames JSONB PostgreSQL con clave temporal y SHA-256. |
| Visor | Tres escalas y estados fechados; mallas anatómicas y terreno ilustrativos/contextuales. |
| Validación actualizada | Pendiente de comparación observacional propia para la ruta diaria corregida. |
| CMIP6 / rendimiento | Sin proyecciones CMIP6 normalizadas en el experimento publicado ni validación de rendimiento a escala HRU/cuenca. |

## 2. Experimentos que conviven

| Identificador | Uso | Interpretación |
| --- | --- | --- |
| `south-fork-final-v1` | `research_domain/final_report.json` | Resultado archivado del antiguo contrato de tres máximos vegetales. |
| `south-fork-final-v2` | `research_domain/final_report_v2.json`; `/reports/final-scientific` | Experimento anterior publicado, evaluación USGS 2018–2020; H1 no respaldada, mejora mensual 0 %. |
| `phase1-sf-2019-v3` | Bundle de ejecución 2019 | Calendarios ejecutados y inputs compatibles, todavía con humedad FSPM constante asumida. |
| `phase234-sf-2019-v1` | Bundle diario anterior | Anterior a la corrección de interpretación del almacenamiento SWAT+. |
| `phase234-sf-2019-v2` | Bundle diario corregido y selección preferida del visor cuando es accesible | Gemelo planta–suelo–agua experimental, no calibración ni nueva prueba de H1. |

Dashboard y reportes consultan el experimento final v2. El visor prioriza el
gemelo diario corregido, salvo que se indique una corrida accesible mediante
`?simId=`. Esa diferencia de linaje debe permanecer explícita.

## 3. Gemelo South Fork 2019 corregido

Bundle: `backend/data/phase1-south-fork-2019/results/phase234-sf-2019-v2/`.
`manifest.json` y `run_status.json` conservan los checksums y las comprobaciones:

- Estado `COMPLETED`, 365 fechas y 20 artefactos catalogados.
- 36 HRU y 37 canales por fecha; outlet GIS `153`.
- 32 HRU de maíz y siete calendarios; 1.000 plantas FSPM por grupo.
- Hasta diez slots representativos por grupo y fecha, hasta 70 muestras activas.
- Siembra modelada el 15/16 de mayo; cosechas/kill del 27 de agosto al 3 de septiembre.
- Dos iteraciones acopladas; máximo cambio final de `sw_ave` de 0,001 mm,
  por debajo de la tolerancia de 0,1 mm, con calendarios coincidentes.
- El proyecto fuente permaneció sin cambios.

En el frame del **2019-07-15** se documentan humedad FSPM estimada de
29,2263 vol%, estrés 0,0442, biomasa 167,6516 g/planta, transpiración
2,3156 mm/día y caudal outlet de 0,3202 m³/s. Son estados modelados/derivados.

La verificación operativa previa registró v1 y v2 en PostgreSQL y comprobó
playback autenticado, reconexión y consultas sin lector SQLite. También migró
el playback de una línea base 2018 sin FSPM. El acceso depende del propietario
y de los datos registrados en cada despliegue, no solo de tener el bundle.

Para consultar la corrida:

```text
GET /api/v1/simulations/phase234-sf-2019-v2/availability
GET /api/v1/simulations/phase234-sf-2019-v2/playback?date=2019-07-15&resolution=DAILY
```

Para importar el bundle en una instalación preparada, desde `backend/`, con
IDs existentes de propietario, South Fork y escenario neutral:

```bash
python scripts/register_phase234_south_fork_2019.py \
  data/phase1-south-fork-2019/results/phase234-sf-2019-v2 \
  --owner-id UUID_USUARIO --watershed-id UUID_CUENCA --scenario-id UUID_ESCENARIO
```

El importador verifica los artefactos y el contenido repetido. No ejecuta SWAT+.

Para una nueva ejecución del flujo diario de 2019, desde `backend/`, con
proyecto experimental y ejecutable disponibles:

```bash
python scripts/run_phase1_south_fork_2019.py \
  --run-id south-fork-2019-nueva-ejecucion \
  --project /ruta/al/proyecto-experimental \
  --executable /ruta/al/ejecutable/swatplus \
  --output-root data/phase1-south-fork-2019 \
  --warmup-years 19 --plant-count 1000 --seed 42
```

El script conserva el nombre histórico de fase 1, pero usa el runner acoplado
actual. El periodo visible está fijado a 2019; escribe CSV, playback comprimido,
logs y manifiesto. Rechaza sobrescribir un run ID existente. La nueva ejecución
tiene su propio linaje y no se registra automáticamente como reporte de H1.

## 4. Límites científicos relevantes

- **Dominio:** un piloto en South Fork; no validación cruzada multicuenca.
- **Manejo:** CDL 2019 estático informa una variante experimental; no
  reconstruye rotaciones ni operaciones históricas observadas.
- **Forcing reciente:** el bundle conserva los archivos SWAT+, pero su origen
  meteorológico no está documentado suficientemente y se marca sin verificar.
- **Humedad:** estimación de zona radicular, no humedad diaria medida por capa.
  Las plantas de un calendario reciben condiciones ponderadas del grupo.
- **Acoplamiento:** el resumen de los grupos actualiza un único registro `corn`;
  no transmite una parametrización vegetal distinta por HRU. ET, uptake y
  estrés diarios FSPM no se imponen a SWAT+.
- **Geometría:** `polygon_id` y `geometry_id` permanecen nulos. Los IDs GIS no
  prueban por sí solos una unión con las mallas del frontend.
- **Planta 3D:** hojas, raíces laterales y órganos son geometría ilustrativa;
  las 1.014 instancias del campo no son 1.014 trayectorias individuales.
- **ML:** los bundles mensuales versionados son sintéticos; el pronóstico diario
  sobre playback aprende de simulación y no demuestra mejora contra USGS.

## 5. Siguiente etapa de investigación

1. Precisar la variable primaria del experimento: hoy el evaluador utiliza
   caudal medio mensual del outlet en m³/s, distinto de escorrentía superficial
   en mm. Registrar esa operacionalización respecto a la ficha técnica.
2. Comparar baseline/acoplado con el flujo corregido de 2019 contra USGS,
   manteniendo proyecto, forcing, warm-up, periodo, outlet y controles comunes.
3. Revisar el ajuste del baseline, procedencia meteorológica y respuesta
   hidrológica antes de atribuir una mejora al FSPM.
4. Extender a varios años y separar desarrollo/calibración de evaluación;
   estimar incertidumbre teniendo en cuenta dependencia temporal.
5. Publicar el nuevo experimento con su propio linaje y conectar comparación,
   reportes y visor a la misma evidencia.

El runner `run_final_south_fork.py` todavía calcula FSPM con humedad constante
asumida. Ejecutarlo no evalúa por sí solo toda la ruta hídrica actual.

## 6. Verificación de software

En la revisión de 2026-10-05 se ejecutaron:

- `venv/bin/python -m pytest -q tests` desde backend: **185 aprobadas, 4 omitidas**.
- `pnpm test` desde frontend: **31 aprobadas**.
- `pnpm exec tsc --noEmit --incremental false`: aprobado.

Son comprobaciones de software; no se ejecutó aquí un nuevo experimento SWAT+,
una nueva evaluación USGS ni una inspección visual en navegador.

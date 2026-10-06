# Diagnóstico de referencia South Fork 2019

Fecha: **2026-10-06**. Primer avance de la
[reformulación](../research_reformulation.md): diagnosticar la referencia física
y hacer consultables sus resultados antes del experimento A/B/C/D.

**Seguimiento:** el [diagnóstico del recorrido del agua](WATER_PATH_DIAGNOSTIC_2019.md)
detectó un error adicional en el reporte de canales artificiales y repitió las
tres variantes con lectura consistente. Las métricas de este documento conservan
su interpretación anterior al hallazgo; no representan los nuevos caudales
normalizados ni deben mezclarse con ellos al atribuir efectos físicos.

## Ejecuciones y persistencia

Se ejecutó SWAT+ **61.0.2.61** por la ruta de producción
`TwinCouplingEngine`, usando la instancia local PostgreSQL `digitaltwin`.
Cada corrida tiene 365 frames diarios persistidos y pertenece al propietario
existente del gemelo South Fork. No se crearon bases auxiliares.

Condiciones comunes: evaluación 2019-01-01–2019-12-31, 19 años de warm-up,
escenario neutral, outlet GIS `153`, proyecto
`backend/data/phase34-cdl-2019/project`, 36 HRU y clima del propio proyecto.
Se ejecutó SWAT+ estándar; estos brazos no ejecutan FSPM ni ML.

| Corrida | Intervención | RMSE mensual (m³/s) | NSE mensual | PBIAS mensual (%) |
| --- | --- | ---: | ---: | ---: |
| `sf19-diag-v1-reference` | Proyecto de referencia | 9,5327 | −0,9611 | −78,0740 |
| `sf19-diag-v1-tile-probe` | `corn_lum.tile = mw24_1000` | 10,1910 | −1,2413 | −85,0949 |
| `sf19-diag-v2-tile-routed` | Misma activación y salida `til` al canal | 8,9144 | −0,7150 | −76,4842 |

Las métricas usan 12 medias mensuales y las mismas fechas válidas para ambas
series. PBIAS se define como `100 × Σ(simulado − observado) / Σ(observado)`;
su signo negativo expresa subestimación. Es un sesgo de medias mensuales, no
un cálculo independiente del balance de masa anual.

## Observaciones y cobertura

Se vinculó el dataset USGS ya registrado, estación **05451210**, mediante
`dataset_roles[dataset_id] = OBSERVATION`. La ejecución física mantiene el
forcing de SWAT+; las observaciones sirven para comparar y representar caudal.

- 365 días emparejados; ningún valor observado imputado.
- 279 valores con qualifier `A`; 86 con `A;e`, estimados por USGS y conservados.
- Cada media mensual exige al menos 90 % de los días calendario.
- El informe incluye métricas diarias, mensuales y sensibilidad diaria al
  excluir observaciones estimadas; esta última no constituye otra prueba de H1.
- Los valores normalizados están en m³/s; el artefacto USGS original y su
  SHA-256 están referenciados en el resumen reproducible.

## Hallazgo del drenaje

El archivo `tiledrain.str` ya contenía una definición, pero las 36 HRU tenían
`tile = null` mediante sus usos de suelo. La primera intervención enlazó
`mw24_1000` únicamente a las 32 HRU cuyo uso es `corn_lum`.

Además, las 36 unidades de ruteo tenían conexiones `sur`, `lat` y `rhg`, sin
salida `til`. En SWAT+ los tipos de hidrograma identifican flujos separados,
incluido el drenaje artificial; véase la
[documentación oficial de conectividad](https://docs.swat.tamu.edu/input-reference/con/).
La tercera corrida añadió `sdc <canal existente> til 1.00000` a cada unidad,
manteniendo las conexiones anteriores y actualizando `out_tot`.

| Término anual | Referencia | Drenaje sin ruteo | Drenaje con ruteo |
| --- | ---: | ---: | ---: |
| Precipitación (mm) | 1080,817 | 1080,817 | 1080,817 |
| ET (mm) | 843,991 | 834,971 | 834,971 |
| Drenaje `qtile` (mm) | 0 | 64,234 | 64,234 |
| Percolación (mm) | 125,130 | 70,784 | 70,784 |
| Rendimiento hídrico `wateryld` (mm) | 109,640 | 175,592 | 175,592 |

Generar drenaje sin conectarlo empeoró el caudal observado en el outlet.
Añadir su conexión mejoró las métricas respecto de esa intervención y de la
referencia. Esto respalda corregir la conectividad al representar drenaje;
la asignación a todo el maíz sigue siendo una máscara experimental.

El NSE continúa negativo y el sesgo es grande. ET/precipitación es aproximadamente
0,78 en la referencia y 0,77 en las pruebas. Ese cociente es una señal para
investigar, no un criterio universal de aceptación. El cierre de masa completo
todavía **no se calculó**: sumar lluvia, ET y algunos flujos reportados no lo
demuestra.

## Recorrido para usuarios

En **Simulaciones**, una corrida SWAT+ puede vincular un dataset observado de
caudal y una estación USGS. La comparación mensual requiere salidas diarias
del baseline estándar. Para estas tres corridas, Simulaciones e Informes
presentan métricas, gráfico observado/simulado, cobertura, indicadores físicos
y descargas CSV/JSON. El JSON conserva configuración, procedencia y diagnóstico.

El playback permite consultar los estados físicos disponibles por fecha;
estas corridas estándar no producen estados FSPM. El control de visibilidad
existente también protege las descargas por propietario o rol autorizado.

Desde una sesión autenticada, por ejemplo:

```text
GET /api/v1/simulations/sf19-diag-v2-tile-routed/availability
GET /api/v1/simulations/sf19-diag-v2-tile-routed/playback?date=2019-07-15&resolution=DAILY
GET /api/v1/simulations/sf19-diag-v2-tile-routed/export/csv
GET /api/v1/simulations/sf19-diag-v2-tile-routed/export/json
```

Las consultas autenticadas de detalle, disponibilidad, playback del 15 de julio
y ambas descargas respondieron HTTP 200 para las tres corridas sobre PostgreSQL.
Cada CSV exportado conserva 365 observaciones y sus 86 qualifiers estimados.
El frontend compiló sus tipos con `tsc --noEmit --incremental false`.
Esta evidencia no incluye una revisión visual del navegador ni una suite de tests.

## Artefactos y reproducción

Resumen versionable:
[south_fork_baseline_2019_diagnostic.json](../research_domain/south_fork_baseline_2019_diagnostic.json).
Los proyectos, logs, salidas completas y descargas permanecen localmente en
`backend/data/baseline-diagnostic-2019-v1/` y `backend/data/baseline-diagnostic-2019-v2/`;
esas carpetas de runtime están excluidas de Git. Los originales conservaron
su fingerprint SHA-256 en ambas ejecuciones.

Desde `backend/`, con IDs de registros existentes y un identificador nuevo:

```bash
venv/bin/python scripts/run_south_fork_baseline_diagnostic.py \
  --experiment-id sf19-nuevo \
  --owner-id UUID_USUARIO --watershed-id UUID_CUENCA \
  --scenario-id UUID_ESCENARIO_NEUTRAL --dataset-id UUID_DATASET_USGS \
  --output-root data/baseline-diagnostic-nuevo --drainage-probe
```

Para ejecutar únicamente la variante drenada con conexión al canal, usar
`--routing-probe` en lugar de `--drainage-probe`, con otro ID y carpeta.
El runner exige PostgreSQL local `digitaltwin`, conserva el proyecto fuente y
rechaza sobrescribir IDs/carpetas. `--project`, `--executable` y
`--warmup-years` permiten declarar sus rutas y warm-up explícitamente.

La lista histórica del adaptador incluía nueve archivos de entrada y omitía
`rout_unit.con`; el resumen agrega su inspección y hashes de intervención.
El código actual incorpora drenaje, hidrología y conectividad en los checksums
para nuevas corridas. El commit registrado por las ejecuciones corresponde
al HEAD durante el desarrollo y no representa por sí solo estos cambios aún
sin commit.

## Siguiente trabajo y límite del resultado

La siguiente tarea física es trazar volúmenes entre HRU, unidades de ruteo,
acuíferos y canales, comprobar unidades/área del outlet y pérdidas, y contrastar
ET y manejo con evidencia externa. Después corresponde delimitar/calibrar la
referencia en un periodo de desarrollo y reservar la evaluación independiente.

Estas pruebas usaron un año ya explorado y una máscara de cultivo estática
CDL 2019; no reconstruyen rotaciones ni drenaje histórico multianual. Son evidencia
de diagnóstico, con **H1 no evaluada**. El reporte final histórico y el gemelo
acoplado `phase234-sf-2019-v2` mantienen su propio linaje.

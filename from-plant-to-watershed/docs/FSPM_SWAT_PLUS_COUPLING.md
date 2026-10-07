# Contrato de acoplamiento FSPM–SWAT+

Describe la ruta vigente de `swat_coupled_runner.py` y
`twin_coupling_engine.py`. Los experimentos anteriores se distinguen en
[estado actual](CURRENT_STATE.md) y [reporte publicado](FINAL_REPORT.md).

## 1. Cadena de ejecución

```text
Solicitud y preflight del proyecto/cultivo
  → copia aislada y compatibilidad de inputs SWAT+
  → SWAT+ baseline: calendario ejecutado y agua por HRU
  → FSPM por grupo de calendario, con forcing asignado y agua estimada
  → resumen estacional dedicado y mapper de plants.plt
  → nueva copia SWAT+ y nueva ejecución
  → comprobación de calendario, agua y forcing; repetición hasta convergencia
  → resultados normalizados, provenance y playback PostgreSQL
```

Cada llamada al adaptador prepara un workspace nuevo. Las entradas científicas
fuente se conservan; las modificaciones y sus hashes se registran en las copias.
El resultado acoplado no se ajusta después de la ejecución.

La primera ejecución baseline permite obtener condiciones y eventos para el
acoplamiento. No implica automáticamente una pareja baseline/acoplado publicada
con validación contra USGS; la corrida normal se registra como simulación de
respuesta a inputs y deja `validation=NOT_AVAILABLE`.

## 2. Preflight y compatibilidad

`POST /api/v1/simulations/preflight` requiere autenticación y no crea corridas.
Comprueba ejecutable, proyecto, archivos declarados, forcing y cadena activa de
cultivo. Un `corn` presente en `plants.plt` no basta: HRU, landuse, comunidad,
rotación y acciones de manejo deben referenciar el cultivo objetivo.

El proyecto fuente South Fork con cultivo genérico `agrl` no se acepta como
maíz acoplado. La variante experimental CDL 2019 enlaza 32 HRU de mayoría de
maíz; no constituye reconstrucción de manejo histórico.

`swat_input_compatibility.py` valida campos enteros de planta, comunidad,
manejo y controles. Convierte tokens decimales matemáticamente enteros a
representación integral solo en la copia: por ejemplo `120.00000 → 120`.
Rechaza valores fraccionarios/no finitos y esquemas inesperados, preservando el
valor numérico de los parámetros. El adaptador exige `success.fin` actual y
outputs generados por el proceso, no archivos obsoletos.

## 3. Calendarios, población y forcing

`swat_executed_calendar.py` lee `PLANT` y `HARV/KILL` de `mgt_out.txt`.
Las HRU se agrupan cuando comparten fechas de siembra/cosecha. El FSPM se
ejecuta por grupo y no aplana los calendarios distintos.

La ruta multianual conserva todas las parejas completas por HRU. Las firmas de
convergencia incluyen cada temporada y los agregados FSPM usan los grupos del
año correspondiente, con una temporada de maíz por HRU/año. Fuera de la
ventana activa, el playback conserva el calendario anual conocido y marca el
cultivo como inactivo. Las temporadas que cruzan años requieren otro contrato
de agregación y se rechazan en esta ruta FSPM.

- Los eventos son operaciones **simuladas por SWAT+**, no observadas en campo.
- El clima usa `hru.con.wst → weather-sta.cli` y sus archivos diarios.
- Los agregados usan área HRU × fracción CDL de maíz cuando está disponible;
  sin manifiesto CDL válido se usan pesos de área HRU y se declara la ausencia.
- El reloj de crecimiento usa `corn.tmp_base` y se reinicia al inicio del cultivo.
- CO₂=400 ppm es una entrada asumida en esta ruta.
- El conteo de plantas es configurable **por grupo**. South Fork 2019 usa
  1.000 por calendario y publica hasta diez muestras de cada población activa.
- Las muestras son slots estables de una población numérica, no plantas de
  campo identificadas por sensores.

El forcing efectivo de la copia SWAT+ se compara con el usado por FSPM; una
diferencia impide aceptar la corrida. El origen meteorológico del bundle
South Fork reciente permanece `SOURCE_UNVERIFIED`.
El experimento posterior `sf-multi-v1` usa la copia meteorológica auditada y
corregida; conserva su procedencia propia sin cambiar las etiquetas históricas.

## 4. Agua SWAT+ → FSPM

En frecuencia `DAILY`, el FSPM recibe la salida `soil_water_average_mm`
(`sw_ave`) por HRU de la iteración SWAT+ previa. `swat_soil_water.py`
relaciona cada HRU con `soils.sol` y usa los umbrales de inicialización de
SWAT+ 61.0.2.61.

En esa versión, el almacenamiento reportado excluye el agua al punto de
marchitez. Se calcula:

```text
f = sw_ave / Σ(AWC_capa × espesor_capa)
agua volumétrica estimada por capa = WP_capa + f × AWC_capa
```

La estimación se pondera por el espesor dentro de la profundidad radicular FSPM
y se limita por saturación. A almacenamiento cero coincide con WP; a
almacenamiento de capacidad de campo coincide con WP + AWC.
Las condiciones y umbrales de las HRU de un calendario se ponderan para la
población de ese grupo.

La fracción disponible se supone uniforme en el perfil porque no hay agua
diaria por capa. Por ello humedad volumétrica, agua radicular y fracción
disponible llevan evidencia **`DERIVED`** y una limitación explícita.
No son mediciones ni estados de humedad SWAT+ por capa.

Con salida SWAT+ mensual/anual, el runner no tiene agua HRU diaria para esta
retroalimentación y usa **24 vol% `ASSUMED`** en el FSPM. Las unidades internas
del modelo son porcentaje volumétrico [0, 100]; la heterogeneidad hídrica usa
puntos porcentuales. El antiguo error `0.24` fracción → `0.24 %` fue corregido
en código, sin recalcular automáticamente resultados históricos.

## 5. FSPM → SWAT+: parámetros estacionales

`CouplingPlantParameterSummary` separa el contrato estacional de los estados
diarios. Los máximos de LAI, altura y raíz pueden tener fechas distintas;
el resumen no sirve para reconstruir una escena fechada.

El runner acepta un resumen vegetal congelado o un periodo exclusivo de
derivación. En la [entrega 2](MULTIYEAR_EXPERIMENT_DELIVERY_2.md), B deriva su
resumen en 2010 y lo reutiliza íntegro en 2013–2020. Los estados diarios siguen
respondiendo al agua/clima de cada año; sus rasgos no se usan para reajustar el
registro vegetal durante TRAIN/VALIDATION.

| Variable/resumen FSPM | Campo SWAT+ | Unidad |
| --- | --- | --- |
| LAI máximo | `lai_pot` | m² hoja/m² suelo |
| Desarrollo relativo de LAI | `frac_hu1`, `lai_max1`, `frac_hu2`, `lai_max2` | Fracciones |
| Inicio de declive foliar | `hu_lai_decl` | Fracción de unidades térmicas |
| Altura máxima | `can_ht_max` | m |
| Profundidad radicular máxima | `rt_dp_max` | m, limitada por el perfil de suelo cuando se conoce |
| Coeficiente de extinción de dosel | `ext_co` | Adimensional |
| Eficiencia de uso de radiación | `bm_e` | kg/ha/(MJ/m²) |

El mapper verifica el header real y los rangos, y registra original, valor FSPM,
valor escrito, delta, unidad, clamp y HRU destinatarias. `ext_co` y `bm_e`
proceden de supuestos paramétricos con variación poblacional; no son rasgos
inferidos de observaciones ni calibrados automáticamente.

Se modifica **un único registro del cultivo objetivo**, `corn` en South Fork.
Los diferentes grupos FSPM quedan resumidos en una parametrización compartida;
no se transmite una parametrización vegetal espacialmente distinta por HRU.

SWAT+ recalcula su hidrología y fisiología. No se escriben directamente ET,
uptake, estrés, conductancia estomática, distribución de raíces ni rendimiento
diarios del FSPM en entradas o salidas SWAT+.

## 6. Convergencia y publicación

El runner permite hasta cinco iteraciones por defecto y exige:

1. Calendarios ejecutados coincidentes por HRU con los usados por FSPM.
2. En `DAILY`, máximo cambio absoluto de agua promedio diaria HRU ≤0,1 mm.
3. Igualdad del forcing comprobado y aplicación del mapper.

Cambios de cobertura o falta de convergencia producen un error. Los manifiestos
conservan cada iteración, workspace y actualización. South Fork 2019 corregido
convergió en dos iteraciones acopladas, con último delta 0,001 mm.

Las salidas conservan resolución y soporte: planta FSPM, campo agregado, HRU
SWAT+, canal SWAT+ y outlet. La altura y raíz proceden del FSPM; el build SWAT+
utilizado no las imprime directamente en `hru_pw_day.txt`. Caudal m³/s y
almacenamiento de canal m³ no justifican inferir nivel hidráulico.

## 7. Evidencia y siguiente evaluación

La [auditoría de sensibilidad](audits/PHASE_3_5_COUPLING_SENSITIVITY_AUDIT.md)
encontró respuesta observable en ocho probes OAT; `ext_co` no dio respuesta
detectable y la altura directa no era observable en ese build. Es evidencia
computacional diagnóstica, no calibración, validación observacional ni Sobol.

El gemelo actualizado requiere comparación propia contra USGS. El runner final
histórico y la ruta operativa no son intercambiables: sus calendarios, humedad,
warm-up y linaje deben quedar explícitos en el siguiente experimento.

# Entrega 1: referencia física South Fork

Fecha: **2026-10-06**. Evaluación de desarrollo: 2019; calentamiento: 2000–2018.
Persistencia: **pglocal / digitaltwin**, por la ruta normal de simulaciones.

## Decisión

**Referencia diagnosticada y preparada para iniciar calibración multianual de
desarrollo, bajo un escenario agrícola fijo y explícito.** No está calibrada ni
validada: sigue subestimando fuertemente el caudal. El cierre numérico de la red
no demuestra precisión física ni respalda H1.

Se corrige la procedencia del clima de warm-up, se reproduce la referencia
preservada y se delimitan los procesos y parámetros que debe abordar la entrega 2.
No se ajustaron parámetros para mejorar 2019 ni se examinó un nuevo TEST.

## 1. Comparación controlada en pglocal

| Corrida | Papel | Volumen outlet, hm³ | RMSE mensual, m³/s | NSE mensual | PBIAS mensual, % | Frames diarios |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `sf19-src-v2-geom-routed` | Referencia preservada | 94,460194 | 8,080962 | −0,409287 | −67,296532 | 365 |
| `sf19-phys-ctrl-v1-reference` | Control con código actual | 94,460194 | 8,080962 | −0,409287 | −67,296532 | 365 |
| `sf19-phys-fix-v1-reference` | Warm-up corregido | 94,520471 | 8,078538 | −0,408441 | −67,277113 | 365 |

USGS 05451210: **289,423232 hm³**, 365 días y 12 meses completos, conservando
86 valores estimados. PBIAS se calcula sobre medias mensuales; no es exactamente
el porcentaje de diferencia entre los volúmenes anuales.

El control reproduce **exactamente los 365 caudales diarios** de la referencia.
La corrección aumenta el volumen anual en **0,060277 hm³**; la diferencia máxima
diaria es 0,292 m³/s. Su efecto mensual es pequeño y no resuelve el déficit.
La diferencia de volumen de la variante corregida frente a USGS es **194,902762 hm³**.

Comunes a control y corrección:

- Motor desde fuente, commit `77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d`;
  SHA-256 del ejecutable `56963a6475aa9014a56a6825749d7fc513fce2dd40dcbb0c0b6a5976364a3c9d`.
- 36 HRU, 37 cauces físicos, outlet GIS `153`, área y conexiones iguales.
- 28 archivos centrales trazados idénticos, incluyendo suelos, manejo,
  drenaje, acuíferos, geometría y configuración de simulación.
- Misma observación, fechas y clima de **2019 y posteriores**, comprobado
  valor por valor en las 25 estaciones. Solo cambia el clima del warm-up.

La copia preparada ya contiene la intervención anterior de geometría/drenaje.
Su fingerprint completo difiere del proyecto original previo a esa intervención;
la reproducción compara los inputs **ejecutados** y los hashes del clima.
La agregación de weather del nuevo playback utiliza áreas HRU; eso corrige una
estadística de presentación y no modifica el forcing nativo del control.

## 2. Corrección climática

La copia `backend/data/baseline-diagnostic-physical-v1/corrected-project` conserva
el proyecto anterior. Se modifican 125 archivos meteorológicos y **1.062 registros**:

- **542 registros** distintos al sustituir los cierres de año interpolados
  de 2000, 2004, 2008, 2012 y 2016 por los valores gridMET recuperados.
  Se revisan 625 registros estación/fecha/archivo; los que coinciden se conservan.
  Temperatura contiene dos valores por registro.
- **192 registros** de lluvia de 2011 en `s42522n93585w`.
- **328 registros** de viento de 2015 en `s42480n93450w`.

Se usan las descargas ya archivadas y contrastadas con el consenso del caché en
la [auditoría meteorológica](METEOROLOGY_DIAGNOSTIC_2019.md), con SHA-256,
coordenadas, fechas, unidades y recibos de procedencia. Se conserva el redondeo
del builder: lluvia/temperatura/solar/viento a 0,01 y humedad relativa a 0,001.
El viento sigue a 10 m: el motor hace su ajuste de altura.

Los cierres de 2020 y 2024 siguen interpolados porque no intervienen en esta
corrida. **Antes de utilizar esos años como forcing deberán corregirse** con las
descargas archivadas; esta variante no se presenta como reparación de 2000–2025.
Recuperar esos datos no convierte gridMET en una observación meteorológica validada.

El manifiesto completo está incluido en la configuración de la corrida corregida
en PostgreSQL y en el artefacto de comparación versionado.

## 3. Procesos físicos de la variante corregida

### ET y cobertura vegetal

| Término nativo 2019 | mm |
| --- | ---: |
| Precipitación | 1.080,817 |
| PET | 978,812 |
| ET | 834,973 |
| `esoil` | 491,180 |
| `eplant` | 321,848 |
| `ecanopy` | 21,943 |
| Percolación inferior | 70,802 |
| Drenaje subsuperficial | 64,277 |

Las diferencias pequeñas entre ET y la suma de componentes proceden del
redondeo de las salidas. `esoil` representa aproximadamente 58,8 % de ET;
no equivale exclusivamente a evaporación de suelo desnudo: el código incluye
demanda evaporativa consumida por nieve y agua superficial.

**407,162 mm de `esoil`** se producen en días/HRU con LAI ≤ 0,1, ponderados por
área: aproximadamente 82,9 % de ese componente. Estos estados tienen una media
de 3.680 kg/ha de residuos; poca cobertura viva no significa suelo sin residuos.
Solo 28,233 mm corresponden a días con nieve al inicio, sin aislar sublimación;
las categorías se solapan. La nieve no explica por sí sola el total de `esoil`.

El maíz se planta el 15/16 de mayo y se cosecha/termina entre el 27 de agosto y
el 3 de septiembre; son eventos **modelados**. La transpiración se concentra
en junio–agosto. La revisión mensual y los 72 eventos agrícolas de las 36 HRU
están en el artefacto de procesos.

TerraClimate AET 2019 suma 683,073 mm en los mismos puntos y pesos. Es otro
modelo, no ET medida; su diferencia no justifica forzar ET a ese valor. PET
SWAT+ queda entre TerraClimate PET y gridMET ETr. Se mantiene `pet_co=1`.

### Suelos y drenaje

- Ocho perfiles gNATSGO usados, todos de 2.000 mm; profundidades de capas
  crecientes, AWC/conductividad positivas y texturas que suman 100 %.
- AWC del perfil ponderada por área: **279,826 mm**; conductividad de las
  capas entre **3,312 y 33,012 mm/h**. Son inputs coherentes, sin validación local.
- Grupo hidrológico D: **63,074 %** del área; el resto es B. Hay diferencias
  espaciales que no deben sustituirse por un suelo único para mejorar caudal.
- Drenaje activo en 32 HRU de maíz: **50.610,133 ha / 90,232 %** del modelo.
  Es una máscara experimental de uso fijo, no cobertura histórica observada.
- La ruta `til` llega al canal; aporta **36,053405 hm³** en 2019. No queda
  drenaje generado fuera de las conexiones por el problema anterior.

**Parámetros efectivos:** `topohyd_init.f90` sustituye `perco` por **0,1** en
HRU con drenaje, aunque `hydrology.hyd` contiene 0,05. La transformación no lineal
da `perco_lim≈0,001467` en esas HRU, frente a ≈0,001126 sin drenaje. Además,
`cal_parm_select.f90` **omite la modificación de `perco` en HRU drenadas**.
No incluir ese parámetro como control ajustable de todo el maíz en esta versión.
Modificar `perco` en el archivo tampoco acredita una intervención efectiva.

### Acuíferos y pérdidas fluviales

36 acuíferos someros y 36 profundos; cada grupo representa el área de la cuenca.
No sumar ambas áreas para normalizar flujos. Términos someros anuales:

- Recarga: **70,799 mm**; aporte al cauce: **9,106 mm / 5,108 hm³**.
- Revap: **20,581 mm**, contabilizado por separado de ET de las HRU.
- Transferencia profunda: **3,539 mm**, recibida por acuíferos profundos sin
  salida al canal; no duplicarla como pérdida de cuenca y cambio de almacenamiento.
- El 92,443 % de los días/acuífero someros reporta flujo cero. La rutina calcula
  retorno cuando la profundidad freática cruza `flo_min` (3 m en el input);
  revisar umbral, almacenamiento y respuesta antes de ajustar el aporte base.

De 2 de enero a 31 de diciembre, el almacenamiento acuífero agregado aumenta
22,974 hm³; suelo +1,190 hm³ y nieve −1,550 hm³. Estos cambios son estados
modelados y no un contraste con observaciones de almacenamiento.

En los 212,637 km de cauces, para esa misma ventana:

- Precipitación sobre cauces: 7,750 hm³; evaporación: 0,901 hm³;
  filtración: 16,359 hm³; almacenamiento cauce +0,326 hm³ y llanura +0,818 hm³.
- Red **CLOSED**, residuo **1,686 m³**; relativo **1,63×10⁻⁸**.
- Contabilidad de cuenca **PARTIAL_ACCOUNTING**, residuo −0,006145 mm:
  falta almacenamiento de dosel y estados terrestres independientes sin redondeo.

La entrada directa anual a la red es 103,620 hm³ y el outlet 94,520 hm³:
diferencia neta **9,100 hm³**. Esto ubica la magnitud del efecto del ruteo;
no demuestra cuál sería el caudal sin pérdidas, porque habría retroacciones.
El déficit frente a USGS es mucho mayor. Área modelada **560,888 km²** frente a
**580,158 km²** de referencia USGS (−3,321 %); tampoco basta para explicar el déficit.

## 4. Qué pasa a la entrega 2

1. Congelar años de desarrollo/calibración, TRAIN, VALIDATION y TEST con el
   registro de años ya explorados. Reparar cierres climáticos de los años que
   entren al nuevo periodo. 2019 permanece como desarrollo.
2. Declarar manejo y máscara de drenaje como **escenario fijo experimental**
   mientras no exista reconstrucción histórica; compartirlos entre A/B/C/D.
3. Registrar un presupuesto acotado de sensibilidad/calibración: partición
   ET/cobertura, drenaje y respuesta acuífera primero. Conservar los perfiles
   espaciales y longitudes físicas. Excluir parámetros inoperantes; verificar
   que cada intervención cambie el proceso pretendido en desarrollo.
4. Evaluar A contra USGS antes de congelarlo y comparar A/B con las mismas
   fechas/forcings. Mantener ET/PET externas como diagnósticos secundarios,
   sin presentarlas como mediciones ni usar ML para dar por validada la física.

## 5. Artefactos y reproducción

- [Comparación y manifiesto climático](../research_domain/south_fork_physical_reference_2019_v1.json).
- [Suelos, ET mensual, eventos, parámetros y acuíferos](../research_domain/south_fork_physical_processes_2019_v1.json).
- Preparación: `backend/scripts/prepare_south_fork_forcing_correction.py`.
- Ejecución/persistencia: `backend/scripts/run_south_fork_baseline_diagnostic.py`
  con `--forcing-manifest` para la variante corregida.
- Comparación: `backend/scripts/inspect_swat_water_path.py`, ahora acepta
  `--forcing-comparison CONTROL TREATMENT`; coteja clima, parámetros,
  calendario, observaciones y reproducción diaria de la referencia.
- Procesos: `backend/scripts/review_south_fork_physical_reference.py`.

Desde `backend`, con PostgreSQL existente, motor y archivos archivados disponibles:

```bash
venv/bin/python scripts/prepare_south_fork_forcing_correction.py \
  --project data/baseline-diagnostic-source-geometry-v2/drainage-probe-project \
  --archive data/baseline-diagnostic-meteorology-v1 \
  --destination data/baseline-diagnostic-physical-replay/corrected-project
```

Ejecutar dos veces el runner normal con IDs nuevos: control sobre el proyecto
preparado de geometría v2, tratamiento sobre la nueva copia y su manifiesto.
Usar `--warmup-years 19`, el binario de `compile-v4`, los IDs existentes de
propietario/cuenca/escenario/dataset y directorios de salida nuevos. Los comandos
rechazan IDs/directorios ocupados; no sobrescriben corridas anteriores.

Las dos corridas nuevas tienen 365 registros y 365 frames cada una. Se auditó la
evidencia nativa y el código fuente fijado. No se ejecutaron suites de tests ni
inspección visual; esta entrega no modifica el frontend.

Rutinas primarias consultadas: [inicialización hidrológica](https://github.com/swat-model/swatplus/blob/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d/src/topohyd_init.f90),
[selección de parámetros](https://github.com/swat-model/swatplus/blob/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d/src/cal_parm_select.f90),
[ET real](https://github.com/swat-model/swatplus/blob/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d/src/et_act.f90),
[acuíferos](https://github.com/swat-model/swatplus/blob/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d/src/aqu_1d_control.f90).
Se leyeron las copias locales del commit; sus hashes acompañan el artefacto.

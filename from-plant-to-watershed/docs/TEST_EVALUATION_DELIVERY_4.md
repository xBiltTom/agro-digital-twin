# Entrega 4 — evaluación mensual reservada

**Fecha:** 2026-10-06. **Experimento:** `sf-test-v1`. **Intervalo:** 2021–2025.
**Estado:** completado en pglocal; **H1 no respaldada**.

## Resultado primario

Se evaluaron los 60 meses TEST, con 1.826 días aprobados: 1.248 A y 578 A,e.
No hubo días faltantes/rechazados en el análisis primario. Los 578 valores
estimados se conservaron según el protocolo; la sensibilidad los excluye.

| Serie | RMSE (m³/s) | MAE (m³/s) | NSE | PBIAS (%) | KGE modificado |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 3,695249 | 2,153886 | 0,268046 | −32,087 | 0,433847 |
| B | 3,579490 | 2,087254 | 0,313187 | −28,626 | 0,478738 |
| C | 2,749353 | 1,997462 | 0,594811 | +44,616 | 0,423755 |
| D | 4,517045 | 2,588070 | −0,093717 | +65,501 | 0,219040 |
| Afín A | 3,946227 | 3,115865 | 0,165243 | +50,023 | 0,165124 |
| Afín B | 3,878842 | 3,085770 | 0,193507 | +50,822 | 0,189095 |
| Climatología | 4,493897 | 3,756530 | −0,082536 | +90,522 | −0,162179 |

La reducción puntual D/A es **−0,821796 m³/s (−22,239 %)**: el RMSE de D es
mayor. IC95 de reducción absoluta **[−3,286117; +1,871064] m³/s**; IC95 relativo
[−140,124; +39,740] %. Incluye cero y no cumple la regla predefinida. No se
respalda H1; tampoco se demuestra un deterioro significativo con ese intervalo.
Las 2.000 réplicas están definidas.

C tiene el menor RMSE puntual, con reducción C/A del 25,598 %, pero su IC95
absoluto [−0,397262; +2,198959] m³/s incluye cero. Además conserva PBIAS +44,616 %
y no mejora KGE frente a A. Por tanto, ese menor RMSE no autoriza declarar
una mejora robusta de todas las métricas ni sustituir post hoc a D por C en H1.
B/A tiene una reducción pequeña de 0,115759 m³/s con intervalo descriptivo
[0,011274; 0,226343]; es un contraste secundario sin ajuste por multiplicidad,
sin decisión confirmatoria separada ni demostración fisiológica.

Al excluir estimados quedan **36 meses** con cobertura ≥ 90 %; los otros 24
permanecen en la máscara del calendario. RMSE A 4,418513, B 4,250830,
C 2,781945 y D 5,383759 m³/s. Reducción D/A −0,965246 m³/s, IC95
[−4,481810; +2,857058]; **H1 sigue no respaldada**. Esta exclusión también
modifica la composición estacional del soporte, por lo que no representa
los mismos 60 meses anuales completos.

El [reporte completo](../research_domain/south_fork_test_delivery_4_v1.json)
conserva cifras sin redondear, todos los contrastes, métricas, QC, hashes y
las predicciones mensuales C/D. La decisión permanece congelada; no se
retocan modelos o umbrales para buscar un resultado favorable.

## Contratos y acceso

La evaluación consume el [protocolo multianual v1](../research_domain/south_fork_multiyear_protocol_v1.json)
y los [bundles C/D congelados](ML_RESIDUAL_DELIVERY_3.md). Antes de las corridas
y de consultar caudal TEST se guardó un recibo con hashes del motor, inputs
físicos, contrato vegetal 2010, modelos, receta y evaluador. El
[contrato de evaluación](../research_domain/south_fork_test_evaluation_contract_v1.json)
precisa intervalos percentiles, máscaras de calendario y sensibilidad a
estimados sin cambiar el contraste primario ni el presupuesto experimental.

C/D mantienen Ridge α = 10 y los scalers ajustados en TRAIN 2013–2017.
Climatología y correcciones afines conservan sus coeficientes TRAIN. No se
ajustan parámetros, features, modelos ni hiperparámetros con TEST.

El builder de features del backend reproduce primero las 96 predicciones de
desarrollo de cada brazo, con tolerancia absoluta 10⁻¹⁰ m³/s. Luego aplica esa
misma receta a TEST. La inferencia usa el mes completo: es retrospectiva.

## Publicación física y soporte observado

Cada pareja A/B anual vuelve a ejecutar desde 2000 con inputs fijos: no reinicia
almacenamientos al comenzar el año publicado. A/B difieren únicamente en
`plants.plt`; B usa el contrato vegetal derivado en 2010, sin recalcularlo con
los resultados TEST. Se publican frames diarios en la base `digitaltwin`
existente y se auditan caudales y balances nativos. Los outputs físicos diarios
se conservan; el resultado ML mensual se adjunta como resultado separado.

Las diez publicaciones suman **3.652 frames diarios**. Las auditorías nativas
clasifican las diez redes como `CLOSED`; el balance de cuenca sigue siendo
`PARTIAL_ACCOUNTING`, sin presentarlo como un cierre hídrico completo.

El dataset pglocal **`sf-test-v1-monthly`** registra doce artefactos: pares A/B
en CSV/Parquet (240 filas entre las dos variantes), predicciones de siete series
(840 filas), observaciones diarias, dos tablas de 2.000 réplicas, linaje,
esquema, contrato, recibos y manifiesto. Este manifiesto conserva además el hash
del reporte completo. Las corridas enlazan ese reporte y sus predicciones ML
mensuales mediante `validation.research_test_evaluation` y `ml_result`.
Los bundles C/D y las publicaciones de desarrollo permanecen intactos.

Los caudales observado/A/B mensuales usan las mismas fechas diarias aprobadas
USGS A/A,e. Se exige cobertura ≥ 90 % de los días del mes y no se imputan
observaciones. Se conserva el calendario completo de 60 meses, con máscara
explícita para meses que no cumplan cobertura.

La sensibilidad excluye A,e, recalcula cobertura y medias pareadas, y aplica
los modelos congelados con ese baseline físico recalculado. No cambia el
soporte del mes completo para meteorología y estados modelados. Por tanto,
esta sensibilidad modifica el target y la entrada de caudal físico del mes;
no es simplemente borrar filas del reporte primario.

## Incertidumbre y decisión

- Contraste primario: D frente a A; reducción absoluta `RMSE(A) − RMSE(D)`.
- Bootstrap circular pareado de bloques móviles de 12 meses calendario,
  2.000 réplicas, semilla 42 (`random.Random.randrange`).
- Cada réplica toma cinco bloques y los concatena. Todos los brazos comparten
  los índices; la máscara de elegibilidad se aplica después del muestreo para
  conservar huecos de calendario.
- Intervalo bilateral del 95 % mediante percentiles e interpolación lineal.
  Se reporta también reducción porcentual con denominador pareado por réplica.
- H1 respaldada solo si el límite inferior del intervalo primario es
  estrictamente positivo y las 2.000 réplicas están definidas. Sin umbral del
  15 % ni prueba t de errores mensuales independientes.
- B/A, C/A, D/B y D/C: contrastes secundarios con intervalos descriptivos sin
  ajuste por multiplicidad. No generan decisiones confirmatorias separadas.

RMSE, MAE, NSE, PBIAS y KGE modificado se calculan mediante
`scientific_core.ValidationEngine`; PBIAS simulado menos observado, KGE con
cociente de coeficientes de variación. El evaluador histórico y sus reportes
mantienen su interpretación anterior, explícita por versión.

## Reproducción y límites

Desde backend:

```bash
venv/bin/python scripts/run_south_fork_test.py
```

Después de completar la entrega, el runner verifica hashes y reutiliza los
resultados sin nuevas corridas, consultas de caudal ni evaluación. Rechaza
resultados o corridas incompatibles. Las interrupciones anteriores a la
evaluación pueden continuar con las publicaciones completadas y los mismos
inputs. No reentrena ni sobrescribe silenciosamente experimentos fallidos.

La referencia física sigue siendo exploratoria porque falló el criterio
predefinido de sesgo de calibración. La comparación evalúa caudal de salida
en una cuenca bajo manejo experimental fijo. Una reducción de error no valida
fisiología, causalidad vegetal ni conservación hídrica del residual ML.
D/C cambia baseline físico y features; no aísla el aporte de las features FSPM.

El recorrido integrado para usuarios y el paquete del artículo corresponden
a la entrega 5. No se ejecuta una suite de tests ni se inspecciona el navegador
como parte de estas corridas científicas.

Para reducir el tiempo de ejecución local se adelantaron los brazos B de 2024
y 2025 con un único worker adicional (`publish_south_fork_test_b.py`), usando
la función `publish` del runner congelado y workspaces/IDs independientes.
El recibo de coordinación conserva el hash del wrapper; ese proceso no consulta
caudal observado, no ajusta modelos y no evalúa H1. El runner principal reutiliza
esas publicaciones completadas antes de abrir las observaciones.

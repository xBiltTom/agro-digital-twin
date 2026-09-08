# Protocolo de selección de cuencas — Fase C

## Universo y definición de Corn Belt

El universo inicial usa la región de producción **Corn Belt** de USDA ERS:
Missouri, Iowa, Illinois, Ohio e Indiana. Se limita a streamgages USGS dentro de
esos estados. Esta delimitación es reproducible, no equivale a afirmar que
cada cuenca de los estados sea agrícola. La lista de candidatos y sus fuentes se
versionan en `research_domain/candidate_matrix.json`.

Fuente de definición: USDA Economic Research Service, *U.S. farm production
regions* (Corn Belt): Missouri, Iowa, Illinois, Ohio e Indiana.

## Inclusión

- fracción agrícola calculada con overlay de una geometría de cuenca verificada y
  USDA Cropland Data Layer, >= 0.60;
- caudal diario USGS (parámetro 00060, estadístico diario medio 00003);
- al menos 20 años efectivos: número de fechas diarias únicas / 365.2425 >= 20;
- completitud diaria >= 90% entre primera y última fecha de la serie utilizada;
- relación gauge–cuenca, geometría, CRS y drainage area oficiales documentados;
- cribado de presas/regulación mediante National Inventory of Dams u otra fuente
  oficial, con decisión y razón registradas;
- disponibilidad comprobada de cobertura de suelo y futura cobertura Landsat.

El umbral de 90% se aplica sólo para evitar que veinte años nominales oculten
gaps grandes; queda configurable en `watershed_selection.py`. Los meses para
agregación mensual usan el mismo umbral y permanecen marcados como excluidos, no
se rellenan. No se usa una tolerancia numérica automática entre área del gauge y
área de geometría: diferencias pueden reflejar métodos de delineación distintos
y requieren revisión y una decisión explícita.

## Exclusión

Se excluye una candidata ante agricultura <60%, período/cobertura insuficientes,
geometría o asociación no verificables, o una presa mayor/regulación material
documentada. Un campo no verificado se registra como `NOT_VERIFIED` y produce
`EXCLUDE`; nunca se convierte en un supuesto positivo.

## Geometría y agricultura

La geometría fuente debe declarar CRS. Las áreas se calculan tras transformar a
un CRS proyectado apropiado para el área (por ejemplo EPSG:5070 continental),
nunca directamente en EPSG:4326. El cálculo requerido es:

`geometría de cuenca + CDL/año + clases agrícolas declaradas → área agrícola / área total`.

Se registran dataset/año CDL, clases, CRS fuente/proyectado, áreas y fracción.
USGS Watershed Boundary Dataset es la fuente prevista para HUC/geometría.

## Presas y Landsat

La pantalla de presas no modela regulación: registra conteo, estructuras
relevantes, fuente y decisión. Landsat se registra como disponibilidad futura
(colección, resolución y período), sin inferir métricas no descargadas.

## Resultado

Sólo las candidatas `INCLUDE` entran al manifiesto congelado de dominio. El
conjunto debe incluir múltiples cuencas si los datos permiten la futura
validación espacial; de lo contrario la limitación se declara y bloquea Fase D.

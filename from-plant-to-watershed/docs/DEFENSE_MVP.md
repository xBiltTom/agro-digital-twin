# Defensa del MVP

## Qué es

Prototipo de gemelo digital agrícola multiescala ejecutable sobre PostgreSQL,
FastAPI y Next.js. Su vertical slice es:

`clima → 1000 plantas → campo → HRU proxy → cuenca → comparación mensual → validación`.

## Qué es real

- stack y persistencia PostgreSQL;
- API, dashboard, ejecución, provenance y cálculos;
- snapshot USGS 05451210 observado con checksum;
- cálculo de RMSE, NSE, PBIAS y R²;
- inferencia independiente de Streamlit mediante un ModelBundle instalado.

## Qué es simplificado

- fisiología individual: `SimplifiedPlantModel`, no FSPM;
- población: variabilidad paramétrica acotada y reproducible;
- tres HRU: `COARSE_HRU_PROXY`, no SWAT+;
- hidrología: SCS-CN/two-store, no SWAT+;
- forcing demo: sintético, incluso cuando se compara con USGS;
- comparación: `DEMONSTRATION_ONLY`, nunca una prueba de H0/H1.

El dominio 05451210 es `REFERENCE_RESEARCH_DOMAIN` con verificación parcial; no
es una cuenca científica congelada.

## Qué falta para la versión científica final

SWAT+ ejecutable y calibrado, FSPM completo, dominio multi-watershed con
CDL/NID/geometría verificados, NEX-GDDP-CMIP6, protocolo formal de validación
espacial y evaluación de H0/H1.

## Guion breve

1. Mostrar `/api/v1/system/capabilities` y distinguir ACTIVE de NOT_AVAILABLE.
2. Ejecutar el modo `DEMO_MULTISCALE` con 1000 plantas.
3. Mostrar agregados de campo, HRU proxy, balance hídrico y curvas mensuales.
4. Mostrar comparación observada sólo donde existan meses alineados.
5. Activar el Random Forest externo y explicar que predice runoff, no reemplaza
   el modelo de planta, y que su entrenamiento declarado es sintético.

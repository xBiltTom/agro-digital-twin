# ADR 001: core científico puro y adaptador de persistencia

Estado: aceptado (2026-09-07).

La lógica científica reside en `backend/scientific_core` y no puede importar
FastAPI, SQLAlchemy, HTTP ni modelos ORM. `SimulationOrchestrator` recibe un
`RunConfig` inmutable y devuelve valores Python de dominio.

`app.services.twin_coupling_engine` es un adaptador de aplicación: carga
entidades, construye la configuración, invoca el core y persiste resultados,
provenance y transiciones de estado. Si el core falla, persiste `FAILED` y un
error estructurado antes de propagar el fallo.

Esta frontera permite probar determinismo, unidades y balances sin base de
datos, y deja un punto de sustitución futuro para modelos de planta/campo,
proveedores climáticos y un adaptador SWAT+ real.

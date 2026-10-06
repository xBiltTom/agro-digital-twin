# ADR 001: core científico puro y adaptador de persistencia

Estado: aceptado (2026-09-07); descripción de implementación revisada 2026-10-05.

La lógica científica reside en `backend/scientific_core` y no puede importar
FastAPI, SQLAlchemy, HTTP ni modelos ORM. `SimulationOrchestrator` y
`MultiscaleSimulationOrchestrator` reciben `RunConfig` inmutable y devuelven
valores Python de dominio para las rutas simplificadas. `PlantPopulation`,
`PlantToFieldAggregator`, contratos, unidades y `ValidationEngine` también
pertenecen a este núcleo.

`app.services.twin_coupling_engine` es un adaptador de aplicación: carga
entidades, construye la configuración, invoca el core y persiste resultados,
provenance y transiciones de estado. Si el core falla, persiste `FAILED` y un
error estructurado antes de propagar el fallo.

La integración real SWAT+ ya existe en servicios de aplicación:
`swat_plus_adapter.py` prepara copias y ejecuta el proceso;
`swat_coupled_runner.py` coordina calendarios, agua y mapeo FSPM;
`playback_database.py` persiste los estados temporales. Esta capa puede usar
I/O y persistencia sin trasladarlos al núcleo puro.

La frontera permite probar determinismo, unidades y balances sin base de datos,
y sustituir proveedores/motores bajo contratos explícitos. Las rutas
simplificadas y SWAT+ real mantienen evidencia diferenciada.

Véanse [acoplamiento](../FSPM_SWAT_PLUS_COUPLING.md) y
[playback](../TWIN_PLAYBACK_CONTRACT.md).

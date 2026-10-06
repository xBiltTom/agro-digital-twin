# From Plant to Watershed

Plataforma de software científico multiescala: **FastAPI + PostgreSQL + Next.js**,
un FSPM simplificado y ejecución real de SWAT+ sobre South Fork Iowa River
(`USGS 05451210`).

La [ficha técnica](project_framework.md) guía la investigación y la
[reformulación experimental](research_reformulation.md) delimita el primer
artículo, sus comparadores y la corrección ML. El alcance implementado y sus
pendientes se describen en [estado actual](docs/CURRENT_STATE.md); el
[índice técnico](docs/README.md) reúne los contratos y la evidencia.

## Qué funciona

- Ejecución SWAT+ en copias aisladas, preflight, normalización de inputs y
  trazabilidad por hashes, configuración efectiva y versión del código.
- FSPM por calendario de siembra/cosecha ejecutado por SWAT+, con agregación
  ponderada y estimación de humedad radicular desde salidas diarias de HRU.
- Playback persistido como JSONB en PostgreSQL, consultable por fecha y resolución.
- Visor 3D de planta, campo y cuenca, con muestras modeladas y explorador de
  resultados HRU/canal. La geometría es contextual: falta la unión espacial
  verificada entre resultados y mallas.
- Catálogo de simulaciones, autenticación/RBAC, informes PDF/Word/Excel y
  diagnóstico interpretativo con LangChain o fallback heurístico.

La corrida operativa de referencia es `phase234-sf-2019-v2` (2019 diario).
El endpoint de reporte científico todavía publica `south-fork-final-v2`
(evaluación 2018–2020), cuya mejora mensual fue **0 %**. Esa evaluación anterior
no mide la ruta hídrica actual. Véase [reporte publicado](docs/FINAL_REPORT.md).

## Instalación local

Requisitos: Python 3.12+, PostgreSQL, Node.js compatible con Next.js 16 y pnpm.
El frontend declara su versión de pnpm en `package.json` y usa `pnpm-lock.yaml`.
Los comandos siguientes parten de `from-plant-to-watershed/`.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Configurar `backend/.env`:

```dotenv
APP_ENV=development
SECRET_KEY=una-clave-local-aleatoria-de-al-menos-32-caracteres
ENABLE_DEMO_SEED=false
DATABASE_URL=postgresql+asyncpg://digitaltwin@/digitaltwin?host=/run/postgresql&port=5432
```

La URL de ejemplo corresponde a la instancia PostgreSQL local por socket
`/run/postgresql`. Ajustarla a la instalación utilizada. No es necesario crear
otro clúster con `scripts/start_local_postgres.sh` para ese entorno.

La API inicializa tablas, migraciones SQL versionadas y roles. Una instalación
nueva puede crear su primer administrador mediante:

```bash
python -m app.cli create-admin --email admin@example.org --full-name "Administración inicial"
uvicorn app.main:app --reload --port 8000
```

`ENABLE_DEMO_SEED=true` habilita explícitamente fixtures legacy de desarrollo.
`python -m app.cli bootstrap-mvp` prepara datos demostrativos, pero no ejecuta
una validación científica ni sustituye la configuración de SWAT+.

### Frontend

En otra terminal, desde `from-plant-to-watershed/`:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Abrir `http://localhost:3000`. Las rutas principales son `/simulations`,
`/twin-3d`, `/datasets` y `/reports`.

## Ejecutar SWAT+ real

El ejecutable y el proyecto de entrada deben estar disponibles localmente.
Configurar en `backend/.env`:

```dotenv
SWAT_PLUS_EXECUTABLE=/ruta/al/ejecutable/swatplus
SWAT_PLUS_PROJECT_DIR=/ruta/al/proyecto/TxtInOut
SWAT_PLUS_WORKING_DIRECTORY=data/swat-runs
SWAT_PLUS_TIMEOUT_SECONDS=3600
```

El proyecto necesita `file.cio` en su raíz o dentro de `TxtInOut/`. Crear la
simulación con `mode=SWAT_PLUS`, `hydrology_backend=SWAT_PLUS` y el `run_type`
`SWAT_STANDARD_BASELINE` o `SWAT_MULTISCALE_COUPLED` en `swat_plus`.
Las opciones por corrida incluyen periodo de calentamiento, frecuencia,
timeout y unidad outlet.

Antes de crear una corrida acoplada, `POST /api/v1/simulations/preflight`
comprueba cultivo activo, manejo, forcing y compatibilidad. La existencia de
una fila `corn` por sí sola no demuestra que las HRU cultiven maíz. South Fork
usa una variante experimental de manejo informada por CDL 2019.

Para retroalimentación hídrica usar salida `DAILY`. En frecuencias más gruesas
la trayectoria FSPM diaria conserva humedad asumida si no hay salidas HRU
diarias. Los fallos quedan como `FAILED`; no se sustituyen por hidrología proxy.
Detalles en [acoplamiento](docs/FSPM_SWAT_PLUS_COUPLING.md).

## Persistencia y playback

`playback_frames` guarda cada frame JSONB por `(simulation_id, resolution, date)`
con SHA-256. FastAPI lee PostgreSQL; los archivos SQLite comprimidos son
artefactos históricos de importación/recuperación. SQLite también se usa en
pruebas aisladas, no como runtime normal.

Los resultados versionados de South Fork 2019 están en
`backend/data/phase1-south-fork-2019/results/`. El script
`backend/scripts/register_phase234_south_fork_2019.py` verifica checksums e
importa un bundle completado con propietario, cuenca y escenario existentes.
El registro es idempotente para contenido coincidente. Véase
[estado actual](docs/CURRENT_STATE.md).

## Laboratorio ML externo

El [laboratorio Streamlit](../agro-digital-twin-st/README.md) exporta bundles
autocontenidos. El backend permite registrar bundles dentro de
`EXTERNAL_MODELS_DIR` mediante `POST /api/v1/models/register`.
Los bundles mensuales versionados son de desarrollo sintético; su desempeño
no es evidencia para H1.

## Verificación

```bash
cd backend
source .venv/bin/activate
pytest -q tests
```

Desde `frontend/`:

```bash
pnpm test
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

La suite backend configura una SQLite temporal propia. Las pruebas de motor
real requieren recursos SWAT+ explícitos; las comprobaciones específicas de
PostgreSQL usan scripts separados. Aprobar pruebas de software no equivale a
validar los resultados frente a observaciones.

# From Plant to Watershed

Base de software científico reproducible para el proyecto de investigación
**“From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling
Individual Plant Models with SWAT Hydrology and Downscaled Climate
Projections”**.

## Estado actual: demostración reproducible

La implementación actual ejecuta un pipeline diario persistente compuesto por:

- `SyntheticClimateProvider`: forzamiento meteorológico estacional y pseudoaleatorio con seed; **no** contiene observaciones ni NEX-GDDP-CMIP6.
- `SimplifiedPlantModel`: planta representativa algebraica; **no** es un FSPM ni representa órganos, fenología o población.
- `SimplifiedHydrologyModel`: balance conceptual agregado SCS-CN con diagnóstico de residual; sigue siendo un proxy y **no** ejecuta SWAT+.
- `SwatPlusAdapter`: ruta opcional a una corrida `SWAT_STANDARD_BASELINE` real. Copia el proyecto a un workspace por `run_id`, ejecuta el binario y persiste únicamente los outputs que SWAT+ produjo.
- `UsgsStreamflowProvider`: infraestructura observacional separada que conserva RAW,
  checksum, QC y caudal diario normalizado; **no** calibra ni alimenta los modelos simplificados.

Cada corrida guarda seed, configuración solicitada y efectiva, provenance, estado,
errores y balance hídrico. El visor WebGL reproduce resultados persistidos y sus
geometrías de campo, cuenca y planta son **procedurales e ilustrativas**.

No están implementados ni demostrados:

- FSPM completo o CMIP6/NEX-GDDP-CMIP6 real;
- USDA NASS, CHIRPS, SoilGrids o Landsat; y un dominio watershed/gauge elegible
  y congelado para USGS;
- población de campo, Planta → Campo o Campo → HRU;
- calibración, validación formal, Sobol, KS, Wilcoxon, bootstrap o la hipótesis H0/H1.

El catálogo Palto/Santa Eulalia/Rímac, si se habilita, es un **LEGACY DEMO** para
desarrollo local. No representa el dominio científico objetivo ni una cuenca
verificada.

Fase C contiene una primera ingesta USGS de referencia y una matriz preliminar
de candidatos, ambas con provenance. Ninguna candidata ha satisfecho todavía
todos los criterios de agricultura, geometría y regulación; por ello no existe
un dominio científico seleccionado ni un baseline SWAT+.

## Arquitectura objetivo (futura)

```text
Plant/FSPM
  ↓
Field population
  ↓
HRU mapping
  ↓
SWAT+
  ↓
CMIP6 and observed-data validation
```

Las etapas futuras se implementarán sólo después de registrar fuentes, versiones,
licencias, checksums, control de calidad y un protocolo verificable de
watershed/gauge.

## Instalación

Requisitos: Python 3.12+ y Node.js con pnpm (el lockfile del frontend es
`pnpm-lock.yaml`).

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

`requirements.txt` contiene las dependencias de ejecución; `requirements-dev.txt`
añade Pytest, HTTPX y soporte async de pruebas. Para uso productivo, configure
una `SECRET_KEY` aleatoria y `ENABLE_DEMO_SEED=false`. El proceso rechaza la clave
placeholder fuera de `APP_ENV=development|test`.

Para desarrollo local con las cuentas y fixtures legacy demo, configure de forma
explícita:

```dotenv
APP_ENV=development
ENABLE_DEMO_SEED=true
SECRET_KEY=una-clave-local-no-compartida
```

Los permisos y roles RBAC se inicializan siempre, incluso con
`ENABLE_DEMO_SEED=false`. Usuarios, Palto/Santa Eulalia, escenarios sintéticos y
simulaciones legacy sólo se crean cuando ese flag está habilitado.

### Baseline SWAT+ real

El proyecto y ejecutable no se distribuyen con este repositorio. Configure rutas
locales en `.env`:

```dotenv
SWAT_PLUS_EXECUTABLE=/ruta/a/swatplus
SWAT_PLUS_PROJECT_DIR=/ruta/al/proyecto-swat-plus
SWAT_PLUS_WORKING_DIRECTORY=../data/swat-runs
SWAT_PLUS_TIMEOUT_SECONDS=3600
```

El proyecto debe incluir `file.cio` en su raíz o en `TxtInOut/`. Cree una
simulación con `mode` y `hydrology_backend` iguales a `SWAT_PLUS`. El objeto
opcional `swat_plus` permite indicar las rutas por corrida, `warmup_period`,
`output_frequency` (`DAILY`, `MONTHLY`, `ANNUAL`) y `timeout_seconds`; esta fase
solo acepta `SWAT_STANDARD_BASELINE`. Si los archivos de canal o balance incluyen
más de una unidad, indique `swat_plus.outlet_unit` para no seleccionar un outlet
arbitrariamente.

La API copia el proyecto a `SWAT_PLUS_WORKING_DIRECTORY/<run_id>`, ejecuta allí
el binario y deja los resultados normalizados en
`GET /api/v1/simulations/{id}/swat-results`, con provenance `REAL_SWAT_PLUS`.
Si falta un recurso, un output o falla el proceso, la corrida queda en `FAILED`
con un código explícito; nunca se sustituye con hidrología proxy.

### Primer administrador

En una instalación nueva, cree el primer administrador con credenciales elegidas
por el operador; el comando solicita la contraseña de forma segura y no habilita
fixtures demo:

```bash
cd backend
python -m app.cli create-admin --email admin@example.org --full-name "Administración inicial"
```

Inicie la API:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

## Base de datos y migraciones

Una DB nueva se crea al iniciar la API. Para una DB existente, la API aplica las
migraciones SQL versionadas de `backend/migrations/` de manera no destructiva y
registra cada archivo en `schema_migrations`. Respaldar la base antes de una
actualización sigue siendo una práctica obligatoria.

El runner y las migraciones versionadas usan SQL común a SQLite y PostgreSQL
(`sqlite+aiosqlite` y `postgresql+asyncpg`). Para verificar PostgreSQL se requiere
una instancia disponible y se puede iniciar la API con, por ejemplo:

```bash
DATABASE_URL='postgresql+asyncpg://usuario:clave@host:5432/ap3' APP_ENV=production ENABLE_DEMO_SEED=false uvicorn app.main:app
```

Esta iteración no levantó una instancia PostgreSQL; la portabilidad se verificó
por SQL común y las pruebas SQLite.

La migración `001_run_manifest_and_provenance.sql` incorpora el manifiesto de
corrida y diagnóstico de balance. No borra filas existentes: las corridas sin
manifiesto quedan etiquetadas como `legacy` y no reproducibles retrospectivamente.

## Verificación

```bash
cd backend
pytest -q tests

cd ../frontend
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

La suite automatizada del backend está en `backend/tests`; cubre core puro,
determinismo, parámetros, balance, API, autenticación, WebSocket, reportes,
migraciones y aislamiento de SQLite. No se fijan conteos de tests en este README.

## Documentación

- [Modelos actualmente implementados](docs/methodology/current-models.md)
- [Protocolo de selección de cuencas](docs/methodology/watershed-selection-protocol.md)
- [USGS streamflow y lineage](docs/methodology/usgs-streamflow.md)
- [Registro de artefactos de datos del MVP](docs/MVP_DATA_ARTIFACTS.md)
- [ADR: core científico puro](docs/adr/001-pure-scientific-core.md)
- [Documentación histórica](docs/README.md): los documentos legados están marcados y no describen el contrato científico vigente.
## ¿Qué funciona hoy?

| Componente | Estado | Implementación |
|---|---|---|
| PostgreSQL | REAL | Runtime local canónico; SQLite sólo para tests rápidos |
| FastAPI + Next.js | ACTIVE | API async y dashboard ejecutable |
| USGS observations | OBSERVED | Snapshot 05451210 con RAW, SHA-256, QC y normalización m³/s |
| Plant population | SIMPLIFIED | 1000 plantas de maíz deterministas con variabilidad acotada |
| Plant → Field | DERIVED | Media, desviación, percentiles y `n_plants` |
| Field → HRU | COARSE_HRU_PROXY | Tres unidades ponderadas por área; no son HRU SWAT+ |
| Hydrology | SIMPLIFIED | SCS-CN/two-store con balance hídrico |
| Baseline vs Twin | DEMONSTRATION_COMPARISON | Forcing idéntico y resultados mensuales separados |
| Validation | REAL COMPUTATION | RMSE, NSE, PBIAS y R² con estados indefinidos explícitos |
| External ML | ML_MODEL | ModelBundle por path; bundle RF vecino detectado, target `monthly_runoff_mm` |
| SWAT+ | CONDITIONAL_REAL | Baseline real con binario y proyecto válidos; sin ellos devuelve error tipado, nunca un proxy |
| CMIP6 | READY_FOR_ARTIFACT | Provider CSV normalizado; demo usa clima sintético |

## Ejecutar el MVP mañana (local)

```bash
cd backend
bash scripts/start_local_postgres.sh
python -m app.cli bootstrap-mvp
uvicorn app.main:app --reload --port 8000
```

En otra terminal:

```bash
cd frontend
pnpm dev
```

Abrir `http://localhost:3000`, iniciar sesión con
`investigador@digitaltwin.org` / `Investiga123!`, entrar a **MVP multiescala**,
crear la corrida y pulsar **Ejecutar gemelo digital**. El bootstrap aplica tablas,
migraciones, RBAC, dominio de referencia, snapshot USGS y registra el ModelBundle
vecino cuando `../agro-digital-twin-st/artifacts` está disponible.

`docker compose up --build` queda como alternativa de despliegue; no es necesario
para el flujo local.

Para instalar otro bundle, copiarlo a `models/external/<bundle_name>/` y llamar
`POST /api/v1/models/register` con su path dentro del runtime. El binario no se
almacena en PostgreSQL.

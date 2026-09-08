# From Plant to Watershed

Base de software científico reproducible para el proyecto de investigación
**“From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling
Individual Plant Models with SWAT Hydrology and Downscaled Climate
Projections”**.

## Estado actual: demostración reproducible

La implementación actual ejecuta un pipeline diario persistente compuesto por:

- `SyntheticClimateProvider`: forzamiento meteorológico estacional y pseudoaleatorio con seed; **no** contiene observaciones ni NEX-GDDP-CMIP6.
- `SimplifiedPlantModel`: planta representativa algebraica; **no** es un FSPM ni representa órganos, fenología o población.
- `SimplifiedHydrologyModel`: balance conceptual agregado SCS-CN con diagnóstico de residual; **no** ejecuta SWAT+.
- `UsgsStreamflowProvider`: infraestructura observacional separada que conserva RAW,
  checksum, QC y caudal diario normalizado; **no** calibra ni alimenta los modelos simplificados.

Cada corrida guarda seed, configuración solicitada y efectiva, provenance, estado,
errores y balance hídrico. El visor WebGL reproduce resultados persistidos y sus
geometrías de campo, cuenca y planta son **procedurales e ilustrativas**.

No están implementados ni demostrados:

- SWAT+ real, FSPM completo o CMIP6/NEX-GDDP-CMIP6 real;
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
- [ADR: core científico puro](docs/adr/001-pure-scientific-core.md)
- [Documentación histórica](docs/README.md): los documentos legados están marcados y no describen el contrato científico vigente.

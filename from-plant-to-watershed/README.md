# From Plant to Watershed

Base de software científico reproducible para el proyecto de investigación
**“From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling
Individual Plant Models with SWAT Hydrology and Downscaled Climate
Projections”**.

## Estado final: piloto científico South Fork

La validación congelada corresponde exclusivamente a **South Fork Iowa River**
(`USGS 05451210`, `HUC8 07080207`). **Multi-watershed validation remains
future work; this implementation performs a reproducible pilot validation on
one real agricultural watershed.**

El experimento final ejecutado usa 2015--2020, con warm-up 2015--2017 y
evaluación USGS 2018--2020. `SWAT_STANDARD_BASELINE` y
`SWAT_MULTISCALE_COUPLED` comparten clima, HRUs, CDL, suelos, manejo general,
periodo y outlet; el acoplado cambia únicamente `corn.lai_pot`,
`corn.can_ht_max` y `corn.rt_dp_max` desde la agregación FSPM de 1,000 plantas.

- Resultado primario: `H1_NOT_SUPPORTED`; RMSE mensual = 9.4471 m3/s para
  ambos casos, mejora = 0.0%.
- `COUPLING_EFFECT = ZERO_WITH_CURRENT_PARAMETERIZATION`: la cadena CDL ->
  HRU -> comunidad -> manejo -> planta fue verificada y los inputs de
  `plants.plt` cambiaron, pero los outputs SWAT+ permanecieron idénticos.
- Artefactos reproducibles: `research_domain/final_report.json`,
  `data/final/experiment_dataset.parquet` y su schema/unidades.
- Escenarios SWAT+ ejecutados: `+2C`, `-15% precipitation`, `no-till` con
  operación `zerotill`, y `maize -> grain sorghum` (`grsg`).
- CMIP6/NASS: `NOT_AVAILABLE`/`LIMITED`; no se usó ningún sustituto sintético.

## Qué es REAL

- South Fork, USGS diario, CDL Iowa 2019 estático, suelos y clima GridMET del
  proyecto SWAT+, SWAT+ 61.0.2.61, población FSPM simplificada, baseline,
  coupled y los cuatro escenarios finalizados.

## Qué es aproximación o proxy

- FSPM simplificado y resumen de forcing por media de estaciones; estados FSPM
  son derivados, no observados. ET, uptake y yield FSPM son `NOT_COUPLED`.
- CDL es un snapshot 2019, no una rotación histórica. La calibración es
  `LIMITED_CALIBRATION`; NASS county/yield no tiene crosswalk a cuenca/HRU.
- No hay artefactos NASA NEX-GDDP-CMIP6 normalizados disponibles en esta
  ejecución. Sobol no se ejecutó completamente; bootstrap SSP5-8.5 no tiene
  serie de yield válida.

## Arquitectura y acoplamiento multiescala

El sistema opera bajo un pipeline multiescala validado en la cuenca agrícola de Iowa:

- **Escala de Planta (Nivel 1)**: Modelo biofísico de maíz (FSPM simplificado con 1,000 plantas parametrizadas, dinámica térmica de GDD, LAI fenológico, altura y profundidad radicular).
- **Escala de Parcela / Campo (Nivel 2)**: Agregación estadística de la comunidad vegetal (media, percentiles, $n=1000$ plantas), balance hídrico de suelo y cálculo de variables de dosel.
- **Escala de Cuenca / SWAT+ (Nivel 3)**: Mapeo de parámetros agregados de la comunidad vegetal (`lai_pot`, `can_ht_max`, `rt_dp_max`, `bm_e`, `ext_co`) hacia `plants.plt` en SWAT+, simulando las 36 subcuencas hidrológicas (HRU clusters) y 37 canales de enrutamiento fluvial hacia el punto de aforo `USGS 05451210` (New Providence, IA).
- **Escala de Clima (Nivel 4)**: Forzamiento meteorológico observado (series diarias de GridMET / USGS) y perturbaciones climáticas controladas (+2°C temperatura, -15% precipitación, labranza cero `zerotill`, rotación maíz a sorgo `grsg`).
- **Modo offline / CI**: Se conservan proveedores desacoplados (`SyntheticClimateProvider`, `SimplifiedPlantModel`, `SimplifiedHydrologyModel`) para pruebas automatizadas e integración continua sin requerir el ejecutable SWAT+.

Cada corrida persiste configuración solicitada y efectiva, hashes SHA-256 de inputs y outputs, balance hídrico, seed y metadatos de linaje.

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

## Documentación técnica y científica

- [Marco Metodológico Oficial (Ficha Técnica)](project_framework.md)
- [Reporte Final del Piloto South Fork](docs/FINAL_REPORT.md)
- [Acoplamiento FSPM → SWAT+ (Contratos v2.1.1)](docs/FSPM_SWAT_PLUS_COUPLING.md)
- [Integración Real SWAT+](docs/SWAT_PLUS_REAL_INTEGRATION.md)
- [Protocolo de Selección de Cuencas en el Corn Belt](docs/methodology/watershed-selection-protocol.md)
- [USGS streamflow y control de calidad](docs/methodology/usgs-streamflow.md)
- [Registro de datos observacionales](docs/methodology/observational-data.md)
- [ADR 001: Core científico puro](docs/adr/001-pure-scientific-core.md)
- [Índice de documentación](docs/README.md)

## ¿Qué funciona hoy?

| Componente | Estado | Implementación |
|---|---|---|
| PostgreSQL | REAL | Runtime local canónico; SQLite sólo para tests rápidos |
| FastAPI + Next.js | ACTIVE | API async y dashboard interactivo |
| SWAT+ | REAL | Motor SWAT+ 61.0.2.61 en South Fork Iowa River con 36 subcuencas y 37 canales |
| USGS observations | OBSERVED | Estación 05451210 (New Providence, IA) con RAW, SHA-256, QC y normalización m³/s |
| Plant population | SIMPLIFIED_FSPM | 1,000 plantas de maíz deterministas con variabilidad acotada |
| Plant → Field | DERIVED | Agregación de comunidad (media, desviación, percentiles, $n=1000$) |
| FSPM → SWAT+ Coupling | REAL_COUPLING | Mapeo térmico/fenológico de dosel a `plants.plt` |
| Gemelo Digital 3D | REAL_GIS_R3F | Visor 3D multiescala con límites GIS de South Fork ($560\text{ km}^2$), 36 subcuencas, red fluvial y aforo |
| Validation | REAL COMPUTATION | RMSE, NSE, PBIAS, R², KS y Wilcoxon con estados explícitos |
| External ML | ML_MODEL | Integración de ModelBundle (`monthly_runoff_mm`) desacoplado de Streamlit |

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

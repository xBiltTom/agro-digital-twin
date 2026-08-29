# AP-3: From Plant to Watershed — Multi-Scale Digital Twin Framework

> **Plataforma de Gemelo Digital 3D Multiescala que acopla modelos fisiológicos individuales de planta con la hidrología de cuencas SWAT y proyecciones climáticas downscaled (CMIP6).**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![Three.js](https://img.shields.io/badge/3D%20Engine-Three.js%20%2F%20R3F-black?style=flat&logo=three.js&logoColor=white)](https://threejs.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20SQLite-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Tests](https://img.shields.io/badge/Tests-14%2F14%20Passed-success?style=flat&logo=pytest&logoColor=white)](#-pruebas-automatizadas)

---

## 📌 Descripción del Proyecto

El proyecto **AP-3 (From Plant to Watershed)** implementa un framework integral de **Gemelo Digital 3D en tiempo real** diseñado para la investigación ecohidrológica avanzada, la gestión sostenible de recursos hídricos en cuencas hidrográficas y la evaluación del impacto del cambio climático en la agricultura.

A diferencia de los modelos agronómicos o hidrológicos aislados, esta plataforma establece un **acoplamiento biofísico bidireccional multiescala**:
1. **Escala Micro (Planta Individual)**: Modela la demanda evaporativa, la resistencia estomática, la absorción radicular mediante la función de reducción de **Feddes**, el índice de estrés hídrico de cultivo (**CWSI**) y la velocidad de flujo de savia xilemática ($cm/h$).
2. **Escala Meso (Parcela Agrícola / HRU - Hydrological Response Unit)**: Simula el balance hídrico en un perfil de suelo estratificado (horizontes $0-30\text{ cm}$, $30-60\text{ cm}$ y $60-100\text{ cm}$) con sensores IoT de humedad volumétrica ($\theta$) y eficiencia de riego por goteo.
3. **Escala Macro (Cuenca Hidrográfica SWAT)**: Modela la cuenca mediante las ecuaciones de balance de masa de **SWAT (Soil & Water Assessment Tool)**, calculando la escorrentía superficial con el método de la **Curva Número SCS**, la percolación profunda, la recarga de acuífero y el tránsito fluvial del caudal hacia el exutorio ($m^3/s$).
4. **Forzamiento Climático Downscaled (CMIP6)**: Permite forzar el sistema con proyecciones climáticas normalizadas bajo escenarios **SSP1-2.6**, **SSP2-4.5** y **SSP5-8.5**, evaluando la resiliencia hídrica ante sequías u olas de calor extremas.

---

## ✨ Funcionalidades Principales

### 1. 🌐 Gemelo Digital 3D Multiescala (Three.js / React Three Fiber / WebGL)
- **Vista Macro (Cuenca SWAT 3D)**:
  - Malla topográfica 3D (DEM) generada proceduralmente con relieve montañoso andino (cotas de $850\text{ m}$ a $4350\text{ m}$).
  - Cauce fluvial 3D reactivo cuyo diámetro y luminosidad responden al caudal instantáneo $Q$ ($m^3/s$).
  - Sistema de partículas dinámico para precipitación y mapa de calor de terreno sensible a la humedad del suelo.
- **Vista Meso (Parcela Agrícola HRU 3D)**:
  - Cuadrícula de cultivo con surcos de riego por goteo y cuadrícula de árboles frutales (Palto Hass).
  - Perfil subterráneo estratificado mostrando los 3 horizontes edáficos.
  - Sonda IoT con antena y baliza LED pulsante de telemetría.
- **Vista Micro (Planta Individual 3D)**:
  - Estructura botánica completa: tronco, xilema central y racimos de follaje foliar.
  - **Coloración dinámica de follaje**: modulada en vivo por el índice **CWSI** (verde esmeralda saludable $\to$ lima $\to$ amarillo marchito bajo sequía).
  - **Partículas de flujo de savia**: partículas ascendentes dentro del tronco que viajan a la velocidad física calculada ($cm/h$).
  - Sistema radicular ramificado subterráneo con halo de absorción radicular de Feddes.
- **Transiciones Cinemáticas y Choques Climáticos en Vivo**:
  - Interpolación vectorial suave entre escalas de cámara (Macro $42\text{ m}$, Meso $18\text{ m}$, Micro $5.5\text{ m}$).
  - Botones de choque interactivo: *"Lluvia +40mm"*, *"Calor +4°C"* y *"Restablecer"*.

### 2. ⚡ Estudio de Modelado SWAT & Proyecciones Climáticas
- **Simulador Interactivo**: Creación de experimentos configurando cuenca, escenario CMIP6, horizonte temporal (30, 90, 180, 365 días) y eficiencia de riego.
- **Gráficos Analíticos con Recharts**:
  - *Hidrograma SWAT*: Precipitaciones diarias ($mm$) vs Caudal del Río ($m^3/s$).
  - *Fisiología Vegetal*: Transpiración real vs Demanda evaporativa ($ET_0$) y velocidad de savia.
  - *Humedad de Suelo*: Dinámica de humedad volumétrica $\theta$ (%) y curva de estrés CWSI.
- **Transmisión WebSocket en Tiempo Real**: Endpoint nativo en `/api/v1/twin/ws/{simulation_id}` con control de velocidad ($1x - 20x$) y comandos `play`, `pause`, `step`.

### 3. 📑 Generador de Reportes Multiformato
- **Reporte PDF Formal Institucional (ReportLab)**: Documento de ingeniería con membrete, metadatos del escenario CMIP6, matriz de KPIs, serie diaria de muestra y conclusiones técnicas para tomadores de decisiones.
- **Documento Técnico Word (.docx) (`python-docx`)**: Informe técnico editable con estilos jerárquicos, tablas estilizadas con sombreado de celdas y narrativa de impacto climático.
- **Libro Analítico Excel (.xlsx) (`openpyxl`)**: Libro con 3 pestañas estructuradas (`Resumen Ejecutivo`, `Series Diarias SWAT`, `Fisiología Vegetal Micro`), formatos numéricos de precisión (`0.00`) y anchos de columna autoajustados.
- **Centro de Descargas y Auditoría**: Registro de descargas previas con timestamp y tamaño de archivo.

### 4. 🔐 Seguridad, Roles y Perfiles (RBAC)
- **Autenticación Segura**: Tokens JWT Bearer con expiración y hashing de contraseñas con `bcrypt`.
- **5 Roles Preconfigurados**:
  - `SUPERADMIN`: Control total del sistema, gestión de usuarios, roles y auditoría.
  - `ADMIN_CIENTIFICO`: Calibración de cuencas, escenarios climáticos y especies.
  - `INVESTIGADOR_HIDROLOGO`: Ejecución de simulaciones, análisis 3D y descarga de reportes.
  - `OPERADOR_AGROPECUARIO`: Monitoreo en tiempo real del gemelo digital de parcela y planta.
  - `LECTOR_AUDITOR`: Lectura de dashboard e informes.
- **13 Permisos Granulares de Dominio**: Control de acceso a simulaciones, visor 3D, exportaciones y gestión de usuarios.
- **Gestión de Perfil Científico**: Actualización de institución, laboratorio, especialidad científica, biografía y cambio de contraseña.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnologías |
| :--- | :--- |
| **Backend** | Python 3.12+, FastAPI, Uvicorn, SQLAlchemy 2.0 (Async), Pydantic v2, WebSockets |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide Icons |
| **Motor 3D** | Three.js, `@react-three/fiber` (v9), `@react-three/drei` (v10), WebGL |
| **Visualización de Datos** | Recharts (Hidrogramas, curvas de transpiración y perfiles de humedad) |
| **Reportes** | ReportLab (PDF), `python-docx` (Word), `openpyxl` (Excel) |
| **Bases de Datos** | PostgreSQL 16+ con `asyncpg` (Producción) / SQLite con `aiosqlite` (Desarrollo local inmediato) |
| **Pruebas** | Pytest, `pytest-asyncio`, HTTPX |

---

## 📂 Estructura del Repositorio

```bash
from-plant-to-watershed/
├── README.md                         # Documentación principal del software
├── backend/
│   ├── app/
│   │   ├── api/                      # Endpoints organizados por versión
│   │   │   ├── deps.py               # Dependencias de autenticación y RBAC
│   │   │   └── v1/
│   │   │       ├── auth.py           # Autenticación JWT (login, register, me, refresh)
│   │   │       ├── users.py          # CRUD de usuarios y asignación de roles
│   │   │       ├── roles.py          # Catálogo de roles y permisos
│   │   │       ├── profile.py        # Perfil del usuario y cambio de contraseña
│   │   │       ├── simulations.py    # Motor y API de simulaciones SWAT
│   │   │       ├── twin_ws.py        # WebSocket en tiempo real para el Gemelo 3D
│   │   │       ├── reports.py        # Streaming de descarga de reportes PDF/Word/Excel
│   │   │       └── router.py         # Enrutador central API v1
│   │   ├── core/
│   │   │   ├── config.py             # Configuración Pydantic Settings
│   │   │   ├── database.py           # Conexión asíncrona a BD con fallback resiliente
│   │   │   └── security.py           # Criptografía bcrypt y tokens JWT
│   │   ├── models/                   # Modelos ORM SQLAlchemy
│   │   │   ├── user.py               # User, Role, Permission, UserProfile
│   │   │   ├── watershed.py          # Watershed, Subbasin, HRU, PlantSpecies
│   │   │   ├── simulation.py         # ClimateScenario, SimulationRun, SimulationResult
│   │   │   └── report.py             # GeneratedReport (auditoría)
│   │   ├── schemas/                  # Esquemas de validación Pydantic v2
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   └── simulation.py
│   │   ├── services/                 # Lógica científica y generadores
│   │   │   ├── plant_model.py        # Fisiología de planta (Penman-Monteith, Feddes RWU, CWSI)
│   │   │   ├── swat_hydrology.py     # Balance SWAT (Curva Número SCS, escorrentía, río)
│   │   │   ├── climate_engine.py     # Forzamiento CMIP6 downscaled (SSP1/2/5)
│   │   │   ├── twin_coupling_engine.py # Orquestador de acoplamiento multiescala
│   │   │   ├── report_service.py     # Generador de PDF (ReportLab), Word y Excel
│   │   │   └── seed_service.py       # Seeder automático inicial de roles, usuarios y cuenca
│   │   └── main.py                   # Inicializador FastAPI con lifespan y CORS
│   ├── tests/                        # Suite de pruebas automatizadas (pytest)
│   │   ├── conftest.py
│   │   ├── test_auth_rbac.py         # Tests de seguridad y RBAC
│   │   ├── test_twin_simulation.py   # Tests biofísicos y de acoplamiento
│   │   └── test_reports.py           # Tests de generación de PDF, Word y Excel
│   ├── requirements.txt              # Dependencias Python
│   └── .env.example                  # Plantilla de variables de entorno
│
└── frontend/
    ├── src/
    │   ├── app/                      # Rutas Next.js App Router
    │   │   ├── (auth)/
    │   │   │   ├── login/page.tsx    # Login con botones de acceso 1-clic por rol
    │   │   │   └── register/page.tsx # Registro de investigadores
    │   │   ├── (dashboard)/
    │   │   │   ├── layout.tsx        # Shell protegido con Sidebar y Navbar
    │   │   │   ├── page.tsx          # Dashboard principal y KPIs
    │   │   │   ├── twin-3d/page.tsx  # Visor 3D Multiescala interactivo
    │   │   │   ├── simulations/page.tsx # Estudio de simulación y gráficos Recharts
    │   │   │   ├── reports/page.tsx  # Centro de reportes (PDF, Word, Excel)
    │   │   │   ├── users/page.tsx    # Administración de usuarios y roles
    │   │   │   └── profile/page.tsx  # Perfil de usuario y credenciales
    │   │   ├── globals.css
    │   │   └── layout.tsx            # Root layout con AuthProvider
    │   ├── components/
    │   │   ├── 3d/                   # Componentes Three.js / React Three Fiber
    │   │   │   ├── MultiScaleViewer3D.tsx # Canvas 3D con transiciones de cámara
    │   │   │   ├── WatershedMesh3D.tsx    # Malla topográfica DEM, río y lluvia
    │   │   │   ├── FieldPlotMesh3D.tsx    # Parcela, horizontes de suelo y sensores
    │   │   │   ├── PlantModel3D.tsx       # Planta 3D, partículas de savia y raíces
    │   │   │   └── TwinHUDOverlay.tsx     # HUD interactivo con choque climático
    │   │   └── layout/
    │   │       ├── Navbar.tsx        # Barra superior con estado en vivo
    │   │       └── Sidebar.tsx       # Navegación lateral con filtrado RBAC
    │   ├── context/
    │   │   └── AuthContext.tsx       # Estado global de autenticación
    │   ├── lib/
    │   │   └── api.ts                # Cliente HTTP tipado con manejo de tokens y descargas
    │   └── types/                    # Tipos e interfaces TypeScript
    │       ├── auth.ts
    │       └── simulation.ts
    ├── package.json
    └── tailwind.config.ts
```

---

## 🚀 Guía de Instalación y Puesta en Marcha

### Prerrequisitos
- **Node.js**: v20 o superior
- **pnpm**: v9 o superior (`npm install -g pnpm`)
- **Python**: v3.12 o superior

---

### 1. Puesta en Marcha del Backend (FastAPI)

1. Ingresa a la carpeta del backend y activa el entorno virtual:
   ```bash
   cd backend
   source venv/bin/activate
   ```
2. Instala dependencias si fuera necesario:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicia el servidor de desarrollo:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - **Servidor activo en**: `http://localhost:8000`
   - **Documentación Swagger UI**: `http://localhost:8000/api/v1/docs`

> **Nota sobre Base de Datos**: Por defecto, el sistema viene preconfigurado con **SQLite local** (`digitaltwin.db`) que se inicializa y puebla automáticamente al arrancar. Si deseas usar **PostgreSQL**, simplemente ejecuta en tu terminal:
> ```bash
> sudo -u postgres psql -c "CREATE USER digitaltwin WITH PASSWORD 'digitaltwin123'; CREATE DATABASE digitaltwin_db OWNER digitaltwin;"
> ```
> Y configura `DATABASE_URL=postgresql+asyncpg://digitaltwin:digitaltwin123@localhost:5432/digitaltwin_db` en tu archivo `backend/.env`.

---

### 2. Puesta en Marcha del Frontend (Next.js)

1. En una nueva terminal, ingresa a la carpeta del frontend:
   ```bash
   cd frontend
   ```
2. Instala dependencias si fuera necesario:
   ```bash
   pnpm install
   ```
3. Inicia el servidor Next.js:
   ```bash
   pnpm dev
   ```
4. Abre tu navegador web en:
   ```
   http://localhost:3000
   ```

---

## 👥 Cuentas y Credenciales de Prueba (Demo)

El sistema incluye un **seeder automático** con 3 cuentas preconfiguradas con diferentes privilegios RBAC:

| Rol | Correo Electrónico | Contraseña | Alcance de Funcionalidad |
| :--- | :--- | :--- | :--- |
| **SUPERADMIN** | `admin@digitaltwin.org` | `Admin123!` | Control total, gestión de usuarios, edición de roles y auditoría. |
| **INVESTIGADOR_HIDROLOGO** | `investigador@digitaltwin.org` | `Investiga123!` | Ejecución de simulaciones SWAT, análisis 3D y descarga de reportes. |
| **OPERADOR_AGROPECUARIO** | `operador@digitaltwin.org` | `Operador123!` | Monitoreo en tiempo real de telemetría de planta y parcela. |

> 💡 **Tip de Usabilidad**: En la pantalla de Login (`/login`) encontrarás botones de **Acceso Rápido (1-Clic)** que rellenan automáticamente los campos para probar cada rol al instante.

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una cobertura completa de pruebas automatizadas en el backend que validan la autenticación, las restricciones de roles, la conservación de masa SWAT, el modelo radicular de Feddes y la exportación de los 3 formatos de reportes:

```bash
cd backend
source venv/bin/activate
PYTHONPATH=. pytest -v backend/tests/
```

Resultado de las 14 pruebas:
```bash
backend/tests/test_auth_rbac.py::test_health_check PASSED                [  7%]
backend/tests/test_auth_rbac.py::test_login_superadmin_success PASSED    [ 14%]
backend/tests/test_auth_rbac.py::test_login_invalid_credentials PASSED   [ 21%]
backend/tests/test_auth_rbac.py::test_get_current_user_me PASSED         [ 28%]
backend/tests/test_auth_rbac.py::test_rbac_access_restrictions PASSED    [ 35%]
backend/tests/test_auth_rbac.py::test_register_new_user_and_profile_update PASSED [ 42%]
backend/tests/test_reports.py::test_generate_pdf_structure PASSED        [ 50%]
backend/tests/test_reports.py::test_generate_docx_structure PASSED       [ 57%]
backend/tests/test_reports.py::test_generate_xlsx_structure PASSED       [ 64%]
backend/tests/test_reports.py::test_api_download_reports PASSED          [ 71%]
backend/tests/test_twin_simulation.py::test_climate_engine_downscaling PASSED [ 78%]
backend/tests/test_twin_simulation.py::test_plant_model_feddes_reduction PASSED [ 85%]
backend/tests/test_twin_simulation.py::test_swat_hydrology_water_balance PASSED [ 92%]
backend/tests/test_twin_simulation.py::test_api_simulation_workflow PASSED [100%]

============================== 14 passed in 7.35s ==============================
```

Para verificar la compilación y tipado del frontend:
```bash
cd frontend
pnpm build
```

---

## 📜 Licencia y Propósito Académico

Desarrollado como solución para la asignatura de **Ingeniería de Software II (Ciclo VIII)** en el marco del tema de investigación:
> *AP-3 From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models with SWAT Hydrology and Downscaled Climate Projections.*

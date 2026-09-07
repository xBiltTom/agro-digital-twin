# 01. Arquitectura y Funcionamiento General del Sistema

Este documento describe la estructura técnica y el flujo de datos que permiten al software funcionar como un **Gemelo Digital 3D en tiempo real**.

---

## 🏛️ 1. Diagrama de Arquitectura Global

El sistema está construido siguiendo una arquitectura limpia y desacoplada en tres capas:

```
                  ┌─────────────────────────────────────────┐
                  │          NAVEGADOR WEB (CLIENTE)        │
                  │                                         │
                  │   Next.js 16 (React 19, TypeScript)     │
                  │   ├── Dashboard & Analíticas (Recharts) │
                  │   ├── Gemelo 3D (Three.js / R3F v9)     │
                  │   ├── Centro de Reportes (PDF/DOCX/XLSX)│
                  │   └── Gestión RBAC & Auth Context       │
                  └───────────────▲─────────────────▲───────┘
                                  │ HTTP/REST       │ WebSockets (ws://)
                                  │ (Port 8000)     │ (Port 8000)
                  ┌───────────────▼─────────────────▼───────┐
                  │             BACKEND FASTAPI             │
                  │                                         │
                  │   ├── API Routers (Auth, Sim, Reports)  │
                  │   ├── Security & RBAC Middleware        │
                  │   ├── Motores Científicos:              │
                  │   │   ├── Climate Engine (CMIP6)        │
                  │   │   ├── SWAT Hydrology Engine         │
                  │   │   ├── Plant Physiology Model        │
                  │   │   └── Twin Coupling Orchestrator    │
                  │   └── Generador de Reportes             │
                  │       (ReportLab, docx, openpyxl)       │
                  └───────────────────▲─────────────────────┘
                                      │ SQLAlchemy 2.0 Async
                                      ▼
                  ┌─────────────────────────────────────────┐
                  │              BASE DE DATOS              │
                  │   PostgreSQL 16 / SQLite (aiosqlite)    │
                  │   (Usuarios, Cuencas, Escenarios, Runs) │
                  └─────────────────────────────────────────┘
```

---

## 🔄 2. El Paradigma de Acoplamiento Multiescala (AP-3)

Los enfoques tradicionales de simulación suelen fallar por dos extremos:
1. **Modelos Agronómicos aislados**: Simulan la planta en una "maceta virtual" sin saber si la cuenca tiene agua o si el río se secó.
2. **Modelos Hidrológicos macro aislados**: Simulan el río y la lluvia en cientos de $km^2$, pero asumen la vegetación como una constante estática sin respuesta fisiológica dinámica.

**La solución AP-3**: Conecta ambas realidades en un bucle cerrado diario:

```
[PASO 1] FORZAMIENTO CLIMÁTICO (CMIP6)
   │ Temperatura diaria, Radiación Solar, Lluvia, CO₂
   ▼
[PASO 2] DEMANDA ATMOSFÉRICA (Penman-Monteith / Turc)
   │ Calcula la Evapotranspiración Potencial (ET₀)
   │ Demanda de la planta: Tpot = Kc × ET₀
   ▼
[PASO 3] HIDROLOGÍA DE CUENCA (SWAT)
   │ Lluvia se divide en:
   │ ├── Escorrentía Superficial Qsurf (Curva Número SCS)
   │ └── Infiltración al perfil de suelo (0-100 cm)
   ▼
[PASO 4] DISPONIBILIDAD DE AGUA EN SUELO (HRU Meso)
   │ Humedad volumétrica θ en horizontes A, B y C
   │ + Riego tecnificado suministrado
   ▼
[PASO 5] ABSORCIÓN RADICULAR Y FISIOLOGÍA (Micro)
   │ Función de Feddes calcula el factor de reducción α(θ)
   │ Transpiración real: Tact = α × Tpot
   │ Velocidad de savia en xilema = f(Tact)
   │ Estrés hídrico CWSI = 1 - (Tact / Tpot)
   ▼
[PASO 6] DESCARGA FLUVIAL Y RECARGA (Macro)
   │ Percolación profunda -> Recarga acuífero -> Caudal base
   │ Tránsito fluvial -> Caudal en el exutorio Q (m³/s)
   ▼
[PASO 7] RETROALIMENTACIÓN AL GEMELO DIGITAL 3D
   │ Actualización instantánea del terreno, río, marcha de árboles y savia
```

---

## 💻 3. Detalle de los Módulos del Software

### Módulo A: Núcleo de Seguridad y RBAC (Role-Based Access Control)
- **Hashing**: Las contraseñas se almacenan con `bcrypt` (sal aleatoria y coste adaptativo).
- **Tokens JWT**: Generación de tokens criptográficos firmados con algoritmo `HS256` y expiración automática.
- **Jerarquía de 5 Roles**:
  - `SUPERADMIN`: Control absoluto, administración de cuentas y asignación de roles.
  - `ADMIN_CIENTIFICO`: Parámetros de cuencas, calibración de constantes biofísicas de cultivos.
  - `INVESTIGADOR_HIDROLOGO`: Configuración y corrida de experimentos de simulación.
  - `OPERADOR_AGROPECUARIO`: Monitoreo de telemetría de parcelas y sensores IoT.
  - `LECTOR_AUDITOR`: Visualización de dashboard y auditoría de reportes.

### Módulo B: Motores Biofísicos e Hidrológicos
- **`climate_engine.py`**: Generador estocástico con calibración climática andina y perturbación según los 4 escenarios IPCC CMIP6 (**Historical, SSP1-2.6, SSP2-4.5, SSP5-8.5**).
- **`swat_hydrology.py`**: Implementa el balance hídrico del modelo SWAT (Soil & Water Assessment Tool), calculando escorrentía superficial SCS con corrección antecedente de humedad, infiltración, almacenamiento en 3 horizontes edáficos y tránsito fluvial.
- **`plant_model.py`**: Modela la planta individual con Penman-Monteith / Turc, función de reducción de Feddes ($\alpha$), conductancia estomática, potencial hídrico foliar ($\Psi_{leaf}$) y velocidad del flujo de savia.
- **`twin_coupling_engine.py`**: Orquestador que ejecuta la integración paso a paso de los motores anteriores, garantizando la **conservación estricta de masa de agua**.

### Módulo C: Gemelo Digital 3D Multiescala (WebGL / Three.js / R3F)
- Renderizado interactivo a 60 FPS con WebGL.
- **Escala Macro**: Malla DEM procedural, hipsometría por vertex colors, río animado físico, partículas de lluvia y nubes.
- **Escala Meso**: Parcela agrícola con surcos, mangueras de goteo activas, estratificación de suelo subterráneo, estación IoT y marchitez dinámica de árboles.
- **Escala Micro**: Planta 3D con xilema visible, partículas de savia ascendente a velocidad real, vapor de transpiración foliar y partículas de absorción de Feddes en raíces.
- **Canal WebSocket**: Streaming continuo `/api/v1/twin/ws/{id}` que transmite los estados diarios al navegador.

### Módulo D: Motor de Reportes Multiformato
- **PDF**: Generado con `ReportLab` en memoria (tablas de balance SWAT, metadatos CMIP6 y conclusiones).
- **Word (`.docx`)**: Generado con `python-docx` con estilos de ingeniería, títulos jerárquicos y tablas con sombreado formal.
- **Excel (`.xlsx`)**: Generado con `openpyxl` con 3 pestañas estructuradas (`Resumen Ejecutivo`, `Series Diarias SWAT`, `Fisiología Planta`).

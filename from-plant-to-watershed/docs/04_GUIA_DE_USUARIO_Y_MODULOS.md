# 04. Guía de Usuario y Módulos (documento legado)

> **Advertencia:** varias etiquetas y controles descritos aquí pertenecen a la
> UI anterior. La aplicación vigente declara clima sintético,
> hidrología/planta simplificadas y vistas 3D ilustrativas; el control de
> eficiencia de riego está deshabilitado.

Esta guía explica paso a paso cómo utilizar cada sección de la plataforma, cómo interactuar con el gemelo 3D, interpretar los gráficos y exportar reportes.

---

## 🔑 1. Acceso y Cuentas Preconfiguradas

En la pantalla de Login (`http://localhost:3000/login`) dispones de botones de **Acceso Rápido (1-Clic)**:

| Perfil Demo | Rol | Credenciales | Capacidades del Usuario |
| :--- | :--- | :--- | :--- |
| **Dr. Alejandro Valdivia** | `SUPERADMIN` | `admin@digitaltwin.org`<br>`Admin123!` | Administración total de usuarios, roles, parámetros y auditoría. |
| **Dra. Elena Ramos** | `INVESTIGADOR_HIDROLOGO` | `investigador@digitaltwin.org`<br>`Investiga123!` | Creación de simulaciones climáticas, visor 3D y descarga de reportes. |
| **Ing. Carlos Morales** | `OPERADOR_AGROPECUARIO` | `operador@digitaltwin.org`<br>`Operador123!` | Monitoreo de telemetría de parcelas agrícolas y sensores IoT. |

---

## 🌐 2. Visor 3D del Gemelo Digital (`/twin-3d`)

El visor 3D es el centro de visualización biofísica interactiva en tiempo real.

```
┌─────────────────────────────────────────────────────────────┐
│ [Macro: Cuenca SWAT]  [Meso: Parcela HRU]  [Micro: Planta 3D] │ <-- Conmutador de Escala
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                                                             │
│                    CANVAS WEBGL 3D INTERACTIVO              │
│                                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [Telemetría: Q = 8.5 m³/s | θ = 28.0% | Tr = 3.2 mm/d]      │ <-- HUD Flotante
│ [ ▶ ]  [=================== Día 45 de 365 =================]│ <-- Reproductor Temporal
└─────────────────────────────────────────────────────────────┘
```

### A. Navegación de Cámara
- **Rotar / Orbitar**: Mantén presionado el **clic izquierdo** del ratón y arrastra.
- **Panear / Desplazar**: Mantén presionado el **clic derecho** (o Shift + clic izquierdo) y arrastra.
- **Zoom**: Gira la **rueda del ratón** (scroll) para acercarte o alejarte.

### B. Transiciones entre Escalas
Puedes saltar entre escalas de dos formas:
1. **Pestañas superiores**: Haz clic en `Macro: Cuenca SWAT`, `Meso: Parcela HRU` o `Micro: Planta 3D`.
2. **Etiquetas 3D interactivas**: En el visor 3D, haz clic directamente sobre la etiqueta flotante `📍 Parcela AP-3` o `🔬 Planta Individual AP-3` para que la cámara haga un zoom cinemático hacia ese elemento.

### C. Controles de Choque Climático en Vivo
En la esquina superior derecha encontrarás 3 botones interactivos:
- **🌧️ Lluvia +40mm**: Simula una tormenta repentina. Verás cómo cae lluvia torrencial, el río se hincha, la escorrentía desciende por las laderas y las gotas de riego se activan.
- **☀️ Calor +4°C**: Simula una ola de calor severa. Verás cómo el follaje de los árboles de la parcela y de la planta 3D se vuelve amarillo/marrón (marchitez física), y el flujo de savia en el xilema se acelera al máximo.
- **🔄 Restablecer**: Devuelve el entorno a las condiciones meteorológicas calculadas para el día actual.

---

## ⚡ 3. Estudio de Simulaciones SWAT (`/simulations`)

En esta sección puedes configurar nuevos experimentos y analizar las series temporales con gráficos interactivos.

### A. Crear un Nuevo Experimento de Simulación
1. Haz clic en el botón verde **"+ Nueva Simulación"**.
2. Completa el formulario:
   - **Nombre de la Simulación**: Ej. *"Evaluación de Resiliencia Santa Eulalia 2030"*.
   - **Cuenca Hidrográfica**: Selecciona la cuenca calibrada (Ej. *Cuenca Santa Eulalia - Rímac*).
   - **Escenario Climático CMIP6**:
     - *Historical Baseline*: Para evaluar condiciones históricas estándar.
     - *SSP1-2.6*: Escenario de mitigación verde.
     - *SSP2-4.5*: Escenario medio (+1.5 °C).
     - *SSP5-8.5*: Escenario de cambio extremo (+3.2 °C, sequías severas).
   - **Horizonte Temporal**: 30 días (un mes), 90 días (estacional), 180 días o 365 días (año completo).
   - **Eficiencia de Riego Tecnificado**: Deslizador de 0% a 100% (el riego por goteo óptimo suele ser 85-90%).
3. Presiona **"Iniciar Simulación Acoplada"**. El backend ejecutará el cálculo biofísico de los 365 días en milisegundos.

### B. Interpretación de los Gráficos (Recharts)
- **1. Hidrograma de Cuenca SWAT**:
  - **Barras Celestes**: Precipitaciones diarias ($mm$).
  - **Línea Teal Sólida**: Caudal del río ($m^3/s$). Observa cómo los picos de caudal ocurren 1-2 días después de las lluvias debido al tiempo de concentración.
- **2. Dinámica Fisiológica Vegetal**:
  - **Línea Púrpura Discontinua**: Demanda evaporativa atmosférica ($ET_0$).
  - **Línea Verde**: Transpiración real de la planta ($Tr$). Si la línea verde se separa mucho de la púrpura hacia abajo, la planta está sufriendo estrés hídrico.
  - **Línea Celeste**: Velocidad de flujo de savia ($cm/h$).
- **3. Humedad de Suelo y Estrés**:
  - **Área Azul**: Humedad volumétrica $\theta$ (%).
  - **Línea Ámbar / Roja**: Curva de estrés CWSI (de 0 a 1).

---

## 📑 4. Centro de Reportes Multiformato (`/reports`)

Permite generar y descargar formalmente los resultados de cualquier simulación en 3 formatos independientes:

```
┌─────────────────────────────────────────────────────────────┐
│                 CENTRO DE REPORTES MULTIFORMATO             │
├─────────────────┬─────────────────────────┬─────────────────┤
│    📄 PDF       │       📝 WORD           │    📊 EXCEL     │
│   EJECUTIVO     │   TÉCNICO (.docx)       │   ANALÍTICO     │
│                 │                         │                 │
│ Membrete formal │ Estructura con títulos  │ 3 Pestañas con  │
│ Tablas de SWAT  │ Tablas sombreadas       │ series diarias  │
│ Recomendaciones │ Texto 100% editable     │ Fórmulas y KPIs │
│                 │                         │                 │
│ [Descargar PDF] │ [Descargar DOCX]        │ [Descargar XLSX]│
└─────────────────┴─────────────────────────┴─────────────────┘
```

1. **Selecciona la simulación** en el selector desplegable superior.
2. Haz clic en el botón de descarga del formato deseado:
   - **PDF**: Abre/descarga un documento formal con diseño editorial listo para impresión o presentación ejecutiva.
   - **Word (`.docx`)**: Descarga un documento editable con estilos de ingeniería, ideal para redactar tesis, informes de consultoría o artículos científicos.
   - **Excel (`.xlsx`)**: Descarga un libro analítico con 3 hojas estructuradas (`Resumen Ejecutivo`, `Balance Hidrológico SWAT`, `Fisiología Vegetal Micro`) con los datos diarios completos.
3. La tabla inferior registrará automáticamente el historial de descargas con timestamp y tamaño de archivo.

---

## 👥 5. Gestión de Usuarios y Roles (`/users`) *(Solo Superadmin)*

1. Accede con la cuenta de **Superadmin** (`admin@digitaltwin.org`).
2. En la tabla de usuarios podrás:
   - Ver el rol y estado activo de cada investigador.
   - **Asignar Roles**: Haz clic en *"Editar Roles"* para otorgar permisos de `ADMIN_CIENTIFICO`, `INVESTIGADOR_HIDROLOGO`, `OPERADOR_AGROPECUARIO` o `LECTOR_AUDITOR`.
   - **Activar / Desactivar**: Alternar el interruptor para suspender temporalmente el acceso de un usuario.

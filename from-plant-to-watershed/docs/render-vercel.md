# Prueba con un usuario: Render Free + Vercel

Sólo se despliegan FastAPI, PostgreSQL y Next.js. Streamlit es un laboratorio
independiente y no forma parte del despliegue.

## Perfil de recursos

El `render.yaml` de la raíz crea una API Docker y una PostgreSQL vacía en la
misma región. Usa un worker Uvicorn, dos conexiones DB sin overflow, un hilo
por librería numérica, consultas de playback de hasta siete días y ejecución
serializada. El perfil admite hasta 366 días y 1000 plantas por solicitud;
rechaza con 422 las solicitudes mayores, sin recortar ni sustituir parámetros
científicos. Estos límites son configurables y sólo el Blueprint usa ese presupuesto.
Las preferencias locales mantienen sus valores por defecto; la serialización
y recuperación de trabajos interrumpidos sólo se activan con
`SERIALIZE_SIMULATIONS=true` (perfil de un único proceso).

La disponibilidad valida los checksums de todos los frames con un cursor SQL
acotado y conserva sólo metadatos. No cachea un diagnóstico que pudiera ocultar
corrupción posterior. El catálogo de Reportes usa proyecciones SQL; el playback
se comprime con gzip cuando el cliente lo acepta. Los cálculos síncronos del
motor se ejecutan en un hilo para que la API pueda seguir atendiendo salud y
consultas mientras calcula. Esto conserva el contrato HTTP actual: la creación
espera el resultado; no hay una cola distribuida ni reanudación automática.

Mediciones locales sobre `phase234-sf-2019-v2`:

| Consulta | Antes | Después |
| --- | --- | --- |
| Importar FastAPI | 173,5 MiB de pico | 76,1 MiB |
| Disponibilidad del año completo | Detenida al superar 453 MiB, sin respuesta | 166,4 MiB de pico; HTTP 200; 365 días |
| Playback de 7 días desde 15 de julio | — | HTTP 200; 0,50 s; 3,39 MB de JSON sin compresión |

La corrida real adicional usó 365 días, 1000 plantas por grupo, 19 años de
warmup, semilla 42, 36 HRUs y 37 canales: el pico Python bajó de 595,3 a
293,5 MiB. Se compararon las celdas de los diez CSV científicos antes y
después: todas son idénticas (el orden de columnas puede variar entre procesos).
El lector climático valida todo el archivo, incluidos duplicados fuera de la
ventana, y sólo retiene los valores del período solicitado. No se recortó el
warmup ni el número de plantas para obtener esa medición.
Además se completó un coupling real de 365 días/1000 plantas dentro de Docker
con **512 MiB de límite, una CPU y sin red**, usando el paquete del proyecto
multianual seleccionado: 261,6 MiB de pico Python, dos iteraciones y 238 s.
Es una comprobación del límite de memoria en contenedor, no del rendimiento de
CPU ni de los tiempos de reinicio propios de Render.
La evidencia está en [render-resource-audit.json](render-resource-audit.json).

Son mediciones de proceso local, no una prueba de carga en Render ni una
promesa de tiempos allí. El consumo de una corrida depende de duración,
plantas, HRUs, outputs, warmup y modelos ML elegidos.

## SWAT+ portable

El código en Git no contiene tu instalación local de SWAT+. Para ejecutar
SWAT+ en Render es obligatorio suministrar su ejecutable Linux x86_64 y el
proyecto real. No se reemplaza por hidrología sintética si falta alguno.

Desde `backend/`, crear un paquete a partir de los recursos existentes:

```bash
python deployment/swat_runtime.py export \
  --executable data/baseline-diagnostic-source-build-v1/compile-v4/swatplus-research \
  --project data/baseline-diagnostic-multiyear-v1/selected-project \
  --output /tmp/agro-render-swat-runtime.tar.gz \
  --bundle-system-runtime
```

El comando imprime el SHA256. Empaqueta el mismo binario, su cargador ELF
y sus bibliotecas originales verificadas por SHA256, evitando depender de la
glibc del contenedor. Incluye inputs y los manifiestos científicos
adyacentes; omite los outputs reconocidos por el adapter. No altera la fuente
ni contiene la DB o credenciales. Subir ese archivo a almacenamiento HTTPS
accesible para el servicio y configurar en Render:

- `SWAT_RUNTIME_BUNDLE_URL`: URL del archivo, fuera de Git.
- `SWAT_RUNTIME_BUNDLE_SHA256`: SHA256 exacto impreso por el exportador.

El arranque descarga a disco, verifica el hash y extrae de forma segura a
`data/swat-runtime`. El Dockerfile instala `libgfortran5`. Los inputs permanecen
separados de `data/swat-runs`, donde el adapter crea cada workspace. Se verificaron el cargador, el binario y las bibliotecas originales dentro de
la imagen Debian con un límite de 512 MB; el binario local por sí solo requería
GLIBC_2.43, ausente en la imagen. El runtime portable resuelve esa incompatibilidad
sin recompilar el modelo ni modificar sus bibliotecas originales.

Sin URL, la API puede iniciar y ejecutar el motor simplificado; SWAT+ informa
que los recursos no están instalados. No utilizar el paquete de un proyecto
distinto para afirmar que se reprodujo el experimento congelado.
El perfil científico congelado además necesita sus catálogos/observaciones y,
si se solicita ML mensual, los ModelBundles originales registrados; no los
crea `bootstrap-reference`. El entrenamiento sigue fuera del despliegue.

## Render

1. Crear un Blueprint desde `render.yaml` en la raíz del repositorio.
2. Configurar `CORS_ORIGINS` como JSON, por ejemplo
   `["https://tu-proyecto.vercel.app"]`. Usar los dominios concretos permitidos.
3. Configurar el paquete SWAT+ y su hash si se ejecutarán corridas reales.
4. Conservar `APP_ENV=production`, el secreto generado y ambos seeds en false.
5. Verificar `/health/ready`: comprueba conexión DB y devuelve 503 si falla.

No se crea un usuario con contraseña conocida ni se importan las simulaciones
locales. Para inicializar la base vacía, Render Free no proporciona shell:
usar la máquina del operador con el código/dependencias instalados y la URL
**externa** de PostgreSQL. Autorizar temporalmente la IP del operador en Render.
La API usa la URL interna del Blueprint.

Desde `backend/`, configurar temporalmente en esa terminal:

```bash
export APP_ENV=production
export DATABASE_URL='postgresql://USUARIO:CLAVE@HOST:5432/digitaltwin?sslmode=require'
export SECRET_KEY='MISMO_SECRETO_CONFIGURADO_EN_RENDER'
export ENABLE_DEMO_SEED=false
export ENABLE_MVP_BOOTSTRAP=false
python -m app.cli create-admin --email TU_CORREO --full-name 'Administrador'
python -m app.cli bootstrap-reference
```

La contraseña del administrador se pide sin imprimirla. `bootstrap-reference`
es idempotente: prepara cuenca de referencia y escenarios, sin cuentas demo,
observaciones, modelos ni corridas. Después cerrar el acceso externo DB del
operador. Crear usuarios desde la aplicación y asignar permisos de investigador
para quienes deban ejecutar corridas; el registro público sólo asigna operador.
No introducir secretos de PostgreSQL o JWT en Vercel ni en Git.

## Vercel

- Root Directory: `from-plant-to-watershed/frontend`.
- Framework: Next.js; build: `pnpm build`.
- `NEXT_PUBLIC_API_URL=https://TU_API.onrender.com/api/v1`, disponible en build.

El renderizado 3D corre en el navegador. No necesita Streamlit ni acceso directo
al filesystem del backend. Cambiar la URL de API requiere un nuevo build.

## Verificación y límites

```bash
# Backend: usa DB de pruebas aislada
python -m pytest -q tests/test_render_profile.py tests/test_playback_diagnostic.py \
  tests/test_playback_contract.py tests/test_simulation_catalog.py \
  tests/test_reports.py tests/test_phase34_preflight_gate.py
# Frontend
pnpm test
pnpm exec tsc --noEmit
```

Verificar en Render una corrida pequeña con la configuración elegida y luego
la corrida de 365 días, observando memoria, estado persistido y playback antes
de ampliar duración. Un segundo envío mientras otra corrida está activa devuelve
409. Un reinicio del perfil serializado marca como FAILED los trabajos pendientes
o en ejecución, para permitir un nuevo intento; no los reanuda ni borra resultados.

Render Free ofrece 512 MB de RAM. El servicio se duerme tras inactividad, puede
reiniciar y su filesystem es efímero. Los resultados publicados viven en
PostgreSQL; los workspaces y logs locales se pierden al reiniciar. El paquete
SWAT+ debe poder descargarse de nuevo, lo que aumenta el tiempo de arranque.
No ejecutar múltiples workers con el perfil serializado.

PostgreSQL Free tiene 1 GB, vence a los 30 días y no incluye backups. Una base
inicialmente vacía no evita esos límites. Exportar backups desde una máquina
autorizada y planificar la retención de corridas desde una herramienta administrativa
(no existe aún un endpoint de borrado de simulaciones);
no borrar automáticamente evidencia científica para ahorrar espacio.

Fuentes: [Render Free](https://render.com/docs/free),
[planes](https://render.com/pricing), [Next.js en Vercel](https://vercel.com/docs/frameworks/full-stack/nextjs).

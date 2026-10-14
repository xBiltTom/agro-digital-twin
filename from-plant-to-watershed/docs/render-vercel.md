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

La imagen del backend incluye `deploy/swat-runtime.tar.gz`, un paquete Linux
x86_64 con el ejecutable, el cargador ELF, sus bibliotecas verificadas por hash
y los inputs South Fork. `deploy/swat-runtime.sha256` fija el paquete; el build
Docker valida el checksum y lo extrae de forma segura a `data/swat-runtime`.
No hace falta publicar el archivo en otro host ni configurar variables de URL
para que Render instale el motor.

El ejecutable es un build de investigación SWAT+ 61.0.2.61, con instrumentación
de almacenamiento diario de canales para el acoplamiento. No es un release
oficial ni reproduce automáticamente una corrida precalculada. Su procedencia,
parche y licencia LGPL-2.1 están descritos en
[`deploy/SWATPLUS-NOTICE.md`](../../deploy/SWATPLUS-NOTICE.md) y `licenses/`.
La imagen conserva los inputs en `data/swat-runtime` y crea workspaces
independientes en `data/swat-runs`; los resultados de playback se persisten en
PostgreSQL. El modelo congelado 2019 y las observaciones no se precargan.

Para actualizar el paquete, exportarlo con `deployment/swat_runtime.py`, revisar
su procedencia y los notices, reemplazar el archivo y actualizar el SHA exacto.
No usar un proyecto distinto para afirmar que se reprodujo el experimento
congelado. Los catálogos/observaciones y los ModelBundles ML mensuales siguen
siendo recursos separados; no los crea `bootstrap-reference`.

## Render

1. Crear un Blueprint desde `render.yaml` en la raíz del repositorio.
2. Configurar `CORS_ORIGINS` como JSON, por ejemplo
   `["https://tu-proyecto.vercel.app"]`. Usar los dominios concretos permitidos.
3. Conservar `APP_ENV=production`, el secreto generado y ambos seeds en false.
4. Verificar `/health/ready`: comprueba conexión DB y devuelve 503 si falla.

La DB queda sin usuarios ni corridas precargadas; la API crea tablas, roles,
permisos, cuenca y escenarios estructurales al arrancar. Render Free no ofrece
shell/SSH para web services. Para el primer admin, autorizar temporalmente sólo
la IP pública del operador en la lista de acceso de PostgreSQL y ejecutar desde
`backend/` con las dependencias instaladas:

```sh
export APP_ENV=production
export DATABASE_URL='postgresql://USUARIO:CLAVE@HOST:5432/agrotwindb?sslmode=require'
export SECRET_KEY='EL_SECRETO_CONFIGURADO_EN_RENDER'
python -m app.cli create-admin --email TU_CORREO --full-name 'Administrador'
```

La contraseña se pide sin mostrarla. Después, retirar la IP de la lista para
mantener PostgreSQL privado; el API continúa conectándose con su URL interna.
El registro público asigna el rol de operador; para ejecutar corridas se
necesita un rol científico/admin. No introducir secretos de PostgreSQL o JWT
en Vercel ni en Git.

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

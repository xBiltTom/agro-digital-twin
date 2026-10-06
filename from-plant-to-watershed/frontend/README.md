# Frontend — plataforma y gemelo 3D

Next.js 16, React 19, Tailwind CSS, Recharts y React Three Fiber/Three.js.
Consume la API FastAPI de la [plataforma](../README.md).

## Desarrollo

Desde esta carpeta, con Node.js compatible con Next.js 16 y pnpm:

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Abrir `http://localhost:3000` con backend disponible en `localhost:8000`.
La configuración del cliente está en `src/lib/api.ts`; `NEXT_PUBLIC_API_URL`
permite cambiar la base completa, por defecto `http://localhost:8000/api/v1`.

## Rutas principales

- `/`: resumen del reporte científico publicado.
- `/simulations`: registro, ejecución y consulta de corridas.
- `/twin-3d?simId=ID`: reproducción del gemelo por corrida/fecha y tres escalas.
- `/datasets`: catálogo de datos.
- `/reports`: evidencia e informes descargables.
- `/users` y `/profile`: administración/perfil según permisos.

Las páginas viven en `src/app/`; componentes en `src/components/`; hooks de
playback en `src/hooks/`. La representación recibe datos desde
`adaptPlaybackVisual()` y `sceneFromRecord()`, no calcula procesos científicos.

## Contratos

- [Playback, disponibilidad y reglas visuales](../docs/TWIN_PLAYBACK_CONTRACT.md).
- [Estado actual y separación de experimentos](../docs/CURRENT_STATE.md).

Dashboard/reportes y visor pueden mostrar experimentos distintos. El reporte
publicado es final v2; el visor prioriza el gemelo diario 2019 corregido.
Conservar versión, fecha, unidad y evidencia en cada vista.

## Comprobaciones

```bash
pnpm test
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

`pnpm test` ejecuta `tests/playback.test.ts`. `pnpm lint:playback` revisa el
conjunto de archivos del visor. `tests/visual-playback.mjs` contiene el recorrido
Playwright con fixtures; requisitos en el contrato temporal.

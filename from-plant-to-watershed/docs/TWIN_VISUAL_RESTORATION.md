# Restauración visual del gemelo 3D (fase 3.1)

La geometría foliar, radicular y reproductiva de `PlantModel3D` y las hojas curvas instanciadas, los surcos y la instrumentación contextual de `FieldPlotMesh3D` se recuperaron selectivamente de `6c1477f`. La topografía y la red fluvial contextual de South Fork permanecen en `WatershedMesh3D`. El contrato `twin-playback-v1` y `useTwinPlayback` siguen siendo la única fuente de estado temporal.

## Reglas de representación

- **Modo científico:** `SceneState` proviene del registro seleccionado. La altura de planta y campo usa 1 unidad de escena por metro, limitada solo para evitar geometrías inválidas. El LAI regula cantidad/tamaño visual de hojas; cobertura regula el tamaño visual del dosel; estrés, cuando existe, modifica color y caída visual. Estas transformaciones gráficas no son salidas adicionales del FSPM. La etapa reproductiva solo dibuja mazorca y panoja cuando el estado FSPM indica `REPRODUCTIVE` o `MATURITY`. No existe calendario de crecimiento en Three.js.
- **Planta individual:** se dibuja únicamente si `crop.active`, el cultivo es maíz y hay una muestra persistida con altura. Los IDs de `plant_samples` y sus coordenadas locales FSPM se conservan. Las raíces se dibujan solo si existe profundidad radicular. Las hojas, nervaduras, mazorca, raíces laterales y estratos edáficos son anatomía ilustrativa; el FSPM no persiste una malla tridimensional validada.
- **Campo:** las 1.014 instancias gráficas son vegetación decorativa basada en *promedios de campo*, no 1.014 trayectorias individuales. Los marcadores con IDs son las muestras realmente persistidas. Fuera de temporada, en baseline sin FSPM, o cuando faltan altura/LAI, no se dibuja el dosel científico. Para otros cultivos no se inventa geometría específica.
- **Modo histórico:** las tres escalas siguen navegables con una parcela y planta de referencia. Sus medidas internas solo definen una maqueta visual estática y no se muestran como resultados. No se anima lluvia ni fisiología histórica sin registros `twin-playback-v1`. Los gráficos históricos conservan sus valores persistidos y su frecuencia declarada o desconocida.
- **Meteorología:** solo un registro `DAILY` con precipitación disponible y positiva activa partículas; cero muestra ausencia de lluvia y `null` significa desconocido. El HUD conserva unidad, evidencia y fuente.
- **Hidrología:** el caudal del outlet no se asigna a cada canal; el terreno y la red fluvial siguen siendo contexto esquemático. No existe correspondencia HRU→polígono validada.

La animación ambiental de hojas y agua es estética. La humedad volumétrica porcentual FSPM sigue separada del almacenamiento SWAT+ en mm; la humedad asumida de South Fork no responde a la lluvia. Las tarjetas y el HUD nunca convierten ausencia en cero.

## Verificación visual reproducible

Con Next.js arrancado localmente, `frontend/tests/visual-playback.mjs` intercepta la API en el navegador y sirve una fixture `twin-playback-v1` de tres fechas y otra corrida histórica sin artefacto. Comprueba navegación entre las tres escalas, cambio de altura, fin de temporada y etiquetas de referencia. Guarda ocho capturas en `VISUAL_OUTPUT_DIR` (por defecto `/tmp/gemelo-visual`). Requiere Playwright y Chromium instalados; si están fuera de `frontend/node_modules`, indicar sus rutas mediante `PLAYWRIGHT_MODULE` y `CHROMIUM_PATH`. La prueba no representa una validación observacional de South Fork.

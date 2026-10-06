# Guía de sustentación — From Plant to Watershed

Asignatura: Ingeniería de Software II. Revisión: 2026-10-05.
La [ficha técnica](from-plant-to-watershed/project_framework.md) guía la
investigación; el [estado actual](from-plant-to-watershed/docs/CURRENT_STATE.md)
define qué se puede demostrar hoy.

## Resumen de 30 segundos

> Desarrollamos una plataforma multiescala que conecta un modelo simplificado
> de plantas de maíz con la hidrología SWAT+ de South Fork Iowa River. El sistema
> ejecuta los modelos, conserva su procedencia y permite explorar estados por
> fecha en planta, campo y cuenca. La versión diaria reciente usa los calendarios
> de manejo ejecutados y una estimación de humedad radicular desde SWAT+.
> La siguiente etapa es evaluar si este acoplamiento actualizado mejora la
> predicción frente a observaciones USGS.

## Qué mostrar en cuatro minutos

### 1. Problema y arquitectura

Explicar las escalas planta → campo/HRU → cuenca, con clima y manejo como
entradas. FastAPI gestiona ejecución y persistencia; PostgreSQL guarda estados
temporales; Next.js presenta gráficos y escenas.

La lógica científica en `backend/scientific_core/` se separa del framework web.
Los servicios de aplicación integran el motor SWAT+ y la base de datos.

### 2. Gemelo diario

Abrir `/twin-3d?simId=phase234-sf-2019-v2` con una cuenta propietaria o acceso
`SUPERADMIN` y la corrida registrada en el catálogo.

- **15 de enero:** hidrología y ausencia de cultivo activo.
- **15 de mayo:** inicio de cultivo según evento simulado de manejo.
- **15 de julio:** campo desarrollado y hasta 70 muestras activas de siete grupos.
- **30 de agosto:** cosecha escalonada; no todas las cohortes permanecen activas.
- **15 de septiembre:** estados hidrológicos sin plantas FSPM de esa temporada.

Mostrar Micro, Meso y Macro, y abrir el explorador de **36 HRU / 37 canales**.
Los estados por ID son resultados del modelo; las mallas del terreno y del
cultivo son representación contextual/ilustrativa. No afirmar que un sector
3D identifica una HRU georreferenciada: esa unión sigue pendiente.

### 3. Evidencia y reportes

En `/reports`, explicar la diferencia entre:

- **Reporte final v2:** evaluación mensual USGS 2018–2020 del acoplamiento
  anterior, RMSE 9,4471 m³/s en ambos brazos, mejora 0 % y `H1_NOT_SUPPORTED`.
- **Gemelo diario corregido 2019:** avance operativo con retroalimentación
  hídrica aproximada; todavía no tiene evaluación observacional propia de H1.

Una hipótesis no respaldada es un resultado que se reporta. Las correcciones
posteriores justifican un experimento nuevo, no cambiar las métricas archivadas.
Los informes PDF/Word/Excel exportan los datos disponibles de la corrida.

### 4. Interpretación asistida y próximos pasos

Mostrar el diagnóstico IA de una corrida en `/simulations`. LangChain conecta
Gemini/OpenAI con un prompt que solicita JSON y utiliza métricas recuperadas;
si falla el proveedor o faltan claves, hay un motor heurístico de respaldo.

El módulo interpreta resultados, no calcula la física ni prueba la hipótesis.
No atribuir garantía absoluta de formato o ausencia de alucinaciones al LLM,
ni afirmar soporte Ollama que el servicio actual no implementa.

Cerrar con la próxima comparación del flujo corregido contra USGS, revisión del
baseline y evaluación multianual con incertidumbre.

## Preguntas frecuentes

**¿Son datos reales?**

La cuenca y la estación USGS corresponden a South Fork; el motor SWAT+ se
ejecuta realmente. Caudal simulado, estados FSPM, estimaciones hídricas y
observaciones son categorías distintas. El frame declara evidencia y unidades.

**¿Las plantas 3D fueron medidas?**

No. Son muestras de poblaciones numéricas. La altura/LAI/raíces pueden provenir
del FSPM persistido, pero la anatomía de la malla es ilustrativa. Las 1.014
instancias Meso son decoración gobernada por agregados, no individuos medidos.

**¿El agua de SWAT+ afecta a las plantas?**

En la ruta diaria corregida sí: `sw_ave` y `soils.sol` permiten estimar humedad
de zona radicular bajo un supuesto de perfil uniforme. SWAT+ conserva sus propias
ecuaciones; no se le impone directamente la transpiración diaria FSPM.

**¿Ya se cumplió la mejora del 15 %?**

No. El reporte publicado tiene mejora 0 %. La versión actualizada requiere una
nueva comparación emparejada. Además, el evaluador mide caudal mensual en m³/s,
no escorrentía superficial en mm.

**¿El laboratorio ML demuestra mayor precisión?**

El campeón mensual versionado reporta NSE 0,9861 sobre datos sintéticos.
El experimento diario aprende de playback simulado. Ninguno demuestra mejora
física observacional de H1. Detalles en la
[Model Card](agro-digital-twin-st/MODEL_CARD.md).

**¿Hay CMIP6 y validación multicuenca?**

Son parte del alcance de investigación. El experimento publicado no dispone
de artefactos CMIP6 normalizados y la evidencia actual corresponde a un piloto
de una sola cuenca.

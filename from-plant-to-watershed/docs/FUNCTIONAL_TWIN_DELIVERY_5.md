# Entrega 5: flujo funcional y paquete del paper

**Fecha:** 2026-10-06. Cierra la quinta entrega acordada del experimento actual.

## Recorrido del usuario

1. **Inicio** muestra el experimento actual TEST 2021–2025: A/B/C/D, referencias simples, gráfico mensual, métricas, intervalo principal y sensibilidad sin estimados.
2. **Simulaciones → Ejecutar una reproducción propia** permite año 2021–2025, física A/B y corrección mensual opcional C/D. Usa la receta congelada; la corrida pertenece al usuario autenticado y se persiste en pglocal.
3. La ejecución comienza en un proceso independiente y se consulta cada diez segundos; el usuario puede salir y volver. Se admite una reproducción física activa por usuario. El botón Actualizar vuelve a consultar tanto evidencia como corrida.
4. Al completar, se ofrecen visor diario, CSV físico y CSV mensual ML. Un fallo de ML conserva la física completada y expone el motivo. No se inventa una trayectoria ML diaria.
5. **Informes** expone JSON, comparación CSV, manuscrito y ZIP del paper. El experimento 2018–2020 permanece identificado como archivo histórico.
6. El **visor** prioriza una reproducción B completada accesible o B TEST 2025. Los enlaces `?simId=` y las consultas de corrida respetan propietario/superadministrador. El informe agregado está disponible para usuarios autenticados.

Se conservaron estilos existentes; no se añadió un sistema de colas, una base nueva ni nuevas tablas. Los archivos de ejecución se aíslan por corrida; la persistencia usa **digitaltwin**.

## Evidencia de esta entrega

La reproducción B 2021 `b18f1d0d-e0fd-4a04-b8e7-49e1085a7f2e` quedó `COMPLETED` en pglocal con **365 registros físicos, 365 frames y 12 predicciones mensuales D**. La inferencia utiliza el checksum D congelado `313930f9b3bc4247df56babe250566eb166942ecc69e309a5407e4678294f051`.

Python compila los módulos nuevos; TypeScript completa `tsc --noEmit --incremental false`. Las figuras se generaron con Matplotlib y se inspeccionaron visualmente. No se ejecutaron suites de pruebas ni se comprobó el recorrido en un navegador.

El recibo se conserva en [delivery 5](../research_domain/south_fork_functional_delivery_5_v1.json). Los resultados científicos TEST y los bundles C/D permanecen congelados; esta reproducción no recalcula H1.

## Paquete científico

- [Manuscrito](../research_domain/paper_v1/manuscript.md): resumen, introducción delimitada, métodos, resultados, discusión, conclusiones, disponibilidad y referencias verificadas.
- [Reproducción](../research_domain/paper_v1/reproduce.md): entorno, dependencias externas, comandos y operación del proceso.
- [Métricas](../research_domain/paper_v1/metrics.csv): TRAIN, VALIDATION, TEST y sensibilidad.
- [Contrastes](../research_domain/paper_v1/contrasts.csv): reducción puntual e intervalos principal/secundarios.
- Figuras PNG, SVG y PDF; manifiestos SHA-256; bundles y recetas dentro del ZIP.
- Dataset `sf-paper-v1` y artefactos registrados en pglocal, incluido el reporte TEST completo. El registro de modelos enlaza la evaluación posterior sin reescribir los archivos congelados del bundle.

El ZIP generado es un artefacto local descargable; Git conserva fuentes, tablas, figuras y manifiesto. Se regenera con `venv/bin/python scripts/package_south_fork_paper.py --register`, desde backend, tras instalar `requirements-paper.txt` en el entorno científico existente.

## Límites y operación

H1 continúa **no respaldada**, con IC95 D/A que incluye cero. El funcionamiento del sistema no valida fisiología, generalización ni balance conservativo de ML. El perfil es histórico y experimental, con referencia física exploratoria y manejo estático; no es una recomendación agrícola operacional.

El paquete no incluye todo el proyecto SWAT+, forcing pesado ni la base PostgreSQL. Esos recursos locales y sus registros son necesarios para reproducir la física. La documentación de reproducción señala expresamente esta dependencia.

No hay cancelación ni recuperación automática si se apaga el host; una corrida interrumpida requiere revisión del operador antes de crear otra. La guía de reproducción explica los logs y el arranque de una corrida pendiente que no llegó a iniciarse.

La revisión editorial, autoría, revista y envío del manuscrito son trabajo posterior del equipo. No condicionan el cierre de las cinco entregas técnicas ni implican aceptación editorial.

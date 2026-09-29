"""AI Scientific Copilot Service for Multi-Scale Digital Twin.

Uses LangChain with Google Gemini or OpenAI to synthesize simulation results,
diagnose multi-scale biophysical interactions (Plant -> Field -> HRU -> Watershed),
and generate policy/management recommendations. Includes a scientific heuristic
engine as a resilient offline/no-key fallback.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _first_not_none(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


SYSTEM_PROMPT = """Eres el Copiloto Científico de "From Plant to Watershed". La solicitud contiene únicamente metadatos y métricas que el backend pudo recuperar para una corrida concreta; puede ser FSPM, SWAT+, histórica o incompleta.

Analiza solo los valores y metadatos explícitos en el payload. No asumas cuenca, estación, cantidad de HRU/plantas, calibración, observación, cierre de balance, resolución ni variables ausentes. No derives procesos que no estén calculados. Si un valor es null o falta, decláralo no disponible. Distingue FSPM simplificado, SWAT+ modelado, observación e importación histórica por su evidencia. Mantén unidades y frecuencia originales. No confundas almacenamiento SWAT+ en mm con humedad volumétrica.

Emite un diagnóstico científico estructurado en español técnico, riguroso y conciso, orientado a investigadores y gestores de cuenca.

Debes responder EXCLUSIVAMENTE un objeto JSON válido con las siguientes claves:
{
  "executive_summary": "Resumen ejecutivo del balance hídrico y comportamiento general en 2 párrafos.",
  "multiscale_biophysical_diagnosis": {
    "micro_scale_plant": "Diagnóstico de la respuesta foliar, dinámica de LAI, absorción radicular y estrés hídrico.",
    "meso_scale_field": "Diagnóstico de humedad volumétrica del suelo en zona radicular, balance infiltración vs escorrentía superficial.",
    "macro_scale_watershed": "Diagnóstico del caudal en exutorio USGS 05451210, coeficiente de escorrentía y régimen hidrológico."
  },
  "climate_resilience_assessment": "Evaluación de resiliencia o vulnerabilidad de la cuenca ante el escenario climático y de manejo.",
  "policy_recommendations": [
    "Recomendación 1 para políticas hídricas regionales o adaptación agronómica",
    "Recomendación 2...",
    "Recomendación 3...",
    "Recomendación 4..."
  ],
  "limitations_and_uncertainty": "Nota honesta sobre supuestos, variables no disponibles, incertidumbre y validación."
}"""


class AICopilotService:
    """Orchestrates LangChain-based scientific synthesis and resilient heuristic fallbacks."""

    @classmethod
    async def analyze_simulation(cls, sim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a simulation run and generate structured AI insights."""
        summary = sim_data.get("summary_metrics") or {}
        water_balance = summary.get("water_balance") or {}
        paired = summary.get("paired_comparison") or {}
        field = sim_data.get("field_aggregates") or {}
        validation = sim_data.get("validation") or {}
        scenario = sim_data.get("scenario") or {}
        management = sim_data.get("management_scenario")
        watershed_name = sim_data.get("watershed_name") or "cuenca no especificada"

        duration = sim_data.get("duration_days")
        discharge_hm3 = summary.get("total_discharge_hm3")
        calculated_mean_q = (
            (discharge_hm3 * 1_000_000.0) / (duration * 86400.0)
            if discharge_hm3 is not None and duration is not None and duration > 0
            else None
        )
        closure_error = water_balance.get("closure_error_mm")
        closure_verified = water_balance.get("closure_metric_verified") is True
        closure_is_finite = isinstance(closure_error, (int, float)) and math.isfinite(closure_error)
        water_balance_closed = (
            abs(closure_error) < 0.1 if closure_verified and closure_is_finite else None
        )

        context_payload = {
            "simulation_id": sim_data.get("id"),
            "simulation_name": sim_data.get("name"),
            "watershed": watershed_name,
            "duration_days": duration,
            "scenario": {
                "name": scenario.get("name") or sim_data.get("scenario_name"),
                "temp_anomaly_c": scenario.get("temp_anomaly_c"),
                "precip_factor": scenario.get("precip_factor"),
                "co2_ppm": scenario.get("co2_ppm"),
                "management": management,
            },
            "water_balance_summary": {
                "total_precipitation_mm": _first_not_none(summary.get("total_precipitation_mm"), summary.get("total_precip_mm")),
                "total_runoff_mm": _first_not_none(summary.get("total_runoff_mm"), summary.get("total_surface_runoff_mm")),
                "total_evapotranspiration_mm": _first_not_none(summary.get("total_evapotranspiration_mm"), summary.get("total_actual_et_mm")),
                "mean_soil_moisture_percent": _first_not_none(summary.get("mean_soil_moisture_percent"), field.get("soil_moisture_vol")),
                "mean_streamflow_m3s": _first_not_none(water_balance.get("mean_streamflow_m3s"), calculated_mean_q),
                "peak_streamflow_m3s": _first_not_none(water_balance.get("peak_streamflow_m3s"), summary.get("peak_streamflow_m3s")),
                "water_balance_closed": water_balance_closed,
                "water_balance_closure_limitation": None if closure_verified and closure_is_finite else "No verified physical closure residual is available",
            },
            "paired_comparison_deltas": paired,
            "field_canopy_aggregates": {
                "mean_lai": _first_not_none(field.get("mean_lai"), field.get("lai_mean"), field.get("mean_LAI")),
                "mean_root_depth_m": _first_not_none(field.get("mean_root_depth_m"), field.get("root_depth_mean_m"), (
                    field.get("mean_root_depth_cm") / 100.0 if field.get("mean_root_depth_cm") is not None else None
                )),
                "mean_transpiration_mm": _first_not_none(field.get("mean_transpiration_mm"), field.get("transpiration_mean_mm"), field.get("transpiration_mm_day")),
                "mean_water_stress": _first_not_none(field.get("mean_water_stress"), field.get("water_stress_mean"), field.get("mean_stress"), summary.get("mean_cwsi")),
            },
            "statistical_validation": validation,
        }

        # Check for configured API keys
        gemini_key = settings.GEMINI_API_KEY.strip()
        openai_key = settings.OPENAI_API_KEY.strip()

        # Try Google Gemini via LangChain
        if gemini_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import SystemMessage, HumanMessage

                model_name = settings.AI_MODEL_NAME if "gemini" in settings.AI_MODEL_NAME else "gemini-2.5-flash"
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=gemini_key,
                    temperature=0.2,
                )
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"Analiza la siguiente simulación del gemelo digital:\n\n{json.dumps(context_payload, indent=2, ensure_ascii=False)}"),
                ]
                response = await llm.ainvoke(messages)
                content = response.content
                if isinstance(content, str):
                    # Clean markdown codeblocks if wrapped in ```json
                    cleaned = content.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    elif cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    parsed = json.loads(cleaned.strip())
                    parsed["provider"] = f"Google {model_name} (LangChain)"
                    parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
                    parsed["raw_metrics_analyzed"] = context_payload
                    return parsed
            except Exception as exc:
                logger.warning(f"Error calling LangChain Google Gemini: {exc}. Falling back to scientific heuristic.")

        # Try OpenAI via LangChain
        if openai_key:
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import SystemMessage, HumanMessage

                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=openai_key,
                    temperature=0.2,
                )
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"Analiza la siguiente simulación del gemelo digital:\n\n{json.dumps(context_payload, indent=2, ensure_ascii=False)}"),
                ]
                response = await llm.ainvoke(messages)
                content = response.content
                if isinstance(content, str):
                    cleaned = content.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    elif cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    parsed = json.loads(cleaned.strip())
                    parsed["provider"] = "OpenAI GPT-4o-mini (LangChain)"
                    parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
                    parsed["raw_metrics_analyzed"] = context_payload
                    return parsed
            except Exception as exc:
                logger.warning(f"Error calling LangChain OpenAI: {exc}. Falling back to scientific heuristic.")

        # Scientific Heuristic Engine fallback (guaranteed offline execution)
        return cls._scientific_heuristic_analysis(context_payload)

    @classmethod
    def _scientific_heuristic_analysis(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic scientific interpretation when no LLM API key is present."""
        wb = ctx.get("water_balance_summary", {})
        scen = ctx.get("scenario", {})
        paired = ctx.get("paired_comparison_deltas", {})
        field = ctx.get("field_canopy_aggregates", {})

        precip = wb.get("total_precipitation_mm")
        runoff = wb.get("total_runoff_mm")
        et = wb.get("total_evapotranspiration_mm")
        sm = wb.get("mean_soil_moisture_percent")
        q_mean = wb.get("mean_streamflow_m3s")
        runoff_ratio = (runoff / precip) * 100 if runoff is not None and precip is not None and precip > 0 else None
        et_ratio = (et / precip) * 100 if et is not None and precip is not None and precip > 0 else None

        temp_anom = scen.get("temp_anomaly_c")
        precip_fac = scen.get("precip_factor")
        mgmt = scen.get("management")

        # Scenario metadata is not evidence of a simulated response.
        if isinstance(temp_anom, (int, float)) and temp_anom > 1.5:
            scen_desc = f"un incremento térmico de +{temp_anom}°C"
        elif isinstance(precip_fac, (int, float)) and precip_fac < 0.9:
            scen_desc = f"una reducción pluviométrica del {(1.0 - precip_fac)*100:.0f}%"
        elif mgmt == "NO_TILL":
            scen_desc = "la adopción de siembra directa (labranza de conservación zerotill)"
        elif mgmt == "MAIZE_TO_SORGHUM":
            scen_desc = "la sustitución de maíz por sorgo granífero (grsg)"
        else:
            scen_desc = "el escenario registrado sin perturbación explícita"

        def metric(label: str, value: Any, unit: str, digits: int = 1) -> str:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                return f"{label}: no disponible"
            return f"{label}: {value:.{digits}f} {unit}"

        summary_items = [
            metric("precipitación acumulada", precip, "mm"),
            metric("evapotranspiración", et, "mm"),
            metric("escorrentía", runoff, "mm"),
            metric("caudal medio", q_mean, "m³/s", 2),
            metric("humedad volumétrica", sm, "%"),
        ]
        if et_ratio is not None:
            summary_items.append(f"ET/precipitación: {et_ratio:.1f}%")
        if runoff_ratio is not None:
            summary_items.append(f"escorrentía/precipitación: {runoff_ratio:.1f}%")
        exec_summary = (
            f"La corrida para {ctx.get('watershed') or 'cuenca no especificada'} declara {scen_desc}. "
            + "; ".join(summary_items)
            + ". Los valores ausentes no se completaron con referencias ni promedios supuestos."
        )

        micro_diag = "; ".join((
            metric("LAI medio de campo", field.get("mean_lai"), "m²/m²", 2),
            metric("profundidad radicular media", field.get("mean_root_depth_m"), "m", 2),
            metric("transpiración FSPM", field.get("mean_transpiration_mm"), "mm/día"),
            metric("estrés hídrico FSPM", field.get("mean_water_stress"), "fracción", 3),
        ))

        meso_diag = (
            "No hay agregados de campo disponibles para describir infiltración o perfil del suelo."
            if sm is None else metric("humedad volumétrica disponible", sm, "%")
        )
        macro_items = [metric("caudal medio de salida", q_mean, "m³/s", 2)]
        if runoff_ratio is not None:
            macro_items.append(f"relación escorrentía/precipitación: {runoff_ratio:.1f}%")
        macro_diag = "; ".join(macro_items) + ". No se infieren procesos espaciales o subcuencas sin esas salidas."
        resilience_note = (
            "La resiliencia no puede evaluarse solo con metadatos del escenario; requiere respuestas modeladas completas y una comparación de referencia."
        )

        recommendations = [
            "Verificar cobertura temporal completa antes de calcular totales hidrológicos.",
            "No declarar cierre del balance sin un residual físico calculado y documentado.",
            "Conservar unidades, frecuencia y evidencia al comparar variables FSPM y SWAT+.",
            "Obtener observaciones independientes antes de atribuir calibración o validación a una corrida.",
        ]

        if paired and paired.get("streamflow_m3s", {}).get("delta_percentage") is not None:
            pct = paired["streamflow_m3s"]["delta_percentage"]
            recommendations.append(f"El contraste emparejado muestra un delta de caudal de {pct:+.2f}% entre la parametrización acoplada y el baseline estándar de SWAT+.")

        return {
            "simulation_id": ctx.get("simulation_id"),
            "simulation_name": ctx.get("simulation_name"),
            "provider": "EcoTwin Scientific Expert Engine (LangChain Ready)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": exec_summary,
            "multiscale_biophysical_diagnosis": {
                "micro_scale_plant": micro_diag,
                "meso_scale_field": meso_diag,
                "macro_scale_watershed": macro_diag,
            },
            "climate_resilience_assessment": resilience_note,
            "policy_recommendations": recommendations,
            "limitations_and_uncertainty": (
                "Este resumen heurístico solo describe métricas persistidas. Los datos faltantes, la resolución temporal, las suposiciones y la procedencia limitan cualquier interpretación. "
                "No declara calibración, cierre físico, observaciones ni procesos espaciales que no estén documentados."
            ),
            "raw_metrics_analyzed": ctx,
        }

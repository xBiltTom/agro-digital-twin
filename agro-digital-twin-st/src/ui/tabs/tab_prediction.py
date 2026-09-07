"""
Tab 4: Runoff & Yield Prediction — Plant-to-Watershed AI Lab.
Executes real-time inference using the standalone ModelBundle service.
Supports Direct Prediction and Residual Correction against SWAT+ baseline.
"""

import os
import streamlit as st
from src.core.inference import load_model_bundle, ModelBundle
from src.ui.components import render_synthetic_data_badge, render_lab_ticket
from src.core.features.schema import TARGET_REGISTRY
from src.utils.config import ARTIFACTS_DIR
from src.infrastructure.database.repositories import SQLAlchemyPredictionRepository
from src.infrastructure.database.models import PredictionRecord


def render():
    st.header("🔮 4. Inferencia: Predicción de Escorrentía y Rendimiento")
    st.caption("🏷️ **[CRISP-DM: Deployment & API Serving]**")
    render_synthetic_data_badge()

    st.markdown("""
    Ejecuta inferencia biofísica acoplada en tiempo real. Ajusta las condiciones climáticas,
    el estado edáfico del suelo y las variables fenológicas de la planta (**Maíz FSPM**)
    para obtener la predicción de **Escorrentía Mensual**, **Caudal Fluvial** o **Rendimiento de Cosecha**.
    """)

    # 1. Selector de Modelo y Target
    col_t, col_m = st.columns(2)

    with col_t:
        target_name = st.selectbox(
            "Variable Objetivo a Predecir:",
            options=list(TARGET_REGISTRY.keys()),
            format_func=lambda x: {
                "monthly_runoff_mm": "Escorrentía Mensual (monthly_runoff_mm)",
                "monthly_streamflow_m3s": "Caudal Fluvial (monthly_streamflow_m3s)",
                "maize_yield_t_ha": "Rendimiento de Grano (maize_yield_t_ha)"
            }.get(x, x)
        )

    # Search available artifact directories for this target
    target_artifacts_dir = os.path.join(ARTIFACTS_DIR, target_name)
    available_bundles = []
    if os.path.exists(target_artifacts_dir):
        for entry in os.listdir(target_artifacts_dir):
            entry_path = os.path.join(target_artifacts_dir, entry)
            if os.path.isdir(entry_path) and os.path.exists(os.path.join(entry_path, "metadata.json")):
                available_bundles.append(entry)

    with col_m:
        if available_bundles:
            default_bundle_idx = available_bundles.index("champion") if "champion" in available_bundles else 0
            selected_bundle_name = st.selectbox(
                "Modelo / Artefacto Seleccionado:",
                options=available_bundles,
                index=default_bundle_idx,
                format_func=lambda x: f"🏆 Campeón ({x})" if x == "champion" else f"Artefacto ({x})"
            )
            bundle_dir = os.path.join(target_artifacts_dir, selected_bundle_name)
        else:
            st.warning("⚠️ No se encontraron modelos entrenados para este target. Ve a la Pestaña 3 para entrenar.")
            bundle_dir = None

    st.markdown("---")

    # 2. Escenarios Preconfigurados
    preset = st.selectbox(
        "⚡ Escenarios Preconfigurados de la Cuenca (Corn Belt):",
        [
            "Personalizado (Ajustar sliders inferiores)",
            "☀️ Verano Húmedo Óptimo (Julio - Pico de Crecimiento)",
            "🔥 Ola de Calor & Sequía Agronómica Severa",
            "🌧️ Evento de Tormenta Intensa (Primavera / Mayo)",
            "🍂 Fin de Temporada & Cosecha (Octubre)"
        ]
    )

    # Presets
    defaults = {
        "precip_mm": 95.0, "temp_mean_c": 22.0, "solar_radiation": 20.0,
        "soil_moisture": 30.0, "infiltration_mm": 55.0,
        "lai": 3.8, "root_depth_m": 1.2, "transpiration_mm": 60.0, "water_stress": 0.08,
        "et_mm": 80.0, "swat_baseline_runoff_mm": 18.5, "swat_baseline_streamflow_m3s": 12.0
    }

    if preset == "☀️ Verano Húmedo Óptimo (Julio - Pico de Crecimiento)":
        defaults = {"precip_mm": 115.0, "temp_mean_c": 24.0, "solar_radiation": 22.5, "soil_moisture": 34.0, "infiltration_mm": 65.0, "lai": 5.0, "root_depth_m": 1.4, "transpiration_mm": 85.0, "water_stress": 0.04, "et_mm": 110.0, "swat_baseline_runoff_mm": 22.0, "swat_baseline_streamflow_m3s": 15.0}
    elif preset == "🔥 Ola de Calor & Sequía Agronómica Severa":
        defaults = {"precip_mm": 25.0, "temp_mean_c": 31.0, "solar_radiation": 26.0, "soil_moisture": 16.0, "infiltration_mm": 15.0, "lai": 2.8, "root_depth_m": 1.1, "transpiration_mm": 30.0, "water_stress": 0.65, "et_mm": 45.0, "swat_baseline_runoff_mm": 3.5, "swat_baseline_streamflow_m3s": 2.5}
    elif preset == "🌧️ Evento de Tormenta Intensa (Primavera / Mayo)":
        defaults = {"precip_mm": 180.0, "temp_mean_c": 17.0, "solar_radiation": 15.0, "soil_moisture": 38.0, "infiltration_mm": 95.0, "lai": 1.2, "root_depth_m": 0.4, "transpiration_mm": 25.0, "water_stress": 0.02, "et_mm": 50.0, "swat_baseline_runoff_mm": 45.0, "swat_baseline_streamflow_m3s": 35.0}
    elif preset == "🍂 Fin de Temporada & Cosecha (Octubre)":
        defaults = {"precip_mm": 45.0, "temp_mean_c": 12.0, "solar_radiation": 12.0, "soil_moisture": 25.0, "infiltration_mm": 30.0, "lai": 0.2, "root_depth_m": 1.3, "transpiration_mm": 5.0, "water_stress": 0.15, "et_mm": 25.0, "swat_baseline_runoff_mm": 8.0, "swat_baseline_streamflow_m3s": 6.0}

    # 3. Sliders de Entrada
    st.subheader("🎛️ Parámetros Multiescala de Entrada")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Nivel 4 — Clima**")
        precip = st.slider("Precipitación Mensual (mm)", 0.0, 300.0, float(defaults["precip_mm"]), 1.0)
        temp = st.slider("Temperatura Media (°C)", -10.0, 40.0, float(defaults["temp_mean_c"]), 0.5)
        sol_rad = st.slider("Radiación Solar (MJ/m²/d)", 5.0, 35.0, float(defaults["solar_radiation"]), 0.5)

    with c2:
        st.markdown("**Nivel 1 & 2 — Planta Maíz & Campo**")
        lai = st.slider("Índice de Área Foliar (LAI)", 0.0, 7.0, float(defaults["lai"]), 0.1)
        root_depth = st.slider("Profundidad Radicular (m)", 0.1, 2.5, float(defaults["root_depth_m"]), 0.05)
        transp = st.slider("Transpiración del Cultivo (mm)", 0.0, 150.0, float(defaults["transpiration_mm"]), 1.0)
        water_stress = st.slider("Índice de Estrés Hídrico [0-1]", 0.0, 1.0, float(defaults["water_stress"]), 0.02)
        et = st.slider("Evapotranspiración Campo ET (mm)", 5.0, 200.0, float(defaults["et_mm"]), 1.0)

    with c3:
        st.markdown("**Nivel 3 — Suelo & Cuenca SWAT+**")
        soil_m = st.slider("Humedad Volumétrica Suelo (% vol)", 8.0, 48.0, float(defaults["soil_moisture"]), 0.5)
        infil = st.slider("Infiltración Edáfica (mm)", 0.0, 200.0, float(defaults["infiltration_mm"]), 1.0)
        swat_runoff = st.slider("Runoff Baseline SWAT+ (mm)", 0.0, 150.0, float(defaults["swat_baseline_runoff_mm"]), 0.5)
        swat_flow = st.slider("Caudal Baseline SWAT+ (m³/s)", 0.0, 100.0, float(defaults["swat_baseline_streamflow_m3s"]), 0.5)

    st.markdown("---")

    # 4. Lanzar Inferencia
    input_payload = {
        "precip_mm": precip,
        "temp_mean_c": temp,
        "solar_radiation": sol_rad,
        "soil_moisture": soil_m,
        "infiltration_mm": infil,
        "lai": lai,
        "root_depth_m": root_depth,
        "transpiration_mm": transp,
        "water_stress": water_stress,
        "et_mm": et,
        "swat_baseline_runoff_mm": swat_runoff,
        "swat_baseline_streamflow_m3s": swat_flow
    }

    if st.button("🧪 Ejecutar Inferencia Biofísica", type="primary", use_container_width=True):
        if bundle_dir and os.path.exists(bundle_dir):
            try:
                bundle = load_model_bundle(bundle_dir)
                res = bundle.predict(input_payload)
                res["water_stress"] = water_stress
                st.session_state.current_prediction = res

                # Log to persistence repository (SQLite / PostgreSQL)
                try:
                    repo = SQLAlchemyPredictionRepository()
                    repo.log_prediction(PredictionRecord(
                        id=None,
                        target_name=target_name,
                        learning_mode=res.get("mode", "direct"),
                        model_used=res.get("model_used", "Champion"),
                        predicted_value=float(res.get("value", 0.0)),
                        baseline_value=float(res.get("swat_baseline_value", 0.0)) if "swat_baseline_value" in res else None,
                        residual_value=float(res.get("predicted_residual", 0.0)) if "predicted_residual" in res else None,
                        unit=res.get("unit", "mm/month")
                    ))
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Error al ejecutar inferencia con el bundle: {e}")
        else:
            st.error("No hay un modelo disponible para inferencia. Por favor entrena un modelo en la Pestaña 3.")

    if st.session_state.get("current_prediction"):
        pred = st.session_state.current_prediction
        st.subheader("📋 Resultado del Diagnóstico Biofísico")
        render_lab_ticket(pred)

"""
Tab 3: AI Model Training — Plant-to-Watershed AI Lab.
Configures and trains 3 Traditional (RF, XGBoost, SVR) + 2 Hybrid (CNN-LSTM, LSTM-AE+RF) models.
Features:
- Target selection: monthly_runoff_mm, monthly_streamflow_m3s, maize_yield_t_ha
- Learning Mode: Direct Prediction vs Residual Correction
- Leak-Free validation strategies: Temporal Holdout, Watershed Holdout, Walk-Forward CV
- Mode FAST/DEV vs FULL TRAINING
- Live progress, duration, artifact bundling
"""

import os
import streamlit as st
import pandas as pd

from src.core.dataset_generator import get_dataset
from src.ui.components import render_hardware_analyzer, render_synthetic_data_badge
from src.core.training.trainer import MultiScaleTrainer
from src.core.features.schema import TARGET_REGISTRY, get_default_feature_schema
from src.utils.config import DATASET_RAW_PATH, ARTIFACTS_DIR
from src.infrastructure.auth import Permission


def render():
    st.header("⚙️ 3. Entrenamiento de Modelos de Inteligencia Artificial")
    st.caption("🏷️ **[CRISP-DM: Modeling]**")
    render_synthetic_data_badge()

    st.markdown("""
    Configura y entrena la batería de **3 algoritmos tradicionales y 2 arquitecturas híbridas**.
    La partición de datos implementa **prevención estricta de Data Leakage** temporal o espacial.
    Al finalizar, el sistema exporta automáticamente los **Artifact Bundles** completos para su integración con FastAPI.
    """)

    df = get_dataset()

    # 1. Configuración de Target y Modo de Aprendizaje
    st.subheader("🎯 1. Target y Modo de Aprendizaje")
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        target_options = list(TARGET_REGISTRY.keys())
        target_labels = {
            "monthly_runoff_mm": "Escorrentía Mensual (monthly_runoff_mm) [mm/mes]",
            "monthly_streamflow_m3s": "Caudal de Desembocadura (monthly_streamflow_m3s) [m³/s]",
            "maize_yield_t_ha": "Rendimiento de Grano de Maíz (maize_yield_t_ha) [t/ha]"
        }
        selected_target = st.selectbox(
            "Seleccionar Variable Objetivo (Target):",
            options=target_options,
            format_func=lambda x: target_labels.get(x, x),
            index=0
        )

    with col_t2:
        mode_options = ["direct", "residual"] if selected_target != "maize_yield_t_ha" else ["direct"]
        mode_labels = {
            "direct": "Modo A: Direct Prediction [Target = f(Clima, FSPM, Suelo, Campo)]",
            "residual": "Modo B: Residual Correction [Residual = Observed - SWAT_baseline]"
        }
        selected_mode = st.selectbox(
            "Modo de Aprendizaje:",
            options=mode_options,
            format_func=lambda x: mode_labels.get(x, x),
            index=0
        )

    if selected_mode == "residual":
        st.info("💡 **Modo B (Residual Correction) Activo**: El modelo aprenderá el error sistemático del SWAT+ estándar no acoplado, permitiendo evaluar si la información multiescala planta-campo agrega señal predictiva neta.")

    st.markdown("---")

    # 2. Estrategia de Validación y Prevención de Data Leakage
    st.subheader("🛡️ 2. Estrategia de Validación (Prevención de Data Leakage)")
    col_v1, col_v2, col_v3 = st.columns(3)

    with col_v1:
        val_strategy = st.selectbox(
            "Estrategia de Split:",
            options=["temporal", "watershed", "timeseries_cv"],
            format_func=lambda x: {
                "temporal": "Temporal Holdout (Entrenar pasado, evaluar futuro)",
                "watershed": "Spatial Holdout (Entrenar cuencas A, evaluar cuenca B)",
                "timeseries_cv": "TimeSeries Walk-Forward (Ventana expansiva)"
            }[x]
        )

    with col_v2:
        if val_strategy == "watershed":
            holdout_ws = st.selectbox("Cuenca de Prueba no vista (Holdout):", df["watershed_id"].unique(), index=len(df["watershed_id"].unique())-1)
        else:
            holdout_ws = None
            test_pct = st.slider("Porcentaje de Datos de Prueba (Test Ratio)", 0.15, 0.35, 0.25, 0.05)

    with col_v3:
        random_seed = st.number_input("Semilla de Reproducibilidad (Seed):", min_value=1, max_value=9999, value=42)

    st.markdown("---")

    # 3. Selección de Modelos y Modo de Cómputo
    st.subheader("🧠 3. Modelos & Recursos de Cómputo")
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("**Modelos a Entrenar (3 Tradicionales + 2 Híbridos):**")
        use_rf = st.checkbox("🌲 Random Forest Regressor", value=True)
        use_xgb = st.checkbox("⚡ XGBoost Regressor", value=True)
        use_svr = st.checkbox("📐 Support Vector Regression (SVR)", value=True)
        use_cnn_lstm = st.checkbox("🧬 CNN-LSTM Hybrid (Deep Learning)", value=True)
        use_ae_rf = st.checkbox("🔬 LSTM Autoencoder + Random Forest (Híbrido)", value=True)

        selected_models_list = []
        if use_rf: selected_models_list.append("Random Forest")
        if use_xgb: selected_models_list.append("XGBoost")
        if use_svr: selected_models_list.append("SVR")
        if use_cnn_lstm: selected_models_list.append("CNN-LSTM")
        if use_ae_rf: selected_models_list.append("LSTM Autoencoder")

    with col_m2:
        st.markdown("**Modo de Entrenamiento:**")
        training_profile = st.radio(
            "Perfil de Hiperparámetros:",
            ["FAST / DEVELOPMENT (Optimizado para CPU rápido)", "FULL TRAINING (Convergencia completa)"],
            index=0
        )
        is_fast = "FAST" in training_profile
        tune_params = False
        if not is_fast:
            tune_params = st.checkbox("🔍 Búsqueda de Hiperparámetros (Train + Val Tuning)", value=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🖥️ Escanear Recursos de Cómputo (CPU / GPU)", use_container_width=True):
            render_hardware_analyzer()

    st.markdown("---")

    # 4. Botón Lanzador de Entrenamiento
    st.subheader("🚀 4. Ejecutar Pipeline de Entrenamiento")
    st.markdown("Al hacer clic, se entrenarán los modelos seleccionados, se evaluarán métricas hidrológicas (RMSE, NSE, PBIAS) y se registrará el Modelo Campeón.")

    current_user = st.session_state.get("auth_user")
    if current_user and not current_user.can(Permission.RUN_TRAINING):
        st.warning(f"🔒 **Modo de Sólo Lectura**: El usuario actual (`{current_user.username}`) con rol `{current_user.role.value}` no tiene permisos de entrenamiento. Cambie al rol `RESEARCHER` o `ADMIN` en la barra lateral.")
        return

    if st.button("▶️ Iniciar Entrenamiento Multiescala", type="primary", use_container_width=True):
        if not selected_models_list:
            st.error("Debes seleccionar al menos un modelo para entrenar.")
            return

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)

        with st.spinner("Entrenando modelos y exportando artefactos..."):
            trainer = MultiScaleTrainer(
                target_name=selected_target,
                learning_mode=selected_mode,
                validation_strategy=val_strategy,
                holdout_watershed=holdout_ws,
                fast_dev_mode=is_fast,
                tune_hyperparameters=tune_params,
                random_seed=random_seed
            )

            res = trainer.train(
                df,
                selected_models=selected_models_list,
                progress_callback=update_progress
            )

        progress_bar.progress(1.0)
        status_text.text(f"¡Entrenamiento finalizado en {res['duration_seconds']} segundos!")

        st.success(f"🏆 **Modelo Campeón Seleccionado**: `{res['champion_model_name']}`")
        st.info(f"📦 Artefacto exportado en: `{res['champion_dir']}` (Contrato `feature_schema.json`, `model`, `preprocessing.joblib`, `metadata.json`)")

        # Tabla de métricas
        st.subheader("📊 Métricas de Validación Obtenidas")
        rows = []
        for name, d in res["results"].items():
            m = d["metrics"]
            rows.append({
                "Modelo": name,
                "R² Score": m.get("r2", 0.0),
                "RMSE": m.get("rmse", 0.0),
                "MAE": m.get("mae", 0.0),
                "NSE (Nash)": m.get("nse", "N/A"),
                "PBIAS (%)": f"{m.get('pbias', 0.0):.2f}%" if "pbias" in m else "N/A",
                "Directorio de Artefactos": d["artifact_dir"]
            })

        st.dataframe(pd.DataFrame(rows).sort_values(by="R² Score", ascending=False), use_container_width=True)

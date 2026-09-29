"""Tab 3: leak-free model training for the selected dataset source."""

import streamlit as st
import pandas as pd

from src.core.features.schema import TARGET_REGISTRY, get_available_feature_schema, get_default_feature_schema
from src.core.training.trainer import MultiScaleTrainer
from src.ui.components import get_active_dataset, render_hardware_analyzer, render_synthetic_data_badge
from src.utils.config import ARTIFACTS_DIR
from src.infrastructure.auth import Permission


MIN_REAL_TRAINING_ROWS = 24


def _target_label(target: str) -> str:
    return {
        "monthly_runoff_mm": "Escorrentía mensual [mm/mes]",
        "monthly_streamflow_m3s": "Caudal mensual [m³/s]",
        "maize_yield_t_ha": "Rendimiento de maíz [t/ha]",
    }.get(target, target)


def render():
    st.header("⚙️ 3. Entrenamiento de Modelos de Inteligencia Artificial")
    st.caption("🏷️ **[CRISP-DM: Modeling]**")
    df, metadata, _ = get_active_dataset()
    render_synthetic_data_badge()
    is_synthetic = bool(metadata.get("is_synthetic_training_data", False))
    available_targets = [target for target in TARGET_REGISTRY if target in df.columns and df[target].notna().any()]
    if not is_synthetic and not metadata.get("is_observation", False):
        # South Fork contains modeled crop state, but no observational target
        # suitable for claiming an agricultural performance model.
        available_targets = [target for target in available_targets if target != "maize_yield_t_ha"]
    if not available_targets:
        st.warning("Este dataset no contiene un objetivo válido para entrenamiento.")
        return

    st.markdown(
        "Configura los algoritmos existentes. El contrato de entrada se construye con variables completas del "
        "dataset seleccionado y el preprocesador se ajusta únicamente con TRAIN."
    )
    st.caption(f"Dataset activo: `{metadata.get('dataset_id', 'n/d')}` | Filas preparadas: `{len(df):,}`")

    st.subheader("🎯 1. Target y modo de aprendizaje")
    left, right = st.columns(2)
    with left:
        selected_target = st.selectbox(
            "Seleccionar variable objetivo",
            options=available_targets,
            format_func=_target_label,
        )
    with right:
        residual_available = is_synthetic and selected_target != "maize_yield_t_ha"
        mode_options = ["direct", "residual"] if residual_available else ["direct"]
        selected_mode = st.selectbox(
            "Modo de aprendizaje",
            options=mode_options,
            format_func=lambda mode: "Modo A: predicción directa" if mode == "direct" else "Modo B: corrección residual SWAT+",
        )
    if not is_synthetic and selected_target == "maize_yield_t_ha":
        st.info("El objetivo agrícola se mantiene preparado para futuras observaciones compatibles, pero no se entrena con esta corrida simulada.")

    try:
        schema = (
            get_default_feature_schema(mode=selected_mode, include_baseline=selected_mode == "residual", target_name=selected_target)
            if is_synthetic
            else get_available_feature_schema(df, target_name=selected_target, mode=selected_mode)
        )
    except (KeyError, ValueError) as exc:
        st.error(f"No es posible construir el contrato de características: {exc}")
        return

    st.dataframe(
        pd.DataFrame([
            {"orden": index + 1, "variable": feature.name, "unidad": feature.unit, "escala": feature.scale_level}
            for index, feature in enumerate(schema.features)
        ]),
        width="stretch",
        hide_index=True,
    )
    st.caption("No se incluyen variables ausentes o incompletas y el objetivo nunca se incorpora como entrada.")

    if not is_synthetic and len(df) < MIN_REAL_TRAINING_ROWS:
        st.warning(
            f"Entrenamiento bloqueado para esta corrida: hay {len(df)} muestras mensuales y se requieren al menos "
            f"{MIN_REAL_TRAINING_ROWS} para una partición temporal mínima. Los 12 meses de 2019 no permiten "
            "validar con solidez modelos complejos; incorpora periodos compatibles sin mezclar corridas distintas."
        )
        st.info("El contrato y las transformaciones están listos. No se exporta un bundle con evidencia insuficiente.")
        return

    st.markdown("---")
    st.subheader("🛡️ 2. Estrategia de validación")
    v1, v2, v3 = st.columns(3)
    with v1:
        val_strategy = st.selectbox(
            "Estrategia de split",
            options=["temporal", "watershed", "timeseries_cv"],
            format_func=lambda value: {
                "temporal": "Temporal 3-way (pasado → futuro)",
                "watershed": "Spatial holdout por cuenca",
                "timeseries_cv": "Walk-forward (adaptado a 3-way)",
            }[value],
        )
    with v2:
        if val_strategy == "watershed":
            watersheds = list(df["watershed_id"].dropna().unique()) if "watershed_id" in df else []
            if len(watersheds) < 3:
                st.info("No hay tres cuencas independientes; se usará partición temporal.")
                holdout_ws = None
            else:
                holdout_ws = st.selectbox("Cuenca de prueba no vista", watersheds, index=len(watersheds) - 1)
            test_pct = 0.20
        else:
            holdout_ws = None
            test_pct = st.slider("Porcentaje de test", 0.15, 0.35, 0.25, 0.05)
    with v3:
        random_seed = st.number_input("Semilla", min_value=1, max_value=9999, value=42)

    st.subheader("🧠 3. Modelos y recursos")
    m1, m2 = st.columns(2)
    with m1:
        use_rf = st.checkbox("🌲 Random Forest Regressor", value=True)
        use_xgb = st.checkbox("⚡ XGBoost Regressor", value=True)
        use_svr = st.checkbox("📐 Support Vector Regression (SVR)", value=True)
        use_cnn_lstm = st.checkbox("🧬 CNN-LSTM Hybrid", value=is_synthetic)
        use_ae_rf = st.checkbox("🔬 LSTM Autoencoder + Random Forest", value=is_synthetic)
        selected_models = [
            name for enabled, name in [
                (use_rf, "Random Forest"), (use_xgb, "XGBoost"), (use_svr, "SVR"),
                (use_cnn_lstm, "CNN-LSTM"), (use_ae_rf, "LSTM Autoencoder"),
            ] if enabled
        ]
    with m2:
        profile = st.radio("Perfil de hiperparámetros", ["FAST / DEVELOPMENT", "FULL TRAINING"], index=0)
        is_fast = profile.startswith("FAST")
        tune_params = st.checkbox("Búsqueda de hiperparámetros (Train + Val)", value=not is_fast) if not is_fast else False
        if st.button("🖥️ Escanear recursos de cómputo"):
            render_hardware_analyzer()

    st.subheader("🚀 4. Ejecutar pipeline")
    current_user = st.session_state.get("auth_user")
    if current_user and not current_user.can(Permission.RUN_TRAINING):
        st.warning("El usuario actual no tiene permisos de entrenamiento.")
        return
    if st.button("▶️ Iniciar entrenamiento multiescala", type="primary"):
        if not selected_models:
            st.error("Selecciona al menos un modelo.")
            return
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(pct, message):
            progress_bar.progress(pct)
            status_text.text(message)

        trainer = MultiScaleTrainer(
            target_name=selected_target,
            learning_mode=selected_mode,
            validation_strategy=val_strategy,
            holdout_watershed=holdout_ws,
            test_ratio=test_pct,
            fast_dev_mode=is_fast,
            tune_hyperparameters=tune_params,
            random_seed=random_seed,
            artifact_base_dir=ARTIFACTS_DIR,
            schema=schema,
            dataset_metadata=metadata,
        )
        with st.spinner("Entrenando modelos y exportando bundles..."):
            result = trainer.train(df, selected_models=selected_models, progress_callback=update_progress)
        st.success(f"🏆 Modelo campeón: `{result['champion_model_name']}`")
        st.info(f"Bundle exportado en `{result['champion_dir']}` con procedencia `{metadata.get('artifact_classification')}`.")
        rows = []
        for name, details in result["results"].items():
            metrics = details["metrics"]
            rows.append({
                "Modelo": name,
                "R²": metrics.get("r2"),
                "RMSE": metrics.get("rmse"),
                "MAE": metrics.get("mae"),
                "NSE": metrics.get("nse"),
                "PBIAS (%)": metrics.get("pbias"),
                "Bundle": details["artifact_dir"],
            })
        st.dataframe(pd.DataFrame(rows), width="stretch")

"""
Tab 5: Model Benchmarking & Statistical Validation — Plant-to-Watershed AI Lab.
Compares traditional vs hybrid models on hydrological metrics (RMSE, NSE, PBIAS, MAE, R²).
Conducts Wilcoxon Signed-Rank Test, Bootstrap 95% Confidence Intervals,
and objective scientific evaluation of H0 vs H1.
Includes Sobol Global Sensitivity specification.
"""

import os
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.core.dataset_generator import get_dataset
from src.core.training.splitters import get_three_way_split
from src.core.inference.bundle import ModelBundle
from src.ui.components import render_synthetic_data_badge
from src.core.statistics_core import (
    get_benchmark_df,
    create_scatter_1to1_plot,
    create_residual_plot,
    load_training_history,
    generate_academic_interpretation
)
from src.core.statistics.hypothesis_tests import (
    perform_wilcoxon_test,
    compute_bootstrap_ci,
    perform_ks_test,
    evaluate_scientific_hypothesis
)
from src.core.statistics.sobol_sensitivity import SobolSensitivityAnalysis


def render():
    st.header("🔬 5. Model Benchmarking & Validación Estadística")
    st.caption("🏷️ **[CRISP-DM: Evaluation & Hypothesis Testing]**")
    render_synthetic_data_badge()

    st.markdown("""
    En esta sección se evalúa con **rigor metodológico** el desempeño de los modelos tradicionales frente a los híbridos,
    y se contrasta formalmente la **Hipótesis Científica Central** del gemelo digital acoplado.
    """)

    # 1. Tabla de Benchmarking
    st.subheader("📋 1. Tabla Comparativa de Rendimiento Hidrológico")
    df_bm = get_benchmark_df()

    st.dataframe(
        df_bm.style.highlight_max(subset=["R² Score", "NSE (Nash)"], color="#064E3B")
                   .highlight_min(subset=["RMSE", "MAE"], color="#064E3B"),
        use_container_width=True
    )

    # 2. Gráficos Comparativos (NSE, RMSE, R²)
    c1, c2, c3 = st.columns(3)
    with c1:
        fig_nse = px.bar(
            df_bm, x="Modelo", y="NSE (Nash)", color="NSE (Nash)",
            color_continuous_scale="Teal", title="Eficiencia Hidrológica (NSE — Nash-Sutcliffe)",
            template="plotly_dark"
        )
        fig_nse.update_layout(height=360, yaxis=dict(range=[0.8, 1.0]))
        st.plotly_chart(fig_nse, use_container_width=True)

    with c2:
        fig_rmse = px.bar(
            df_bm, x="Modelo", y="RMSE", color="RMSE",
            color_continuous_scale="Reds_r", title="Error Cuadrático (RMSE — menor es mejor)",
            template="plotly_dark"
        )
        fig_rmse.update_layout(height=360)
        st.plotly_chart(fig_rmse, use_container_width=True)

    with c3:
        fig_pbias = px.bar(
            df_bm, x="Modelo", y="PBIAS (%)", color="PBIAS (%)",
            color_continuous_scale="Viridis", title="Sesgo Porcentual (PBIAS — ideal: 0%)",
            template="plotly_dark"
        )
        fig_pbias.update_layout(height=360)
        st.plotly_chart(fig_pbias, use_container_width=True)

    st.markdown("---")

    # 3. Evaluación Formal de la Hipótesis Científica (H0 vs H1)
    st.subheader("⚖️ 2. Evaluación de la Hipótesis Científica (H0 vs H1)")
    st.markdown("""
    <div class="tech-box">
        <b>H0 (Hipótesis Nula)</b>: El acoplamiento planta-cuenca <b>no mejora</b> la predicción de escorrentía respecto a SWAT+ estándar con parámetros de cultivo promedio.<br/>
        <b>H1 (Hipótesis Alternativa)</b>: El gemelo multi-escala <b>reduce el RMSE mensual en al menos un 15%</b> respecto a SWAT+ estándar y representa mejor la variabilidad espacial.
    </div>
    """, unsafe_allow_html=True)

    df = get_dataset()
    champ_path = "artifacts/monthly_runoff_mm/champion"
    bundle = None
    if os.path.exists(champ_path):
        try:
            bundle = ModelBundle.load(champ_path)
        except Exception as e:
            st.warning(f"No se pudo cargar el artefacto del modelo campeón: {e}")
            bundle = None

    if bundle is not None:
        val_strategy = bundle.metadata.get("validation_strategy", "temporal")
        train_idx, val_idx, test_idx, _ = get_three_way_split(df, strategy=val_strategy)
        test_df = df.iloc[test_idx].copy()
        y_true = test_df["monthly_runoff_mm"].values
        y_swat = test_df["swat_baseline_runoff_mm"].values

        # Inferencia real desde el bundle campeón
        pred_res = bundle.predict(test_df)
        pred_vals = pred_res.get("values", [pred_res.get("value", 0.0)])
        y_twin = np.array(pred_vals, dtype=np.float64)

        # Alinear longitud de arrays en caso de reducción por ventanas temporales
        n_eval = min(len(y_true), len(y_swat), len(y_twin))
        y_true = y_true[-n_eval:]
        y_swat = y_swat[-n_eval:]
        y_twin = y_twin[-n_eval:]

        st.info(f"💡 **Inferencia Real**: Predicciones generadas por el modelo campeón `{bundle.metadata.get('model_name')}` sobre la partición TEST (n={n_eval} muestras evaluadas).")
        st.caption("DEMO / SYNTHETIC DATA — Evaluación ilustrativa con datos sintéticos generados para el gemelo digital acoplado Zea mays / SWAT+.")

        hyp_res = evaluate_scientific_hypothesis(y_true, y_swat, y_twin)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric(label="RMSE SWAT+ Estándar", value=f"{hyp_res['rmse_swat_baseline']:.2f} mm")
        with k2:
            st.metric(label="RMSE Gemelo Digital (Twin)", value=f"{hyp_res['rmse_twin']:.2f} mm")
        with k3:
            st.metric(label="Reducción del RMSE", value=f"{hyp_res['rmse_reduction_pct']:.1f}%", delta="Objetivo >= 15%")
        with k4:
            st.metric(label="p-valor Wilcoxon", value=f"{hyp_res['wilcoxon']['p_value']:.4e}")

        # Verdict Card
        if hyp_res["rejects_h0"]:
            st.success(f"✅ **Veredicto Estadístico**: {hyp_res['verdict']}\n\n{hyp_res['narrative']}")
        else:
            st.warning(f"⚠️ **Veredicto Estadístico**: {hyp_res['verdict']}\n\n{hyp_res['narrative']}")

        st.markdown("---")

        # 4. Intervalos de Confianza Bootstrap & Kolmogorov-Smirnov
        st.subheader("📊 3. Intervalos de Confianza Bootstrap (95%) & Kolmogorov-Smirnov")
        col_b1, col_b2 = st.columns(2)

        with col_b1:
            boot = hyp_res["bootstrap"]
            st.markdown(f"""
            <div class="tech-box">
                <h4>Intervalo de Confianza Bootstrap para ΔRMSE:</h4>
                <ul>
                    <li><b>Iteraciones Bootstrap</b>: {boot['n_bootstraps']} re-muestreos con reemplazo</li>
                    <li><b>Media de ΔRMSE</b>: {boot['mean_delta_rmse']:.3f} mm</li>
                    <li><b>IC 95% Inferior</b>: {boot['ci_lower']:.3f} mm</li>
                    <li><b>IC 95% Superior</b>: {boot['ci_upper']:.3f} mm</li>
                    <li><b>Mejora Estrictamente Positiva</b>: {'Sí (IC > 0)' if boot['strictly_positive_improvement'] else 'No'}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col_b2:
            ks = hyp_res["ks_test"]
            st.markdown(f"""
            <div class="tech-box">
                <h4>Prueba Kolmogorov-Smirnov (Residuos Twin vs SWAT):</h4>
                <ul>
                    <li><b>Estadístico D de KS</b>: {ks['ks_stat']:.4f}</li>
                    <li><b>p-valor KS</b>: {ks['p_value']:.4e}</li>
                    <li><b>Distribución de Errores Distinta</b>: {'Sí (p < 0.05)' if ks['distributions_differ'] else 'No'}</li>
                    <li><b>Interpretación</b>: Confirma si la estructura del error del modelo sustituto es significativamente diferente de la línea base mecanística.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        # Gráficos 1:1 y Residuos
        c_scat, c_res = st.columns(2)
        with c_scat:
            fig_1to1 = create_scatter_1to1_plot(y_true.tolist(), y_twin.tolist(), model_name=f"Campeón ({bundle.metadata.get('model_name')})", unit="mm/mes")
            st.plotly_chart(fig_1to1, use_container_width=True)

        with c_res:
            fig_res = create_residual_plot(y_true.tolist(), y_twin.tolist(), unit="mm/mes")
            st.plotly_chart(fig_res, use_container_width=True)
    else:
        st.warning("⚠️ No se encontró un modelo campeón entrenado en `artifacts/monthly_runoff_mm/champion/`. Por favor, ejecute el entrenamiento en la pestaña **4. Model Training** para generar las predicciones reales del gemelo digital.")
        st.caption("DEMO / SYNTHETIC DATA — Evaluación ilustrativa con datos sintéticos.")

    st.markdown("---")

    # 5. Sobol Global Sensitivity Analysis (Contract & Setup)
    st.subheader("📐 4. Análisis de Sensibilidad Global de Sobol (FSPM ➔ SWAT+)")
    st.markdown("""
    El método de Sobol descompone la varianza de la salida para cuantificar qué fracción de la incertidumbre en la escorrentía
    se debe a parámetros fisiológicos individuales del maíz frente a propiedades del suelo de la cuenca.
    """)

    sobol_mgr = SobolSensitivityAnalysis()
    sobol_exec = sobol_mgr.execute_sampling_and_analysis()

    st.info(f"📌 **Estado del Módulo de Sobol**: `{sobol_exec['status']}` — {sobol_exec['message']}")

    with st.expander("🔍 Ver Espacio de Parámetros de Sobol Especificado"):
        param_table = pd.DataFrame(sobol_exec["parameter_space"]["parameters"])
        st.dataframe(param_table, use_container_width=True)

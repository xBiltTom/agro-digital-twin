"""
Pestaña 4: Estadísticas & Benchmarking de Modelos — AgroTwin-AI.
Comparativa detallada de métricas R2, RMSE, MAE, NSE, gráficos 1:1 y curvas de error.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.core.statistics_core import (
    get_benchmark_df,
    create_scatter_1to1_plot,
    create_residual_plot,
    load_training_history
)
from src.core.dataset_generator import get_dataset
from src.core.inference import predict_stress_and_irrigation

def render():
    st.header("📊 4. Estadísticas y Benchmarking Comparativo de Modelos")
    st.markdown("""
    En esta sección se comparan exhaustivamente las **5 arquitecturas de Redes Neuronales** evaluadas bajo validación cruzada ($K$-Fold).
    Analiza la precisión predictiva, los coeficientes hidrológicos de Nash-Sutcliffe y la distribución de errores residuales.
    """)
    
    # 1. Tabla de Benchmarking
    st.subheader("📋 1. Tabla de Métricas de Rendimiento (K-Fold CV)")
    df_bm = get_benchmark_df()
    
    st.dataframe(
        df_bm.style.highlight_max(subset=["R² (Score)", "NSE (Nash-Sutcliffe)"], color="#064E3B")
                   .highlight_min(subset=["RMSE", "MAE"], color="#064E3B"),
        use_container_width=True
    )
    
    # 2. Gráficos Comparativos de Barras (R2 y RMSE)
    c1, c2 = st.columns(2)
    with c1:
        fig_r2 = px.bar(
            df_bm,
            x="Modelo",
            y="R² (Score)",
            color="R² (Score)",
            color_continuous_scale="Teal",
            title="Comparativa de Coeficiente de Determinación (R²)",
            template="plotly_dark"
        )
        fig_r2.update_layout(yaxis=dict(range=[0.8, 1.0]), height=380)
        st.plotly_chart(fig_r2, use_container_width=True)
        
    with c2:
        fig_rmse = px.bar(
            df_bm,
            x="Modelo",
            y="RMSE",
            color="RMSE",
            color_continuous_scale="Reds_r",
            title="Comparativa de Error Cuadrático Medio (RMSE — menor es mejor)",
            template="plotly_dark"
        )
        fig_rmse.update_layout(height=380)
        st.plotly_chart(fig_rmse, use_container_width=True)
        
    st.markdown("---")
    
    # 3. Gráficos 1:1 de Dispersión y Errores Residuales
    st.subheader("🎯 2. Validación 1:1 y Distribución Residual")
    
    # Generar predicciones de muestra para visualización
    df_data = get_dataset()
    sample_sub = df_data.sample(min(400, len(df_data)), random_state=42)
    y_true_sample = sample_sub["cwsi_stress_index"].tolist()
    
    # Generar predicción del modelo
    y_pred_sample = []
    for _, row in sample_sub.iterrows():
        p = predict_stress_and_irrigation(row.to_dict())
        y_pred_sample.append(p["cwsi"])
        
    col_scat, col_res = st.columns(2)
    with col_scat:
        fig_1to1 = create_scatter_1to1_plot(y_true_sample, y_pred_sample, model_name="Modelo Campeón")
        st.plotly_chart(fig_1to1, use_container_width=True)
        
    with col_res:
        fig_res = create_residual_plot(y_true_sample, y_pred_sample)
        st.plotly_chart(fig_res, use_container_width=True)
        
    st.markdown("---")
    
    # 4. Curvas de Aprendizaje del Historial
    st.subheader("📈 3. Curvas de Convergencia (Pérdida por Época)")
    history = load_training_history()
    curves = history.get("training_curves", {})
    
    if curves:
        model_to_plot = st.selectbox("Seleccionar modelo para ver curvas de aprendizaje:", list(curves.keys()))
        fold_runs = curves.get(model_to_plot, [])
        if fold_runs:
            fig_loss = go.Figure()
            # Promediar folds
            n_epochs = len(fold_runs[0].get("loss", []))
            epochs_x = list(range(1, n_epochs + 1))
            
            mean_loss = np.mean([f["loss"] for f in fold_runs], axis=0)
            mean_val_loss = np.mean([f["val_loss"] for f in fold_runs], axis=0)
            
            fig_loss.add_trace(go.Scatter(x=epochs_x, y=mean_loss, mode="lines", name="Pérdida Entrenamiento (Loss)", line=dict(color="#10B981", width=2)))
            fig_loss.add_trace(go.Scatter(x=epochs_x, y=mean_val_loss, mode="lines", name="Pérdida Validación (Val_Loss)", line=dict(color="#F59E0B", width=2, dash="dash")))
            
            fig_loss.update_layout(
                title=f"Curva de Pérdida Promedio en K-Fold — {model_to_plot}",
                xaxis_title="Época",
                yaxis_title="MSE Loss",
                template="plotly_dark",
                height=400
            )
            st.plotly_chart(fig_loss, use_container_width=True)
    else:
        st.info("💡 Ejecuta el entrenamiento en la **Pestaña 2** para generar las curvas dinámicas de convergencia fold a fold.")

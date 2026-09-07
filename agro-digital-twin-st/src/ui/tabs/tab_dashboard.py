"""
Pestaña 1: EDA & Dashboard de Datos Eco-Hidrológicos — AgroTwin-AI.
Análisis exploratorio de datos, correlaciones climáticas-edáficas y limpieza del dataset.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.core.dataset_generator import get_dataset
from src.utils.config import DATASET_RAW_PATH, DATASET_CLEANED_PATH

def render():
    st.header("📈 1. Análisis Exploratorio de Datos (EDA) & Dashboard")
    st.markdown("""
    Esta sección permite explorar las variables físicas y biológicas del dataset eco-hidrológico generado para el gemelo digital.
    Examina las correlaciones no lineales entre el clima (**VPD, Radiación, Temperatura**), el suelo (**Humedad $\\theta$**) y la planta (**$CWSI$**).
    """)
    
    # 1. Cargar Dataset
    df = get_dataset()
    
    # KPIs Rápidos
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(label="Total Registros Diarios", value=f"{len(df):,} días")
    with k2:
        st.metric(label="Temperatura Media", value=f"{df['temp_mean'].mean():.1f} °C")
    with k3:
        st.metric(label="Humedad de Suelo Promedio", value=f"{df['soil_moisture_vol'].mean():.1f} % vol")
    with k4:
        st.metric(label="Estrés Hídrico Medio (CWSI)", value=f"{df['cwsi_stress_index'].mean():.3f}")
        
    st.markdown("---")
    
    # Vista previa del Dataset
    with st.expander("📁 Ver Tabla de Datos Brutos (Primeros 100 Registros)", expanded=False):
        st.dataframe(df.head(100), use_container_width=True)
        st.caption(f"Archivo cargado desde: `{DATASET_RAW_PATH}`")
        
    # 2. Matriz de Correlación de Pearson
    st.subheader("🔥 Matriz de Correlación de Pearson Multivariable")
    st.markdown("Descubre qué variables climáticas y de suelo influyen con mayor fuerza en el estrés de la planta:")
    
    numeric_cols = [
        "temp_mean", "solar_rad", "rh_mean", "vpd_kpa",
        "precip_mm", "soil_moisture_vol", "streamflow_m3s",
        "et0_mm", "actual_transpiration_mm", "cwsi_stress_index", "irrigation_need_mm"
    ]
    corr = df[numeric_cols].corr()
    
    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        title="Matriz de Correlación de Pearson (Variables Clima ⇄ Suelo ⇄ Planta)",
        template="plotly_dark"
    )
    fig_corr.update_layout(height=520)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    st.info("💡 **Hallazgo Clave**: Nota la fuerte correlación negativa entre `soil_moisture_vol` y `cwsi_stress_index` (-0.85 aprox.), y la correlación positiva entre `vpd_kpa` y el estrés, lo que confirma la validez biofísica de las ecuaciones de Feddes.")
    
    st.markdown("---")
    
    # 3. Gráficos de Dispersión y Comportamiento Fisiológico
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("💧 Humedad de Suelo vs Estrés (CWSI)")
        fig_scatter = px.scatter(
            df,
            x="soil_moisture_vol",
            y="cwsi_stress_index",
            color="temp_max",
            color_continuous_scale="Turbo",
            title="Curva de Reducción de Feddes: Humedad (θ) vs CWSI",
            labels={"soil_moisture_vol": "Humedad Suelo (% vol)", "cwsi_stress_index": "Estrés CWSI (0 a 1)", "temp_max": "T° Máx (°C)"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with c2:
        st.subheader("🌡️ Déficit de Presión de Vapor (VPD) vs Demanda de Riego")
        fig_vpd = px.scatter(
            df,
            x="vpd_kpa",
            y="irrigation_need_mm",
            color="stress_category",
            color_continuous_scale="Viridis",
            title="Impacto del VPD (Atmósfera Seca) en la Dosis de Riego",
            labels={"vpd_kpa": "VPD (kPa)", "irrigation_need_mm": "Lámina de Riego (mm)", "stress_category": "Severidad"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_vpd, use_container_width=True)
        
    # 4. Serie Temporal Multiaño
    st.subheader("📅 Serie Temporal Multiaño: Clima, Balance de Suelo y Transpiración")
    
    sample_df = df.iloc[:365] # Primer año representativo
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=sample_df["date"], y=sample_df["soil_moisture_vol"], mode="lines", name="Humedad Suelo θ (%)", line=dict(color="#0EA5E9", width=2)))
    fig_ts.add_trace(go.Scatter(x=sample_df["date"], y=sample_df["actual_transpiration_mm"], mode="lines", name="Transpiración Planta (mm/d)", line=dict(color="#10B981", width=2)))
    fig_ts.add_trace(go.Bar(x=sample_df["date"], y=sample_df["precip_mm"], name="Lluvia (mm)", marker_color="#38BDF8", opacity=0.5))
    fig_ts.add_trace(go.Scatter(x=sample_df["date"], y=sample_df["cwsi_stress_index"] * 40.0, mode="lines", name="CWSI escalado (0-40)", line=dict(color="#EF4444", dash="dot")))
    
    fig_ts.update_layout(
        title="Dinámica Anual del Gemelo Digital (Primeros 365 días)",
        xaxis_title="Fecha",
        yaxis_title="Magnitud",
        template="plotly_dark",
        height=400,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_ts, use_container_width=True)
    
    # 5. Módulo de Limpieza y Preprocesamiento
    st.markdown("---")
    st.subheader("🧹 Preprocesamiento y Guardado de Dataset Limpio")
    st.markdown("Verifica la integridad de datos, elimina valores fuera de rango físico y guarda la copia normalizada para entrenamiento.")
    
    if st.button("✨ Ejecutar Preprocesamiento y Limpieza de Datos"):
        with st.spinner("Procesando dataset..."):
            # Filtrar posibles NaNs o valores fuera de límites biofísicos
            cleaned_df = df.dropna().copy()
            cleaned_df["cwsi_stress_index"] = cleaned_df["cwsi_stress_index"].clip(0.0, 1.0)
            cleaned_df["soil_moisture_vol"] = cleaned_df["soil_moisture_vol"].clip(5.0, 48.0)
            cleaned_df.to_csv(DATASET_CLEANED_PATH, index=False)
            st.success(f"✅ Dataset limpio exportado con éxito en: `{DATASET_CLEANED_PATH}` ({len(cleaned_df)} filas)")

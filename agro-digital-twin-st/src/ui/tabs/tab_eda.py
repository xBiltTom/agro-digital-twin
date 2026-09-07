"""
Tab 2: Exploratory Data Analysis (EDA) — Plant-to-Watershed AI Lab.
Explores multi-scale variables:
Precipitation, Temperature, Solar Radiation, Soil Moisture, Infiltration,
ET, LAI, Root Depth, Transpiration, Water Stress, Runoff, Streamflow, Maize Yield.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.core.dataset_generator import get_dataset
from src.ui.components import render_synthetic_data_badge


def render():
    st.header("📈 2. Análisis Exploratorio de Datos Multiescala (EDA)")
    st.caption("🏷️ **[CRISP-DM: Data Understanding]**")
    render_synthetic_data_badge()

    st.markdown("""
    Analiza la interconexión biofísica y ambiental entre las cuatro escalas:
    **Clima** ➔ **Suelo / HRU** ➔ **Planta FSPM (Maíz)** ➔ **Cuenca SWAT+**.
    """)

    df = get_dataset()

    # 1. Estadísticas Descriptivas y Missing Values
    st.subheader("📋 1. Resumen Estadístico & Calidad del Dataset")
    numeric_cols = [
        "precip_mm", "temp_mean_c", "solar_radiation", "soil_moisture",
        "infiltration_mm", "et_mm", "lai", "root_depth_m",
        "transpiration_mm", "water_stress", "swat_baseline_runoff_mm",
        "monthly_runoff_mm", "monthly_streamflow_m3s", "maize_yield_t_ha"
    ]

    c1, c2 = st.columns([3, 1])
    with c1:
        st.dataframe(df[numeric_cols].describe().T.round(2), use_container_width=True)
    with c2:
        missing_count = df.isnull().sum().sum()
        st.metric(label="Valores Nulos (NaN)", value=missing_count)
        st.metric(label="Total Columnas", value=len(df.columns))
        st.metric(label="Escenarios Climáticos", value=df["climate_scenario"].nunique())

    st.markdown("---")

    # 2. Matriz de Correlación Pearson
    st.subheader("🔥 2. Matriz de Correlación Multiescala (Pearson)")
    st.markdown("Observa la correlación entre variables fisiológicas individuales y las respuestas hidrológicas de cuenca:")

    corr = df[numeric_cols].corr()
    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        title="Correlaciones: Clima ⇄ Suelo ⇄ FSPM Maíz ⇄ Cuenca SWAT+",
        template="plotly_dark"
    )
    fig_corr.update_layout(height=550)
    st.plotly_chart(fig_corr, use_container_width=True)

    st.info("💡 **Anotación Científica**: Observa la alta correlación entre `precip_mm` y `monthly_runoff_mm` (+0.81 aprox.), así como el efecto regulador de `lai` y `root_depth_m` en la infiltración y amortiguación de caudales pico.")

    st.markdown("---")

    # 3. Relaciones Físicas Clave
    st.subheader("🌾 3. Relaciones Biofísicas Fundamentales")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**Precipitación vs Escorrentía Mensual (Runoff)**")
        fig_pr = px.scatter(
            df,
            x="precip_mm",
            y="monthly_runoff_mm",
            color="climate_scenario",
            size="lai",
            title="Precipitación vs Runoff (Tamaño: LAI del Maíz)",
            labels={"precip_mm": "Precipitación (mm)", "monthly_runoff_mm": "Escorrentía Mensual (mm)"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_pr, use_container_width=True)

    with col_g2:
        st.markdown("**Evapotranspiración (ET) vs Rendimiento de Maíz (Yield)**")
        # Filtrar registros de cosecha (octubre / yield > 0)
        df_harvest = df[df["maize_yield_t_ha"] > 0.0]
        fig_ey = px.scatter(
            df_harvest,
            x="et_mm",
            y="maize_yield_t_ha",
            color="management_scenario",
            title="Evapotranspiración vs Rendimiento de Grano (Cosecha)",
            labels={"et_mm": "ET de Campo (mm)", "maize_yield_t_ha": "Rendimiento (t/ha)"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_ey, use_container_width=True)

    st.markdown("---")

    # 4. Dinámica Temporal de la Serie
    st.subheader("📅 4. Serie Temporal Anual: Fenología de Maíz y Respuesta Hidrológica")
    ws_pick = st.selectbox("Seleccionar Cuenca para Visualización Temporal:", df["watershed_id"].unique())

    sub_ts = df[(df["watershed_id"] == ws_pick) & (df["climate_scenario"] == "Historical")].iloc[:48]

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Bar(x=sub_ts["date"], y=sub_ts["precip_mm"], name="Precipitación (mm)", marker_color="#38BDF8", opacity=0.4))
    fig_ts.add_trace(go.Scatter(x=sub_ts["date"], y=sub_ts["monthly_runoff_mm"], mode="lines+markers", name="Escorrentía Acoplada (mm)", line=dict(color="#EF4444", width=2)))
    fig_ts.add_trace(go.Scatter(x=sub_ts["date"], y=sub_ts["swat_baseline_runoff_mm"], mode="lines", name="SWAT+ Baseline (mm)", line=dict(color="#94A3B8", dash="dash")))
    fig_ts.add_trace(go.Scatter(x=sub_ts["date"], y=sub_ts["lai"] * 10.0, mode="lines", name="LAI Maíz (x10)", line=dict(color="#10B981", width=2)))

    fig_ts.update_layout(
        title=f"Dinámica Eco-Hidrológica en {ws_pick} (Primeros 4 Años Históricos)",
        xaxis_title="Fecha",
        yaxis_title="Magnitud",
        template="plotly_dark",
        height=420,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_ts, use_container_width=True)

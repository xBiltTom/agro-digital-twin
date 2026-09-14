"""
Tab 6: Scenario Simulator — Plant-to-Watershed AI Lab.
Simulates climate (Historical, SSP2-4.5, SSP5-8.5, +2°C, -15% Precip)
and management scenarios (Baseline, No-Till, Maize -> Sorghum) on Runoff & Yield.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.core.dataset_generator import get_dataset
from src.ui.components import render_synthetic_data_badge


def render():
    st.header("🌐 6. Simulador de Escenarios Climáticos y de Manejo")
    st.caption("🏷️ **[CRISP-DM: Data Preparation & Simulation Coupling]**")
    render_synthetic_data_badge()

    st.markdown("""
    Evalúa la resiliencia del agroecosistema y la cuenca hidrográfica bajo proyecciones de cambio climático (**SSP2-4.5, SSP5-8.5**)
    y prácticas de manejo adaptativo (**Labranza Cero / No-Till**, **Sustitución Maíz ➔ Sorgo**).
    """)

    df = get_dataset()

    # 1. Comparativa de Escenarios Climáticos
    st.subheader("🌡️ 1. Impacto del Cambio Climático en el Régimen Hidrológico")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        # Boxplot de Escorrentía por Escenario
        fig_box_ro = px.box(
            df,
            x="climate_scenario",
            y="monthly_runoff_mm",
            color="climate_scenario",
            title="Distribución de Escorrentía Mensual (Runoff) por Escenario Climático",
            labels={"climate_scenario": "Escenario", "monthly_runoff_mm": "Runoff (mm/mes)"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_box_ro, use_container_width=True)

    with col_s2:
        # Boxplot de Caudal Fluvial
        fig_box_flow = px.box(
            df,
            x="climate_scenario",
            y="monthly_streamflow_m3s",
            color="climate_scenario",
            title="Distribución de Caudal en Desembocadura (Streamflow)",
            labels={"climate_scenario": "Escenario", "monthly_streamflow_m3s": "Caudal (m³/s)"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_box_flow, use_container_width=True)

    st.markdown("---")

    # 2. Impacto de Prácticas de Manejo en el Rendimiento y el Estrés Hídrico
    st.subheader("🚜 2. Eficacia de Prácticas de Manejo Adaptativo")

    df_harvest = df[df["maize_yield_t_ha"] > 0.0]

    c_m1, c_m2 = st.columns(2)
    with c_m1:
        fig_mgmt_yield = px.histogram(
            df_harvest,
            x="maize_yield_t_ha",
            color="management_scenario",
            barmode="overlay",
            title="Rendimiento de Cosecha según Manejo",
            labels={"maize_yield_t_ha": "Rendimiento de Grano (t/ha)", "management_scenario": "Manejo"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_mgmt_yield, use_container_width=True)

    with c_m2:
        fig_stress = px.violin(
            df,
            x="management_scenario",
            y="water_stress",
            color="management_scenario",
            box=True,
            title="Distribución de Estrés Hídrico Vegetal según Manejo",
            labels={"management_scenario": "Manejo", "water_stress": "Índice de Estrés [0-1]"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_stress, use_container_width=True)

    # 3. Resumen Cuantitativo
    st.subheader("📋 Resumen Comparativo de Medias por Escenario")
    summary = df.groupby(["climate_scenario", "management_scenario"]).agg({
        "precip_mm": "mean",
        "temp_mean_c": "mean",
        "monthly_runoff_mm": "mean",
        "monthly_streamflow_m3s": "mean",
        "soil_moisture": "mean",
        "water_stress": "mean"
    }).round(2).reset_index()

    st.dataframe(summary, use_container_width=True)

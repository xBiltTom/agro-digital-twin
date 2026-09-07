"""
Tab 1: Dashboard & Data Explorer — Plant-to-Watershed AI Lab.
Shows active dataset, watersheds, HRUs, records, temporal range,
active target, champion model metrics, and prominent SYNTHETIC DATA status.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px

from src.core.dataset_generator import get_dataset
from src.ui.components import render_synthetic_data_badge
from src.core.statistics_core import load_training_history
from src.utils.config import DATASET_RAW_PATH


def render():
    st.header("📊 1. Dashboard & Data Explorer")
    st.caption("🏷️ **[CRISP-DM: Business / Domain Understanding]**")
    render_synthetic_data_badge()

    st.markdown("""
    Bienvenido al **Plant-to-Watershed AI Lab**. Este laboratorio acopla modelos biofísicos individuales de planta (**Maíz FSPM**)
    con la hidrología distribuida de cuenca (**SWAT+ con HRUs**) bajo forzantes climáticas históricas y proyecciones de cambio climático (**SSP2-4.5 y SSP5-8.5**).
    """)

    # 1. Cargar Dataset
    df = get_dataset()

    # 2. Historial de Entrenamiento y Modelo Campeón
    history = load_training_history()
    champ_name = history.get("champion_model_name", "No entrenado")
    champ_metrics = history.get("champion_metrics", {})
    target_active = history.get("target_name", "monthly_runoff_mm")

    # 3. KPIs Principales del Sistema
    st.subheader("📌 Estado del Sistema & Modelo Campeón")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(label="Dataset Activo", value="Corn Belt Synth", delta="Sintético")
    with k2:
        st.metric(label="Cuencas Monitoreadas", value=f"{df['watershed_id'].nunique()} Cuencas")
    with k3:
        st.metric(label="Unidades HRU", value=f"{df['hru_id'].nunique()} HRUs")
    with k4:
        st.metric(label="Registros Totales", value=f"{len(df):,} filas")
    with k5:
        st.metric(label="Rango Temporal", value=f"{df['date'].min().year} - {df['date'].max().year}")

    st.markdown("---")

    # 4. KPIs del Modelo Campeón Actual
    st.subheader(f"🏆 Métricas del Modelo Campeón (`{champ_name}`)")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Target Activo", value=target_active)
    with m2:
        st.metric(label="NSE (Nash-Sutcliffe)", value=f"{champ_metrics.get('nse', 0.0):.4f}" if "nse" in champ_metrics else "N/A")
    with m3:
        st.metric(label="RMSE", value=f"{champ_metrics.get('rmse', 0.0):.4f}" if "rmse" in champ_metrics else "N/A")
    with m4:
        st.metric(label="PBIAS (%)", value=f"{champ_metrics.get('pbias', 0.0):.2f}%" if "pbias" in champ_metrics else "N/A")
    with m5:
        st.metric(label="R² Score", value=f"{champ_metrics.get('r2', 0.0):.4f}" if "r2" in champ_metrics else "N/A")

    st.markdown("---")

    # 5. Explorador de Datos con Filtros
    st.subheader("🔍 Explorador de Registros Multiescala")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        ws_selected = st.multiselect(
            "Filtrar por Cuenca:",
            options=df["watershed_id"].unique(),
            default=df["watershed_id"].unique()
        )
    with col_f2:
        scen_selected = st.multiselect(
            "Filtrar por Escenario Climático:",
            options=df["climate_scenario"].unique(),
            default=df["climate_scenario"].unique()
        )
    with col_f3:
        mgmt_selected = st.multiselect(
            "Filtrar por Manejo:",
            options=df["management_scenario"].unique(),
            default=df["management_scenario"].unique()
        )

    filtered_df = df[
        (df["watershed_id"].isin(ws_selected)) &
        (df["climate_scenario"].isin(scen_selected)) &
        (df["management_scenario"].isin(mgmt_selected))
    ]

    st.dataframe(filtered_df.head(200), use_container_width=True)
    st.caption(f"Mostrando {min(200, len(filtered_df))} de {len(filtered_df)} registros filtrados desde `{DATASET_RAW_PATH}`")

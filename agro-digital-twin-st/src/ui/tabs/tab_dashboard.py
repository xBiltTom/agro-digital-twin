"""Tab 1: dashboard for the source selected in the laboratory sidebar."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.core.statistics_core import load_training_history
from src.ui.components import get_active_dataset, render_synthetic_data_badge


def render():
    st.header("📊 1. Dashboard & Explorador Multiescala")
    st.caption("🏷️ **[CRISP-DM: Business / Domain Understanding]**")
    df, metadata, _ = get_active_dataset()
    render_synthetic_data_badge()

    history = load_training_history()
    champ_name = history.get("champion_model_name", "No entrenado")
    champ_metrics = history.get("champion_metrics", {})
    target_active = history.get("target_name", "monthly_runoff_mm")

    st.markdown(
        "Este panel mantiene la navegación existente y muestra la cobertura del dataset seleccionado. "
        "Los resultados de simulación se identifican como tales y no se presentan como observaciones."
    )
    st.subheader("📌 1. Estado del dataset activo")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Fuente", "Demo sintética" if metadata.get("is_synthetic_training_data") else "Simulación")
    with k2:
        st.metric("Cuencas", int(df["watershed_id"].nunique()) if "watershed_id" in df else "n/d")
    with k3:
        st.metric("HRU / entidades", int(df["hru_id"].nunique()) if "hru_id" in df else "n/d")
    with k4:
        st.metric("Registros", f"{len(df):,}")
    with k5:
        if "date" in df:
            dates = pd.to_datetime(df["date"], errors="coerce").dropna()
            value = f"{dates.min().year} - {dates.max().year}" if not dates.empty else "n/d"
        else:
            value = "n/d"
        st.metric("Periodo", value)
    st.caption(f"**Procedencia:** {metadata.get('origin', 'n/d')} | **Clasificación:** {metadata.get('artifact_classification', 'n/d')}")

    st.subheader(f"🏆 2. Modelo campeón actual (`{champ_name}`)")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Target", target_active)
    with m2:
        st.metric("NSE", f"{champ_metrics.get('nse', 0.0):.4f}" if "nse" in champ_metrics else "N/A")
    with m3:
        st.metric("RMSE", f"{champ_metrics.get('rmse', 0.0):.4f}" if "rmse" in champ_metrics else "N/A")
    with m4:
        st.metric("PBIAS (%)", f"{champ_metrics.get('pbias', 0.0):.2f}" if "pbias" in champ_metrics else "N/A")
    with m5:
        st.metric("R²", f"{champ_metrics.get('r2', 0.0):.4f}" if "r2" in champ_metrics else "N/A")

    st.subheader("📈 3. Dinámica temporal")
    if "date" in df:
        plot_columns = [column for column in ["precip_mm", "et_mm", "monthly_runoff_mm", "monthly_streamflow_m3s"] if column in df]
        if plot_columns:
            time_df = df.copy()
            time_df["date"] = pd.to_datetime(time_df["date"], errors="coerce")
            time_df = time_df.dropna(subset=["date"]).groupby("date", as_index=True)[plot_columns].mean()
            st.line_chart(time_df, width="stretch")
        else:
            st.info("El dataset no contiene variables hidrológicas/climáticas canonicalizadas para este gráfico.")
    else:
        st.info("El dataset no contiene una serie temporal.")

    st.subheader("🌾 4. Relación de crecimiento vegetal")
    plant_columns = [column for column in ["lai", "water_stress", "maize_yield_t_ha", "fspm_biomass_g_plant"] if column in df]
    if len(plant_columns) >= 2:
        x_column, y_column = plant_columns[:2]
        relation = df[[x_column, y_column]].apply(pd.to_numeric, errors="coerce").dropna()
        if not relation.empty:
            st.plotly_chart(px.scatter(relation, x=x_column, y=y_column, template="plotly_dark"), width="stretch")
    else:
        st.info("No hay dos estados vegetales completos para comparar en este dataset.")

    st.subheader("🔍 5. Explorador de registros")
    filtered = df.copy()
    filter_columns = [column for column in ["watershed_id", "hru_id", "climate_scenario", "management_scenario"] if column in df]
    if filter_columns:
        filter_widgets = st.columns(min(3, len(filter_columns)))
        for index, column in enumerate(filter_columns):
            with filter_widgets[index % len(filter_widgets)]:
                values = list(df[column].dropna().unique())
                selected = st.multiselect(f"Filtrar por {column}", values, default=values, key=f"dashboard_filter_{column}")
                filtered = filtered[filtered[column].isin(selected)]
    st.dataframe(filtered.head(200), width="stretch")
    st.caption(f"Mostrando {min(200, len(filtered))} de {len(filtered)} registros.")

    with st.expander("💡 Guía del sistema", expanded=False):
        st.markdown(
            "- **Dashboard:** cobertura y controles del origen seleccionado.\n"
            "- **EDA:** variables, faltantes, correlaciones y series.\n"
            "- **Entrenamiento:** contratos estrictos, splits temporales y bundles.\n"
            "- **Inferencia, benchmarking, escenarios y reportes:** conservan sus funciones existentes."
        )

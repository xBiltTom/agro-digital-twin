"""Tab 2: exploratory analysis for synthetic and published result datasets."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.ui.components import get_active_dataset, render_synthetic_data_badge


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    excluded = {"is_synthetic", "is_observation"}
    return [
        column for column in df.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(df[column])
    ]


def render():
    st.header("📈 2. Análisis Exploratorio de Datos Multiescala (EDA)")
    st.caption("🏷️ **[CRISP-DM: Data Understanding]**")
    df, metadata, variable_catalog = get_active_dataset()
    render_synthetic_data_badge()
    numeric_cols = _numeric_columns(df)

    st.markdown(
        "Analiza la relación entre clima, balance hídrico, estados vegetales y resultados hidrológicos "
        "sin combinar corridas experimentales distintas."
    )

    st.subheader("📌 1. Origen, periodo y cobertura")
    info = st.columns(5)
    with info[0]:
        st.metric("Fuente", "Demo sintética" if metadata.get("is_synthetic_training_data") else "Simulación")
    with info[1]:
        st.metric("Registros", f"{len(df):,}")
    with info[2]:
        st.metric("Variables numéricas", len(numeric_cols))
    with info[3]:
        period = metadata.get("period", ["n/d", "n/d"])
        st.metric("Inicio", str(period[0]))
    with info[4]:
        st.metric("Fin", str(period[-1]))
    st.caption(f"**Procedencia:** {metadata.get('origin', 'no especificada')}")
    if metadata.get("limitations"):
        with st.expander("Limitaciones declaradas por el origen", expanded=False):
            for limitation in metadata["limitations"]:
                st.write(f"- {limitation}")

    st.subheader("📋 2. Variables, unidades y calidad")
    left, right = st.columns([3, 2])
    with left:
        if variable_catalog.empty:
            st.info("El origen no publicó un catálogo de variables.")
        else:
            st.dataframe(variable_catalog, width="stretch", height=280)
    with right:
        quality = pd.DataFrame({
            "variable": df.columns,
            "nulos": df.isna().sum().values,
            "completitud_%": (100.0 * df.notna().mean()).round(1).values,
        }).sort_values(["nulos", "variable"], ascending=[False, True])
        st.dataframe(quality, width="stretch", height=280)
        st.metric("Celdas nulas", f"{int(df.isna().sum().sum()):,}")
    st.caption("Los valores faltantes se muestran y se conservan; no se imputan silenciosamente.")

    st.subheader("📊 3. Resumen estadístico")
    if numeric_cols:
        st.dataframe(df[numeric_cols].describe().T.round(3), width="stretch")
    else:
        st.warning("No hay variables numéricas disponibles para describir.")

    st.subheader("🔥 4. Relaciones entre variables disponibles")
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr(numeric_only=True)
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            title="Correlaciones del dataset seleccionado",
            template="plotly_dark",
        )
        fig_corr.update_layout(height=520)
        st.plotly_chart(fig_corr, width="stretch")

        rel_left, rel_right = st.columns(2)
        with rel_left:
            x_column = st.selectbox("Variable explicativa", numeric_cols, index=0)
        with rel_right:
            y_options = [column for column in numeric_cols if column != x_column]
            y_column = st.selectbox("Variable de respuesta", y_options, index=0)
        relation_df = df[[x_column, y_column]].dropna()
        if relation_df.empty:
            st.warning("No hay pares completos para la relación seleccionada.")
        else:
            st.plotly_chart(
                px.scatter(
                    relation_df,
                    x=x_column,
                    y=y_column,
                    title=f"Relación: {x_column} vs {y_column}",
                    template="plotly_dark",
                ),
                width="stretch",
            )
    else:
        st.info("Se requieren al menos dos variables numéricas para calcular relaciones.")

    st.subheader("📅 5. Evolución temporal de clima, vegetación e hidrología")
    if "date" not in df.columns:
        st.warning("El dataset no tiene una columna temporal.")
        return
    temporal = df.copy()
    temporal["date"] = pd.to_datetime(temporal["date"], errors="coerce")
    temporal = temporal.dropna(subset=["date"])
    temporal_columns = [column for column in numeric_cols if column in temporal.columns]
    preferred = [
        "precip_mm", "temp_mean_c", "soil_moisture", "lai", "water_stress",
        "et_mm", "monthly_runoff_mm", "monthly_streamflow_m3s",
    ]
    default_columns = [column for column in preferred if column in temporal_columns][:4]
    selected_columns = st.multiselect(
        "Variables para la serie temporal",
        options=temporal_columns,
        default=default_columns or temporal_columns[: min(4, len(temporal_columns))],
    )
    if selected_columns:
        plot_df = temporal[["date", *selected_columns]].sort_values("date").set_index("date")
        st.line_chart(plot_df, width="stretch")
    else:
        st.info("Selecciona al menos una variable.")

    st.subheader("🧾 6. Muestra del dataset mensual preparado")
    st.dataframe(df.head(200), width="stretch", height=300)
    st.caption(f"Se muestran hasta 200 filas de {len(df):,}. Dataset: `{metadata.get('dataset_id', 'n/d')}`.")

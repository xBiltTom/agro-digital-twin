"""
Tab 1: Dashboard & Data Explorer — Plant-to-Watershed AI Lab.
Shows active dataset, watersheds, HRUs, records, temporal range,
active target, champion model metrics, interactive charts with descriptions,
and a comprehensive system guide explaining what each element and button does.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.core.dataset_generator import get_dataset
from src.ui.components import render_synthetic_data_badge
from src.core.statistics_core import load_training_history
from src.utils.config import DATASET_RAW_PATH


def render():
    st.header("📊 1. Dashboard & Explorador Multiescala")
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
    st.subheader("📌 1. Estado del Sistema & Parámetros Generales")
    st.markdown("Muestra la cobertura espacial, temporal y volumétrica del gemelo digital activo en el entorno:")

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
    st.subheader(f"🏆 2. Métricas del Modelo Campeón Actual (`{champ_name}`)")
    st.markdown("Monitorea la precisión predictiva del mejor modelo de machine learning seleccionado:")

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

    # 5. Gráficos Biofísicos con Descripción Detallada
    st.subheader("📈 3. Gráficos de Dinámica Hidrológica y Fisiológica")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### 🌊 Balance Hídrico Temporal (Precipitación vs Escorrentía)")
        # Agregar por fecha media para visualización limpia
        ts_df = df.groupby("date").agg({
            "precip_mm": "mean",
            "monthly_runoff_mm": "mean",
            "et_mm": "mean"
        }).reset_index()

        fig_ts = px.line(
            ts_df,
            x="date",
            y=["precip_mm", "monthly_runoff_mm", "et_mm"],
            labels={"value": "Milímetros (mm/mes)", "date": "Fecha", "variable": "Componente"},
            title="Balance Hídrico Mensual Promedio en Cuenca",
            color_discrete_map={
                "precip_mm": "#38bdf8",
                "monthly_runoff_mm": "#10b981",
                "et_mm": "#f59e0b"
            },
            template="plotly_dark"
        )
        fig_ts.update_layout(height=380, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_ts, use_container_width=True)

        # Descripción del Gráfico 1
        st.info("""
        **🔍 ¿Qué muestra este gráfico y cómo interpretarlo?**
        * **Línea Celeste (`precip_mm`)**: Precipitación mensual captada en la cuenca.
        * **Línea Verde (`monthly_runoff_mm`)**: Escorrentía generada tras la saturación del suelo. Observa cómo los picos de escorrentía coinciden con las lluvias intensas de primavera.
        * **Línea Naranja (`et_mm`)**: Evapotranspiración total del campo (suelo + canopeo de maíz), alcanzando su máximo en julio-agosto durante la etapa de máxima demanda vegetativa.
        """)

    with col_g2:
        st.markdown("#### 🌽 Rendimiento de Maíz vs Área Foliar (LAI) y Estrés")
        df_harvest = df[df["maize_yield_t_ha"] > 0.0]

        fig_yield = px.scatter(
            df_harvest,
            x="lai",
            y="maize_yield_t_ha",
            color="water_stress",
            size="soil_moisture",
            color_continuous_scale="Viridis",
            labels={
                "lai": "Índice de Área Foliar (LAI)",
                "maize_yield_t_ha": "Rendimiento de Grano (t/ha)",
                "water_stress": "Estrés CWSI",
                "soil_moisture": "Humedad Suelo (%)"
            },
            title="Rendimiento de Cosecha según Vigor y Estrés Hídrico",
            template="plotly_dark"
        )
        fig_yield.update_layout(height=380)
        st.plotly_chart(fig_yield, use_container_width=True)

        # Descripción del Gráfico 2
        st.info("""
        **🔍 ¿Qué muestra este gráfico y cómo interpretarlo?**
        * **Eje X (`lai`)**: Área foliar de la planta de maíz ($m^2$ hoja / $m^2$ suelo). A mayor LAI, mayor capacidad fotosintética.
        * **Eje Y (`maize_yield_t_ha`)**: Rendimiento de cosecha en toneladas por hectárea.
        * **Color (`water_stress`)**: Índice de estrés hídrico de 0 a 1. Observa que las parcelas con bajo estrés y alto LAI alcanzan rendimientos óptimos de 9-12 t/ha, mientras que el estrés reduce el grano drásticamente.
        """)

    st.markdown("---")

    # 6. Explorador de Datos con Filtros
    st.subheader("🔍 4. Explorador de Registros Multiescala Filtrados")
    st.markdown("Filtra interactivamente el dataset para analizar combinaciones específicas de cuenca, clima y manejo:")

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
            "Filtrar por Manejo Agrícola:",
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

    st.markdown("---")

    # 7. Guía Completa de la Página y sus Controles
    st.subheader("💡 5. Guía del Sistema: ¿Qué hace cada botón y elemento?")
    st.markdown("Resumen intuitivo para comprender el funcionamiento y la navegación dentro del laboratorio:")

    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.markdown("""
        #### 🧭 Secciones de Navegación (Menú Lateral Izquierdo)
        * **📊 1. Dashboard & Explorador**: Visión general, KPIs clave, gráficos de balance hídrico y tabla de registros.
        * **📈 2. EDA (Análisis Exploratorio)**: Distribuciones estadísticas, correlaciones Pearson y relaciones físicas entre variables.
        * **🧠 3. Entrenamiento**: Entrena 6 algoritmos de Machine Learning (Random Forest, XGBoost, SVR, CNN-LSTM, LSTM-AE-RF) y elige al modelo campeón.
        * **🔮 4. Inferencia y Predicción**: Panel interactivo con sliders para ajustar clima, planta y suelo y obtener predicciones en tiempo real con diagnóstico *Lab Ticket*.
        * **🏆 5. Benchmarking & Validación**: Validación cruzada espacial (Leave-One-Watershed-Out), métricas de cuenca ($NSE$, $RMSE$) y prueba de hipótesis $H_1$ (Wilcoxon).
        * **🌐 6. Simulador de Escenarios**: Evalúa el impacto del cambio climático (SSP2-4.5 vs SSP5-8.5) y prácticas de manejo (siembra directa / sorgo).
        * **📑 7. Centro de Reportes**: Exporta informes formales consolidados en formatos descargables **PDF**, **Word (.docx)** y **Excel (.xlsx)**.
        """)

    with col_b2:
        st.markdown("""
        #### 📐 Glosario de Métricas y Controles Clave
        * **NSE (Nash-Sutcliffe Efficiency)**: Mide la bondad de ajuste hidrológica. Un valor de $1.0$ es perfecto; $>0.75$ indica un modelo de alta precisión.
        * **RMSE (Error Cuadrático Medio)**: Magnitud media del error de predicción en milímetros ($mm$) o metros cúbicos por segundo ($m^3/s$).
        * **PBIAS (Sesgo Porcentual)**: Indica si el modelo tiende a sobreestimar (positivo) o subestimar (negativo) el caudal real.
        * **R² (Coeficiente de Determinación)**: Porcentaje de varianza explicada por el modelo (de $0$ a $1$).
        * **Filtros de Cuenca y Escenario**: Permiten aislar registros de una cuenca particular (e.g. `WS_Cedar_01`) o escenario climático (e.g. `SSP5-8.5`) para evaluar respuestas locales.
        * **Lab Ticket**: Tarjeta diagnóstica generada tras la inferencia que compara el valor predicho contra la línea base tradicional de SWAT+.
        """)

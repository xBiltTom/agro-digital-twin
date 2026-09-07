"""
Plant-to-Watershed AI Lab — Punto de Entrada Principal de la Aplicación Streamlit.
Research Context:
"From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models
with SWAT Hydrology and Downscaled Climate Projections"

Orquestador central que:
1. Inicializa configuración de página y estilos institucionales.
2. Renderiza la barra lateral con información del sistema y estado de artefactos.
3. Enruta a las 7 secciones del laboratorio CRISP-DM.
"""

import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import streamlit as st

# 1. Configuración de Página y Sesión
from src.utils.config import setup_page, init_session_state
setup_page()
init_session_state()

# 2. Componentes de UI y Localización
from src.ui.components import render_sidebar
from src.locales.i18n import t

# 3. Módulos de Pestañas
from src.ui.tabs import (
    tab_dashboard,
    tab_eda,
    tab_training,
    tab_prediction,
    tab_benchmarking,
    tab_scenarios,
    tab_reports
)


def main():
    """Función principal: orquesta la interfaz de Plant-to-Watershed AI Lab."""

    # Encabezado Principal
    st.title(f"🌽 {t('app_title')}")
    st.markdown(f"*{t('app_subtitle')}*")

    # Menú de Navegación en el Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("🧭 Navegación del Laboratorio")

    page_options = [
        t("nav_dashboard"),
        t("nav_eda"),
        t("nav_training"),
        t("nav_prediction"),
        t("nav_benchmarking"),
        t("nav_scenarios"),
        t("nav_reports")
    ]

    selection = st.sidebar.radio("Ir a la sección:", page_options)

    # Componentes inferiores del sidebar (info de sistema y modelo campeón)
    render_sidebar()

    # Enrutamiento de Módulos
    if selection == page_options[0]:
        tab_dashboard.render()
    elif selection == page_options[1]:
        tab_eda.render()
    elif selection == page_options[2]:
        tab_training.render()
    elif selection == page_options[3]:
        tab_prediction.render()
    elif selection == page_options[4]:
        tab_benchmarking.render()
    elif selection == page_options[5]:
        tab_scenarios.render()
    elif selection == page_options[6]:
        tab_reports.render()


if __name__ == "__main__":
    main()

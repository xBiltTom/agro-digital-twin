"""
AgroTwin-AI — Punto de Entrada Principal de la Aplicación Streamlit.

Orquestador central que:
1. Inicializa la configuración de página y estilos CSS.
2. Renderiza la barra lateral con menú de navegación.
3. Enruta a las 6 pestañas principales (EDA, Entrenamiento, Inferencia, Estadísticas, McNemar, Reportes).
"""

import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import streamlit as st

# 1. Configuración de Página y CSS
from src.utils.config import setup_page, init_session_state
setup_page()
init_session_state()

# 2. Componentes de UI y Localización
from src.ui.components import render_sidebar
from src.locales.i18n import t

# 3. Pestañas Principales
from src.ui.tabs import (
    tab_dashboard,
    tab_training,
    tab_diagnosis,
    tab_statistics,
    tab_mcnemar,
    tab_reports
)


def main():
    """Función principal: orquesta la interfaz completa de AgroTwin-AI."""
    
    # Encabezado Principal
    st.title(f"🌱 {t('app_title')}")
    st.markdown(f"*{t('app_subtitle')}*")
    
    # Menú de Navegación en el Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("🧭 Navegación del Sistema")
    
    page_options = [
        t("nav_eda"),
        t("nav_training"),
        t("nav_inference"),
        t("nav_statistics"),
        t("nav_hypothesis"),
        t("nav_reports")
    ]
    
    selection = st.sidebar.radio("Ir a la sección:", page_options)
    
    # Componentes inferiores del sidebar (info de sistema y estado)
    render_sidebar()
    
    # Enrutamiento de Módulos
    if selection == page_options[0]:
        tab_dashboard.render()
    elif selection == page_options[1]:
        tab_training.render()
    elif selection == page_options[2]:
        tab_diagnosis.render()
    elif selection == page_options[3]:
        tab_statistics.render()
    elif selection == page_options[4]:
        tab_mcnemar.render()
    elif selection == page_options[5]:
        tab_reports.render()


if __name__ == "__main__":
    main()

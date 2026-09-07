"""
Global configuration module for Plant-to-Watershed AI Lab.
Centralizes paths, constants, session state, and institutional CSS styling.
"""

import os
import streamlit as st

# ======= FILE & DIRECTORY PATHS =======
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_RAW_PATH = os.path.join(BASE_DIR, "dataset", "agro_watershed_dataset.csv")
DATASET_CLEANED_PATH = os.path.join(BASE_DIR, "dataset", "dataset_cleaned.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

# ======= MAIZE ECO-PHYSIOLOGICAL STRESS CLASSES =======
MAIZE_STRESS_CLASSES = {
    0: {
        "name": "Óptimo (Turgente)",
        "color": "#10B981",
        "badge": "🟢",
        "desc": "Dosel vegetal con transpiración plena y conductancia estomática máxima. Sin déficit hídrico en zona radicular."
    },
    1: {
        "name": "Estrés Moderado",
        "color": "#F59E0B",
        "badge": "🟡",
        "desc": "Cierre estomático incipiente por reducción de humedad edáfica bajo θ_crit. Tasa de transpiración reducida ~30%."
    },
    2: {
        "name": "Estrés Crítico (Alerta)",
        "color": "#EF4444",
        "badge": "🔴",
        "desc": "Marchitamiento foliar y senescencia acelerada. Afectación severa durante floración (R1) y llenado de grano de maíz."
    }
}

# Backwards compatibility alias
STRESS_CLASSES = MAIZE_STRESS_CLASSES

# ======= INSTITUTIONAL CSS STYLES =======
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital,wght@0,500;0,600;1,400&display=swap');

    .main .block-container {
        padding: 1.8rem 2.5rem;
        max-width: 1440px;
    }

    h1, h2, h3, h4 {
        font-family: 'Lora', serif !important;
    }

    p, span, div, label, input, button {
        font-family: 'Inter', sans-serif;
    }

    /* Synthetic Data Warning Banner */
    .synthetic-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid #F59E0B;
        color: #D97706;
        padding: 0.35rem 0.85rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.82rem;
        margin-bottom: 0.8rem;
    }

    /* Lab Ticket */
    .lab-ticket {
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(0,0,0,0.25));
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-top: 5px solid #10B981;
        padding: 1.6rem;
        border-radius: 12px;
        margin: 1.2rem 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }
    
    .lab-ticket.warning {
        border-top-color: #F59E0B;
    }

    .lab-ticket.critical {
        border-top-color: #EF4444;
    }

    .lab-ticket-eyebrow {
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.12em;
        opacity: 0.8;
        margin-bottom: 0.4rem;
        display: block;
        font-weight: 600;
    }

    .lab-ticket-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 0.6rem 0;
        line-height: 1.2;
    }

    .lab-ticket-badge {
        font-size: 0.95rem;
        font-weight: 600;
        display: inline-block;
        padding: 0.3rem 0.85rem;
        border-radius: 20px;
        color: white;
        background-color: #10B981;
    }
    .lab-ticket.warning .lab-ticket-badge {
        background-color: #F59E0B;
    }
    .lab-ticket.critical .lab-ticket-badge {
        background-color: #EF4444;
    }

    .tech-box {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1.2rem;
        border-radius: 10px;
        margin: 0.8rem 0;
    }
    
    .tech-box h4 {
        margin-top: 0;
        font-size: 0.95rem;
        font-weight: 600;
    }
</style>
"""


def setup_page():
    """Initializes Streamlit page configuration."""
    st.set_page_config(
        page_title="Plant-to-Watershed AI Lab",
        page_icon="🌽",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """Initializes session state keys."""
    defaults = {
        "dataset_loaded": False,
        "models_trained": False,
        "champion_model_name": None,
        "champion_metrics": {},
        "current_target": "monthly_runoff_mm",
        "current_prediction": None,
        "active_scenario": "Historical"
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

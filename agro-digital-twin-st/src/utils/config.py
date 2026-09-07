"""
Módulo de configuración global de AgroTwin-AI.
Centraliza rutas, constantes, inicialización de sesión y CSS institucional.
"""

import os
import streamlit as st

# ======= RUTAS DE ARCHIVOS Y DIRECTORIOS =======
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_RAW_PATH = os.path.join(BASE_DIR, "dataset", "agro_watershed_dataset.csv")
DATASET_CLEANED_PATH = os.path.join(BASE_DIR, "dataset", "dataset_cleaned.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")

# ======= RUTAS DE MODELOS EN DISCO =======
MODEL_PATHS = {
    "Deep MLP (DNN)":          os.path.join(MODELS_DIR, "mlp_model.keras"),
    "1D-CNN (Temporal ConvNet)": os.path.join(MODELS_DIR, "cnn1d_model.keras"),
    "LSTM Recurrente":         os.path.join(MODELS_DIR, "lstm_model.keras"),
    "Híbrido CNN-LSTM":        os.path.join(MODELS_DIR, "cnn_lstm_model.keras"),
    "Híbrido Autoencoder":     os.path.join(MODELS_DIR, "autoencoder_model.keras"),
    "Modelo Campeón (.keras)": os.path.join(MODELS_DIR, "best_agrotwin_model.keras"),
    "Modelo Campeón (.h5)":    os.path.join(MODELS_DIR, "best_agrotwin_model.h5"),
}

# ======= CLASES DE ESTRÉS HÍDRICO (CWSI) =======
STRESS_CLASSES = {
    0: {"name": "Óptimo (Sin Estrés)", "color": "#10B981", "badge": "🟢", "desc": "Planta túrgida con transpiración plena. No requiere riego."},
    1: {"name": "Estrés Moderado", "color": "#F59E0B", "badge": "🟡", "desc": "Cierre estomático incipiente. Programar riego en las próximas 24h."},
    2: {"name": "Estrés Crítico (Alerta)", "color": "#EF4444", "badge": "🔴", "desc": "Marchitamiento foliar y cavitación de xilema. Aplicar riego de emergencia inmediato."}
}

# ======= ESTILOS CSS PERSONALIZADOS (LAB TICKET) =======
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital,wght@0,500;0,600;1,400&display=swap');

    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }

    h1, h2, h3, h4 {
        font-family: 'Lora', serif !important;
    }

    p, span, div, label, input, button {
        font-family: 'Inter', sans-serif;
    }

    /* === SIGNATURE ELEMENT: Lab Ticket (Tarjeta de Diagnóstico) === */
    .lab-ticket {
        background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(0,0,0,0.2));
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-top: 5px solid #10B981;
        padding: 1.8rem;
        border-radius: 12px;
        margin: 1.5rem 0;
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
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.8rem 0;
        line-height: 1.2;
    }

    .lab-ticket-badge {
        font-size: 1rem;
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

    /* === DATA / TECH BOXES === */
    .tech-box {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1.3rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .tech-box h4 {
        margin-top: 0;
        font-size: 0.95rem;
        font-weight: 600;
    }

    /* === STAT CARDS === */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
</style>
"""

def setup_page():
    """Configuración inicial de la página Streamlit."""
    st.set_page_config(
        page_title="AgroTwin-AI — Deep Eco-Hydrology",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """Inicializa variables de estado de sesión de Streamlit."""
    defaults = {
        "dataset_loaded": False,
        "models_trained": False,
        "models_loaded": False,
        "best_model_name": None,
        "best_r2_score": 0.0,
        "train_dataset_valid": False,
        "training_history": {},
        "current_prediction": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

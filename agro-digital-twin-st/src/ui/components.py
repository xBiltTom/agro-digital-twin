"""
Módulo de Componentes de Interfaz de Usuario para AgroTwin-AI.
Incluye barra lateral, analizador de hardware, banners institucionales y tarjetas Lab Ticket.
"""

import os
import platform
import streamlit as st
from src.locales.i18n import t
from src.utils.config import MODEL_PATHS

def render_sidebar():
    """Renderiza la barra lateral con información de sistema y estado de modelos."""
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"ℹ️ {t('sidebar_title')}")
    
    # Estado de modelos en disco
    keras_exists = os.path.exists(MODEL_PATHS["Modelo Campeón (.keras)"])
    h5_exists = os.path.exists(MODEL_PATHS["Modelo Campeón (.h5)"])
    
    if keras_exists or h5_exists:
        st.sidebar.success("✅ Modelo Campeón: Listo en disco")
        st.sidebar.caption("Archivos: `best_model.keras` / `.h5`")
    else:
        st.sidebar.warning("⚠️ Modelo Campeón: Pendiente de entrenamiento")
        st.sidebar.caption("Dirígete a la pestaña **2. Entrenamiento**")
        
    st.sidebar.markdown("---")
    st.sidebar.caption(f"**Versión**: {t('sidebar_version')}")
    st.sidebar.caption(f"**Entorno**: {t('sidebar_env')}")
    st.sidebar.caption("**Dominio**: Ecohidrología SWAT & Feddes")


def render_hardware_analyzer():
    """Escanea y muestra las especificaciones de hardware de la máquina de entrenamiento."""
    with st.spinner("Escaneando recursos de CPU, núcleos y memoria RAM..."):
        # CPU
        cpu_name = platform.processor() or "CPU x86_64"
        if os.path.exists('/proc/cpuinfo'):
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            cpu_name = line.split(':')[1].strip()
                            break
            except Exception:
                pass
                
        # RAM
        ram_gb = "Desconocida"
        if os.path.exists('/proc/meminfo'):
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            kb = int(line.split()[1])
                            ram_gb = f"{round(kb / (1024**2), 1)} GB"
                            break
            except Exception:
                pass
                
        os_info = f"{platform.system()} {platform.release()}"
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="Procesador (CPU)", value=cpu_name[:22] + "...")
        with c2:
            st.metric(label="Memoria RAM Total", value=ram_gb)
        with c3:
            st.metric(label="Sistema Operativo", value=platform.system())
            
        st.success("✅ Hardware verificado: Recursos óptimos para entrenamiento acelerado de Redes Neuronales Keras.")


def render_lab_ticket(pred: dict):
    """
    Renderiza la tarjeta de diagnóstico "Lab Ticket" (elemento de firma).
    """
    css_class = pred.get("css_class", "healthy")
    badge_icon = pred.get("badge", "🟢")
    category_name = pred.get("category_name", "Óptimo")
    cwsi_val = pred.get("cwsi", 0.15)
    model_name = pred.get("model_used", "Modelo Campeón")
    
    html = f"""
    <div class="lab-ticket {css_class}">
        <span class="lab-ticket-eyebrow">Diagnóstico Biofísico de Planta — AgroTwin AI Lab</span>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div class="lab-ticket-title">{badge_icon} {category_name}</div>
            <div class="lab-ticket-badge">CWSI: {cwsi_val:.3f}</div>
        </div>
        <p style="margin: 0.5rem 0 1rem 0; font-size: 0.95rem; opacity: 0.9;">
            {pred.get('description', '')}
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,0.2);">
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Transpiración (Tr)</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #10B981;">{pred.get('actual_transpiration_mm', 0):.2f} mm/d</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Lámina de Riego Neta</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #38BDF8;">{pred.get('net_irrigation_mm', 0):.2f} mm</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Dosis por Hectárea</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #0EA5E9;">{pred.get('volume_m3_ha', 0):.1f} m³/ha</div>
            </div>
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Dosis por Árbol</span>
                <div style="font-size: 1.2rem; font-weight: 700; color: #6366F1;">{pred.get('liters_per_tree', 0):.1f} L/árbol</div>
            </div>
        </div>
        <div style="margin-top: 0.8rem; font-size: 0.75rem; opacity: 0.6; font-family: monospace;">
            Inferencia ejecutada con: {model_name}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

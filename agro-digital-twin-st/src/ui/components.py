"""
UI Components for Plant-to-Watershed AI Lab.
Sidebar, hardware inspector, synthetic data disclaimer, and prediction cards.
"""

import os
import streamlit as st
from src.locales.i18n import t
from src.core.hardware import detect_compute_device
from src.core.datasets.synthetic_generator import DATASET_SOURCE_LABEL
from src.core.statistics_core import load_training_history


def render_synthetic_data_badge():
    """Renders prominent disclaimer badge for synthetic data."""
    st.markdown(f"""
    <div class="synthetic-badge">
        <span>⚠️</span>
        <span><b>MODO: {DATASET_SOURCE_LABEL}</b> — Datos generados para desarrollo de arquitectura y pruebas de gemelo digital. No representan observaciones reales USGS/USDA/CMIP6.</span>
    </div>
    """, unsafe_allow_html=True)


def render_auth_widget():
    """Renders authentication box with user role badge and credentials switcher."""
    from src.infrastructure.auth import AuthService, Role, get_role_description

    if "auth_user" not in st.session_state:
        st.session_state["auth_user"] = AuthService.get_default_guest()

    user = st.session_state["auth_user"]
    desc, color = get_role_description(user.role)

    st.sidebar.markdown(f"""
    <div style="background-color: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; font-size: 0.9rem;">👤 {user.username.upper()}</span>
            <span style="background-color: {color}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 0.75rem; font-weight: bold;">
                {user.role.value}
            </span>
        </div>
        <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 4px;">{user.full_name}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar.expander("🔑 Cambiar Usuario / Rol"):
        role_select = st.selectbox(
            "Acceso rápido por rol:",
            options=["admin (ADMIN)", "researcher (RESEARCHER)", "analyst (ANALYST)", "guest (GUEST)"],
            index=["admin", "researcher", "analyst", "guest"].index(user.username.lower()) if user.username.lower() in ["admin", "researcher", "analyst", "guest"] else 3
        )
        selected_key = role_select.split()[0]

        if st.button("Aplicar Rol", use_container_width=True):
            passwords = {
                "admin": "Admin123!",
                "researcher": "Research123!",
                "analyst": "Analyst123!",
                "guest": "Guest123!"
            }
            new_user = AuthService.authenticate(selected_key, passwords[selected_key])
            if new_user:
                st.session_state["auth_user"] = new_user
                st.sidebar.success(f"Conectado como {selected_key}")
                st.rerun()


def render_sidebar():
    """Renders sidebar system status, active target, auth widget, and champion model."""
    render_auth_widget()

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"ℹ️ {t('sidebar_title')}")

    # Inspect champion artifact
    history = load_training_history()
    champ_name = history.get("champion_model_name")
    champ_metrics = history.get("champion_metrics", {})
    target_name = history.get("target_name", "monthly_runoff_mm")

    if champ_name:
        st.sidebar.success(f"🏆 Campeón: **{champ_name}**")
        st.sidebar.caption(f"Target: `{target_name}` | NSE: `{champ_metrics.get('nse', 'N/A')}` | RMSE: `{champ_metrics.get('rmse', 'N/A')}`")
    else:
        st.sidebar.warning("⚠️ Modelo Campeón: Pendiente de entrenamiento")
        st.sidebar.caption("Ejecuta el entrenamiento en la Pestaña 3.")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"**Versión**: {t('sidebar_version')}")
    st.sidebar.caption(f"**Entorno**: {t('sidebar_env')}")
    st.sidebar.caption("**Dominio**: Maíz (Zea mays) • Corn Belt • SWAT+")
    st.sidebar.caption("**Dataset**: DEMO / SYNTHETIC DATA")


def render_hardware_analyzer():
    """Inspects compute resources using detect_compute_device()."""
    with st.spinner("Escaneando recursos de CPU, núcleos, RAM y aceleración GPU..."):
        hw = detect_compute_device()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(label="Modo de Cómputo", value=hw["device_mode"])
        with c2:
            st.metric(label="Núcleos de CPU", value=f"{hw['cpu']['cores']} cores")
        with c3:
            st.metric(label="Memoria RAM", value=f"{hw['ram']['total_gb']} GB")
        with c4:
            tf_status = "GPU Activa" if hw["tensorflow"]["gpu_available"] else "CPU Backend"
            st.metric(label="TensorFlow Backend", value=tf_status)

        st.caption(f"**Procesador detectado**: {hw['cpu']['model']}")
        if hw["tensorflow"]["gpu_available"]:
            st.success(f"✅ Aceleración GPU detectada: {hw['tensorflow']['gpus']}")
        else:
            st.info("ℹ️ Ejecución en CPU activa: Los modelos tradicionales y redes neuronales están optimizados para operar sin requerir GPU.")


def render_lab_ticket(pred: dict):
    """
    Renders the signature Lab Ticket prediction card adapted for Plant-to-Watershed.
    """
    mode = pred.get("mode", "direct_prediction")
    target_name = pred.get("target", "monthly_runoff_mm")
    val = pred.get("value", 0.0)
    unit = pred.get("unit", "mm/month")
    model_name = pred.get("model_used", "Modelo Campeón")

    # Water stress info
    water_stress = pred.get("water_stress", 0.10)
    if water_stress < 0.20:
        css_class = ""
        badge = "🟢 Óptimo"
    elif water_stress < 0.45:
        css_class = "warning"
        badge = "🟡 Estrés Moderado"
    else:
        css_class = "critical"
        badge = "🔴 Estrés Crítico"

    residual_html = ""
    if mode == "residual_correction":
        residual_html = f"""
        <div>
            <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Base SWAT+</span>
            <div style="font-size: 1.15rem; font-weight: 700; color: #94A3B8;">{pred.get('swat_baseline_value', 0):.2f} {unit}</div>
        </div>
        <div>
            <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Residual Corregido (Δ)</span>
            <div style="font-size: 1.15rem; font-weight: 700; color: #F59E0B;">{pred.get('predicted_residual', 0):+.2f} {unit}</div>
        </div>
        """

    html = f"""
    <div class="lab-ticket {css_class}">
        <span class="lab-ticket-eyebrow">Plant-to-Watershed AI Lab — Inferencia Biofísica</span>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <div class="lab-ticket-title">🌽 Predicción: {val:.2f} {unit}</div>
            <div class="lab-ticket-badge">{badge} (Estrés: {water_stress:.2f})</div>
        </div>
        <p style="margin: 0.5rem 0 1rem 0; font-size: 0.95rem; opacity: 0.9;">
            Predicción generada mediante el modo <b>{mode.replace('_', ' ').upper()}</b> para la variable objetivo <code>{target_name}</code>.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,0.2);">
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Valor Estimado</span>
                <div style="font-size: 1.25rem; font-weight: 700; color: #10B981;">{val:.2f} {unit}</div>
            </div>
            {residual_html}
            <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.7;">Modelo Empleado</span>
                <div style="font-size: 1.05rem; font-weight: 600; color: #38BDF8;">{model_name}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

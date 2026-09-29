"""
UI Components for Plant-to-Watershed AI Lab.
Sidebar, hardware inspector, synthetic data disclaimer, and prediction cards.
"""

import os
import streamlit as st
from src.locales.i18n import t
from src.core.hardware import detect_compute_device
from src.core.statistics_core import load_training_history
from src.core.datasets.catalog import (
    API_SOURCE_PREFIX,
    configured_real_artifact_dir,
    load_api_simulation_dataset,
    load_lab_dataset,
    source_labels,
)
from src.core.integrations.fastapi_client import FastAPIClient, FastAPIConnectionError


def render_synthetic_data_badge():
    """Renders a source badge without calling simulated results observations."""
    metadata = st.session_state.get("active_dataset_metadata", {})
    source_kind = metadata.get("source_kind", "synthetic_demo")
    if source_kind == "synthetic_demo":
        st.warning("**Modo demo sintético:** datos generados para pruebas de arquitectura; no son observaciones de campo.")
    elif source_kind == "simulation_results":
        st.info("**Resultados de simulación:** South Fork 2019 combina salidas SWAT+ y FSPM; no representa observaciones de campo.")
    else:
        st.info(f"**Origen del dataset:** {metadata.get('origin', 'no especificado')}")


@st.cache_data(show_spinner=False)
def load_selected_dataset(source: str, artifact_dir: str):
    """Cache validated source loading while keeping core modules Streamlit-free."""
    return load_lab_dataset(source, artifact_dir or None)


def get_active_dataset():
    """Load the source selected in the sidebar."""
    source = st.session_state.get("active_dataset_source", "synthetic_demo")
    artifact_dir = st.session_state.get("active_dataset_artifact_dir", str(configured_real_artifact_dir()))
    if source.startswith(API_SOURCE_PREFIX):
        client = st.session_state.get("fastapi_client")
        if client is None or not client.is_authenticated:
            st.error("La fuente FastAPI requiere autenticación en el panel lateral.")
            st.stop()
        try:
            frame, metadata, variable_catalog = load_api_simulation_dataset(
                client,
                source.removeprefix(API_SOURCE_PREFIX),
                simulation=st.session_state.get("fastapi_selected_simulation"),
            )
        except FastAPIConnectionError as exc:
            st.error(f"No fue posible cargar el playback FastAPI: {exc}")
            st.stop()
    else:
        frame, metadata, variable_catalog = load_selected_dataset(source, artifact_dir)
    st.session_state["active_dataset_metadata"] = metadata
    st.session_state["dataset_loaded"] = True
    return frame, metadata, variable_catalog


def render_dataset_selector():
    """Select synthetic demo or one validated artifact run for all tabs."""
    api_labels = {}
    with st.sidebar.expander("FastAPI: playback de simulaciones", expanded=False):
        base_url = st.text_input(
            "URL base",
            value=os.environ.get("AGRO_TWIN_FASTAPI_URL", "http://localhost:8000"),
            key="fastapi_base_url",
        )
        client = st.session_state.get("fastapi_client")
        if client is None or client.base_url.removesuffix("/api/v1") != base_url.rstrip("/"):
            client = FastAPIClient(base_url=base_url)
            st.session_state["fastapi_client"] = client
            st.session_state["fastapi_simulations"] = []
        email = st.text_input("Correo FastAPI", key="fastapi_email")
        password = st.text_input("Contraseña FastAPI", type="password", key="fastapi_password")
        if st.button("Autenticar y listar simulaciones", key="fastapi_login"):
            try:
                client.login(email, password)
                st.session_state["fastapi_simulations"] = client.list_simulations()
                st.success("FastAPI autenticado en memoria.")
            except FastAPIConnectionError as exc:
                client.token = None
                st.session_state["fastapi_simulations"] = []
                st.error(str(exc))
        simulations = st.session_state.get("fastapi_simulations", [])
        if client.is_authenticated and not simulations:
            try:
                simulations = client.list_simulations()
                st.session_state["fastapi_simulations"] = simulations
            except FastAPIConnectionError as exc:
                st.warning(f"No se pudo listar simulaciones: {exc}")
        if simulations:
            simulations_by_id = {str(item.get("id")): item for item in simulations if item.get("id")}
            simulation_options = {
                str(item.get("id")): (
                    f"{item.get('name') or item.get('external_model_id') or item.get('id')} "
                    f"[{item.get('status', 'UNKNOWN')}]"
                )
                for item in simulations
                if item.get("id")
            }
            if simulation_options:
                selected_simulation = st.selectbox(
                    "Simulación API",
                    options=list(simulation_options),
                    format_func=simulation_options.get,
                    key="fastapi_simulation_selector",
                )
                api_labels[f"{API_SOURCE_PREFIX}{selected_simulation}"] = (
                    f"FastAPI: {simulation_options[selected_simulation]}"
                )
                st.session_state["fastapi_selected_simulation"] = simulations_by_id[selected_simulation]
    labels = {**source_labels(), **api_labels}
    source_keys = list(labels)
    source_options = [labels[key] for key in source_keys]
    current = st.session_state.get("active_dataset_source", source_keys[0])
    if current not in source_keys:
        current = source_keys[0]
    selected_label = st.sidebar.selectbox(
        "Fuente de datos del laboratorio:",
        options=source_options,
        index=source_keys.index(current),
        key="dataset_source_selector",
    )
    selected = source_keys[source_options.index(selected_label)]
    st.session_state["active_dataset_source"] = selected
    artifact_dir = str(configured_real_artifact_dir())
    st.session_state["active_dataset_artifact_dir"] = artifact_dir
    if selected != "synthetic_demo":
        st.sidebar.caption(f"Artefactos: `{artifact_dir}`")


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
    render_dataset_selector()
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
    metadata = st.session_state.get("active_dataset_metadata", {})
    st.sidebar.caption(f"**Dataset**: {metadata.get('artifact_classification', 'SYNTHETIC_DEVELOPMENT_ARTIFACT')}")


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

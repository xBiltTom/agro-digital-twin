"""
Pestaña 3: Inferencia de Estrés & Recomendador de Riego — AgroTwin-AI.
Diagnóstico biofísico instantáneo, tarjeta Lab Ticket y prescripción de riego tecnificado.
"""

import streamlit as st
from src.core.inference import predict_stress_and_irrigation
from src.ui.components import render_lab_ticket
from src.utils.config import MODEL_PATHS

def render():
    st.header("🔍 3. Inferencia de Estrés Hídrico & Recomendador de Riego")
    st.markdown("""
    Ingresa las condiciones meteorológicas y el estado actual del suelo para que la Red Neuronal entrenada
    diagnostique en tiempo real el **Índice de Estrés Hídrico ($CWSI$)** y calcule la **Dosis Óptima de Riego**.
    """)
    
    # 1. Selector de Modelo
    col_m, col_scen = st.columns([2, 2])
    with col_m:
        model_options = list(MODEL_PATHS.keys())
        selected_model = st.selectbox("🧠 Modelo de Inferencia:", model_options, index=0)
        
    with col_scen:
        scenario = st.selectbox(
            "⚡ Escenarios Preconfigurados de Campo:",
            [
                "Personalizado (Ajustar sliders)",
                "🌱 Día Templado Óptimo (Primavera)",
                "⚠️ Estrés Moderado de Mediodía",
                "🔥 Ola de Calor Extrema / Suelo Seco",
                "🌧️ Día Posterior a Lluvia Intensa"
            ]
        )
        
    # Valores por defecto según escenario
    defaults = {
        "temp_max": 26.5, "temp_min": 14.0, "solar_rad": 22.0, "rh_mean": 55.0,
        "vpd_kpa": 1.45, "wind_speed": 2.1, "precip_mm": 0.0, "precip_3d": 0.0,
        "streamflow_m3s": 6.5, "soil_moisture_vol": 25.0, "et0_mm": 4.1
    }
    
    if scenario == "🌱 Día Templado Óptimo (Primavera)":
        defaults = {"temp_max": 23.0, "temp_min": 13.0, "solar_rad": 19.5, "rh_mean": 65.0, "vpd_kpa": 0.95, "wind_speed": 1.8, "precip_mm": 0.0, "precip_3d": 5.0, "streamflow_m3s": 8.0, "soil_moisture_vol": 30.5, "et0_mm": 3.4}
    elif scenario == "⚠️ Estrés Moderado de Mediodía":
        defaults = {"temp_max": 29.0, "temp_min": 16.0, "solar_rad": 25.0, "rh_mean": 42.0, "vpd_kpa": 2.10, "wind_speed": 2.8, "precip_mm": 0.0, "precip_3d": 0.0, "streamflow_m3s": 4.8, "soil_moisture_vol": 20.2, "et0_mm": 5.2}
    elif scenario == "🔥 Ola de Calor Extrema / Suelo Seco":
        defaults = {"temp_max": 35.5, "temp_min": 19.0, "solar_rad": 28.5, "rh_mean": 28.0, "vpd_kpa": 3.45, "wind_speed": 3.5, "precip_mm": 0.0, "precip_3d": 0.0, "streamflow_m3s": 2.5, "soil_moisture_vol": 14.2, "et0_mm": 6.8}
    elif scenario == "🌧️ Día Posterior a Lluvia Intensa":
        defaults = {"temp_max": 20.0, "temp_min": 12.0, "solar_rad": 14.0, "rh_mean": 82.0, "vpd_kpa": 0.45, "wind_speed": 1.5, "precip_mm": 22.0, "precip_3d": 35.0, "streamflow_m3s": 18.5, "soil_moisture_vol": 38.0, "et0_mm": 2.1}

    st.markdown("---")
    st.subheader("🎛️ Parámetros de Entrada de Campo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Atmósfera & Temperatura**")
        t_max = st.slider("Temperatura Máxima (°C)", 10.0, 42.0, float(defaults["temp_max"]), 0.5)
        t_min = st.slider("Temperatura Mínima (°C)", 2.0, 26.0, float(defaults["temp_min"]), 0.5)
        t_mean = round((t_max + t_min) / 2.0, 2)
        solar_rad = st.slider("Radiación Solar (MJ/m²)", 5.0, 35.0, float(defaults["solar_rad"]), 0.5)
        
    with col2:
        st.markdown("**Humedad & Viento**")
        rh = st.slider("Humedad Relativa (%)", 15.0, 95.0, float(defaults["rh_mean"]), 1.0)
        vpd = st.slider("Déficit Presión Vapor - VPD (kPa)", 0.2, 5.0, float(defaults["vpd_kpa"]), 0.05)
        wind = st.slider("Velocidad Viento (m/s)", 0.2, 8.0, float(defaults["wind_speed"]), 0.1)
        et0 = st.slider("Evapotranspiración ET0 (mm/d)", 0.5, 9.0, float(defaults["et0_mm"]), 0.1)
        
    with col3:
        st.markdown("**Suelo & Cuenca Hidrográfica**")
        soil_moist = st.slider("Humedad Suelo Zona Radicular θ (% vol)", 8.0, 44.0, float(defaults["soil_moisture_vol"]), 0.5)
        precip = st.slider("Precipitación Hoy (mm)", 0.0, 50.0, float(defaults["precip_mm"]), 0.5)
        precip_3d = st.slider("Lluvia Acumulada 3 días (mm)", 0.0, 100.0, float(defaults["precip_3d"]), 1.0)
        streamflow = st.slider("Caudal Cuenca SWAT (m³/s)", 0.5, 40.0, float(defaults["streamflow_m3s"]), 0.5)
        
    st.markdown("---")
    
    input_payload = {
        "temp_max": t_max,
        "temp_min": t_min,
        "temp_mean": t_mean,
        "solar_rad": solar_rad,
        "rh_mean": rh,
        "vpd_kpa": vpd,
        "wind_speed": wind,
        "precip_mm": precip,
        "precip_3d": precip_3d,
        "streamflow_m3s": streamflow,
        "soil_moisture_vol": soil_moist,
        "et0_mm": et0
    }
    
    if st.button("🧪 Diagnosticar Cultivo & Calcular Dosis de Riego", type="primary", use_container_width=True):
        pred = predict_stress_and_irrigation(input_payload, model_key=selected_model)
        st.session_state.current_prediction = pred
        
    if st.session_state.get("current_prediction"):
        pred = st.session_state.current_prediction
        st.subheader("📋 Resultado del Diagnóstico Biofísico")
        render_lab_ticket(pred)
        
        # Explicación detallada de la recomendación
        if pred["cwsi"] >= 0.55:
            st.error(f"🚨 **Alerta Agronómica**: El modelo detectó estrés severo ($CWSI = {pred['cwsi']:.3f}$). Se recomienda encender el sistema de riego por goteo inmediatamente para reponer **{pred['gross_irrigation_mm']:.2f} mm** ({pred['volume_m3_ha']:.1f} m³/ha).")
        elif pred["cwsi"] >= 0.25:
            st.warning(f"⚠️ **Atención de Campo**: Estrés moderado ($CWSI = {pred['cwsi']:.3f}$). Se sugiere programar el turno de riego en las próximas 24 horas aplicando **{pred['gross_irrigation_mm']:.2f} mm**.")
        else:
            st.success(f"✅ **Estado Hidráulico Óptimo**: El cultivo no presenta estrés hídrico ($CWSI = {pred['cwsi']:.3f}$). Transpiración fisiológica al 100%. No requiere aporte hídrico hoy.")

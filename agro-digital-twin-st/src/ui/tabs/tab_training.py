"""
Pestaña 2: Configuración de Entrenamiento y Validación Cruzada (K-Fold) — AgroTwin-AI.
Configuración de hiperparámetros, escaneo de hardware y ejecución de K-Fold CV sobre 5 modelos.
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.utils.config import DATASET_RAW_PATH, DATASET_CLEANED_PATH, MODEL_PATHS
from src.ui.components import render_hardware_analyzer
from src.core.trainer import train_pipeline, MODEL_NAMES

def render():
    st.header("⚙️ 2. Entrenamiento y Validación Cruzada (K-Fold)")
    st.markdown("""
    En esta sección se entrenan y calibran las **5 arquitecturas de Deep Learning en Keras/TensorFlow** mediante **Validación Cruzada Estratificada ($K$-Fold)**.
    El sistema evalúa cada arquitectura a través de los folds y guarda automáticamente el **Modelo Campeón** en disco como `.keras` y `.h5`.
    """)
    
    # 1. Validación de Dataset
    st.subheader("📁 1. Dataset de Entrada para Entrenamiento")
    col_path, col_val = st.columns([3, 1])
    with col_path:
        default_path = DATASET_CLEANED_PATH if os.path.exists(DATASET_CLEANED_PATH) else DATASET_RAW_PATH
        train_path = st.text_input("Ruta del archivo CSV para entrenar:", value=default_path)
    with col_val:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✔️ Validar Archivo", use_container_width=True):
            if os.path.exists(train_path):
                df = pd.read_csv(train_path)
                st.success(f"Archivo válido: {len(df)} registros y {len(df.columns)} columnas.")
                st.session_state.train_dataset_valid = True
            else:
                st.error("La ruta no existe.")
                st.session_state.train_dataset_valid = False
                
    st.markdown("---")
    
    # 2. Hiperparámetros y Arquitecturas
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🛠️ Hiperparámetros de Tuning")
        lr = st.selectbox("Tasa de Aprendizaje (Learning Rate)", [0.001, 0.0005, 0.0001], index=0)
        dropout = st.slider("Tasa de Dropout (Regularización)", 0.1, 0.5, 0.3, 0.05)
        batch_size = st.selectbox("Tamaño de Lote (Batch Size)", [16, 32, 64], index=1)
        epochs = st.slider("Número de Épocas (Epochs)", 10, 60, 25, 5)
        k_folds = st.selectbox("Folds para Validación Cruzada (K)", [3, 5, 10], index=1)
        
    with c2:
        st.subheader("🧠 Modelos en el Pipeline de Competición")
        st.markdown("""
        <div class="tech-box">
        <h4>Las 5 Arquitecturas en Evaluación:</h4>
        <ol style="margin-left: 1.2rem; font-size: 0.9rem; line-height: 1.6;">
            <li><b>Deep MLP / DNN</b>: Capas densas (128-64-32) con BatchNorm y regularización L2.</li>
            <li><b>1D-CNN (Temporal ConvNet)</b>: Filtros convolucionales unidimensionales para features locales.</li>
            <li><b>LSTM Recurrente</b>: Celdas de memoria para secuencias y retardo hídrico.</li>
            <li><b>Híbrido CNN-LSTM</b>: Extracción convolucional combinada con memoria recurrente.</li>
            <li><b>Híbrido Autoencoder</b>: Espacio latente comprimido con cabezal de regresión.</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 3. Analizador de Hardware
    st.subheader("🖥️ Evaluación de Recursos de Cómputo")
    st.markdown("Antes de entrenar las 5 redes neuronales, el sistema certifica la capacidad de memoria y procesador:")
    
    if st.button("🔍 Analizar Hardware del Sistema", use_container_width=True):
        render_hardware_analyzer()
        
    st.markdown("---")
    
    # 4. Lanzador de Entrenamiento
    st.subheader("🚀 Ejecutar Entrenamiento K-Fold")
    st.markdown("Al presionar el botón, se ejecutará el K-Fold sobre los 5 modelos, se calcularán las métricas de prueba y se serializará el modelo campeón.")
    
    if st.button("▶️ Iniciar Entrenamiento de los 5 Modelos", type="primary", use_container_width=True):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)
            
        with st.spinner("Entrenando modelos de Deep Learning..."):
            res = train_pipeline(
                epochs=epochs,
                batch_size=batch_size,
                lr=lr,
                dropout=dropout,
                k_folds=k_folds,
                progress_callback=update_progress
            )
            
        progress_bar.progress(1.0)
        status_text.text("¡Entrenamiento y Validación Cruzada completados con éxito!")
        
        best_name = res["best_model_name"]
        best_r2 = res["best_r2_score"]
        
        st.success(f"🏆 **Modelo Campeón Seleccionado**: `{best_name}` con Coeficiente **R² = {best_r2:.4f}**")
        st.info(f"💾 Modelo serializado en: `{MODEL_PATHS['Modelo Campeón (.keras)']}` y `{MODEL_PATHS['Modelo Campeón (.h5)']}`")
        
        st.session_state.models_trained = True
        st.session_state.best_model_name = best_name
        st.session_state.best_r2_score = best_r2
        
        # Tabla resumen inmediata
        st.subheader("📋 Resumen de Métricas por Modelo")
        summary_rows = []
        for name, metrics in res["results"].items():
            summary_rows.append({
                "Modelo": name,
                "R² Score": metrics["r2"],
                "RMSE": metrics["rmse"],
                "MAE": metrics["mae"],
                "NSE (Nash)": metrics["nse"]
            })
        st.dataframe(pd.DataFrame(summary_rows).sort_values(by="R² Score", ascending=False), use_container_width=True)

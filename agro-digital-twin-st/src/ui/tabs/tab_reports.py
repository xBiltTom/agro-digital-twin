"""
Pestaña 6: Generación de Reportes Técnicos en PDF — AgroTwin-AI.
Compilación y descarga de informes ejecutivos de benchmarking y validación científica.
"""

import streamlit as st
from datetime import datetime
from src.core.pdf_generator import generate_pdf_report
from src.core.statistics_core import get_benchmark_df, load_training_history

def render():
    st.header("📄 6. Generador de Reportes Técnicos Ejecutivos")
    st.markdown("""
    En esta sección puedes exportar el informe formal de validación y benchmarking de los modelos de Deep Learning en formato **PDF**.
    El documento incluye membrete institucional, tablas de métricas $K$-Fold, pruebas de significancia estadística y conclusiones.
    """)
    
    # 1. Configuración del Reporte
    st.subheader("📝 Configuración de Metadatos del Informe")
    
    col1, col2 = st.columns(2)
    with col1:
        evaluator_name = st.text_input("Nombre del Evaluador / Docente:", value="Comité de Evaluación de Inteligencia Artificial")
        institution = st.text_input("Institución / Laboratorio:", value="Universidad Nacional de Ingeniería — Lab. de Ecohidrología e IA")
    with col2:
        custom_notes = st.text_area(
            "Notas u Observaciones del Experimento:",
            value="Validación biofísica multiescala del modelo sustituto para gemelos digitales bajo forzamientos CMIP6. Modelo listo para integración en tiempo real."
        )
        
    st.markdown("---")
    
    # 2. Resumen Previo al PDF
    st.subheader("👁️ Vista Previa de Datos a Incluir")
    history = load_training_history()
    best_name = history.get("best_model_name", "Híbrido CNN-LSTM")
    best_r2 = history.get("best_r2_score", 0.978)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"🏆 **Modelo Campeón**: {best_name}")
    with c2:
        st.success(f"📊 **Coeficiente R²**: {best_r2:.4f}")
    with c3:
        st.warning(f"📅 **Fecha**: {datetime.now().strftime('%d/%m/%Y')}")
        
    st.dataframe(get_benchmark_df(), use_container_width=True)
    
    st.markdown("---")
    
    # 3. Generación y Descarga
    st.subheader("📥 Exportación del Documento")
    
    col_btn, _ = st.columns([2, 2])
    with col_btn:
        if st.button("🔨 Compilar y Generar Reporte PDF", type="primary", use_container_width=True):
            with st.spinner("Generando PDF institucional con ReportLab..."):
                full_notes = f"Evaluador: {evaluator_name}\nInstitución: {institution}\n\nObservaciones:\n{custom_notes}"
                pdf_bytes = generate_pdf_report(custom_notes=full_notes)
                
                filename = f"Informe_Tecnico_AgroTwin_AI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                
                st.download_button(
                    label="⬇️ Descargar Informe PDF Formal",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ ¡Reporte PDF generado exitosamente! Haz clic en el botón superior para guardarlo.")

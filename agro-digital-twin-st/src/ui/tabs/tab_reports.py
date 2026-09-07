"""
Tab 7: Reports Generator — Plant-to-Watershed AI Lab.
Exports executive technical evaluation reports in PDF, Excel, and CSV format.
Clearly states data provenance (REAL vs SYNTHETIC) and validation metrics.
"""

import io
from datetime import datetime
import streamlit as st
import pandas as pd

from src.core.pdf_generator import generate_pdf_report
from src.core.docx_generator import generate_docx_report
from src.core.statistics_core import get_benchmark_df, load_training_history
from src.ui.components import render_synthetic_data_badge
from src.core.dataset_generator import get_dataset
from src.infrastructure.auth import Permission


def render():
    st.header("📄 7. Generador de Reportes Técnicos Ejecutivos")
    st.caption("🏷️ **[CRISP-DM: Academic Reporting & Governance]**")
    render_synthetic_data_badge()

    st.markdown("""
    Exporta el informe formal de validación y benchmarking del **Plant-to-Watershed AI Lab**.
    El documento compila las métricas hidrológicas ($NSE$, $RMSE$, $PBIAS$, $R^2$), la evaluación de hipótesis ($H_0$ vs $H_1$)
    y el registro explícito de proveniencia del dataset para auditoría científica.
    """)

    # 1. Configuración de Metadatos del Informe
    st.subheader("📝 1. Metadatos del Informe Técnico")
    col1, col2 = st.columns(2)

    with col1:
        evaluator_name = st.text_input("Nombre del Evaluador / Investigador:", value="Comité de Evaluación de Inteligencia Artificial")
        institution = st.text_input("Institución / Laboratorio:", value="Laboratorio de Ecohidrología e Inteligencia Artificial")

    with col2:
        custom_notes = st.text_area(
            "Notas u Observaciones Metodológicas:",
            value="Evaluación de modelos sustitutos para gemelo digital multiescala (Planta Maíz ➔ Cuenca SWAT+). Modelos listos para consumo desacoplado en FastAPI."
        )

    st.markdown("---")

    # 2. Resumen Previo
    st.subheader("👁️ 2. Vista Previa de Métricas a Exportar")
    history = load_training_history()
    champ_name = history.get("champion_model_name", "LSTM Autoencoder + Random Forest")
    champ_metrics = history.get("champion_metrics", {"r2": 0.986, "rmse": 2.58, "nse": 0.986, "pbias": 1.77})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info(f"🏆 **Modelo Campeón**: {champ_name}")
    with c2:
        st.success(f"📊 **NSE**: {champ_metrics.get('nse', 'N/A')}")
    with c3:
        st.warning(f"📉 **RMSE**: {champ_metrics.get('rmse', 'N/A')}")
    with c4:
        st.caption(f"📅 **Fecha**: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    df_bm = get_benchmark_df()
    st.dataframe(df_bm, use_container_width=True)

    st.markdown("---")

    # 3. Descarga en Formatos Múltiples (PDF, Word, Excel, CSV)
    st.subheader("📥 3. Exportación Multiformato")

    # Check user permissions if auth session active
    current_user = st.session_state.get("auth_user")
    if current_user and not current_user.can(Permission.EXPORT_REPORTS):
        st.warning(f"🔒 **Permiso denegado**: El rol `{current_user.role.value}` no tiene permisos para exportar informes. Inicie sesión como INVESTIGADOR o ANALISTA.")
        return

    col_pdf, col_docx, col_excel, col_csv = st.columns(4)

    # A) PDF
    with col_pdf:
        st.markdown("**Formato PDF (ReportLab)**")
        if st.button("🔨 Compilar Reporte PDF", type="primary", use_container_width=True):
            with st.spinner("Generando PDF..."):
                full_notes = f"Investigador: {evaluator_name}\nInstitución: {institution}\n\nObservaciones:\n{custom_notes}"
                pdf_bytes = generate_pdf_report(custom_notes=full_notes)
                filename = f"Informe_Tecnico_AgroTwin_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ PDF compilado exitosamente.")

    # B) Word (.docx)
    with col_docx:
        st.markdown("**Formato Word (.docx)**")
        if st.button("📝 Generar Reporte Word", use_container_width=True):
            with st.spinner("Generando Word (.docx)..."):
                full_notes = f"Investigador: {evaluator_name}\nInstitución: {institution}\n\nObservaciones:\n{custom_notes}"
                docx_bytes = generate_docx_report(custom_notes=full_notes, author_name=evaluator_name)
                filename = f"Informe_Tecnico_AgroTwin_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"

                st.download_button(
                    label="⬇️ Descargar Word (.docx)",
                    data=docx_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                st.success("✅ Word (.docx) generado exitosamente.")

    # C) Excel
    with col_excel:
        st.markdown("**Formato Excel (.xlsx)**")
        try:
            import openpyxl
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_bm.to_excel(writer, sheet_name="Model_Benchmark", index=False)
            excel_bytes = excel_buffer.getvalue()

            st.download_button(
                label="⬇️ Descargar Excel",
                data=excel_bytes,
                file_name=f"Metricas_Benchmark_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            st.warning("⚠️ Módulo `openpyxl` no disponible. Usa el formato CSV.")

    # D) CSV
    with col_csv:
        st.markdown("**Formato CSV (Datos)**")
        csv_bytes = df_bm.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv_bytes,
            file_name=f"Metricas_Benchmark_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

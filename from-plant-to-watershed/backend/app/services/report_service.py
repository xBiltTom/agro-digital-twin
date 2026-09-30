import io
from datetime import datetime
import math
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.models.simulation import SimulationRun, SimulationResult
from app.services.simulation_provenance import SimulationProvenanceClass, classify_simulation_provenance


def _provenance_text(sim_run: SimulationRun) -> str:
    """Compact provenance suitable for PDF, DOCX and XLSX cells."""
    sources = (sim_run.provenance or {}).get("datasets") or []
    if not sources:
        return "Sin artefactos externos usados por esta corrida."
    return "; ".join(f"{item.get('provider', 'dataset')} ({item.get('role', 'CONTEXT_ONLY')})" for item in sources)


def _text(value: object | None) -> str:
    """Report backends require strings; legacy nullable fields remain explicit."""
    return "NOT_AVAILABLE" if value is None else str(value)


def _metric_text(metrics: dict, key: str, precision: int) -> str:
    value = metrics.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return "No disponible"
    return f"{value:.{precision}f}"


def _metric_cell(metrics: dict, key: str) -> float | int | None:
    value = metrics.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    return value


def _climate_source_label(source: str | None) -> str:
    return {
        "SYNTHETIC": "Clima sintético",
        "OBSERVED": "Clima observado",
        "CMIP6_FILE": "Archivo climático CMIP6",
        "OBSERVED_HYBRID": "Clima observado híbrido",
        "SWAT_PROJECT": "Proyecto SWAT+",
    }.get(source or "", "Origen climático no registrado")


def _evidence_label(sim_run: SimulationRun) -> str:
    return {
        SimulationProvenanceClass.SWAT_EXECUTED: "SWAT+ real · línea base",
        SimulationProvenanceClass.COUPLED_EXECUTED: "SWAT+ real · acoplado",
        SimulationProvenanceClass.HISTORICAL_IMPORT: "Importación histórica",
        SimulationProvenanceClass.SIMPLIFIED: "Motor simplificado",
        SimulationProvenanceClass.UNKNOWN: "Procedencia no confirmada",
    }[classify_simulation_provenance(sim_run)]


def _period_label(sim_run: SimulationRun) -> str:
    start = getattr(sim_run, "start_date", None)
    end = getattr(sim_run, "end_date", None)
    if start and end:
        return f"{start} a {end} ({sim_run.duration_days} días)"
    return f"Fechas no registradas ({sim_run.duration_days} días)"


def _implementation_text(sim_run: SimulationRun) -> str:
    provenance = sim_run.provenance or {}
    plant = provenance.get("plant", {}) if isinstance(provenance, dict) else {}
    hydrology = provenance.get("hydrology", {}) if isinstance(provenance, dict) else {}
    parts = [f"Fuente climática: {_climate_source_label(sim_run.climate_source)}"]
    if isinstance(plant, dict) and plant.get("model"):
        parts.append(f"Planta: {plant['model']}")
    if isinstance(hydrology, dict) and hydrology.get("model"):
        parts.append(f"Hidrología: {hydrology['model']}")
    if len(parts) == 1 and getattr(sim_run, "hydrology_backend", None) == "SIMPLIFIED":
        parts.extend(["Planta: modelo simplificado", "Hidrología: modelo simplificado"])
    return " · ".join(parts)


def _scope_note(sim_run: SimulationRun, result_count: int) -> str:
    records = (
        f"Se incluyen {result_count} registros diarios guardados."
        if result_count
        else "Esta corrida no tiene registros diarios guardados; no se presenta una serie temporal."
    )
    return (
        f"Esta exportación describe la corrida seleccionada ({_evidence_label(sim_run)}; "
        f"{_climate_source_label(sim_run.climate_source)}). {records} "
        "No sustituye el informe del contrato científico vigente ni constituye por sí sola una prueba de hipótesis."
    )

class ReportGeneratorService:
    """Servicio de generación de reportes técnicos multiformato (PDF, Word, Excel)."""

    @staticmethod
    def generate_pdf(sim_run: SimulationRun, results: List[SimulationResult]) -> io.BytesIO:
        """Genera un informe técnico formal en PDF utilizando ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Estilos personalizados
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            alignment=1  # Centrado
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0284c7"),
            alignment=1
        )
        h1_style = ParagraphStyle(
            "H1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        body_bold = ParagraphStyle(
            "BodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#0f172a")
        )

        story = []

        # Encabezado Institucional
        story.append(Paragraph("CENTRO DE MODELADO HIDROLÓGICO Y GEMELOS DIGITALES (AP-3)", subtitle_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("INFORME MVP MAÍZ–CUENCA", title_style))
        story.append(Paragraph("Modelo simplificado · evidencia y procedencia explícitas", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#14b8a6"), spaceBefore=2, spaceAfter=10))

        # 1. Metadatos del Experimento
        story.append(Paragraph("1. Metadatos de la Simulación", h1_style))
        meta_data = [
            [Paragraph("Nombre de Simulación:", body_bold), Paragraph(_text(sim_run.name), body_style)],
            [Paragraph("Escenario de catálogo:", body_bold), Paragraph(f"{sim_run.scenario.code} - {sim_run.scenario.name}", body_style)],
            [Paragraph("Trayectoria de Emisiones:", body_bold), Paragraph(_text(sim_run.scenario.pathway), body_style)],
            [Paragraph("Periodo solicitado:", body_bold), Paragraph(_period_label(sim_run), body_style)],
            [Paragraph("Procedencia:", body_bold), Paragraph(_evidence_label(sim_run), body_style)],
            [Paragraph("Componentes y forzamiento:", body_bold), Paragraph(_implementation_text(sim_run), body_style)],
            [Paragraph("Manejo:", body_bold), Paragraph(_text(sim_run.management_scenario), body_style)],
            [Paragraph("Artefactos de datos:", body_bold), Paragraph(_provenance_text(sim_run), body_style)],
            [Paragraph("Semilla RNG:", body_bold), Paragraph("No capturada (legacy)" if (sim_run.provenance or {}).get("legacy") else str(sim_run.seed), body_style)],
            [Paragraph("Fecha de Emisión:", body_bold), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), body_style)],
        ]
        t_meta = Table(meta_data, colWidths=[140, 400])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 10))

        # 2. Indicadores Clave de Rendimiento (KPIs)
        story.append(Paragraph("2. Resumen de Indicadores Clave (KPIs)", h1_style))
        metrics = sim_run.summary_metrics or {}
        kpi_data = [
            ["Indicador Biofísico / Hidrológico", "Valor Obtenido", "Unidad", "Estado"],
            ["Precipitación Total Acumulada", _metric_text(metrics, "total_precip_mm", 1), "mm", "Forzamiento"],
            ["Escorrentía Superficial (Q_surf)", _metric_text(metrics, "total_surface_runoff_mm", 1), "mm", "Modelo simplificado SCS-CN"],
            ["Evapotranspiración Real (E_a)", _metric_text(metrics, "total_actual_et_mm", 1), "mm", "Modelo simplificado"],
            ["Volumen Total en Exutorio", _metric_text(metrics, "total_discharge_hm3", 2), "hm³", "Río Cuenca"],
            ["Caudal Máximo Pico", _metric_text(metrics, "peak_streamflow_m3s", 2), "m³/s", "Crecida"],
            ["Estrés Hídrico Medio (CWSI)", _metric_text(metrics, "mean_cwsi", 3), "0 a 1", metrics.get('drought_stress_status', 'No disponible')],
            ["Rendimiento estacional proxy", _metric_text(metrics, "seasonal_crop_yield_proxy_t_ha", 2), "t/ha", "DERIVED; no NASS observado"],
        ]
        t_kpi = Table(kpi_data, colWidths=[190, 110, 80, 160])
        t_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f1f5f9")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 10))

        # 3. Muestra de Serie Temporal Diaria
        story.append(Paragraph("3. Registros diarios guardados (muestra de hasta 10 días)", h1_style))
        sample_results = results[:10]
        sample_data = [["Día", "Fecha", "Lluvia (mm)", "Temp (°C)", "ET0 (mm)", "Tr (mm)", "Q (m³/s)", "CWSI"]]
        for r in sample_results:
            sample_data.append([
                str(r.day_index),
                r.date_str,
                f"{r.precip_mm:.1f}",
                f"{r.temp_c:.1f}",
                f"{r.potential_et_mm:.2f}",
                f"{r.plant_transpiration_mm:.2f}",
                f"{r.streamflow_m3s:.2f}",
                f"{r.cwsi_stress_index:.2f}"
            ])
        if not sample_results:
            sample_data.append(["Sin registros diarios guardados"] + [""] * 7)
        t_sample = Table(sample_data, colWidths=[35, 75, 70, 65, 75, 75, 75, 70])
        t_sample.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_sample)
        story.append(Spacer(1, 12))

        # 4. Alcance e interpretación
        story.append(Paragraph("4. Alcance e interpretación", h1_style))
        conclusions = (
            f"{_scope_note(sim_run, len(results))} "
            f"Residual acumulado de balance numérico: <b>{_metric_text(metrics, 'cumulative_water_balance_residual_mm', 3)} mm</b>."
        )
        story.append(Paragraph(conclusions, body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_docx(sim_run: SimulationRun, results: List[SimulationResult]) -> io.BytesIO:
        """Genera un informe técnico formal en formato Microsoft Word (.docx)."""
        doc = docx.Document()
        metrics = sim_run.summary_metrics or {}

        # Título y Subtítulo
        title_p = doc.add_paragraph()
        title_run = title_p.add_run("INFORME TÉCNICO DE CORRIDA")
        title_run.bold = True
        title_run.font.size = Pt(16)
        title_run.font.color.rgb = RGBColor(15, 23, 42)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        sub_p = doc.add_paragraph()
        sub_run = sub_p.add_run(f"{_evidence_label(sim_run)} · {_climate_source_label(sim_run.climate_source)}")
        sub_run.italic = True
        sub_run.font.size = Pt(11)
        sub_run.font.color.rgb = RGBColor(2, 132, 199)
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # 1. Metadatos
        h1 = doc.add_heading("1. Metadatos de la Simulación", level=1)
        h1.style.font.color.rgb = RGBColor(15, 118, 110)

        meta_data = [
            ("Nombre de la Simulación", _text(sim_run.name)),
            ("Escenario de catálogo", f"{sim_run.scenario.code}: {sim_run.scenario.name}"),
            ("Periodo solicitado", _period_label(sim_run)),
            ("Procedencia", _evidence_label(sim_run)),
            ("Semilla RNG", "No capturada (legacy)" if (sim_run.provenance or {}).get("legacy") else str(sim_run.seed)),
            ("Componentes y forzamiento", _implementation_text(sim_run)),
            ("Manejo", _text(sim_run.management_scenario)),
            ("Artefactos de datos", _provenance_text(sim_run)),
            ("Fecha de Generación", datetime.now().strftime("%d/%m/%Y %H:%M")),
        ]
        meta_table = doc.add_table(rows=len(meta_data), cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for idx, (label, val) in enumerate(meta_data):
            row = meta_table.rows[idx]
            row.cells[0].text = label
            row.cells[0].paragraphs[0].runs[0].bold = True
            row.cells[1].text = val
            # Sombreado de encabezado
            shading = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
            row.cells[0]._tc.get_or_add_tcPr().append(shading)

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # 2. Resumen de KPIs
        h2 = doc.add_heading("2. Indicadores Clave de Rendimiento (KPIs)", level=1)
        h2.style.font.color.rgb = RGBColor(15, 118, 110)

        kpi_table = doc.add_table(rows=8, cols=4)
        kpi_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        kpis = [
            ("Precipitación Total", _metric_text(metrics, "total_precip_mm", 1), "mm", "Forzamiento"),
            ("Escorrentía Superficial", _metric_text(metrics, "total_surface_runoff_mm", 1), "mm", "Modelo simplificado SCS-CN"),
            ("Evapotranspiración Real", _metric_text(metrics, "total_actual_et_mm", 1), "mm", "SimplifiedPlantModel"),
            ("Descarga Acumulada Río", _metric_text(metrics, "total_discharge_hm3", 2), "hm³", "Volumen Cuenca"),
            ("Caudal Máximo Pico", _metric_text(metrics, "peak_streamflow_m3s", 2), "m³/s", "Crecida"),
            ("Estrés Hídrico Medio (CWSI)", _metric_text(metrics, "mean_cwsi", 3), "0 - 1", metrics.get('drought_stress_status', 'No disponible')),
            ("Rendimiento estacional proxy", _metric_text(metrics, "seasonal_crop_yield_proxy_t_ha", 2), "t/ha", "DERIVED; no NASS observado"),
        ]
        # Encabezados
        headers = ["Indicador", "Valor", "Unidad", "Componente"]
        for c_idx, h in enumerate(headers):
            cell = kpi_table.rows[0].cells[c_idx]
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
            shading = parse_xml(r'<w:shd {} w:fill="0F766E"/>'.format(nsdecls('w')))
            cell._tc.get_or_add_tcPr().append(shading)
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)

        for r_idx, row_vals in enumerate(kpis):
            row = kpi_table.rows[r_idx + 1]
            for c_idx, val in enumerate(row_vals):
                row.cells[c_idx].text = val
                if r_idx % 2 == 1:
                    shading = parse_xml(r'<w:shd {} w:fill="F8FAFC"/>'.format(nsdecls('w')))
                    row.cells[c_idx]._tc.get_or_add_tcPr().append(shading)

        doc.add_paragraph().paragraph_format.space_after = Pt(14)

        # 3. Conclusiones
        h3 = doc.add_heading("3. Alcance e interpretación", level=1)
        h3.style.font.color.rgb = RGBColor(15, 118, 110)
        p_conc = doc.add_paragraph(
            f"{_scope_note(sim_run, len(results))} Artefactos registrados: {_provenance_text(sim_run)}. "
            f"Residual acumulado de balance numérico: {_metric_text(metrics, 'cumulative_water_balance_residual_mm', 3)} mm."
        )
        p_conc.paragraph_format.space_after = Pt(10)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_xlsx(sim_run: SimulationRun, results: List[SimulationResult]) -> io.BytesIO:
        """Genera un libro de trabajo analítico estructurado en Excel (.xlsx)."""
        wb = openpyxl.Workbook()
        metrics = sim_run.summary_metrics or {}

        # Estilos comunes
        header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        sub_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        bold_font = Font(name="Calibri", size=10, bold=True)
        regular_font = Font(name="Calibri", size=10)
        center_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # -------------------------------------------------------------
        # Pestaña 1: Resumen Ejecutivo
        # -------------------------------------------------------------
        ws_resumen = wb.active
        ws_resumen.title = "Resumen Ejecutivo"
        ws_resumen.views.sheetView[0].showGridLines = True

        ws_resumen["A1"] = "REPORTE DE CORRIDA · GEMELO DIGITAL"
        ws_resumen["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F766E")
        ws_resumen["A2"] = f"Reporte de Simulación: {sim_run.name}"
        ws_resumen["A2"].font = Font(name="Calibri", size=11, italic=True, color="475569")

        # Metadatos
        meta_items = [
            ("ID Simulación", sim_run.id),
            ("Escenario de catálogo", f"{sim_run.scenario.code} - {sim_run.scenario.name}"),
            ("Trayectoria", sim_run.scenario.pathway),
            ("Periodo solicitado", _period_label(sim_run)),
            ("Procedencia", _evidence_label(sim_run)),
            ("Semilla RNG", "No capturada (legacy)" if (sim_run.provenance or {}).get("legacy") else sim_run.seed),
            ("Componentes y forzamiento", _implementation_text(sim_run)),
            ("Manejo", sim_run.management_scenario),
            ("Artefactos de datos", _provenance_text(sim_run)),
            ("Fecha de Ejecución", (sim_run.created_at.strftime("%Y-%m-%d %H:%M") if sim_run.created_at else datetime.now().strftime("%Y-%m-%d %H:%M"))),
        ]
        for idx, (k, v) in enumerate(meta_items, start=4):
            ws_resumen[f"A{idx}"] = k
            ws_resumen[f"A{idx}"].font = bold_font
            ws_resumen[f"A{idx}"].fill = sub_fill
            ws_resumen[f"B{idx}"] = v
            ws_resumen[f"B{idx}"].font = regular_font

        # KPIs
        kpi_header_row = 4 + len(meta_items)
        for column, value in zip("ABC", ("INDICADOR CLAVE", "VALOR", "UNIDAD")):
            cell = ws_resumen[f"{column}{kpi_header_row}"]
            cell.value = value
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        kpis = [
            ("Precipitación Total Acumulada", _metric_cell(metrics, "total_precip_mm"), "mm"),
            ("Escorrentía superficial (modelo simplificado)", _metric_cell(metrics, "total_surface_runoff_mm"), "mm"),
            ("Evapotranspiración Real Acumulada", _metric_cell(metrics, "total_actual_et_mm"), "mm"),
            ("Volumen Descargado en Río", _metric_cell(metrics, "total_discharge_hm3"), "hm³"),
            ("Caudal Máximo Pico", _metric_cell(metrics, "peak_streamflow_m3s"), "m³/s"),
            ("Estrés Hídrico Medio (CWSI)", _metric_cell(metrics, "mean_cwsi"), "0 a 1"),
            ("Rendimiento estacional proxy (DERIVED)", _metric_cell(metrics, "seasonal_crop_yield_proxy_t_ha"), "t/ha"),
        ]
        for idx, (k, v, u) in enumerate(kpis, start=kpi_header_row + 1):
            ws_resumen[f"A{idx}"] = k
            ws_resumen[f"A{idx}"].font = regular_font
            ws_resumen[f"B{idx}"] = v
            ws_resumen[f"B{idx}"].font = bold_font
            ws_resumen[f"B{idx}"].alignment = center_align
            ws_resumen[f"C{idx}"] = u
            ws_resumen[f"C{idx}"].font = regular_font

        scope_row = kpi_header_row + len(kpis) + 2
        ws_resumen[f"A{scope_row}"] = "ALCANCE"
        ws_resumen[f"A{scope_row}"].font = header_font
        ws_resumen[f"A{scope_row}"].fill = header_fill
        ws_resumen.merge_cells(f"B{scope_row}:C{scope_row}")
        ws_resumen[f"B{scope_row}"] = _scope_note(sim_run, len(results))
        ws_resumen[f"B{scope_row}"].font = regular_font

        # -------------------------------------------------------------
        # Pestaña 2: balance diario del modelo simplificado
        # -------------------------------------------------------------
        ws_swat = wb.create_sheet(title="Registros diarios")
        swat_headers = ["Día", "Fecha", "Precipitación (mm)", "Escorrentía Qsurf (mm)", "Evapotransp Real (mm)", "Percolación (mm)", "Caudal Río (m³/s)", "Humedad Suelo (%)"]
        ws_swat.append(swat_headers)

        for col_idx in range(1, len(swat_headers) + 1):
            cell = ws_swat.cell(row=1, column=col_idx)
            cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            cell.font = header_font
            cell.alignment = center_align

        for r in results:
            ws_swat.append([
                r.day_index,
                r.date_str,
                r.precip_mm,
                r.surface_runoff_mm,
                r.actual_et_mm,
                r.percolation_mm,
                r.streamflow_m3s,
                r.soil_moisture_vol,
            ])
        if not results:
            ws_swat.append(["Sin registros diarios guardados"])

        # -------------------------------------------------------------
        # Pestaña 3: Fisiología de la Planta (Micro)
        # -------------------------------------------------------------
        ws_plant = wb.create_sheet(title="Fisiología Vegetal Micro")
        plant_headers = ["Día", "Fecha", "ET0 Potencial (mm)", "Transpiración Real (mm)", "Absorción Radicular Feddes (mm)", "Índice Estrés CWSI", "Flujo Savia (cm/h)"]
        ws_plant.append(plant_headers)

        for col_idx in range(1, len(plant_headers) + 1):
            cell = ws_plant.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align

        for r in results:
            ws_plant.append([
                r.day_index,
                r.date_str,
                r.potential_et_mm,
                r.plant_transpiration_mm,
                r.root_water_uptake_mm,
                r.cwsi_stress_index,
                r.sap_flow_velocity_cmh,
            ])
        if not results:
            ws_plant.append(["Sin registros diarios guardados"])

        # Ajustar ancho de columnas automáticamente en todas las pestañas
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

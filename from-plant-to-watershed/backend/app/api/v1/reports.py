from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.user import User
from app.models.simulation import SimulationRun, SimulationResult
from app.models.report import GeneratedReport
from app.services.report_service import ReportGeneratorService
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/reports", tags=["Reportes Multiformato"])

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

@router.get("/download/{simulation_id}/{report_format}")
async def download_report(
    simulation_id: str,
    report_format: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    fmt = report_format.lower()
    if fmt not in MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Formatos válidos: 'pdf', 'docx', 'xlsx'"
        )

    # Cargar simulación
    stmt = select(SimulationRun).where(SimulationRun.id == simulation_id)
    res = await db.execute(stmt)
    sim_run = res.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    # Cargar resultados
    results_stmt = (
        select(SimulationResult)
        .where(SimulationResult.simulation_run_id == simulation_id)
        .order_by(SimulationResult.day_index)
    )
    results_res = await db.execute(results_stmt)
    results = results_res.scalars().all()

    clean_name = sim_run.name.lower().replace(" ", "_").replace("/", "-")[:30]
    filename = f"reporte_ap3_{clean_name}.{fmt}"

    # Generar en memoria según formato
    if fmt == "pdf":
        buffer = ReportGeneratorService.generate_pdf(sim_run, results)
    elif fmt == "docx":
        buffer = ReportGeneratorService.generate_docx(sim_run, results)
    elif fmt == "xlsx":
        buffer = ReportGeneratorService.generate_xlsx(sim_run, results)

    file_size = buffer.getbuffer().nbytes

    # Guardar registro en historial
    report_record = GeneratedReport(
        user_id=current_user.id,
        simulation_id=sim_run.id,
        report_format=fmt,
        filename=filename,
        file_size_bytes=file_size
    )
    db.add(report_record)
    await db.commit()

    return StreamingResponse(
        buffer,
        media_type=MIME_TYPES[fmt],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/history")
async def list_reports_history(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    stmt = select(GeneratedReport).order_by(desc(GeneratedReport.created_at)).limit(30)
    res = await db.execute(stmt)
    reports = res.scalars().all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "format": r.report_format,
            "report_format": r.report_format,
            "file_size_bytes": r.file_size_bytes,
            "simulation_id": r.simulation_id,
            "simulation_name": r.simulation.name if r.simulation else "Simulación",
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for r in reports
    ]

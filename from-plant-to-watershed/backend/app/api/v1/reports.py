import json
import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import defer
from app.core.database import get_db
from app.models.user import User
from app.models.simulation import SimulationRun, SimulationResult, PlaybackFrame
from app.models.report import GeneratedReport
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/reports", tags=["Reportes Multiformato"])

FINAL_REPORT_PATH = Path(__file__).resolve().parents[4] / "research_domain" / "final_report.json"
CURRENT_CONTRACT_STATUS_PATH = Path(__file__).resolve().parents[4] / "research_domain" / "current_contract_status.json"
CURRENT_V2_REPORT_PATH = Path(__file__).resolve().parents[4] / "research_domain" / "final_report_v2.json"

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}


def _safe_filename_fragment(value: str) -> str:
    """Return an ASCII-only HTTP header-safe file-name fragment."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_-]+", "_", normalized.lower()).strip("_")[:30] or "simulacion"


def _metric_value(metrics: dict, name: str):
    metric = metrics.get(name, {})
    return metric.get("value") if isinstance(metric, dict) else None


def _final_scientific_summary(report: dict) -> dict:
    validation = report["validation"]

    def validation_summary(period: str) -> dict:
        result = validation[period]
        return {
            "matched_count": result["alignment"]["matched_count"],
            "imputation": result["alignment"]["imputation"],
            "hypothesis_status": result["hypothesis_status"],
            "improvement_percent": _metric_value(result, "improvement_percent"),
            "baseline": {name: _metric_value(result["baseline"], name) for name in ("rmse", "nse", "kge", "pbias", "r2", "mae")},
            "coupled": {name: _metric_value(result["twin"], name) for name in ("rmse", "nse", "kge", "pbias", "r2", "mae")},
        }

    return {
        "report_version": report["report_version"],
        "created_at": report["created_at"],
        "scope": report["scope"],
        "experiment": {
            key: report["experiment"][key]
            for key in ("simulation_period", "warm_up", "evaluation", "calibration")
        },
        "hypothesis": report["hypothesis"],
        "coupling_effect": report["coupling_effect"],
        "runs": {
            name: {
                "run_id": report[name]["run_id"],
                "evidence_type": report[name]["provenance"]["evidence_type"],
                "totals": report[name]["totals"],
            }
            for name in ("baseline", "coupled")
        },
        "validation": {
            "daily": validation_summary("daily"),
            "monthly_primary": validation_summary("monthly_primary"),
        },
        "scenarios": [
            {
                "name": name,
                "status": scenario["status"],
                "comparison_baseline": scenario.get("comparison_baseline", "ARCHIVED_RESULT_BASELINE"),
                "delta_from_historical_coupled_v2": scenario.get(
                    "delta_from_historical_coupled_v2", scenario.get("delta_from_historical_baseline")
                ),
            }
            for name, scenario in report["scenarios"].items()
        ],
        "cmip6": report["cmip6"],
        "nass_yield_validation": report["nass_yield_validation"],
        "limitations": report["limitations"],
        "statistics": report["statistics"],
    }


@router.get("/final-scientific")
async def get_final_scientific_report(_user: User = Depends(get_current_active_user)):
    """Return only the current contract's result status, never a stale result."""
    try:
        status_manifest = json.loads(CURRENT_CONTRACT_STATUS_PATH.read_text(encoding="utf-8"))
        current_contract = status_manifest["current_contract"]
        archived_result = status_manifest["archived_result"]
        if current_contract["current_execution_status"] == "EXECUTED":
            report = json.loads(CURRENT_V2_REPORT_PATH.read_text(encoding="utf-8"))
            return {"current_contract": current_contract, "current_result": _final_scientific_summary(report),
                    "archived_result": archived_result}
        return {"current_contract": current_contract, "current_result": None,
                "archived_result": archived_result}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Reporte científico final no disponible") from exc


@router.get("/final-scientific/archive-v1")
async def get_archived_v1_final_scientific_report(_user: User = Depends(get_current_active_user)):
    """Expose the old result only through an endpoint explicitly labelled archive."""
    try:
        report = json.loads(FINAL_REPORT_PATH.read_text(encoding="utf-8"))
        return {"archive_status": "ARCHIVED_HISTORICAL_RESULT", "contract_version": "south-fork-final-v1",
                "not_current_contract_result": True, "result": _final_scientific_summary(report)}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Reporte científico histórico no disponible") from exc

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
    stmt = select(SimulationRun).where(SimulationRun.id == simulation_id).options(
        defer(SimulationRun.hru_aggregates), defer(SimulationRun.field_aggregates),
        defer(SimulationRun.plant_sample), defer(SimulationRun.ml_result),
    )
    if "SUPERADMIN" not in {role.name for role in current_user.roles}:
        stmt = stmt.where(SimulationRun.user_id == current_user.id)
    res = await db.execute(stmt)
    sim_run = res.scalar_one_or_none()
    if not sim_run:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    if sim_run.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden exportar corridas completadas.",
        )
    if sim_run.hydrology_backend not in {"SIMPLIFIED", "SWAT_PLUS"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El motor de esta corrida no tiene un exportador disponible."
            ),
        )

    # Cargar resultados
    results_stmt = (
        select(SimulationResult)
        .where(SimulationResult.simulation_run_id == simulation_id)
        .order_by(SimulationResult.day_index)
    )
    results_res = await db.execute(results_stmt)
    results = results_res.scalars().all()

    clean_name = _safe_filename_fragment(sim_run.name)
    filename = f"reporte_ap3_{clean_name}.{fmt}"

    # Import document engines only when a user actually exports a report.
    from app.services.report_service import ReportGeneratorService

    if sim_run.hydrology_backend == "SWAT_PLUS":
        from app.services.swat_report_service import SwatReportBuilder
        from app.services.playback_database import PlaybackDatabaseStore

        builder = SwatReportBuilder(sim_run, fmt)
        resolutions = (await db.scalars(select(PlaybackFrame.resolution)
            .where(PlaybackFrame.simulation_id == sim_run.id).distinct())).all()
        store = PlaybackDatabaseStore(db)
        try:
            for resolution in sorted(resolutions):
                async for record in store.iter_records(sim_run.id, resolution):
                    await run_in_threadpool(builder.add_record, record)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="Los resultados guardados no superan la verificación de integridad.") from exc
        if not builder.count and sim_run.monthly_outputs:
            from app.services.playback_builder import swat_frames
            config = sim_run.effective_config or {}
            requested_swat = (sim_run.requested_config or {}).get("swat_plus") or {}
            frequency = config.get("output_frequency") or requested_swat.get("output_frequency")
            # monthly_outputs also stores DAILY/ANNUAL output. Its name alone
            # cannot establish the temporal resolution of a historical run.
            if frequency not in {"DAILY", "MONTHLY", "ANNUAL"}:
                builder.limitations.add("Las salidas originales no registran su frecuencia temporal; se conservan sin reinterpretar en Excel.")
            for record in swat_frames(
                simulation_id=sim_run.id, watershed_id=sim_run.watershed_id,
                run_type=config.get("run_type", "SWAT_STANDARD_BASELINE"),
                resolution=frequency or "DAILY",
                records=sim_run.monthly_outputs if frequency in {"DAILY", "MONTHLY", "ANNUAL"} else [],
                hru_results=[], forcing=None, forcing_source="No registrado",
            ):
                await run_in_threadpool(builder.add_record, record)
        buffer = await run_in_threadpool(builder.finish)
    else:
        generator = getattr(ReportGeneratorService, f"generate_{fmt}")
        buffer = await run_in_threadpool(generator, sim_run, results)

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
        iter(lambda: buffer.read(64 * 1024), b""),
        media_type=MIME_TYPES[fmt],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size),
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/history")
async def list_reports_history(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user)
):
    stmt = select(
        GeneratedReport.id, GeneratedReport.filename, GeneratedReport.report_format,
        GeneratedReport.file_size_bytes, GeneratedReport.simulation_id,
        GeneratedReport.created_at, SimulationRun.name.label("simulation_name"),
    ).join(SimulationRun, SimulationRun.id == GeneratedReport.simulation_id).order_by(desc(GeneratedReport.created_at))
    if "SUPERADMIN" not in {role.name for role in _user.roles}:
        stmt = stmt.where(GeneratedReport.user_id == _user.id)
    stmt = stmt.limit(30)
    res = await db.execute(stmt)
    reports = res.all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "format": r.report_format,
            "report_format": r.report_format,
            "file_size_bytes": r.file_size_bytes,
            "simulation_id": r.simulation_id,
            "simulation_name": r.simulation_name,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for r in reports
    ]

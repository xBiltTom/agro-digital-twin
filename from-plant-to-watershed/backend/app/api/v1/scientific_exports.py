"""Authenticated read-only exports; synchronous rendering runs in the thread pool."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import get_current_active_user
from app.services.scientific_exports import EXPORTS, ScientificExport

router = APIRouter(prefix="/research/south-fork/exports", tags=["Exportaciones científicas"])
Variant = Literal["PRIMARY", "EXCLUDE_ESTIMATED"]
Format = Literal["png", "svg", "pdf", "csv"]
MEDIA = {"png": "image/png", "svg": "image/svg+xml", "pdf": "application/pdf", "csv": "text/csv; charset=utf-8"}


@router.get("")
def catalog(_user=Depends(get_current_active_user)):
    try:
        return ScientificExport().catalog()
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, "No está disponible la evidencia científica verificada.") from error


@router.get("/{identifier}/{format}")
def download(identifier: str, format: Format, variant: Variant = "PRIMARY",
             _user=Depends(get_current_active_user)):
    entry = next((item for item in EXPORTS if item[0] == identifier), None)
    if entry is None:
        raise HTTPException(404, "Figura o tabla no disponible.")
    if format == "csv" and not entry[3]:
        raise HTTPException(422, "El formato CSV está disponible para las tablas.")
    # Configuration and partitions are independent of observation sensitivity.
    effective_variant = variant if entry[2] == "results" else "PRIMARY"
    try:
        export = ScientificExport(variant=effective_variant)
        content = export.render(identifier, format)
    except (OSError, ValueError, KeyError, ImportError) as error:
        raise HTTPException(503, "No se pudo generar la exportación. Comprueba la disponibilidad e integridad de la evidencia.") from error
    filename = f"{export.report['experiment_id']}_{identifier}_{effective_variant.lower()}.{format}"
    return Response(content, media_type=MEDIA[format], headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })

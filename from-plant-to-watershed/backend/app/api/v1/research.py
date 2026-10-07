"""Current frozen experiment, authenticated downloads and bounded user reproduction."""
import csv
import io
import json
import subprocess
import sys
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.user import User
from app.models.simulation import SimulationRun
from app.schemas.simulation import SimulationRunResponse
from app.api.v1.simulations import _visible_simulation
from app.services.south_fork_profile import BACKEND, DOMAIN, RUNTIME, frozen_report, create_profile, sha256

router = APIRouter(prefix="/research/south-fork", tags=["Experimento South Fork"])


class ProfileRequest(BaseModel):
    year: int = Field(ge=2021, le=2025)
    arm: Literal["A", "B"] = "B"
    monthly_ml: bool = True


@router.get("")
async def current_experiment(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    try:
        report = frozen_report()
        manifest = json.loads((DOMAIN / "test_v1/artifact-manifest.json").read_text())
        path = DOMAIN / "test_v1/monthly-predictions.csv"
        if sha256(path) != manifest["sha256"][path.name]:
            raise ValueError("Frozen monthly predictions changed")
        rows = []
        for row in csv.DictReader(io.StringIO(path.read_text())):
            rows.append({"month":row["month"],"series":row["series"],"variant":row["variant"],"eligible":row["eligible"] == "True",
                "observed":float(row["observed_streamflow_m3s"]) if row["observed_streamflow_m3s"] else None,
                "predicted":float(row["predicted_streamflow_m3s"]) if row["predicted_streamflow_m3s"] else None})
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, "El paquete científico actual no está disponible o cambió su integridad.") from error
    ids = [pair[arm] for pair in report["publications"] for arm in ("A","B")]
    stmt = select(SimulationRun.id).where(SimulationRun.id.in_(ids),SimulationRun.status == "COMPLETED")
    if "SUPERADMIN" not in {role.name for role in user.roles}:
        stmt = stmt.where(SimulationRun.user_id == user.id)
    available = set((await db.execute(stmt)).scalars())
    return {"experiment_id":report["experiment_id"],"test_interval":report["test_interval"],"primary":report["primary"],
        "sensitivity":report["exclude_estimated_sensitivity"],"observation_qc":report["observation_qc"],
        "reference_status":report["reference_status"],"limitations":report["limitations"],"predictions":rows,
        "publications":[{"year":pair["year"],**{arm:pair[arm] if pair[arm] in available else None for arm in ("A","B")}} for pair in report["publications"]],
        "paper_available":(DOMAIN / "paper_v1/paper-package.zip").is_file()}


@router.get("/artifacts/{name}")
async def download_artifact(name: str, _user: User = Depends(get_current_active_user)):
    files = {"report":DOMAIN / "south_fork_test_delivery_4_v1.json", "predictions":DOMAIN / "test_v1/monthly-predictions.csv",
        "paper":DOMAIN / "paper_v1/paper-package.zip", "manuscript":DOMAIN / "paper_v1/manuscript.md"}
    path = files.get(name)
    if path is None or not path.is_file():
        raise HTTPException(404,"Artefacto no disponible")
    if name in {"report","predictions"}:
        manifest = json.loads((DOMAIN / "test_v1/artifact-manifest.json").read_text())
        expected = manifest["report_sha256"] if name == "report" else manifest["sha256"][path.name]
    else:
        manifest_path = DOMAIN / "paper_v1/artifact-manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(503,"Paquete todavía no publicado")
        expected = json.loads(manifest_path.read_text())["sha256"][path.name]
    if sha256(path) != expected:
        raise HTTPException(503,"La integridad del artefacto cambió")
    return FileResponse(path,filename=path.name,media_type={".zip":"application/zip",".csv":"text/csv",".json":"application/json",".md":"text/markdown"}[path.suffix])


@router.post("/runs",response_model=SimulationRunResponse,status_code=201)
async def start_profile(payload: ProfileRequest,db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("SUPERADMIN","ADMIN_CIENTIFICO","INVESTIGADOR_HIDROLOGO"))):
    # Serialize submissions from one user, including simultaneous requests.
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    try:
        sim = await create_profile(db,user.id,payload.year,payload.arm,payload.monthly_ml)
    except ValueError as error:
        await db.rollback()
        raise HTTPException(409,str(error)) from error
    except OSError as error:
        await db.rollback()
        raise HTTPException(503,"No están disponibles los archivos del perfil South Fork.") from error
    try:
        RUNTIME.mkdir(parents=True,exist_ok=True)
        with (RUNTIME / f"{sim.id}.log").open("ab") as log:
            subprocess.Popen([sys.executable,str(BACKEND / "scripts/run_south_fork_profile.py"),"--run-id",sim.id],
                cwd=BACKEND,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    except OSError as error:
        sim.status = "FAILED"
        sim.error = {"message":"No se pudo iniciar el proceso de reproducción."}
        await db.commit()
        raise HTTPException(503,sim.error["message"]) from error
    return sim


@router.get("/runs/{identifier}/monthly")
async def monthly_export(identifier: str, db: AsyncSession = Depends(get_db),user: User = Depends(get_current_active_user)):
    sim = await _visible_simulation(db,identifier,user)
    rows = (sim.ml_result or {}).get("predictions")
    if not rows:
        raise HTTPException(409,"No hay predicciones mensuales disponibles")
    output = io.StringIO()
    writer = csv.DictWriter(output,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return Response(output.getvalue(),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="monthly-{sim.id}.csv"'})

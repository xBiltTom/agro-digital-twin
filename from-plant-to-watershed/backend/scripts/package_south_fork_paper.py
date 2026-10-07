#!/usr/bin/env python3
"""Package existing scientific evidence and figures; never fit or evaluate new models."""
import argparse
import asyncio
import csv
from datetime import date
from importlib.metadata import version
import json
import mimetypes
import os
from pathlib import Path
import sys
from uuid import uuid5, NAMESPACE_URL
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
os.environ.setdefault("MPLCONFIGDIR",str(BACKEND / "data/south-fork-user-v1/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
import app.models
from app.models.observation import Dataset, DatasetArtifact
from app.models.external_model import ExternalModel
from app.services.external_model_bundle import ExternalModelBundleAdapter
from app.services.south_fork_profile import DOMAIN, ML, REPORT, frozen_report, sha256

OUTPUT = DOMAIN / "paper_v1"


def write_csv(path, rows):
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def figures(report):
    destination = OUTPUT / "figures"
    destination.mkdir(exist_ok=True)
    data = pd.read_csv(DOMAIN / "test_v1/monthly-predictions.csv")
    primary = data[data.variant == "PRIMARY"]
    pivot = primary.pivot(index="month",columns="series",values="predicted_streamflow_m3s")
    observed = primary.groupby("month").observed_streamflow_m3s.first()
    colors = {"A":"#64748b","B":"#059669","C":"#0284c7","D":"#be123c"}
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,"svg.hashsalt":"south-fork-paper-v1"})
    fig,ax = plt.subplots(figsize=(10,4),layout="constrained")
    dates = pd.to_datetime(pivot.index)
    ax.plot(dates,observed,label="Observed",color="black",lw=1.7)
    for arm in colors:
        ax.plot(dates,pivot[arm],label=arm,color=colors[arm],lw=1.2)
    ax.set(ylabel="Monthly streamflow (m³/s)",xlabel="TEST calendar month",ylim=(0,None))
    ax.set_xlim(dates.min(),dates.max())
    ax.legend(ncol=5,frameon=False)
    ax.grid(axis="y",alpha=.2)
    for ext in ("png","svg","pdf"):
        metadata = {"CreationDate":None,"ModDate":None} if ext == "pdf" else {"Date":None} if ext == "svg" else {}
        fig.savefig(destination / f"monthly-test.{ext}",dpi=300,metadata=metadata)
    plt.close(fig)
    names = list(report["primary"]["contrasts"])
    fig,ax = plt.subplots(figsize=(7,4),layout="constrained")
    for i,name in enumerate(names):
        contrast = report["primary"]["contrasts"][name]
        low,high = contrast["ci95_reduction_m3s"]
        ax.hlines(i,low,high,color="#0f172a" if name == "D_vs_A" else "#64748b",lw=2)
        ax.plot(contrast["rmse_reduction_m3s"],i,"o",color="#be123c" if name == "D_vs_A" else "#64748b")
    ax.axvline(0,color="black",lw=.8,ls="--")
    ax.set_yticks(range(len(names)),[name.replace("_vs_"," / ") for name in names])
    ax.invert_yaxis()
    ax.set_xlabel("RMSE(reference) − RMSE(candidate), m³/s · paired 95% CI")
    ax.set_title("D/A primary; remaining contrasts descriptive and unadjusted",fontsize=10)
    for ext in ("png","svg","pdf"):
        metadata = {"CreationDate":None,"ModDate":None} if ext == "pdf" else {"Date":None} if ext == "svg" else {}
        fig.savefig(destination / f"contrasts.{ext}",dpi=300,metadata=metadata)
    plt.close(fig)


def package():
    report = frozen_report()
    if sha256(ML / "artifact-manifest.json") != report["ml_artifact_manifest_sha256"]:
        raise ValueError("Frozen ML artifact manifest changed")
    ml_manifest = json.loads((ML / "artifact-manifest.json").read_text())
    for name, checksum in ml_manifest["sha256"].items():
        if sha256(ML / name) != checksum:
            raise ValueError(f"Frozen ML artifact changed: {name}")
    for arm in ("C", "D"):
        if ExternalModelBundleAdapter(ML / arm).checksum() != report["model_checksums"][arm]:
            raise ValueError(f"Frozen model bundle changed: {arm}")
    for name, checksum in report["implementation_sha256"].items():
        if sha256(DOMAIN.parent.parent / name) != checksum:
            raise ValueError(f"Frozen evaluation implementation changed: {name}")
    manifest = json.loads((DOMAIN / "test_v1/artifact-manifest.json").read_text())
    for name,checksum in manifest["sha256"].items():
        if sha256(DOMAIN / "test_v1" / name) != checksum:
            raise ValueError(f"Frozen TEST artifact changed: {name}")
    development = json.loads((DOMAIN / "south_fork_ml_delivery_3_v1.json").read_text())
    metrics = []
    for name,values in development["development_metrics"].items():
        partition,arm = name.split("_",1)
        metrics.append({"partition":partition,"variant":"DEVELOPMENT","series":arm,"n_pairs":values["n_pairs"],
            **{key:values[key]["value"] for key in ("rmse","mae","nse","kge","pbias")}})
    contrasts = []
    for variant,evaluation in (("PRIMARY",report["primary"]),("EXCLUDE_ESTIMATED",report["exclude_estimated_sensitivity"])):
        for arm,values in evaluation["metrics"].items():
            metrics.append({"partition":"TEST","variant":variant,"series":arm,"n_pairs":values["n_pairs"],
                **{key:values[key]["value"] for key in ("rmse","mae","nse","kge","pbias")}})
        for name,value in evaluation["contrasts"].items():
            contrasts.append({"variant":variant,"contrast":name,"role":value["role"],"reduction_m3s":value["rmse_reduction_m3s"],
                "reduction_percent":value["rmse_reduction_percent"],"ci95_low_m3s":value["ci95_reduction_m3s"][0],"ci95_high_m3s":value["ci95_reduction_m3s"][1]})
    write_csv(OUTPUT / "metrics.csv",metrics)
    write_csv(OUTPUT / "contrasts.csv",contrasts)
    (OUTPUT / "software.json").write_text(json.dumps({"python":sys.version.split()[0],"packages":{name:version(name) for name in (
        "numpy","pandas","scipy","scikit-learn","joblib","matplotlib","sqlalchemy","asyncpg")}},indent=2)+"\n")
    figures(report)
    sources = [*sorted(OUTPUT.glob("*.md")),*sorted(OUTPUT.glob("*.csv")),OUTPUT / "software.json",*sorted((OUTPUT / "figures").iterdir()),
        *sorted(DOMAIN.glob("south_fork_*_v1.json")),*sorted((DOMAIN / "test_v1").iterdir()),*sorted((DOMAIN / "multiyear_v1").iterdir()),
        *sorted(ML.rglob("*"))]
    sources += [BACKEND / "scripts" / name for name in ("run_south_fork_multiyear.py","package_south_fork_multiyear.py","run_south_fork_ml.py","run_south_fork_test.py","package_south_fork_paper.py","run_south_fork_profile.py")]
    sources += [BACKEND / "scientific_core" / name for name in ("validation.py","monthly_hypothesis.py")]
    sources += [BACKEND / "app/services" / name for name in ("south_fork_profile.py","external_model_bundle.py")]
    sources += [BACKEND / "requirements-paper.txt", DOMAIN.parent / "docs/FUNCTIONAL_TWIN_DELIVERY_5.md"]
    sources += sorted((DOMAIN.parent.parent / "agro-digital-twin-st/src").rglob("*.py"))
    files = sorted({p for p in sources if p.is_file() and "__pycache__" not in p.parts})
    repo = DOMAIN.parent.parent
    archive_hashes = {str(p.relative_to(repo)):sha256(p) for p in files}
    with ZipFile(OUTPUT / "paper-package.zip","w",compression=ZIP_DEFLATED) as archive:
        for p in files:
            info = ZipInfo(str(p.relative_to(repo)),date_time=(2026,10,6,0,0,0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info,p.read_bytes())
        info = ZipInfo("archive-manifest.json",date_time=(2026,10,6,0,0,0))
        info.compress_type = ZIP_DEFLATED
        archive.writestr(info,json.dumps({"sha256":archive_hashes},indent=2))
    artifacts = [p for p in sorted(OUTPUT.rglob("*")) if p.is_file() and p.name != "artifact-manifest.json"]
    (OUTPUT / "artifact-manifest.json").write_text(json.dumps({"schema_version":"south-fork-paper/v1",
        "test_report_sha256":sha256(REPORT),"hypothesis_status":report["primary"]["hypothesis_status"],
        "sha256":{str(p.relative_to(OUTPUT)):sha256(p) for p in artifacts}},indent=2)+"\n")
    return report, artifacts


async def register(report, artifacts):
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None,"localhost","127.0.0.1","::1"}:
        raise ValueError("Use existing pglocal digitaltwin")
    provenance = {"test_report_sha256":sha256(REPORT),"test_report_reference":"research_domain/south_fork_test_delivery_4_v1.json",
        "test_dataset_id":"sf-test-v1-monthly","hypothesis_status":report["primary"]["hypothesis_status"],"fit_on_test":False,
        "scope":"Paper draft and reproducibility evidence; no new hypothesis test"}
    async with AsyncSessionLocal() as db:
        dataset = await db.get(Dataset,"sf-paper-v1")
        if dataset is None:
            db.add(Dataset(id="sf-paper-v1",provider="LOCAL_RESEARCH",dataset_name="South Fork paper and functional twin evidence v1",version="1",
                variable="paper_reproducibility",unit="m3/s",temporal_resolution="MONTHLY",spatial_support="USGS 05451210 / South Fork",
                coverage_start=date(2021,1,1),coverage_end=date(2025,12,31),source_reference=str(OUTPUT),evidence_type="DERIVED",metadata_json=provenance))
            await db.flush()
        for path in [*artifacts,OUTPUT / "artifact-manifest.json",REPORT]:
            identifier = str(uuid5(NAMESPACE_URL,f"sf-paper-v1/{path.relative_to(DOMAIN)}"))
            artifact = await db.get(DatasetArtifact,identifier)
            if artifact is None:
                artifact = DatasetArtifact(id=identifier,dataset_id="sf-paper-v1",artifact_kind="DERIVED")
                db.add(artifact)
            artifact.storage_path = str(path)
            artifact.checksum_sha256 = sha256(path)
            artifact.byte_size = path.stat().st_size
            artifact.content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            artifact.metadata_json = provenance
        for arm in ("c","d"):
            model = await db.get(ExternalModel,f"sf-ml-v1-{arm}")
            if model is None:
                raise ValueError("Register frozen C/D bundles before paper")
            model.provenance = {**(model.provenance or {}),"reserved_test_evaluation":provenance}
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--register",action="store_true")
    args = parser.parse_args()
    report, artifacts = package()
    if args.register:
        asyncio.run(register(report,artifacts))
    print(json.dumps({"package":str(OUTPUT / "paper-package.zip"),"artifacts":len(artifacts),"hypothesis_status":report["primary"]["hypothesis_status"]}))

#!/usr/bin/env python3
"""Freeze, fit and register monthly development bundles in existing pglocal."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
LAB = ROOT.parent / "agro-digital-twin-st"
sys.path.insert(0, str(BACKEND))

import numpy as np
import pandas as pd
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.external_model import ExternalModel
from app.models.observation import Dataset, DatasetArtifact
from app.services.external_model_bundle import ExternalModelBundleAdapter
from scientific_core import ValidationEngine
sys.path.insert(0, str(LAB))
from src.core.experiments.monthly_residual import prepare_arm, run_experiment
from src.core.inference.bundle import ModelBundle

PROTOCOL = ROOT / "research_domain/south_fork_ml_protocol_v1.json"
INPUT = ROOT / "research_domain/multiyear_v1/monthly-ab.csv"
OUTPUT = LAB / "artifacts/south_fork_monthly_residual_v1"
REPORT = ROOT / "research_domain/south_fork_ml_delivery_3_v1.json"
DATASET_ID = "sf-ml-v1-development"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


async def run():
    url = make_url(settings.DATABASE_URL)
    if url.get_backend_name() != "postgresql" or url.database != "digitaltwin" or url.host not in {None, "localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use existing pglocal digitaltwin")
    protocol = json.loads(PROTOCOL.read_text())
    if digest(INPUT) != protocol["input_csv_sha256"] or digest(ROOT / "research_domain/south_fork_multiyear_protocol_v1.json") != protocol["parent_protocol_sha256"]:
        raise ValueError("Frozen parent protocol or development dataset changed")
    frame = pd.read_csv(INPUT, dtype={"station_id": str})
    schema = json.loads((INPUT.parent / "schema.json").read_text())
    provenance = {"protocol_sha256": digest(PROTOCOL), "input_csv_sha256": digest(INPUT),
        "parent_dataset_id": protocol["dataset_id"], "reference_status": protocol["reference_status"],
        "test_accessed": False, "hypothesis_status": "NOT_EVALUATED"}
    async with AsyncSessionLocal() as db:
        parent = await db.get(Dataset, protocol["dataset_id"])
        if parent is None or not any(a.checksum_sha256 == digest(INPUT) and a.artifact_kind == "NORMALIZED" for a in parent.artifacts):
            raise ValueError("Input must already be registered in pglocal")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        frozen = OUTPUT / "protocol.json"
        receipt_path = OUTPUT / "freeze-receipt.json"
        implementation = {str(p.relative_to(ROOT.parent)): digest(p) for p in (
            Path(__file__), LAB / "src/core/experiments/monthly_residual.py",
            LAB / "src/core/features/preprocessor.py", LAB / "src/core/inference/bundle.py",
            LAB / "src/core/training/residual.py")}
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if receipt["protocol_sha256"] != digest(PROTOCOL) or receipt["implementation_sha256"] != implementation or digest(frozen) != digest(PROTOCOL):
                raise ValueError("Frozen experiment changed: use a new experiment id")
        else:
            if any((OUTPUT / name).exists() for name in ("C", "D", "selection.json")):
                raise ValueError("Cannot freeze an experiment after model artifacts exist")
            shutil.copy2(PROTOCOL, frozen)
            write_json(receipt_path, {**provenance, "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                "implementation_sha256": implementation, "stage": "BEFORE_ANY_MODEL_FIT"})
        manifest_path = OUTPUT / "artifact-manifest.json"
        if manifest_path.exists():
            old = json.loads(manifest_path.read_text())
            if any(digest(OUTPUT / name) != checksum for name, checksum in old["sha256"].items()):
                raise ValueError("Frozen artifacts changed")
            selection = json.loads((OUTPUT / "selection.json").read_text())
            print("REUSE frozen C/D weights", flush=True)
        else:
            if (OUTPUT / "selection.json").exists() or (OUTPUT / "C").exists() or (OUTPUT / "D").exists():
                raise ValueError("Incomplete fit requires investigation; do not silently retrain")
            selection = run_experiment(frame, protocol, schema["units"], OUTPUT, {
                "is_synthetic_training_data": False, "dataset_version": "sf-multi-v1-monthly-ab",
                "dataset_id": protocol["dataset_id"], "origin": "USGS observed Q; modelled SWAT+/FSPM and gridMET inputs",
                "source_kind": "observed_target_modelled_predictors", "period": "2013-01/2020-12",
                "artifact_classification": "OBSERVATIONAL_DEVELOPMENT_ARTIFACT",
                "deployment_status": "development_only_pending_reserved_test",
                "experiment_status": "TRAIN_ONLY_FIT_VALIDATION_SELECTION_TEST_RESERVED",
                "limitations": protocol["limitations"], "aggregation_rules": schema["aggregation"]})
            print("FITTED six identical candidates per arm", flush=True)
        predictions = pd.read_csv(OUTPUT / "development-predictions.csv", dtype={"station_id": str})
        metrics = {}
        for (partition, series), rows in predictions.groupby(["partition", "series"]):
            expected = 60 if partition == "TRAIN" else 36
            if partition not in {"TRAIN", "VALIDATION"} or len(rows) != expected or rows.month.duplicated().any():
                raise ValueError("Invalid development prediction support")
            metrics[f"{partition}_{series}"] = ValidationEngine.evaluate(rows.observed_streamflow_m3s, rows.predicted_streamflow_m3s)
        inference = {}
        adapters = {}
        for arm in ("C", "D"):
            work, features = prepare_arm(frame, protocol, arm)
            adapter = ExternalModelBundleAdapter(OUTPUT / arm).load()
            bundle = ModelBundle.load(str(OUTPUT / arm))
            payloads = work[features].to_dict("records")
            backend_q = np.array([adapter.predict(payload)["value"] for payload in payloads])
            lab_q = np.array(bundle.predict(payloads)["values"])
            expected_q = predictions[predictions.series == arm].sort_values("month").predicted_streamflow_m3s.to_numpy()
            if not np.allclose(backend_q, expected_q, rtol=0, atol=1e-10) or not np.allclose(lab_q, expected_q, rtol=0, atol=1e-10):
                raise ValueError("Saved bundle inference differs between training, laboratory and backend")
            info = adapter.validate_bundle()
            inference[arm] = {"months": len(payloads), "max_absolute_error_m3s": float(max(np.max(abs(backend_q - expected_q)), np.max(abs(lab_q - expected_q)))), "status": "MATCHED", "bundle_sha256": info["checksum"]}
            adapters[arm] = info
        report = {"schema_version": "south-fork-ml-delivery-3/v1", **provenance, **selection,
            "dataset_id": DATASET_ID, "development_metrics": metrics, "inference_audit": inference,
            "freeze_receipt": json.loads(receipt_path.read_text()),
            "interpretation": "TRAIN in-sample; VALIDATION previously explored development; no H1 conclusion",
            "metric_convention": "Canonical scientific_core.ValidationEngine; PBIAS simulated minus observed; KGE variability is CV ratio",
            "external_model_ids": {"C": "sf-ml-v1-c", "D": "sf-ml-v1-d"},
            "artifact_directory": str(OUTPUT.relative_to(ROOT.parent))}
        # Portable paths in the versioned report; database storage paths remain absolute.
        for arm in ("C", "D"):
            report["selection"][arm]["bundle"] = str((OUTPUT / arm).relative_to(ROOT.parent))
        write_json(OUTPUT / "development-report.json", report)
        if not manifest_path.exists():
            write_json(manifest_path, {**provenance, "sha256": {str(p.relative_to(OUTPUT)): digest(p)
                for p in sorted(OUTPUT.rglob("*")) if p.is_file() and p != manifest_path}})
        report["artifacts_sha256"] = json.loads(manifest_path.read_text())["sha256"]
        write_json(REPORT, report)
        dataset = await db.get(Dataset, DATASET_ID)
        if dataset is None:
            dataset = Dataset(id=DATASET_ID, provider="LOCAL_RESEARCH", dataset_name="South Fork monthly residual C/D development v1",
                version="1", variable="monthly_outlet_Q_predictions", unit="m3/s", temporal_resolution="MONTHLY",
                spatial_support="USGS 05451210 / South Fork", coverage_start=date(2013, 1, 1), coverage_end=date(2020, 12, 31),
                source_reference=str(OUTPUT), evidence_type="DERIVED", quality_control={"inference_audit": inference}, metadata_json=provenance)
            db.add(dataset)
            await db.flush()
        for arm, info in adapters.items():
            identifier = f"sf-ml-v1-{arm.lower()}"
            model = await db.get(ExternalModel, identifier)
            if model is not None and model.checksum != info["checksum"]:
                raise ValueError("Registered model checksum changed")
            if model is None:
                db.add(ExternalModel(id=identifier, name=f"South Fork monthly residual {arm} v1", target=protocol["target"],
                    framework=info["framework"], artifact_path=str(OUTPUT / arm), version="sf-ml-v1",
                    feature_schema=ExternalModelBundleAdapter(OUTPUT / arm).read_feature_schema(), metrics=info["metrics"], checksum=info["checksum"],
                    bundle_contract_version=info["bundle_contract_version"], learning_mode="residual", training_data_type="OBSERVED_TARGET_MODELLED_FEATURES",
                    training_dataset_version=protocol["dataset_id"], status="VALIDATED", provenance={**provenance,
                        "validation_scope": "Bundle contract and development inference only; TEST/H1 not evaluated", "selection": report["selection"][arm]}))
        for index, path in enumerate(sorted(p for p in OUTPUT.rglob("*") if p.is_file())):
            identifier = f"sf-ml-v1-artifact-{index:02d}"
            artifact = await db.get(DatasetArtifact, identifier)
            if artifact is not None and (artifact.storage_path != str(path) or artifact.checksum_sha256 != digest(path)):
                raise ValueError("Registered artifact changed")
            if artifact is None:
                db.add(DatasetArtifact(id=identifier, dataset_id=DATASET_ID, artifact_kind="NORMALIZED" if path.suffix == ".csv" else "DERIVED",
                    storage_path=str(path), checksum_sha256=digest(path), byte_size=path.stat().st_size,
                    content_type={".json": "application/json", ".csv": "text/csv"}.get(path.suffix, "application/octet-stream"), metadata_json=provenance))
        await db.commit()
        print(json.dumps({"selected": report["selection"], "validation_rmse": {k: v["rmse"]["value"] for k,v in metrics.items() if k.startswith("VALIDATION")}, "registered_dataset": DATASET_ID}), flush=True)


async def main():
    try:
        await run()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

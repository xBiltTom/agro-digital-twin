"""Safe, metadata-first registration of small MVP data artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import Dataset, DatasetArtifact
from app.schemas.observation import DatasetArtifactRegister


def _safe_artifact_path(root: str, requested_path: str) -> Path:
    root_path = Path(root).resolve()
    artifact = Path(requested_path).resolve()
    try:
        artifact.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("artifact_path must be located below DATA_ARTIFACT_ROOT") from exc
    if not artifact.is_file():
        raise ValueError("artifact_path does not point to a readable file")
    return artifact


async def register_dataset_artifact(db: AsyncSession, payload: DatasetArtifactRegister, *, root: str) -> Dataset:
    path = _safe_artifact_path(root, payload.artifact_path)
    raw = path.read_bytes()
    dataset = Dataset(
        provider=payload.provider, dataset_name=payload.dataset_name, version=payload.version,
        variable=payload.variable, unit=payload.unit, temporal_resolution=payload.temporal_resolution,
        spatial_support=payload.spatial_support, coverage_start=payload.coverage_start,
        coverage_end=payload.coverage_end, source_reference=payload.source_reference, license=payload.license,
        evidence_type=payload.evidence_type, quality_control=payload.quality_control,
        metadata_json=payload.metadata_json,
    )
    db.add(dataset)
    await db.flush()
    db.add(DatasetArtifact(
        dataset_id=dataset.id, artifact_kind=payload.artifact_kind, storage_path=str(path),
        checksum_sha256=hashlib.sha256(raw).hexdigest(), content_type=payload.content_type,
        byte_size=len(raw), metadata_json={"registered_by": "operator", **payload.metadata_json},
    ))
    await db.commit()
    await db.refresh(dataset)
    return dataset

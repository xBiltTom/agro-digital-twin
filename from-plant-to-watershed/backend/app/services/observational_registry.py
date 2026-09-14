"""Persistence boundary for raw, normalized, and derived observational lineage."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import Dataset, DatasetArtifact, StreamflowObservation
from app.services.usgs_streamflow import PARSER_VERSION, USGS_DAILY_VALUES_REFERENCE, QualityReport, StreamflowRecord


async def register_usgs_streamflow(
    db: AsyncSession, station_id: str, source_url: str, artifact_path: Path, checksum: str,
    records: list[StreamflowRecord], qc: QualityReport,
) -> Dataset:
    """Persist an OBSERVED USGS dataset plus its immutable raw-artifact reference."""
    now = datetime.now(timezone.utc)
    dataset = Dataset(
        provider="USGS", dataset_name="USGS Daily Values", version="daily-values-json",
        variable="streamflow", unit="m3/s", temporal_resolution="daily",
        spatial_support=f"USGS streamgage {station_id}", coverage_start=(records[0].observed_on if records else None),
        coverage_end=(records[-1].observed_on if records else None), source_reference=source_url,
        license="USGS public data; see source reference", evidence_type="OBSERVED",
        quality_control=qc.as_dict(), metadata_json={"parser_version": PARSER_VERSION, "documentation": USGS_DAILY_VALUES_REFERENCE},
        retrieved_at=now,
    )
    db.add(dataset)
    await db.flush()
    artifact = DatasetArtifact(
        dataset_id=dataset.id, artifact_kind="RAW", storage_path=str(artifact_path), checksum_sha256=checksum,
        content_type="application/json", byte_size=artifact_path.stat().st_size, retrieved_at=now,
        metadata_json={"station_id": station_id, "parser_version": PARSER_VERSION},
    )
    db.add(artifact)
    await db.flush()
    db.add_all([
        StreamflowObservation(
            dataset_id=dataset.id, artifact_id=artifact.id, station_id=station_id, observed_on=row.observed_on,
            value_m3s=row.value_m3s, original_value=row.original_value, original_unit=row.original_unit,
            quality_status=row.quality_status, source=source_url,
        ) for row in records
    ])
    await db.commit()
    # ``DatasetResponse.normalized_artifact_count`` is derived from this
    # relationship.  Load it while the async session is active so FastAPI never
    # tries a lazy database query during synchronous response serialization.
    await db.refresh(dataset, attribute_names=["artifacts"])
    return dataset

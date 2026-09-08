"""Persistent metadata and normalized observations for externally sourced datasets."""

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, utc_now


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(100))
    variable: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    temporal_resolution: Mapped[str] = mapped_column(String(40), nullable=False)
    spatial_support: Mapped[str] = mapped_column(String(160), nullable=False)
    coverage_start: Mapped[Optional[date]] = mapped_column(Date)
    coverage_end: Mapped[Optional[date]] = mapped_column(Date)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[Optional[str]] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_control: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    artifacts: Mapped[list["DatasetArtifact"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def normalized_artifact_count(self) -> int:
        return sum(artifact.artifact_kind == "NORMALIZED" for artifact in self.artifacts)


class DatasetArtifact(Base, TimestampMixin):
    __tablename__ = "dataset_artifacts"

    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    artifact_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # RAW, NORMALIZED, DERIVED
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    dataset: Mapped[Dataset] = relationship(back_populates="artifacts")


class StreamflowObservation(Base, TimestampMixin):
    __tablename__ = "streamflow_observations"

    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("dataset_artifacts.id", ondelete="SET NULL"))
    station_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_m3s: Mapped[Optional[float]] = mapped_column(Float)
    original_value: Mapped[Optional[float]] = mapped_column(Float)
    original_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    variable: Mapped[str] = mapped_column(String(80), nullable=False, default="streamflow")
    quality_status: Mapped[Optional[str]] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(Text, nullable=False)

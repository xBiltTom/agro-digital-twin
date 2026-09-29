"""Operational playback persistence in the application's SQLAlchemy database."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import PlaybackFrame
from app.schemas.playback import PlaybackRecord, SCHEMA_VERSION


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _period_start(day: date, resolution: str) -> date:
    if resolution == "MONTHLY":
        return day.replace(day=1)
    if resolution == "ANNUAL":
        return day.replace(month=1, day=1)
    return day


class PlaybackDatabaseStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write(self, simulation_id: str, records: Iterable[PlaybackRecord], *, provenance: dict,
                    limitations: list[str] | None = None, idempotent: bool = False) -> dict:
        """Insert dated frames in the caller's transaction; reject conflicting imports."""
        existing = {}
        if idempotent:
            rows = await self.session.execute(select(PlaybackFrame.date, PlaybackFrame.resolution, PlaybackFrame.sha256)
                                              .where(PlaybackFrame.simulation_id == simulation_id))
            existing = {(day, resolution): digest for day, resolution, digest in rows}
        count = 0
        first_date = last_date = resolution = None
        variables: dict[str, dict] = {}
        batch: list[dict] = []
        for record in records:
            if record.simulation_id != simulation_id:
                raise ValueError("Playback record belongs to another simulation")
            if resolution is None:
                resolution = record.resolution
            elif record.resolution != resolution:
                raise ValueError("A playback series must have one temporal resolution")
            day = record.date.isoformat()
            if last_date is not None and day <= last_date:
                raise ValueError("Playback dates must be unique and strictly increasing")
            payload = record.model_dump(mode="json", exclude_none=False)
            digest = _digest(payload)
            key = record.date, record.resolution
            if key in existing:
                if existing[key] != digest:
                    raise ValueError(f"Existing playback frame differs for {simulation_id} {day}")
            else:
                batch.append({"simulation_id": simulation_id, "resolution": record.resolution,
                              "date": record.date, "payload": payload, "sha256": digest})
            groups = [(name, getattr(record, name)) for name in ("weather", "field", "hydrology")]
            groups.extend(("plant_samples", sample.variables) for sample in record.plant_samples)
            groups.extend(("hru_results", hru.variables) for hru in record.hru_results)
            groups.extend(("channel_results", channel.variables) for channel in record.channel_results)
            for group_name, group in groups:
                for name, state in group.items():
                    entry = variables.setdefault(f"{group_name}.{name}", {"unit": state.unit, "evidence": [], "available": False})
                    if entry["unit"] != state.unit:
                        raise ValueError(f"Inconsistent units for {group_name}.{name}")
                    if state.evidence.value not in entry["evidence"]:
                        entry["evidence"].append(state.evidence.value)
                    entry["available"] |= state.availability == "AVAILABLE"
            if len(batch) >= 16:
                await self.session.execute(PlaybackFrame.__table__.insert(), batch)
                batch.clear()
            count += 1
            first_date = first_date or day
            last_date = day
        if batch:
            await self.session.execute(PlaybackFrame.__table__.insert(), batch)
        if not count:
            raise ValueError("A playback series requires at least one dated record")
        return {"schema_version": SCHEMA_VERSION, "storage": "POSTGRESQL_JSONB",
                "record_count": count, "first_date": first_date, "last_date": last_date,
                "resolution": resolution, "variables": variables,
                "provenance": provenance, "limitations": limitations or []}

    async def page(self, simulation_id: str, resolution: str, *, start: date | None = None,
                   end: date | None = None, on: date | None = None,
                   offset: int = 0, limit: int = 100) -> tuple[int, list[PlaybackRecord]]:
        conditions = [PlaybackFrame.simulation_id == simulation_id, PlaybackFrame.resolution == resolution]
        if on is not None:
            conditions.append(PlaybackFrame.date == _period_start(on, resolution))
        if start is not None:
            conditions.append(PlaybackFrame.date >= _period_start(start, resolution))
        if end is not None:
            conditions.append(PlaybackFrame.date <= _period_start(end, resolution))
        total = await self.session.scalar(select(func.count()).select_from(PlaybackFrame).where(*conditions)) or 0
        rows = (await self.session.execute(select(PlaybackFrame.payload, PlaybackFrame.sha256)
                                           .where(*conditions).order_by(PlaybackFrame.date)
                                           .limit(limit).offset(offset))).all()
        return total, [self._validate(payload, digest, simulation_id, resolution) for payload, digest in rows]

    async def count(self, simulation_id: str, resolution: str) -> int:
        return await self.session.scalar(select(func.count()).select_from(PlaybackFrame)
                                         .where(PlaybackFrame.simulation_id == simulation_id,
                                                PlaybackFrame.resolution == resolution)) or 0

    async def records(self, simulation_id: str, resolution: str) -> list[PlaybackRecord]:
        rows = (await self.session.execute(select(PlaybackFrame.payload, PlaybackFrame.sha256)
                                           .where(PlaybackFrame.simulation_id == simulation_id,
                                                  PlaybackFrame.resolution == resolution)
                                           .order_by(PlaybackFrame.date))).all()
        return [self._validate(payload, digest, simulation_id, resolution) for payload, digest in rows]

    @staticmethod
    def _validate(payload: dict, digest: str, simulation_id: str, resolution: str) -> PlaybackRecord:
        if _digest(payload) != digest:
            raise ValueError("Playback frame checksum mismatch")
        record = PlaybackRecord.model_validate(payload)
        if record.simulation_id != simulation_id or record.resolution != resolution:
            raise ValueError("Playback frame identity mismatch")
        return record

"""Indexed, versioned playback sidecars; PostgreSQL stores only their manifest."""

from __future__ import annotations

from datetime import date
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Iterable
from uuid import uuid4

from app.core.config import settings
from app.schemas.playback import PlaybackRecord, SCHEMA_VERSION


_SAFE_RUN_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")


class PlaybackArtifactStore:
    _verified: dict[tuple[str, str], tuple[int, int, int, int, int]] = {}
    _verification_lock = threading.Lock()

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(settings.DATA_ARTIFACT_ROOT) / "playback" / "v1").resolve()

    def _path(self, simulation_id: str) -> Path:
        if not _SAFE_RUN_ID.fullmatch(simulation_id):
            raise ValueError("Invalid simulation id for playback artifact")
        return self.root / f"{simulation_id}.sqlite"

    def _manifest_path(self, simulation_id: str, manifest: dict) -> Path:
        self._path(simulation_id)  # validates the simulation identifier
        name = manifest.get("artifact_file", "")
        if not isinstance(name, str) or not re.fullmatch(rf"{re.escape(simulation_id)}(?:\.[0-9a-f]{{32}})?\.sqlite", name):
            raise ValueError("Playback manifest does not match this simulation")
        return self.root / name

    @staticmethod
    def _signature(path: Path) -> tuple[int, int, int, int, int]:
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    def _verify_manifest_hash(self, path: Path, manifest: dict) -> tuple[int, int, int, int, int]:
        expected = manifest.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Playback manifest has no valid SHA-256 checksum")
        signature = self._signature(path)
        key = str(path), expected
        with self._verification_lock:
            if self._verified.get(key) == signature:
                return signature
        if self._sha256(path) != expected or self._signature(path) != signature:
            raise ValueError("Playback artifact SHA-256 mismatch")
        with self._verification_lock:
            self._verified[key] = signature
        return signature

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def write(self, simulation_id: str, records: Iterable[PlaybackRecord], *,
              provenance: dict, limitations: list[str] | None = None) -> dict:
        """Atomically publish a read-only SQLite series with a date index."""
        self._path(simulation_id)
        path = self.root / f"{simulation_id}.{uuid4().hex}.sqlite"
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        count = 0
        first_date = last_date = resolution = None
        variables: dict[str, dict] = {}
        try:
            with sqlite3.connect(temporary) as connection:
                connection.execute("CREATE TABLE frames (date TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL)")
                for record in records:
                    if record.simulation_id != simulation_id:
                        raise ValueError("Playback record belongs to another simulation")
                    if resolution is None:
                        resolution = record.resolution
                    elif record.resolution != resolution:
                        raise ValueError("A playback artifact must have one effective temporal resolution")
                    day = record.date.isoformat()
                    if last_date is not None and day <= last_date:
                        raise ValueError("Playback dates must be unique and strictly increasing")
                    payload = record.model_dump_json(exclude_none=False)
                    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                    connection.execute("INSERT INTO frames VALUES (?, ?, ?)", (day, payload, digest))
                    groups = [(name, getattr(record, name)) for name in ("weather", "field", "hydrology")]
                    groups.extend(("plant_samples", sample.variables) for sample in record.plant_samples)
                    groups.extend(("hru_results", hru.variables) for hru in record.hru_results)
                    for group_name, group in groups:
                        for name, state in group.items():
                            entry = variables.setdefault(f"{group_name}.{name}", {"unit": state.unit, "evidence": [], "available": False})
                            if entry["unit"] != state.unit:
                                raise ValueError(f"Inconsistent units for {group_name}.{name}")
                            if state.evidence.value not in entry["evidence"]:
                                entry["evidence"].append(state.evidence.value)
                            entry["available"] |= state.availability == "AVAILABLE"
                    count += 1
                    first_date = first_date or day
                    last_date = day
            if count == 0:
                raise ValueError("A playback artifact requires at least one dated record")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "schema_version": SCHEMA_VERSION, "artifact_file": path.name,
            "sha256": self._sha256(path), "record_count": count,
            "first_date": first_date, "last_date": last_date,
            "resolution": resolution, "variables": variables,
            "provenance": provenance, "limitations": limitations or [],
        }

    def page(self, simulation_id: str, manifest: dict, *, start: date | None = None,
             end: date | None = None, on: date | None = None,
             offset: int = 0, limit: int = 100) -> tuple[int, list[PlaybackRecord]]:
        path = self._manifest_path(simulation_id, manifest)
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Playback manifest does not match this simulation and schema")
        if not path.is_file():
            raise FileNotFoundError(path)
        signature = self._verify_manifest_hash(path, manifest)
        resolution = manifest.get("resolution")
        if resolution not in {"DAILY", "MONTHLY", "ANNUAL"}:
            raise ValueError("Playback manifest has no supported temporal resolution")
        def period_start(day: date) -> date:
            if resolution == "MONTHLY":
                return day.replace(day=1)
            if resolution == "ANNUAL":
                return day.replace(month=1, day=1)
            return day
        conditions: list[str] = []
        parameters: list[str | int] = []
        if on is not None:
            conditions.append("date = ?")
            parameters.append(period_start(on).isoformat())
        if start is not None:
            conditions.append("date >= ?")
            parameters.append(period_start(start).isoformat())
        if end is not None:
            conditions.append("date <= ?")
            parameters.append(period_start(end).isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            total = connection.execute("SELECT COUNT(*) FROM frames" + where, parameters).fetchone()[0]
            rows = connection.execute(
                "SELECT payload, sha256 FROM frames" + where + " ORDER BY date LIMIT ? OFFSET ?",
                [*parameters, limit, offset],
            ).fetchall()
        if self._signature(path) != signature:
            raise ValueError("Playback artifact changed during query")
        records = []
        for payload, digest in rows:
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest:
                raise ValueError("Playback frame checksum mismatch")
            records.append(PlaybackRecord.model_validate_json(payload))
        return total, records

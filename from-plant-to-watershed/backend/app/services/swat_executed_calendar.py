"""Date-preserving crop calendars extracted from SWAT+ ``mgt_out.txt``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any, Iterable
from pathlib import Path


@dataclass(frozen=True)
class CropCalendarGroup:
    calendar_id: str
    crop: str
    planting_date: str
    harvest_date: str
    hru_ids: tuple[int, ...]
    spatial_weight: float


@dataclass(frozen=True)
class SwatExecutedCropCalendar:
    crop: str
    start_date: str
    end_date: str
    groups: tuple[CropCalendarGroup, ...]
    hru_calendar: dict[int, str | tuple[str, ...]]
    event_count: int

    @staticmethod
    def hru_spatial_weights(project: str | Path, crop_fraction_by_hru: dict[int, float] | None = None) -> dict[int, float]:
        """Use SWAT+ HRU areas, optionally multiplied by source CDL fractions."""
        root = Path(project)
        if (root / "TxtInOut" / "hru.con").is_file():
            root = root / "TxtInOut"
        path = root / "hru.con"
        if not path.is_file():
            raise ValueError("hru.con is required to weight executed crop-calendar groups")
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        if len(lines) < 3:
            raise ValueError("hru.con does not contain HRU area rows")
        header = [token.lower() for token in lines[1].split()]
        try:
            id_index, area_index = header.index("id"), header.index("area")
        except ValueError:
            raise ValueError("hru.con must expose id and area fields") from None
        weights: dict[int, float] = {}
        for line_number, raw in enumerate(lines[2:], 3):
            values = raw.split()
            if len(values) <= max(id_index, area_index):
                continue
            try:
                hru_id = int(values[id_index])
                area = float(values[area_index])
            except ValueError:
                raise ValueError(f"Invalid HRU area in hru.con:{line_number}") from None
            if crop_fraction_by_hru is not None and hru_id not in crop_fraction_by_hru:
                continue
            fraction = (crop_fraction_by_hru or {}).get(hru_id, 1.0)
            if not math.isfinite(area) or area <= 0 or not math.isfinite(fraction) or not 0 < fraction <= 1:
                raise ValueError(f"Invalid area/crop fraction for HRU {hru_id}")
            weights[hru_id] = area * fraction
        if crop_fraction_by_hru is not None and set(crop_fraction_by_hru) - set(weights):
            raise ValueError(f"hru.con does not expose crop HRUs {sorted(set(crop_fraction_by_hru) - set(weights))}")
        return weights

    @classmethod
    def from_events(
        cls,
        events: Iterable[dict[str, Any]],
        *,
        crop: str,
        start_date: date,
        end_date: date,
        hru_weights: dict[int, float] | None = None,
    ) -> "SwatExecutedCropCalendar":
        if end_date < start_date:
            raise ValueError("calendar interval end precedes start")
        rows = [event for event in events if str(event.get("crop", "")).lower() == crop.lower()
                and start_date.isoformat() <= str(event.get("date", "")) <= end_date.isoformat()]
        if not rows:
            raise ValueError(f"SWAT+ emitted no dated management events for {crop!r} in the requested interval")
        by_hru: dict[int, dict[str, list[str]]] = {}
        for event in rows:
            try:
                hru_id = int(event["hru_id"])
                event_date = date.fromisoformat(str(event["date"])).isoformat()
            except (KeyError, TypeError, ValueError):
                raise ValueError("SWAT+ management event is missing a valid HRU id or date") from None
            operation = str(event.get("operation", "")).strip().upper()
            target = "plant" if operation in {"PLANT", "PLNT"} else "harvest" if (
                operation.startswith(("HARV", "KILL")) or operation in {"HARV/KILL", "HVKL"}
            ) else None
            if target is None:
                continue
            by_hru.setdefault(hru_id, {"plant": [], "harvest": []})[target].append(event_date)
        grouped: dict[tuple[str, str], list[int]] = {}
        hru_calendar: dict[int, str | tuple[str, ...]] = {}
        for hru_id, events_by_type in by_hru.items():
            plants = sorted(set(events_by_type["plant"]))
            harvests = sorted(set(events_by_type["harvest"]))
            if not plants or len(plants) != len(harvests):
                raise ValueError(
                    f"HRU {hru_id} has {len(plants)} maize plant and {len(harvests)} harvest/kill events; "
                    "each planting requires a complete harvest/kill pair"
                )
            if hru_weights is None:
                weight = 1.0
            else:
                weight = float(hru_weights.get(hru_id, 0.0))
                if not math.isfinite(weight) or weight <= 0:
                    raise ValueError(f"HRU {hru_id} has no positive finite spatial weight")
            for index, (planting, harvest) in enumerate(zip(plants, harvests, strict=True)):
                if planting > harvest or (index and harvests[index - 1] >= planting):
                    raise ValueError(f"HRU {hru_id} has reversed or overlapping crop seasons")
                grouped.setdefault((planting, harvest), []).append(hru_id)

        if hru_weights is not None and set(by_hru) - set(hru_weights):
            raise ValueError(f"SWAT+ crop event HRUs lack spatial weights: {sorted(set(by_hru) - set(hru_weights))}")

        groups: list[CropCalendarGroup] = []
        for index, ((planting, harvest), hru_ids) in enumerate(sorted(grouped.items()), 1):
            calendar_id = f"{crop}-{planting}-to-{harvest}-{index:02d}"
            ids = tuple(sorted(hru_ids))
            weight = sum(float(hru_weights[hru_id]) if hru_weights is not None else 1.0 for hru_id in ids)
            group = CropCalendarGroup(calendar_id, crop, planting, harvest, ids, weight)
            groups.append(group)
            for hru_id in ids:
                existing = hru_calendar.get(hru_id)
                hru_calendar[hru_id] = calendar_id if existing is None else (
                    (existing, calendar_id) if isinstance(existing, str) else (*existing, calendar_id))
        if not groups:
            raise ValueError(f"SWAT+ emitted no PLANT and HARV/KILL pair for {crop!r}")
        return cls(crop, start_date.isoformat(), end_date.isoformat(), tuple(groups), hru_calendar, len(rows))

    def group_for_hru(self, hru_id: int, on_date: date | None = None) -> CropCalendarGroup:
        groups = [group for group in self.groups if hru_id in group.hru_ids]
        if on_date is not None:
            groups = [group for group in groups if group.planting_date <= on_date.isoformat() <= group.harvest_date]
        if len(groups) != 1:
            raise ValueError(f"HRU {hru_id} requires a date identifying one active crop season")
        return groups[0]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "EXECUTED_SWAT_MANAGEMENT_EVENTS",
            "source_file": "mgt_out.txt",
            "crop": self.crop,
            "requested_period": [self.start_date, self.end_date],
            "event_count": self.event_count,
            "calendar_group_count": len(self.groups),
            "hru_count": len(self.hru_calendar),
            "hru_calendar": {str(hru_id): calendar_id for hru_id, calendar_id in sorted(self.hru_calendar.items())},
            "groups": [
                {"calendar_id": group.calendar_id, "crop": group.crop,
                 "planting_date": group.planting_date, "harvest_date": group.harvest_date,
                 "hru_ids": list(group.hru_ids), "spatial_weight": group.spatial_weight,
                 "spatial_weight_semantics": "SWAT HRU area multiplied by 2019 CDL corn fraction when present; otherwise SWAT HRU area"}
                for group in self.groups
            ],
            "limitation": "Management dates are SWAT+ simulated execution events at daily resolution, not observed field operation dates. FSPM applies the date to the complete day because subdaily operation timing is unavailable.",
        }
